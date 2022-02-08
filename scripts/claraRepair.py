from srcU.Helpers import ConfigFile as CF, Helper as H

import traceback
import glob
from joblib import Parallel, delayed
import time


#region: Results class

class Result:
    def __init__(self, progName):
        self.progName = progName
        self.repair = None
        self.exception = None
        self.success = False
        self.patch_size = 0
        self.overfit = False
        self.structMatch = False
        self.sm = ''
        self.startTime = time.time()
        self.endTime, self.timeTaken = None, None

    def __str__(self):
        # if self.structMatch == False:
        #     self.sm = 'structMismatch'
        # return '{}: {}\t{}\ttime:{}\t patch size:{}\t overfit:{}'.format(self.progName, self.success, self.sm,
        #                                                              self.timeTaken, self.patch_size, self.overfit)
        return '{}: {}\t\ttime:{}\t patch size:{}\t overfit:{}'.format(self.progName, self.success,
                                                                         self.timeTaken, self.patch_size, self.overfit)

    def logEndTime(self):
        self.endTime = time.time()
        self.timeTaken = round(self.endTime - self.startTime, 2)
#endregion

#region: Dump results

def write_results(df_codes_all, results, debug=False):

    labIDs = df_codes_all['labName'].unique()
    df_codes_all['clara_time_taken'] = [res.timeTaken for res in results]
    df_codes_all['clara_exception'] = [res.exception for res in results]
    df_codes_all['repairs'] = [res.repair for res in results]
    df_codes_all['clara_result'] = [int(res.success) for res in results]
    df_codes_all['patch_size'] = [float(res.patch_size) for res in results]

    if not debug:
        for labID in labIDs:
            df_codes = df_codes_all[df_codes_all['labName'] == labID]
            for assignId in df_codes['problem_id'].unique():
                df_codes_ass = df_codes[df_codes['problem_id'] == assignId]
                df_codes_ass.to_excel(CF.path_itsp_result + 'results_clara_{}_{}.xlsx'.format(labID, assignId), encoding = "ISO-8859-1", index=False)

#endregion

#region: Main func of clara repair

def repair_single_cmd(res:Result, fname_c, fname_i, ins, debug):
    # Run Clara
    cmd_list = ['clara', 'repair', '--timeout', str(CF.timeout_clara), fname_c, fname_i, '--ins', str(ins), '--entryfunc', 'main']
    if debug:
        cmd_list += ['--verbose', '1']
    success, outs = H.subprocess_run(cmd_list, blame_str='Clara', timeout=CF.timeout_clara, debug=debug)

    res.success = success
    res.repair = outs
    if 'Relative Patch Size' not in outs:
        res.patch_size = None
    else:
        res.patch_size = outs.split("Relative Patch Size:\n")[-1].replace("\n", "")

def repair_with_multi_reference(row, debug=False, fname_i=None, perc=''):
    progName = row['code_id']
    problemId = row['problem_id']
    codeText_c = []

    res = Result(progName)
    for code in glob.glob(CF.path_clara_cluster_output + perc + '/' + problemId + "/*.c"):
        if code.split('/')[-1].split('.')[0] == progName:
            continue
        codeText_c.append(code)
    structMatch = False
    for code in codeText_c:
        if res.structMatch == True:
            structMatch = True
        if res.success:
            return res
        res = repair_with_single_reference(row, debug=debug, fname_c=code, fname_i=fname_i)
    res.structMatch = structMatch
    return res

def repair_with_single_reference(row, debug=False, fname_c=None, fname_i=None):
    progName = row['code_id']
    codeText_c, codeText_i = row['code_reference'], row['code_buggy']
    allins = []
    for ins_lines, out_lines in row['test_cases']:
        oneins = []
        for ins in ins_lines.split():
            try:
                oneins.append(float(ins))
            except:
                oneins.append(ins)
        allins.append(oneins)
    res = Result(progName)

    # Write files
    if fname_c is None:
        fname_c = '{}/{}_c.c'.format(CF.path_tmp, progName)
        H.write_file(fname_c, codeText_c)

    if fname_i is None:
        fname_i = '{}/{}_i.c'.format(CF.path_tmp, progName)
        H.write_file(fname_i, codeText_i)

    try:
        repair_single_cmd(res, fname_c, fname_i, allins, debug=True)
    # Handle any exceptions
    except Exception as e:
        if "Timeout" in str(e):
            res.exception = "Timeout"
            res.structMatch = True
        else:
            res.exception = str(e).split('\\n')[-2]
            if res.exception != 'clara.repair.StructMismatch':
                res.structMatch = True
        if debug:
            print(traceback.format_exc())

    finally:
        res.logEndTime()
        H.del_file(fname_c)
        H.del_file(fname_i)
    return res

def reproduce_clara(df_codes, debug=False, enableMulti=False, perc=None, jobs=1):
    print('Clara invoked on #{} codes ...'.format(len(df_codes)))

    results = []

    for index in range(0, len(df_codes), jobs):
        df_temp = df_codes.iloc[index : index + jobs]

        code_correct = df_codes[['problem_id', 'code_id', 'code_correct']]
        if enableMulti:
            results_temp = Parallel(n_jobs=jobs)(
                delayed(repair_with_multi_reference)(row, code_correct, debug=debug, perc=perc)
                for i, row in df_temp.iterrows())
        else:
            results_temp = Parallel(n_jobs=jobs)(
                delayed(repair_with_single_reference)(row, debug=debug)
                    for i, row in df_temp.iterrows())

        print(H.joinList(results_temp))
        results += results_temp

    if not enableMulti:
        write_results(df_codes, results)
    print('#Exceptions      = {0[0]}/{0[1]} = {0[2]} %'.format(H.calc_accuracy(df_codes, 'clara_exception', nullCheck=True)))
    print('#Success         = {0[0]}/{0[1]} = {0[2]} %'.format(H.calc_accuracy(df_codes, 'clara_result')))

#endregion

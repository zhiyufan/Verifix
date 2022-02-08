import copy
import os
import sys
import traceback
import glob

import timeout_decorator

from joblib import Parallel, delayed

from srcU.ClaraP import c_parser
from srcU.Helpers import ConfigFile as CF, Helper as H
from srcU.Verifix import Result
from srcU.Verifix.Align import AlignPAA
from srcU.Verifix.CFG import CFG, Concretize
from srcU.Verifix.Process import Preprocessing, Postprocessing
from srcU.Verifix.Repair import Repair
from srcU.Verifix.Verify import Verification

import copy

# region: Verify and repair automata

def verify_repair(res: Result, ppa_li, debug=False):
    '''Repair automata one by one. Select best one and dump it'''
    res.numPPA = len(ppa_li)
    if debug:
        print('#PAAs = {}'.format(res.numPPA))

    # For each PPA
    for index in range(len(ppa_li)):
        if index > 0:   # Only consider the first ppa
            continue
            # break
        ppa = ppa_li[index]
        ppa_old = copy.deepcopy(ppa)

        # VCGen
        numValid_before, numTotal_before = Verification.verify_ppa(ppa, debug=debug)
        # Inits
        res.update(ppa_old, ppa, numValid_before, numTotal_before, numValid_before, numTotal_before)

        if numValid_before != numTotal_before:
            ppa, numValid_after, numTotal_after, exception = Repair.repair(ppa, debug=debug)
            if exception != None:
                res.exception = exception
        else:
            numValid_after = numValid_before
            numTotal_after = numTotal_before

        if numValid_after == numTotal_after:
            res.update(ppa_old, ppa, numValid_before, numTotal_before, numValid_after, numTotal_after)
            break
        # Is it the best automata seen so far? Save it
        res.update(ppa_old, ppa, numValid_before, numTotal_before, numValid_after, numTotal_after)
    return res


# endregion

# region: Main function to align, verify and repair

def parse_cfg(progName, codeText, isPrimed, cfg=None):
    if cfg is None:
        prog = c_parser.CParser().parse_code(codeText)
        cfg = CFG.get_optCFG(prog,isPrimed=isPrimed)
    return cfg


def repair(res, codeText_c, codeText_i, test_cases, progName, debug=False):
    cfgC = parse_cfg(progName, codeText_c, False)
    cfgI = parse_cfg(progName, codeText_i, True)

    # Align and create PAA
    if res.exception == None:
        align_nodes = AlignPAA.gen_alignNodes(res, cfgC, cfgI)

    if res.exception == None:
        ppa_li = AlignPAA.generate_ppaLi(res, cfgC, cfgI, align_nodes, debug=debug)

    if res.exception == None:
        # Align line number
        Preprocessing.insert_dummy_line_ppaLi(ppa_li)

        # Verify and repair
        verify_repair(res, ppa_li, debug=debug)

        # Remove useless line
        Postprocessing.remove_dummy_line_ppa(res.ppa_after)
        Postprocessing.remove_dummy_line_ppa(res.ppa_before)

        # Update result
        res.update_test(test_cases, debug)
    if res.exception != None:
        print(res.exception)

@timeout_decorator.timeout(CF.timeout_verifix)
def repair_single(res: Result, codeText_c, codeText_i, progName, test_cases,
                  cfgC=None, cfgI=None, debug=False):
    try:
        # Fetch CFGs
        if progName == '278279' or \
                progName == '278270' or \
                progName == '277541' or \
                progName == '278271' or \
                progName == '277861':
            return res
        cfgC = parse_cfg(progName, codeText_c, False)
        cfgI = parse_cfg(progName, codeText_i, True)

        # Align and create PAA

        if res.exception == None:
            align_nodes = AlignPAA.gen_alignNodes(res, cfgC, cfgI)

        if res.exception == None:
            ppa_li = AlignPAA.generate_ppaLi(res, cfgC, cfgI, align_nodes, debug=debug)

        if res.exception == None:
            # Align line number
            Preprocessing.insert_dummy_line_ppaLi(ppa_li)

            # Verify and repair
            verify_repair(res, ppa_li, debug=debug)

            # Remove useless line
            Postprocessing.remove_dummy_line_ppa(res.ppa_after)
            Postprocessing.remove_dummy_line_ppa(res.ppa_before)

            # Update result
            res.update_test(test_cases, debug)
    except Exception as e:
        if res.exception != None:
            res.exception += str(e)
        raise (e)

    finally:
        res.make_pickleSafe()
        return res

def repair_with_single_reference(row, printFlag=True, debug=False, cfgC=None, cfgI=None):

    progName = row['code_id']
    codeText_c, codeText_i = row['code_reference'], row['code_buggy']
    test_cases = row['test_cases']
    res = Result.Result(progName)

    try:
        repair_single(res, codeText_c, codeText_i, progName, test_cases,
                      debug=debug, cfgC=cfgC, cfgI=cfgI)

    # Handle any exceptions
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if res.exception != None:
            res.exception += str(exc_value)
        else:
            res.exception = str(exc_value)
        if debug:
            print(traceback.format_exc())
            raise
    except TimeoutError:
        res.exception = 'Timeout'
    # log endtime and print result
    finally:
        res.logEndTime()
        res.make_pickleSafe()
        if printFlag:
            print(res, flush=True)

    return res

def repair_with_multi_reference(row, printFlag=True, debug=False, cfgC=None, cfgI=None, perc=''):

    progName = row['code_id']
    problemId = row['problem_id']
    codeText_c = []

    for code in glob.glob(CF.path_clara_cluster_output + perc + '/' + problemId + "/*.c"):
        if code.split('/')[-1].split('.')[0] == progName:
            continue
        codeText_c.append(open(code).read())

    codeText_i = row['code_buggy']
    test_cases = row['test_cases']

    res = Result.Result(progName)
    try:
        for code in codeText_c:
            if res.is_success():
                break
            res = Result.Result(progName)
            res = repair_single(res, code, codeText_i, progName, test_cases,
                      debug=debug, cfgC=cfgC, cfgI=cfgI)

    # Handle any exceptions
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if res.exception != None:
            res.exception += str(exc_value)
        else:
            res.exception = str(exc_value)
        if debug:
            print(traceback.format_exc())
            raise
    except TimeoutError:
        res.exception = 'Timeout'
    # log endtime and print result
    finally:
        res.logEndTime()
        res.make_pickleSafe()
        if printFlag:
            print(res, flush=True)

    return res

# endregion

# region: Repair df_codes

def reproduce_verifix(df_codes, debug=False, cfgC=None, enableMulti=False, perc='', jobs=1):
    print('Verifix invoked on #{} codes ...'.format(len(df_codes)))

    results = []

    for index in range(0, len(df_codes), jobs):
        df_temp = df_codes.iloc[index: index + jobs]

        if enableMulti:
            results_temp = Parallel(n_jobs=jobs)(
                delayed(repair_with_multi_reference)(row, printFlag=False, debug=debug, cfgC=cfgC,
                                                     perc=perc)
                for i, row in df_temp.iterrows())
        else:
            results_temp = Parallel(n_jobs=jobs)(
                delayed(repair_with_single_reference)(row, printFlag=False, debug=debug, cfgC=cfgC)
                for i, row in df_temp.iterrows())

        # Print/Append results
        print(H.joinList(results_temp))
        results += results_temp

    # Attach results to df_codes
    df_codes['verifix_exception'] = [res.exception for res in results]
    df_codes['verifix_isPartial'] = [res.isPartial for res in results]
    df_codes['verifix_isComplete'] = [res.isComplete for res in results]
    df_codes['verifix_isTest'] = [res.isTest for res in results]

    # Dump Results
    Result.write_results(df_codes, results, debug=debug)

    print('\n', df_codes.groupby('exceptions').size().sort_values(ascending=False), '\n')
    print('#Exceptions         = {0[0]}/{0[1]} = {0[2]} %'.format(
        H.calc_accuracy(df_codes, 'exceptions', nullCheck=True)))
    print('#Partial-Success    = {0[0]}/{0[1]} = {0[2]} %'.format(H.calc_accuracy(df_codes, 'isRepair_partial')))
    print('#Complete-Success   = {0[0]}/{0[1]} = {0[2]} %'.format(H.calc_accuracy(df_codes, 'isRepair_complete')))
    print('#Evaluation-Success = {0[0]}/{0[1]} = {0[2]} %'.format(H.calc_accuracy(df_codes, 'isRepair_evaluate')))

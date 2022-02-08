
from srcU.Helpers import ConfigFile as CF, Helper as H, FetchData

import shutil
import os, traceback
import glob
from joblib import Parallel, delayed
import time
import random
import math


def cluster_single_cmd(correct_path, output_path, ins, debug):
    progs = glob.glob(correct_path+'/*.c')

    cmd_list = ['clara', 'cluster'] + progs + [ '--clusterdir', output_path, '--entryfunc', 'main', '--ins', str(ins)]
    if debug:
        cmd_list += ['--verbose', '1']
    H.subprocess_run(cmd_list, blame_str='Clara', timeout=CF.timeout_clara, debug=debug)

def cluster(lab_ids=None, problem_ids=None, code_id=None, perc=''):
    # Select all Lab folders
    for labName in os.listdir(CF.path_itsp):
        if 'Lab' in labName:

            # Filter lab_id, or all labs?
            if lab_ids is None or len(lab_ids) == 0 or labName in lab_ids:

                # Filter pid, or all assignments?
                for pid in os.listdir(CF.path_itsp + '/' + labName):
                    if problem_ids is None or len(problem_ids) == 0 or int(pid) in problem_ids:
                        cluster_by_assignment(labName, pid, code_id=code_id, perc=perc)


def cluster_by_assignment(labName, pid, code_id=None, perc=''):

    pathProb = FetchData.get_pathProb(labName, pid)
    code_ref = FetchData.get_codeRef(pathProb)

    test_cases = FetchData.read_itsp_testCases(pid)
    correct_path = CF.path_clara_cluster+perc+'/'+pid
    output_path = CF.path_clara_cluster_output+perc+'/'+pid

    code_corrects = []
    if os.path.exists(correct_path):
        shutil.rmtree(correct_path)
    os.makedirs(correct_path)
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    shutil.copyfile(pathProb+'/Main.c', correct_path+'/Main.c')
    for fname in os.listdir(pathProb):
        if 'buggy' in fname:
            cid = fname.split('_')[0]
            fname_buggy = pathProb + fname
            fname_correct = pathProb + cid + '_correct.c'
            # Filter code_id?
            if (code_id is None or str(cid) in code_id) and '277580' != str(cid):
                code_buggy, code_correct = open(fname_buggy).read(), open(fname_correct).read()
                code_corrects.append((cid, code_correct))
                # shutil.copyfile(fname_correct, CF.path_clara_cluster+'/'+pid+'/c_'+cid+'.c')

    code_corrects = random.sample(code_corrects, max(1, math.floor(float(perc) * len(code_corrects))))
    code_corrects.append(('Main',code_ref))

    for idx, (cid,code) in enumerate(code_corrects):
        fname_c = '{}/{}.c'.format(output_path, cid)
        H.write_file(fname_c, code)

    allins = []
    for ins_lines, out_lines in test_cases:
        oneins = []
        for ins in ins_lines.split():
            try:
                oneins.append(float(ins))
            except:
                oneins.append(ins)
        allins.append(oneins)
    #
    try:
        cluster_single_cmd(correct_path, output_path, allins, True)
    except:
        print('error in ', pid)
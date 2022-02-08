from srcU.Helpers import ConfigFile as CF

import os, sys
import pandas as pd


def read_testCases(path):
    fnames = os.listdir(path)
    test_cases = []

    while True:
        fname_in = 'in.{}.txt'.format(len(test_cases) + 1)
        fname_out = 'out.{}.txt'.format(len(test_cases) + 1)

        if fname_in in fnames and fname_out in fnames:
            test_input = open(path + fname_in).read()
            test_output = open(path + fname_out).read()
            test_cases.append((test_input, test_output))
        else:
            break
    return test_cases


def read_itsp_testCases(pid):
    fnames = os.listdir(CF.path_itsp_tests)
    test_cases = []

    while True:
        fname_in = 'in.{}.{}.txt'.format(pid, len(test_cases) + 1)
        fname_out = 'out.{}.{}.txt'.format(pid, len(test_cases) + 1)

        if fname_in in fnames and fname_out in fnames:
            test_input = open(CF.path_itsp_tests + fname_in).read()
            test_output = open(CF.path_itsp_tests + fname_out).read()
            test_cases.append((test_input, test_output))

        else:
            break
    
    return test_cases

def get_pathProb(labName, pid):
    return '{}/{}/{}/'.format(CF.path_itsp, labName, pid)

def get_codeRef(pathProb):
    return open(pathProb + 'Main.c').read()

def read_prob(rows, labName, pid, code_id=None):
    pathProb = get_pathProb(labName, pid)
    code_ref = get_codeRef(pathProb)
    
    # Select buggy-correct pair
    for fname in os.listdir(pathProb):
        if 'buggy' in fname:

            cid = fname.split('_')[0]                            
            fname_buggy   = pathProb + fname
            fname_correct = pathProb + cid +'_correct.c'
            
            # Filter code_id?
            if code_id is None or str(cid) in code_id:
                code_buggy, code_correct = open(fname_buggy).read(), open(fname_correct).read()
                test_cases = read_itsp_testCases(pid)
                rows.append([labName, pid, cid, pathProb, test_cases, code_ref, code_buggy, code_correct])

def read_itsp_data(lab_ids=None, problem_ids=None, code_id=None):
    rows = []
    # Select all Lab folders
    for labName in os.listdir(CF.path_itsp):
        if 'Lab' in labName: 

            # Filter lab_id, or all labs?
            if lab_ids is None or len(lab_ids) == 0 or labName in lab_ids:
            
                # Filter pid, or all assignments?
                for pid in os.listdir(CF.path_itsp + '/' + labName):
                    if problem_ids is None or len(problem_ids) == 0 or int(pid) in problem_ids: 

                        read_prob(rows, labName, pid, code_id=code_id)
                        
    df = pd.DataFrame(rows, columns=['labName', 'problem_id', 'code_id', 'pathProb', 'test_cases', 'code_reference', 'code_buggy', 'code_correct'])
    return df.sort_values(by="code_id", ascending=True)

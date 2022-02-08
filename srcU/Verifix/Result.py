import time
from typing import List

import pandas as pd
from graphviz import Digraph

from srcU.Helpers import ConfigFile as CF, Helper as H, Execute
from srcU.Verifix.CFG import CFG, Concretize, claraAST
from srcU.Verifix.Verify import Verification
import os

#region: Result class
class Result:
    def __init__(self, progName):
        self.progName = progName
        self.numPPA = None
        self.ppa_before, self.ppa_after = None, None

        self.numValid_before, self.numTotal_before = None, None
        self.numValid_after, self.numTotal_after = None, None
        
        self.exception = None
        self.isComplete, self.isPartial, self.isTest = False, False, False

        self.startTime = time.time()
        self.endTime, self.timeTaken = None, None

        self.code_repair = None
        self.repairs_li = []
        
        self.relative_patch_size = 0

    def __str__(self):
        exceptionStr = self.exception if self.exception is not None else ''
        if self.endTime is None:
            self.logEndTime()

        partial, complete, test = H.ite(self.isPartial, 'P', ' '), H.ite(self.isComplete, 'C', ' '), H.ite(self.isTest, 'T', ' ')
        return '\t{}: {}{}{}\t{} PPAs\t{}/{} --> {}/{} in {} (s) with rps: {:.2f} \t{}'.format(self.progName, partial, complete, test, self.numPPA,
            self.numValid_before, self.numTotal_before, self.numValid_after, self.numTotal_after, self.timeTaken, float(self.relative_patch_size), exceptionStr)

    def is_success(self):
        return (self.isTest and self.isPartial) or (self.isPartial and self.isComplete)

    def make_pickleSafe(self):
        '''Delete references to pointers, to make it safe for pickling (in case of parallel run)'''
        self.ppa_before, self.ppa_after = None, None

    def isBetterRes(self, numValid_after, numTotal_after):
        if self.numTotal_after is None: # First result - Any result is better than no result
            return True
        
        # As long as new result is better or equal to old result, log it
        return numValid_after/numTotal_after >= self.numValid_after/self.numTotal_after

    def update(self, ppa_before, ppa_after, numValid_before, numTotal_before, numValid_after, numTotal_after):
        '''Are the new results better? Then update'''
        if self.isBetterRes(numValid_after, numTotal_after):            
            self.ppa_before, self.ppa_after = ppa_before, ppa_after

            self.numValid_before, self.numTotal_before = numValid_before, numTotal_before
            self.numValid_after, self.numTotal_after = numValid_after, numTotal_after

            self.isComplete = numValid_after == numTotal_after
            self.isPartial = self.isComplete or (numValid_before/numTotal_before) < (numValid_after/numTotal_after)

    def update_test(self, test_cases, debug):
        self.code_repair = Concretize.concretize_prog(self.ppa_after.cfgI.prog)

        if debug:
            print(self.code_repair)

        self.isTest = Execute.execute_prog(self.code_repair, test_cases, fname=self.progName, debug=debug)
        if self.progName != '271569':
            self.relative_patch_size = claraAST.tree_edit_dist(self.ppa_before.cfgI.prog, self.ppa_after.cfgI.prog) / claraAST.patch_size(self.ppa_before.cfgI.prog)
        # self.relative_patch_size = 0

    def logEndTime(self):
        self.endTime = time.time()
        self.timeTaken = round(self.endTime - self.startTime, 2)
#endregion


def write_results(df_codes_all:pd.DataFrame, results:List[Result], debug=False):

    labIDs = df_codes_all['labName'].unique()
    df_codes_all['code_repair'] = [res.code_repair for res in results]
    df_codes_all['exceptions'] = [res.exception for res in results]
    df_codes_all['numPaths_total'] = [res.numTotal_after for res in results]
    df_codes_all['numPaths_valid_preRepair'] = [res.numValid_before for res in results]
    df_codes_all['numPaths_valid_postRepair'] = [res.numValid_after for res in results]
    df_codes_all['timeTaken'] = [res.timeTaken for res in results]

    df_codes_all['isRepair_complete'] = [int(res.isComplete) for res in results]
    df_codes_all['isRepair_partial'] = [int(res.isPartial) for res in results]
    df_codes_all['isRepair_evaluate'] = [int(res.isTest) for res in results]
    df_codes_all['relative_patch_size'] = ['{:.2f}'.format(res.relative_patch_size) for res in results]

    if not debug:
        for labID in labIDs:
            df_codes = df_codes_all[df_codes_all['labName'] == labID]

            for assignId in df_codes['problem_id'].unique():
                df_codes_tmp = df_codes[df_codes['problem_id'] == assignId]
                df_codes_tmp.to_excel(CF.path_itsp_result + 'results_verifix_{}_{}_fse17.xlsx'.format(labID, assignId), encoding ="ISO-8859-1", index=False)


#endregion

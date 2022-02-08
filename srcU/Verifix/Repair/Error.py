from srcU.Verifix.Verify import Verification, VCGen
from srcU.Verifix.CFG.Automata import PPA, Path
from srcU.Helpers import Helper as H

import z3

#region: Locate erroneous var
class Error:
    def __init__(self, ppa:PPA, path:Path, preCE=[]):
        self.vars = error_var(ppa, path)
        # self.cond_blocksC, self.cond_blocksI, self.data_blocksC, self.data_blocksI = parse_unsat_core(ppa, path, mode='errorloc', preCE=preCE)
        self.cond_blocksC, self.cond_blocksI, self.data_blocksC, self.data_blocksI = [], [], [], []
        # If cond error exists
        if len(self.cond_blocksC) == 0 or len(self.cond_blocksI) == 0:
            # If cond list is empty, consider all cond in path
            self.cond_blocksC = H.empty_assign(self.cond_blocksC, path.blocks_c) 
            self.cond_blocksI = H.empty_assign(self.cond_blocksI, path.blocks_i) 

        # If data error exists
        if len(self.data_blocksC) == 0 or len(self.data_blocksI) == 0:
            # If data list is empty, consider all data blocks in path
            self.data_blocksC = H.empty_assign(self.data_blocksC, path.blocks_c) 
            self.data_blocksI = H.empty_assign(self.data_blocksI, path.blocks_i) 


    def get_varI(self):
        return [varI for varC, varI in self.vars]

    def get_varC(self):
        return [varC for varC, varI in self.vars]

    def get_varC_varI(self, varC_orig=None, varI_orig=None):
        '''Given a specific varC (or varI), return the corresponding varI (or varC)'''
        if varC_orig is not None:
            for varC, varI in self.vars:
                if varC == varC_orig:
                    return varI
        
        if varI_orig is not None:
            for varC, varI in self.vars:
                if varI == varI_orig:
                    return varC

    def __str__(self):
        var_s = ' '.join(['{}-{}'.format(varC, varI) for varC, varI in self.vars])
        cond_c = ''.join([c.label for c in self.cond_blocksC])
        cond_i = ''.join([c.label for c in self.cond_blocksI])

        data_c = ''.join([c.label for c in self.data_blocksC])
        data_i = ''.join([c.label for c in self.data_blocksI])

        return '{} [{};{}] {};{}'.format(var_s, cond_c, cond_i, data_c, data_i)

def error_var(ppa: PPA, path: Path, mode='vcgen'):
    '''Returns the variable whose value differs, based on align_pred and SAT model. Along with blame of Cond/Data component'''
    errorVars = []

    try:
        model = path.solver[mode].model()
    except z3.z3types.Z3Exception:
        # If no model is available, when res==UNKNOWN, nothing to do
        return errorVars
    a = path.get_align_pred_fnc(ppa)
    for key, val in path.get_align_pred_fnc(ppa).items():
        bool_post = z3.Bool('ce0-post@{}@{}'.format(key, val))

        if str(model[bool_post]) == 'False':
            lhsNames, rhsNames = [], []
            VCGen.get_varName(key, lhsNames, isCorrect=True, isSMTVar=False, ce_index='0')
            VCGen.get_varName(val, rhsNames, isCorrect=False, isSMTVar=False, ce_index='0')
            if len(lhsNames) > 1 or len(rhsNames) > 1:
                raise Exception('Expecting only single variable per alignment-predicate')

            # If repair wasn't attempted earlier
            varC, varI = lhsNames[0], rhsNames[0]
            errorVars.append((varC, varI))
    return errorVars

def parse_unsat_core(ppa:PPA, path:Path, mode='errorloc', preCE=[]):
    Verification.vcgen_path(ppa, path, mode=mode, preCE=preCE)
    isValid = Verification.verify(path, mode=mode)
    unsat_core_list = []
    cond_fault_loc = []
    data_fault_loc = []

    if isValid:
        unsat_core_list = path.solver[mode].unsat_core()
        print(path.solver[mode].sexpr())
    for query in unsat_core_list:
        query_name = str(query)
        if 'cond' in query_name:
            cond_fault_loc.append(query_name)
        elif 'data' in query_name:
            data_fault_loc.append(query_name)

    cond_fault_blocksC, cond_fault_blocksI = parse_blocks(path, cond_fault_loc)
    data_fault_blocksC, data_fault_blocksI = parse_blocks(path, data_fault_loc)
    return cond_fault_blocksC, cond_fault_blocksI, data_fault_blocksC, data_fault_blocksI

def find_blocks_by_labels(path:Path, label_list, isPrime):
    blocks = path.blocks_i if isPrime else path.blocks_c
    fault_blocks = []
    for label in label_list:
        for block in blocks:
            if label == block.label:
                fault_blocks.append(block)
    return fault_blocks

def find_block_by_label(path:Path, label, isPrime):
    blocks = path.blocks_i if isPrime else path.blocks_c
    for block in blocks:
        if label == block.label:
            return block

def parse_blocks(path:Path, fault_loc):
    '''
    :param fault_loc: the cond/data fault list for both correct program and incorrect program
    :return: the cond/data list for correct program and the cond/data list for incorrect program
    '''
    fault_label_blocksC = []
    fault_label_blocksI = []
    for query in fault_loc:
        block_label = query.split('@')[2]
        if '\'' in block_label:
            fault_label_blocksI.append(block_label)
        else:
            fault_label_blocksC.append(block_label)
    fault_blocksC = find_blocks_by_labels(path, fault_label_blocksC, isPrime=False)
    fault_blocksI = find_blocks_by_labels(path, fault_label_blocksI, isPrime=True)
    return  fault_blocksC, fault_blocksI

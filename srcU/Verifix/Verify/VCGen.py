from srcU.Verifix.CFG import CFG, Automata
from srcU.ClaraP import model
from srcU.Verifix.Verify import SMT, VCGen_Block

from z3 import *

import re

# region: Var Helper functions for verification
def get_varName(expr: model.Expr, names: list, isCorrect, ce_index:str, isSMTVar=True):
    if type(expr) is model.Var:
        if isSMTVar:
            names.append(SMT.z3_name(expr.name, isCorrect, ce_index=ce_index))
        else:
            names.append(expr.name)

    elif type(expr) is model.Op:
        for arg in expr.args:
            get_varName(arg, names, isCorrect, ce_index=ce_index, isSMTVar=isSMTVar)


def get_varExists(expr: model.Expr, var: str, ce_index=''):
    varNames = []
    get_varName(expr, varNames, isCorrect=False, isSMTVar=False, ce_index=ce_index)
    return var in varNames

def add_vari(solver, vari, types, ce_index, isCorrect):
    for nameOrig, myType in types.items():
        name = SMT.z3_name(nameOrig, isCorrect, ce_index=ce_index)
        SMT.z3_varNew(solver, name, vari, isCorrect, myType=myType)

def get_vari(solver, ppa:Automata.PPA, path:Automata.Path, ce_index:str):
    vari = {}

    varC_list = ppa.cfgC.prog.fncs[path.fncName].types
    varI_list = ppa.cfgI.prog.fncs[path.fncName].types

    add_vari(solver, vari, varC_list, ce_index, isCorrect=True)
    add_vari(solver, vari, varI_list, ce_index, isCorrect=False)

    return vari

# endregion

# region: Pre /\ Inv 

def add_preCond(solver: Optimize, vari, ppa, path, align_pred_fnc, ce_index:str, mode=None):
    bool_pre = Bool('ce{}-pre'.format(ce_index))

    # vari: {name:[SMT_var0, SMT_var1, ...]}
    # For each predicate alignment
    align_pred_fnc[model.Var('$outInt')] = model.Var('$outInt')
    align_pred_fnc[model.Var('$outFloat')] = model.Var('$outFloat')
    for key, val in align_pred_fnc.items():
        if str(key) == '$outInt' or str(key) == '$outFloat':
            type_c = 'list'
            type_i = 'list'
        else:
            type_c = path.get_var_type(ppa.cfgC.prog, key)
            type_i = path.get_var_type(ppa.cfgC.prog, val)
            
        lhs = SMT.z3_gen(solver, key, vari, True, mode=mode, ce_index=ce_index, var_type=type_c)
        rhs = SMT.z3_gen(solver, val, vari, False,  mode=mode, ce_index=ce_index, var_type=type_i)

        if mode == 'vcgen' or mode == 'apply_repair':
            solver.add(bool_pre == (lhs == rhs))
            if str(key) == '$outInt':
                solver.add(lhs == K(IntSort(), -100))
            elif str(key) == '$outFloat':
                solver.add(lhs == K(RealSort(), RealVal(-10)))
            elif str(key) == '$out':
                solver.add(lhs == StringVal(''))

def add_invariants_blocks(solver: Optimize, vari, bool_inv, blocks, invariants, isCorrect, ce_index:str, mode=None):
    # Per block
    if mode not in ['vcgen', 'apply_repair']:
        return
    for block in blocks:
        if block.label in invariants:
            # Per inv
            for inv in invariants[block.label]:
                z3_inv = SMT.z3_gen(solver, inv, vari, isCorrect, ce_index=ce_index)
                solver.add(bool_inv == z3_inv)

def add_invariants(solver: Optimize, vari, ppa: Automata.PPA, path: Automata.Path, ce_index:str, mode=None):
    bool_inv = Bool('ce{}-inv'.format(ce_index))

    add_invariants_blocks(solver, vari, bool_inv, path.blocks_c, ppa.cfgC.invariants, isCorrect=True, mode=mode, ce_index=ce_index)
    add_invariants_blocks(solver, vari, bool_inv, path.blocks_i, ppa.cfgI.invariants, isCorrect=False, mode=mode, ce_index=ce_index)

#endregion

#region: Post

def add_postCond(solver: Optimize, vari, align_pred_fnc, ce_index:str, mode=None):
    flagPost = True
    bool_post = Bool('ce{}-post'.format(ce_index))
    bool_temps = []

    # For each predicate alignment
    for i, (key, val) in enumerate(align_pred_fnc.items()):

        # Fetch the list of variable updates: var_0, var_1, ...
        lhs_names, rhs_names = [], []
        get_varName(key, lhs_names, True, ce_index=ce_index)
        get_varName(val, rhs_names, False, ce_index=ce_index)

        # Fetch the Z3 var
        lhs = SMT.z3_gen(solver, key, vari, True, ce_index=ce_index)
        rhs = SMT.z3_gen(solver, val, vari, False, ce_index=ce_index)

        # Was this variable updated?
        flagChanged = False
        for name in lhs_names + rhs_names:
            if len(vari[name]) > 1:
                flagChanged = True
                flagPost = False

        # Add negative assertion, only if variable got updated in statements
        # if flagChanged and (('out' in str(key) and 'out' in str(val)) or ('ret' in str(key) and 'ret' in str(val))):
        if flagChanged:
            bool_temp = Bool('ce{}-post@{}@{}'.format(ce_index, key, val))
            bool_temps.append(bool_temp)

            VCGen_Block.add_solver(solver, bool_temp == (lhs == rhs),
                mode=mode)

    # Add final post query
    if flagPost:  # If no variables changed, add dummy True post-condition
        VCGen_Block.add_solver(solver, bool_post == SMT.z3_true(vari, ce_index=ce_index),
            mode=mode)
    else: # Otherwise, if variables changed, add the post assertion
        VCGen_Block.add_solver(solver, bool_post == And(bool_temps),
            mode=mode)

#endregion

#region: final queries

def add_finalVC(solver: Optimize, ce_index:str):
    r'''pre /\ inv /\ blocksC /\ blocksI /\ !post'''
    # bool_pre, bool_inv, bool_post, bool_finalVC = Bools('ce{}-pre ce{}-inv ce{}-post ce{}-final'.format(ce_index, ce_index, ce_index, ce_index))
    # bool_blocksC, bool_blocksI = Bools('ce{}-blocksC ce{}-blocksI'.format(ce_index, ce_index))
    bool_pre, bool_post, bool_finalVC = Bools(
        'ce{}-pre ce{}-post ce{}-final'.format(ce_index, ce_index, ce_index))
    bool_blocksC, bool_blocksI = Bools('ce{}-blocksC ce{}-blocksI'.format(ce_index, ce_index))
    solver.add( bool_finalVC == z3.And(bool_pre, bool_blocksC, bool_blocksI, z3.Not(bool_post)) )

def add_finalCE(solver:Optimize, ce_index:str):
    r'''ce /\ blocks /\ post'''
    bool_CE, bool_post, bool_finalCE = Bools('ce{}-CE ce{}-post ce{}-final'.format(ce_index, ce_index, ce_index))
    bool_blocksC, bool_blocksI = Bools('ce{}-blocksC ce{}-blocksI'.format(ce_index, ce_index))

    solver.add(bool_finalCE == z3.And(bool_CE, bool_blocksC, bool_blocksI, bool_post))

#endregion

def add_post_bool(solver:Optimize, path, num_loop):
    ''' Make sure every bool selector choose the same value'''

    for repair_line, value in path.repair_space.items():
        for repair_idx in value.keys():
            for i in range(1, num_loop):
                VCGen_Block.add_solver(solver, Bool('{}@{}'.format(repair_line, repair_idx)) == Bool(
                    '{}@{}'.format(repair_line.replace('0', str(i), 1), repair_idx)))
                # if 'data' in repair_line:
                #     VCGen_Block.add_solver(solver, Bool('{}_{}'.format(repair_line, repair_idx)) == Bool(
                #         '{}_{}'.format(repair_line.replace('0', str(i), 1), repair_idx)))
                # elif 'cond' in repair_line:
                #     VCGen_Block.add_solver(solver, Bool('{}_{}'.format(repair_line, repair_idx)) == Bool(
                #         '{}_{}'.format(repair_line.replace('0', str(i), 1), repair_idx)))

    for repair_line, value in path.repair_space.items():
        solver.add(z3.PbEq([(Bool('{}@{}'.format(repair_line, repair_idx)), 1) for repair_idx in value.keys()], 1))

#region: Counter Example part

def in_Blacklist(ce_name, ce_index:str):
    '''Does ce_name contain any of the blacklist as its prefix'''
    blacklist = ('ce{}-pre'.format(ce_index), 'ce{}-inv'.format(ce_index), 'ce{}-post'.format(ce_index),
                 'ce{}-final'.format(ce_index), 'ce{}-cond'.format(ce_index), 'ce{}-data'.format(ce_index),
                 'ce{}-block'.format(ce_index), 'final', 'repair', 'CE', 'ce{}_CE'.format(ce_index))

    return ce_name.startswith(blacklist) or 'retVal' in ce_name or 'ipVal' in ce_name

def add_counterexample(solver:Optimize, ce_index:str, preCE=[]):
    '''TODO handle function call'''
    pattern = re.compile('ce[0-9]-(C|I)-.+@[1-9][\d]*$')
    CE_list = []
    oldModel = preCE[int(ce_index)]
    for i in oldModel:
        not_first = pattern.match(str(i))
        name = str(i).replace('ce0', 'ce{}'.format(ce_index))
        # if 'C-toStrIp' in str(i) and 'repair' not in str(i):
        #     func = z3.Function('toStr', [RealSort(), StringSort()])
        #     inp = oldModel[i]
        #     out = None
        #     for j in oldModel:
        #         if str(j) == str(i).replace('toStrIp', 'toStrRe'):
        #             out = oldModel[j]
        #     solver.add(func(inp) == out)
        if 'C-ipVal' in str(i) and 'repair' not in str(i):
            func = z3.Function('check_prime', [IntSort(), IntSort()])
            inp = oldModel[i]
            out = None
            for j in oldModel:
                if str(j) == str(i).replace('ipVal', 'retVal'):
                    out = oldModel[j]
            solver.add(func(inp) == out)
            continue
        elif in_Blacklist(str(i), ce_index='0') or not_first != None:
            continue
        elif isinstance(oldModel[i], BoolRef):
            bool_i = Bool(name)
        elif isinstance(oldModel[i], IntNumRef):
            bool_i = Int(name)
        elif isinstance(oldModel[i], SeqRef):
            bool_i = String(name)
        elif isinstance(oldModel[i], FPRef):
            bool_i = FP(name,Float32())
        elif isinstance(oldModel[i], ArrayRef):
            if oldModel[i].range().is_int():
                bool_i = Array(name, IntSort(), IntSort())
            elif oldModel[i].range().is_real():
                bool_i = Array(name, RealSort(), RealSort())
        elif isinstance(oldModel[i], RatNumRef):
            bool_i = Real(name)
        try:
            CE_list.append(bool_i == oldModel[i])
        except:
            a = oldModel[i]
    CE = Bool('ce{}-CE'.format(ce_index))
    solver.add(CE == And([x for x in CE_list]))

def add_counterexample_reverse(solver:Optimize, ce_index:str, preCE=[]):
    '''TODO handle function call'''
    pattern = re.compile('ce[0-9]-(C|I)-.+@[1-9][\d]*$')
    CE_list = []
    # oldModel = preCE[int(ce_index)]
    for idx, oldModel in enumerate(preCE):
        CE_one = []
        for i in oldModel:
            not_first = pattern.match(str(i))
            if 'C-toStrIp' in str(i) and 'repair' not in str(i):
                func = z3.Function('toStr', [RealSort(), StringSort()])
                inp = oldModel[i]
                out = None
                for j in oldModel:
                    if str(j) == str(i).replace('toStrIp', 'toStrRe'):
                        out = oldModel[j]
                solver.add(func(inp) == out)
            elif 'C-ipVal' in str(i) and 'repair' not in str(i):
                func = z3.Function('check_prime', [IntSort(), IntSort()])
                inp = oldModel[i]
                out = None
                for j in oldModel:
                    if str(j) == str(i).replace('ipVal', 'retVal'):
                        out = oldModel[j]
                solver.add(func(inp) == out)
                continue
            elif in_Blacklist(str(i), ce_index=ce_index) or not_first != None:
                continue
            elif isinstance(oldModel[i], BoolRef):
                bool_i = Bool(str(i))
            elif isinstance(oldModel[i], IntNumRef):
                bool_i = Int(str(i))
            elif isinstance(oldModel[i], SeqRef):
                bool_i = String(str(i))
            elif isinstance(oldModel[i], FPRef):
                bool_i = FP(str(i), Float32())
            elif isinstance(oldModel[i], ArrayRef):
                if oldModel[i].range().is_int():
                    bool_i = Array(str(i), IntSort(), IntSort())
                elif oldModel[i].range().is_real():
                    bool_i = Array(str(i), RealSort(), RealSort())
            elif isinstance(oldModel[i], RatNumRef):
                bool_i = Real(str(i))

            try:
                CE_one.append(bool_i == oldModel[i])
            except:
                a = oldModel[i]
        CE = Bool('ce{}@CE@{}'.format(ce_index, idx))
        CE_list.append(CE)
        solver.add(CE == And([x for x in CE_one]))
    if len(CE_list) > 0:
        CE_final = Bool('CE')
        solver.add(CE_final == Not (Or([x for x in CE_list])))
        solver.add(CE_final)
#endregion




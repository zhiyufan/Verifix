from srcU.Verifix.Verify import Verification
from srcU.Verifix.Repair import Error
from srcU.Verifix.CFG import CFG
from srcU.Verifix.CFG.Automata import PPA, Path
from srcU.Helpers import Helper as H
from srcU.ClaraP import model

import z3, copy
from typing import Union, List

#region: Replace exprs/vars

def replace_var_expr(ppa:PPA, ppaCopy:PPA, path:Path, varC, exprC, history):
    '''TODO: ppaCopy=ppa currently. That is, the newVar is being added to original PPA - change later'''
    complexOps = ['ListHead', 'ListTail']

    if type(exprC) is model.Op:
        if exprC.name in complexOps: # If its a complex Op
            
            # Define new variable in incorrect program of same type as correct varC
            varName = 'newVar_'+ varC.name            
            varI = model.Var(varName)
            myType = ppaCopy.cfgC.prog.fncs[path.fncName].types[varC.name]

            # Add to ppaCopy and align_pred
            ppaCopy.cfgI.prog.fncs[path.fncName].addtype(varName, myType)
            align_pred_fnc = path.get_align_pred_fnc(ppaCopy)
            align_pred_fnc[varC] = varI

            # Return a copy of varI
            exprI = copy.deepcopy(varI)
            return exprI

    # Else, return the symbolic exprC
    return replace_expr(ppa, ppaCopy, path, exprC, history)

def replace_var_path(ppa:PPA, ppaCopy:PPA, path:Path, varC:model.Var, history):
    '''Search for variable in blocks of path'''
    for block in path.blocks_c[::-1]: # Reverse sort, to find last assignment
        for var, exprC in block.get_varExprs(ppa.cfgC.prog):
            # print(exprC, var, expr)
            if varC.name == var:
                # print(exprC, var, expr, history)
                if exprC not in history:
                    
                    return replace_var_expr(ppa, ppaCopy, path, varC, exprC, history)

    return None

def replace_var_global(ppa:PPA, ppaCopy:PPA, varC:model.Var, history):
    '''Search for variable in blocks of ALL path. Returns the first occurrence.
    TODO: Return multiple occurrences'''
    # For each path
    for path in ppa.paths.values():        
        expr = replace_var_path(ppa, ppaCopy, path, varC, history)

        # If an expr replacement is found
        if expr is not None:
            return expr # return it

def replace_var(ppa:PPA, ppaCopy:PPA, path:Path, varC:model.Var, history):
    history.append(varC)    

    # If varC is a function name (call)
    if varC.name in ppa.cfgC.prog.fncs and varC.name in ppa.cfgI.prog.fncs:
        exprI = copy.deepcopy(varC)
        return exprI

    # If varC exists in align_pred, replace it with varI
    align_pred_fnc = path.get_align_pred_fnc(ppaCopy)
    if varC in align_pred_fnc:
        pred = align_pred_fnc[varC]
        exprI = copy.deepcopy(pred)
        return exprI

    # Otherwise, probably a temporary variable. Search for the last symbolic expr assigned to this
    exprI = replace_var_path(ppa, ppaCopy, path, varC, history)
    if exprI is not None: 
        return exprI

    # If var not found in any block of this path, search for blocks in other paths
    exprI = replace_var_global(ppa, ppaCopy, varC, history)
    return exprI
        

def replace_expr(ppa:PPA, ppaCopy:PPA, path:Path, exprC, history):
    '''Returns a new/copy of exprC, with variables replaced using align_pred.'''
    if type(exprC) is model.Var: 
        return replace_var(ppa, ppaCopy, path, exprC, history)

    elif type(exprC) is model.Op:
        history.append(exprC)
        args = [replace_expr(ppa, ppaCopy, path, arg, history) for arg in exprC.args]
        if None in args:
            return None
        return model.Op(exprC.name, *args)

    elif type(exprC) is model.Const:
        return model.Const(exprC.value)

    elif type(exprC) is str and exprC in ['True', 'False']:
        return exprC
    elif type(exprC) is model.Expr:
        raise Exception('Repair: Unknown type of exprC = {} : {}'.format(exprC, type(exprC)))
    else:
        raise Exception('Repair: Unknown type of exprC = {} : {}'.format(exprC, type(exprC)))

#endregion

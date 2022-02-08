import pandas as pd
import itertools, copy
from collections import OrderedDict
from typing import Union, List
import numpy as np
import Levenshtein

from srcU.Helpers import Helper as H
from srcU.ClaraP.model import Var, Op, Const
from srcU.Verifix.CFG import CFG, Automata
from srcU.Verifix.Verify import Verification, VCGen

#region: Default alignment and helpers

def get_alignPred_def(res, cfgC, cfgI, fncName, align_pred):
    '''Return the default alignment, of special variables and function params'''
    # $in, $out and $ret are special variables.
    align_pred[fncName] = {Var('$out'):Var('$out'), Var('$ret'):Var('$ret'), Var('$in'):Var('$in'), Var('$break'):Var('$break'), Var('$continue'):Var('$continue')}

    # Match function params
    paramsC, paramsI = cfgC.prog.fncs[fncName].params, cfgI.prog.fncs[fncName].params
    if len(paramsC) != len(paramsI):
        res.exception = 'structural mismatch'
        # raise Exception('structural mismatch')

    for varC_type, varI_type in zip(paramsC, paramsI):
        align_pred[fncName][Var(varC_type[0])] = Var(varI_type[0])


def get_alignPred_rem(cfg, fncName, aligned_vars):
    '''Return non aligned variables (remaining to be aligned)'''
    return [varName
        for varName in cfg.prog.fncs[fncName].types.keys()
            if Var(varName) not in aligned_vars]

#endregion

#region: DUA (define-use-analysis)

def get_alignPred_block(prog, blocks:CFG.Block, var):
    '''Is varC used in condition or statement of blocks'''    
    numBlock, numITE, numStat = 0, 0, 0
    matchCond, matchITEc, matchITEe, matchLHS, matchRHS = 0, 0, 0, 0, 0
    scoreCond, scoreITEc, scoreITEe, scoreLHS, scoreRHS = 0, 0, 0, 0, 0

    for block in blocks:
        numBlock += 1

        # Exists in cond        
        if VCGen.get_varExists(block.get_cond(prog), var):
            matchCond += 1
        
        for varUpdate, expr in block.get_varExprs(prog):
            numStat += 1

            # Exists in LHS 
            if var == varUpdate:                
                matchLHS += 1

            # ITE?
            if type(expr) is Op and expr.name == 'ite':
                numITE += 1
                
                # Cond expr of ITE
                if VCGen.get_varExists(expr.args[0], var):
                    matchITEc += 1

                # Then expr of ITE
                if VCGen.get_varExists(expr.args[1], var):
                    matchITEe += 1

                # Else expr  of ITE
                if VCGen.get_varExists(expr.args[2], var):
                    matchITEe += 1

            # Else Exists in RHS of normal statements?
            elif VCGen.get_varExists(expr, var):
                matchRHS += 1
        
    # Calc normalized integer score for this path
    if numBlock != 0:
        scoreCond = matchCond / numBlock

    if numITE != 0:
        scoreITEc = matchITEc / numITE
        scoreITEe = matchITEe/(numITE*2) # Each ITE adds 2 additional statements
    if numStat != 0:
        scoreLHS, scoreRHS = matchLHS / numStat, matchRHS / numStat    

    return scoreCond, scoreITEc, scoreITEe, scoreLHS, scoreRHS

def update_counts(scorePath, numPaths, scoreC, scoreI):
    '''Update numPaths if either flagC or flagI is true. Increment numMatch if both are 1.'''
    if scoreC > 0 or scoreI > 0:
        numPaths += 1
        scorePath += 1 - abs(scoreC - scoreI)

    return scorePath, numPaths

def get_alignPred_dua(ppa:Automata.PPA, fncName, varC, varI):
    '''Get alignment score based on define-use-analysis (DUA)'''
    scorePath, numPaths, score = 0, 0, 0

    # For each path
    for path in ppa.paths.values():

        # If it belongs to the fnc
        if path.fncName == fncName:
            scoreCond_c, scoreITEc_c, scoreITEe_c, scoreLHS_c, scoreRHS_c = get_alignPred_block(ppa.cfgC.prog, path.blocks_c, varC)
            scoreCond_i, scoreITEc_i, scoreITEe_i, scoreLHS_i, scoreRHS_i = get_alignPred_block(ppa.cfgI.prog, path.blocks_i, varI)

            scorePath, numPaths = update_counts(scorePath, numPaths, scoreCond_c, scoreCond_i) # Either var exists in cond
            scorePath, numPaths = update_counts(scorePath, numPaths, scoreITEc_c, scoreITEc_i) # Either var exists in cond of ITE
            scorePath, numPaths = update_counts(scorePath, numPaths, scoreITEe_c, scoreITEe_i) # Either var exists in expr of ITE
            scorePath, numPaths = update_counts(scorePath, numPaths, scoreLHS_c, scoreLHS_i) # Either var exists in LHS of statements
            scorePath, numPaths = update_counts(scorePath, numPaths, scoreRHS_c, scoreRHS_i) # Either var exists in RHS of statements

            # if varC == 't' and varI == 'flag' or varC == 'flag' and varI == 'flag':
                # print('\n', varC, varI)
                # print(scoreCond_c, scoreITEc_c, scoreITEe_c, scoreLHS_c, scoreRHS_c)
                # print(scoreCond_i, scoreITEc_i, scoreITEe_i, scoreLHS_i, scoreRHS_i)

    if numPaths != 0:
        score = float(scorePath)/numPaths

    # print('{}<->{} = {}/{} = {}'.format(varC, varI, scorePath, numPaths, score))
    return score

#endregion

#region: Alignment score matrix

def get_alignPred_matrix(ppa, cfgC, cfgI, fncName, align_pred):
    '''Get alignment matrix based on define-use-analysis (DUA)'''
    varsC = get_alignPred_rem(cfgC, fncName, align_pred[fncName].keys())
    varsI = get_alignPred_rem(cfgI, fncName, align_pred[fncName].values())

    align_matrix = []
    for varC in varsC:
        align_row = []

        for varI in varsI:
            if cfgC.prog.fncs[fncName].types[varC] != cfgI.prog.fncs[fncName].types[varI]:
                score = -1
            else:
                score = get_alignPred_dua(ppa, fncName, varC, varI)
            align_row.append(score)

        align_matrix.append(align_row)

    return align_matrix, varsC, varsI

def get_bestMapping(mat:np.matrix, maxScore, varsC, varsI):
    '''Given a score matrix MxN and a max score, return the best variable mapping based on edit dist'''
    score_hash = {} # #{score1:[var_score11, var_score12, ...]}

    for i in range(len(mat)):
        for j in range(len(mat[i])):

            score = mat[i][j] # Find the numeric score
            if score == maxScore: # If it is equal to argmax
                var_score = Levenshtein.ratio(varsC[i], varsI[j]) # Compute dist between variable names
                score_hash[var_score] = (i,j)
    
    # Return the index where best name mapping was found
    maxKey = max(score_hash.keys()) 
    return score_hash[maxKey]
    


def get_maxAlign(align_pred, align_matrix, varsC, varsI, fncName):
    '''Given a score matrix MxN, select the best mapping between M varsC and N varsI'''
    mat = np.array(align_matrix)

    while mat.size != 0: # While matrix non-empty (there is a varC and varI to be mapped)
        # print(mat.argmax(), mat.shape, np.unravel_index(mat.argmax(), mat.shape))
        indexC, indexI = np.unravel_index(mat.argmax(), mat.shape) # Find the first index of max score
        indexC, indexI = get_bestMapping(mat, mat[indexC][indexI], varsC, varsI) # If multiple matches, find the best variable mapping based on edit dist

        varC, varI = varsC.pop(indexC), varsI.pop(indexI) # Find vars corresponding to max score
        align_pred[fncName][Var(varC)] = Var(varI) # Add to align_pred

        mat = np.delete(mat, indexC, axis=0) # Delete the varC row
        mat = np.delete(mat, indexI, axis=1) # and varI column from score matrix


#endregion

#region: main pred align

def get_alignPred(res, ppa, cfgC, cfgI, debug=False):
    '''Returns {Var('i'): Op('+', Var('j'), 1)}, implies value of 'i' in correct is equal to the value of 'j+1' in incorrect.
    TODO: 1. Only DUA used for now. Implement DEA (Dynamic Equivalence Analysis of trace) later
    2. Handle the case of both correct/incorrect program having a temporary flag variable - these flags will get mapped using DUA!'''
    align_pred = {}

    for fncName in cfgC.prog.fncs:
        get_alignPred_def(res, cfgC, cfgI, fncName, align_pred)
        align_matrix, varsC, varsI = get_alignPred_matrix(ppa, cfgC, cfgI, fncName, align_pred)
        get_maxAlign(align_pred, align_matrix, varsC, varsI, fncName)
        while len(varsC) > 0:
            varC = varsC.pop()
            newVarI = 'newVar{}'.format(varC)
            align_pred[fncName][Var(varC)] = Var('{}'.format(newVarI))
            fnc = ppa.cfgI.prog.getfnc(fncName)
            type = ppa.cfgC.prog.getfnc(fncName).gettype(varC)
            fnc.addtype(newVarI, type)
        while len(varsI) > 0:
            varI = varsI.pop()
            newVarC = 'newVar{}'.format(varI)
            align_pred[fncName][Var('{}'.format(newVarC))] = Var(varI)
            fnc = ppa.cfgC.prog.getfnc(fncName)
            type = ppa.cfgI.prog.getfnc(fncName).gettype(varI)
            fnc.addtype(newVarC, type)
        for fnc, aligns in align_pred.items():
            for varC, varI in aligns.items():
                typeC = ppa.cfgC.prog.getfnc(fnc).gettype(str(varC))
                typeI = ppa.cfgI.prog.getfnc(fnc).gettype(str(varI))
                if not type_equal(typeC, typeI):
                    fncI = ppa.cfgI.prog.getfnc(fnc)
                    fncI.addtype(str(varI), typeC, skiponexist=False)
                    fncIcopy = copy.deepcopy(fncI)
                    for loc, exprs in fncIcopy.locexprs.items():
                        for idx, (val, expr) in enumerate(exprs):
                            if val == str(varI) and 'ListHead' in str(expr):
                                # if len(expr.args) == 3:
                                #     assert 'ArrayAssign' == expr.name
                                #     fncI.locexprs[loc].pop(idx)
                                #     newExpr = copy.deepcopy(expr)
                                #     newExpr.args[2].args[0] = Const(typeC)
                                #     fncI.locexprs[loc].insert(idx, (val, (val, newExpr)))
                                # else:
                                    fncI.locexprs[loc].pop(idx)
                                    newExpr = copy.deepcopy(expr)
                                    newExpr.args[0] = Const(typeC)
                                    fncI.locexprs[loc].insert(idx, (val, newExpr))
                                    break

        fncI = ppa.cfgI.prog.getfnc(fncName)
        fncIcopy = copy.deepcopy(fncI)


        for loc, exprs in fncIcopy.locexprs.items():
            for idx, (val, expr) in enumerate(exprs):
                if 'ListHead' in str(expr):
                    if len(expr.args) == 3:
                        assert 'ArrayAssign' == expr.name
                        in_type = expr.args[2].args[0]
                        val_type = fncI.gettype(val).split('[]')[0]
                        if val_type != str(in_type):
                            fncI.locexprs[loc].pop(idx)
                            newExpr = copy.deepcopy(expr)
                            newExpr.args[2].args[0] = Const(fncI.gettype(val))
                            fncI.locexprs[loc].insert(idx, (val, (val,newExpr)))
                    else:
                        in_type = expr.args[0]
                        if fncI.gettype(val) != str(in_type):
                            fncI.locexprs[loc].pop(idx)
                            newExpr = copy.deepcopy(expr)
                            newExpr.args[0] = Const(fncI.gettype(val))
                            fncI.locexprs[loc].insert(idx, (val, newExpr))

    if debug:
        print(align_pred)
    return align_pred

def type_equal(typeC, typeI):

    # if typeC == None and typeI == None:
    #     return True
    # elif typeC == None and typeI != None:
    #     return False
    # elif typeI == None and typeC != None:
    #     return False
    # else:
    #     typeC = typeC.split('_')[0]
    #     typeI = typeI.split('_')[0]
    return typeC == typeI
#endregion
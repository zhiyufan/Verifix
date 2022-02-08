from srcU.ClaraP import model
from srcU.Verifix.Verify import SMT
from srcU.Verifix.CFG import Concretize
from z3 import *


# region: Helper funcs

def add_solver(solver, query, mode=None, weight=1):
    if mode == 'repair':
        if str(query).split('@')[-1] == '0':
           solver.add_soft(query, 100 * weight)
        else:
            solver.add_soft(query, 0.1 * weight)
    else:
        solver.add(query)


# endregion

# region: Normal assignment statement

def add_assignNormal(prog, path, solver: Solver, last_cond, label, vari, name_orig, expr, bool_data, bool_dataP,
                     isCorrect, parent_dataP, i, ce_index: str, block=None, mode=None, repairs=None, candidates=None,
                     last_block=False, last_line=False):
    '''parent_dataP: Used if ITE is creating a sub-block'''

    name_lhs = SMT.z3_name(name_orig, isCorrect, ce_index=ce_index)
    z3_expr_rhs = SMT.z3_gen(solver, expr, vari, isCorrect, ce_index=ce_index)
    # For each variable
    repair_var_exprs = {}
    assert_hard_ori = []
    assert_rds = []
    assert_outInt = {}
    assert_outFloat = {}
    if mode == 'repair' or mode == 'apply_repair':

        for index, (var, expr_li) in enumerate(candidates.datas.items()):
            repair_var_exprs.setdefault(var, [])
            try:
                for expr_2 in expr_li:
                    # if block.isAfterFor and 'ite' == expr_2.name:
                    #     continue
                    repair_var_exprs[var] += [SMT.z3_gen(solver, expr_2, vari, isCorrect=isCorrect, ce_index=ce_index, mode=mode)]
            except:
                pass
        if not isCorrect:
            old_inIdx, new_inIdx = SMT.z3_varNew(solver, 'ce{}-I-$inIdx'.format(ce_index), vari, isCorrect, myType='int')
            # old_$inIdx, new_$inIdx = SMT.z3_varNew(solver, 'ce{}-I-$inIdx'.format(ce_index), vari, isCorrect, myType='float')
            vari['ce{}-I-$in'.format(ce_index)][-1].increIndex()
        z3_repair_line = Bool('{}@{}'.format(str(bool_data), i))
        add_solver(solver, Implies(bool_data, z3_repair_line), mode='vcgen')
    # if 'break' in name_lhs or 'continue' in name_lhs:
    #     name = SMT.z3_name(name_orig, isCorrect, ce_index=ce_index)
    #     SMT.z3_varNew(solver, name, vari, isCorrect, myType='int')
    for name in vari:
        # If the name belongs to isCorrect program

        if not SMT.z3_name_check(name, ce_index=ce_index) == isCorrect:
            continue

        if 'dummy' in name:
            continue

        if 'checkprime' in name:
            continue

        if '$in' in name or '$inIdx' in name:
            continue

        if '$ret' in name and (last_line != True or last_block != True):
            continue

        if '$break' in name and (last_line != True or last_block != True):
            continue

        if ('$outInt' in name or '$outFloat' in name):# and mode == 'vcgen':
            continue

        var_name = name.split('-')[-1]
        if var_name not in repair_var_exprs:
            repair_var_exprs[var_name] = []
        # TODO what's the purpose of myType? we should pass name_origi instead of name
        myType = path.get_var_type(prog, var_name)
        oldVar, newVar = SMT.z3_varNew(solver, name, vari, isCorrect, myType=myType, mode=mode)

        # Case-1: This variable appears in LHS

        if name == name_lhs and '$in' not in name:
            z3_expr = z3_expr_rhs

        # Case-2: Some other variable
        else:
            z3_expr = oldVar.smtVar

        # Don't add assignment to $in and No-ops
        if z3_expr is not None:
            # data

            if mode == 'vcgen':
                if '$out' in name:
                    name_outInt = SMT.z3_name('$outInt', isCorrect, ce_index=ce_index)
                    name_outFloat = SMT.z3_name('$outFloat', isCorrect, ce_index=ce_index)
                    old_outInt, new_outInt = SMT.z3_varNew(solver, name_outInt, vari, isCorrect, myType='list', mode=mode)
                    old_outFloat, new_outFloat = SMT.z3_varNew(solver, name_outFloat, vari, isCorrect, myType='list', mode=mode)
                    if type(z3_expr) == type(z3_expr_rhs):
                        z3_expr_outStr = z3_expr[0]
                        if len(z3_expr) == 4:
                            cond = z3_expr[3]
                        else:
                            cond = True
                        z3_expr_outInt = old_outInt.smtVar
                        z3_expr_outFloat = old_outFloat.smtVar
                        if len(z3_expr[1]) == 0:
                            z3_expr_outIntIdx = z3.If(cond, new_outInt.indexTemp == old_outInt.indexTemp,
                                                  new_outInt.indexTemp == old_outInt.indexTemp)
                            add_solver(solver, Implies(bool_data, z3_expr_outIntIdx), mode=mode)
                            add_solver(solver, Implies(bool_data, new_outInt.smtVar == z3_expr_outInt), mode=mode)
                        if len(z3_expr[2]) == 0:
                            z3_expr_outIntIdx = z3.If(cond, new_outFloat.indexTemp == old_outFloat.indexTemp,
                                                      new_outFloat.indexTemp == old_outFloat.indexTemp)
                            add_solver(solver, Implies(bool_data, z3_expr_outIntIdx), mode=mode)
                            add_solver(solver, Implies(bool_data, new_outFloat.smtVar == z3_expr_outFloat), mode=mode)
                        for idx, z3_expr_IntVal in enumerate(z3_expr[1]):
                            z3_expr_outInt = z3.If(cond, z3.Store(z3_expr_outInt, old_outInt.indexTemp, z3_expr_IntVal), z3_expr_outInt)
                            z3_expr_outIntIdx = z3.If(cond, new_outInt.indexTemp == old_outInt.indexTemp + 1, new_outInt.indexTemp == old_outInt.indexTemp)
                            add_solver(solver, Implies(bool_data, z3_expr_outIntIdx), mode=mode)
                            add_solver(solver, Implies(bool_data, new_outInt.smtVar == z3_expr_outInt), mode=mode)
                            if idx < len(z3_expr[1]) - 1:
                                old_outInt, new_outInt = SMT.z3_varNew(solver, name_outInt, vari, isCorrect, myType='list',
                                                                   mode=mode)

                            # old_outInt.indexTemp += 1
                            # new_outInt.indexTemp = old_outInt.indexTemp
                        for idx, z3_expr_FloatVal in enumerate(z3_expr[2]):
                            z3_expr_outFloat = z3.If(cond, z3.Store(z3_expr_outFloat, old_outFloat.indexTemp,
                                                        z3_expr_FloatVal), z3_expr_outFloat)

                            z3_expr_outFloatIdx = z3.If(cond, new_outFloat.indexTemp == old_outFloat.indexTemp + 1, new_outFloat.indexTemp == old_outFloat.indexTemp)
                            add_solver(solver, Implies(bool_data, z3_expr_outFloatIdx), mode=mode)

                            add_solver(solver, Implies(bool_data, new_outFloat.smtVar == z3_expr_outFloat), mode=mode)
                            if idx < len(z3_expr[2]) - 1:
                                old_outFloat, new_outFloat = SMT.z3_varNew(solver, name_outFloat, vari, isCorrect,
                                                                       myType='list', mode=mode)
                            # old_outFloat.indexTemp += 1
                            # new_outFloat.indexTemp = old_outFloat.indexTemp

                        add_solver(solver, Implies(bool_data, newVar.smtVar == z3_expr_outStr), mode=mode)
                        # add_solver(solver, Implies(bool_data, new_outInt.smtVar == z3_expr_outInt), mode=mode)
                        # add_solver(solver, Implies(bool_data, new_outFloat.smtVar == z3_expr_outFloat), mode=mode)
                    else:
                        z3_expr_outStr = z3_expr
                        z3_expr_outInt = old_outInt.smtVar
                        z3_expr_outFloat = old_outFloat.smtVar
                        add_solver(solver, Implies(bool_data, newVar.smtVar == z3_expr_outStr), mode=mode)
                        add_solver(solver, Implies(bool_data, new_outInt.smtVar == z3_expr_outInt), mode=mode)
                        add_solver(solver, Implies(bool_data, new_outFloat.smtVar == z3_expr_outFloat), mode=mode)
                        add_solver(solver, Implies(bool_data, new_outInt.indexTemp == old_outInt.indexTemp), mode=mode)
                        add_solver(solver, Implies(bool_data, new_outFloat.indexTemp == old_outFloat.indexTemp), mode=mode)
                else:
                    try:
                        add_solver(solver, Implies(bool_data, newVar.smtVar == z3_expr), mode=mode)
                    except:
                        print('vcgen add block error')
            elif mode == 'repair' or mode == 'apply_repair':

                z3_repair_0 = Bool('repair@{}@{}@{}@{}'.format(bool_data, var_name, i, 1))
                assert_hard_ori.append(z3_repair_0 == True)

                if '$out' in var_name:
                    name_outInt = SMT.z3_name('$outInt', isCorrect, ce_index=ce_index)
                    name_outFloat = SMT.z3_name('$outFloat', isCorrect, ce_index=ce_index)
                    old_outInt, new_outInt = SMT.z3_varNew(solver, name_outInt, vari, isCorrect, myType='list',
                                                           mode=mode)
                    old_outFloat, new_outFloat = SMT.z3_varNew(solver, name_outFloat, vari, isCorrect,
                                                               myType='list', mode=mode)

                    if type(z3_expr) != type(z3_expr_rhs):
                        z3_expr = (oldVar.smtVar, old_outInt.smtVar, old_outFloat.smtVar)

                    orig_smt = (oldVar.smtVar, old_outInt.smtVar, old_outFloat.smtVar)
                else:
                    orig_smt = oldVar.smtVar
                for index, z3_repair_expr in enumerate([z3_expr, orig_smt] + repair_var_exprs[var_name]):
                    # print(var_name)
                    if str(z3_expr) == str(orig_smt) and index == 0:
                        continue
                    try:
                        # a = newVar.smtVar == z3_repair_expr
                        z3_repair = Bool('repair@{}@{}@{}@{}'.format(bool_data, var_name, i, index))

                        if '$out' in var_name:
                            if index == 1:
                                add_solver(solver, Implies(z3_repair, Implies(z3_repair_line, newVar.smtVar == z3_repair_expr[0])),
                                           mode='vcgen')
                                add_solver(solver, Implies(z3_repair, Implies(z3_repair_line, new_outInt.smtVar == z3_repair_expr[1])),
                                           mode='vcgen')
                                add_solver(solver, Implies(z3_repair, Implies(z3_repair_line, new_outFloat.smtVar == z3_repair_expr[2])),
                                           mode='vcgen')
                                cond = True
                            else:
                                z3_expr_outStr = z3_repair_expr[0]

                                # if len(z3_expr) == 4:
                                if len(z3_repair_expr) == 4:
                                    cond = z3_repair_expr[3]
                                else:
                                    cond = True
                                cp_old_outInt = copy.deepcopy(old_outInt)
                                cp_old_outFloat = copy.deepcopy(old_outFloat)
                                z3_expr_outInt = cp_old_outInt.smtVar
                                z3_expr_outFloat = cp_old_outFloat.smtVar
                                for z3_expr_IntVal in z3_repair_expr[1]:
                                    z3_expr_outInt = z3.If(cond, z3.Store(z3_expr_outInt, cp_old_outInt.indexTemp, z3_expr_IntVal), z3_expr_outInt)
                                    cp_old_outInt.indexTemp += 1

                                for z3_expr_FloatVal in z3_repair_expr[2]:
                                    z3_expr_outFloat = z3.If(cond, z3.Store(z3_expr_outFloat, cp_old_outFloat.indexTemp,
                                                                z3_expr_FloatVal), z3_expr_outFloat)
                                    cp_old_outFloat.indexTemp += 1

                                add_solver(solver, Implies(z3_repair, Implies(z3_repair_line, newVar.smtVar == z3_expr_outStr)),mode='vcgen')
                                add_solver(solver, Implies(z3_repair, Implies(z3_repair_line, new_outInt.smtVar == z3_expr_outInt)),mode='vcgen')
                                add_solver(solver, Implies(z3_repair, Implies(z3_repair_line, new_outFloat.smtVar == z3_expr_outFloat)),mode='vcgen')
                            assert_outInt[z3_repair] = (copy.deepcopy(old_outInt), copy.deepcopy(new_outInt), cond)
                            assert_outFloat[z3_repair] = (copy.deepcopy(old_outFloat), copy.deepcopy(new_outFloat), cond)
                        else:
                            add_solver(solver,
                                       Implies(z3_repair, Implies(z3_repair_line, newVar.smtVar == z3_repair_expr)),
                                       mode='vcgen')
                            if ('$in' in str(z3_repair_expr)):
                                assert_rds.append(z3_repair)
                    except:
                        continue

                    if mode == 'repair':
                        if str(z3_expr) == str(oldVar.smtVar) and index == 1:
                            weight = 1000
                        else:
                            weight = 1
                        add_solver(solver, z3_repair, mode=mode, weight=weight)
                        if name != name_lhs:
                            tmp = None
                        else:
                            tmp = expr
                        path.add_reps_candidate('repair@{}@{}@{}'.format(bool_data, var_name, i), index, (
                            var_name, ([tmp, model.Var(var_name)] + candidates.datas[var_name])[index]))

                    elif mode == 'apply_repair':
                        if str(z3_repair) in repairs:
                            add_solver(solver, z3_repair, mode=mode)
                        else:
                            add_solver(solver, z3_repair == SMT.z3_false(vari, ce_index), mode=mode)

            if oldVar is not None:
                # data-Prime
                if mode == 'repair':
                    else_mode = 'vcgen'
                    add_solver(solver, Implies(bool_dataP, newVar.smtVar == oldVar.smtVar), mode=else_mode)
                    # if '$out' in name:
                    #     add_solver(solver, Implies(bool_dataP, newVar.smtVar == oldVar.smtVar), mode=else_mode)
                    #     add_solver(solver, Implies(bool_dataP, new_outInt.smtVar == old_outInt.smtVar), mode=else_mode)
                    #     add_solver(solver, Implies(bool_dataP, new_outFloat.smtVar == old_outFloat.smtVar), mode=else_mode)
                    # else:
                    #     add_solver(solver, Implies(bool_dataP, newVar.smtVar == oldVar.smtVar), mode=else_mode)
                else:
                    else_mode = mode
                    if '$out' in name:
                        add_solver(solver, Implies(bool_dataP, newVar.smtVar == oldVar.smtVar), mode=else_mode)
                        add_solver(solver, Implies(bool_dataP, new_outInt.smtVar == old_outInt.smtVar), mode=else_mode)
                        add_solver(solver, Implies(bool_dataP, new_outFloat.smtVar == old_outFloat.smtVar), mode=else_mode)
                    else:
                        add_solver(solver, Implies(bool_dataP, newVar.smtVar == oldVar.smtVar), mode=else_mode)

                # ITE: If this is a sub-block (created by ITE) and the parent-block isn't executed
                if parent_dataP is not None:
                    add_solver(solver, Implies(parent_dataP, newVar.smtVar == oldVar.smtVar),
                               # Then newVar value remains the same as oldVar
                               mode=else_mode)
    if mode == 'repair':
        solver.add(z3.PbGe([(x, 1) for x in assert_hard_ori], len(assert_hard_ori) - 1))

    if mode == 'repair' or mode == 'apply_repair':
        cond = z3.Or([c for c in assert_rds])
        add_solver(solver, z3.If(cond, new_inIdx.smtVar == old_inIdx.smtVar + 1, new_inIdx.smtVar == old_inIdx.smtVar),
               mode='vcgen')
        for z3_repair_expr, (old_outInt, new_outInt, cond) in assert_outInt.items():
            if int(str(z3_repair_expr).split('@')[-1]) == 1:
                add_solver(solver, z3.If(z3_repair_expr, z3.If(cond, new_outInt.indexTemp == old_outInt.indexTemp, new_outInt.indexTemp == old_outInt.indexTemp), 1==1))#, new_outInt.indexStart == old_outInt.indexStart))
            else:
                add_solver(solver, z3.If(z3_repair_expr, z3.If(cond, new_outInt.indexTemp == old_outInt.indexTemp+1, new_outInt.indexTemp == old_outInt.indexTemp), 1==1))#, new_outInt.indexStart == old_outInt.indexStart))

        for z3_repair_expr, (old_outFloat, new_outInt, cond) in assert_outFloat.items():
            if int(str(z3_repair_expr).split('@')[-1]) == 1:
                add_solver(solver, z3.If(z3_repair_expr, z3.If(cond, new_outFloat.indexTemp == old_outFloat.indexTemp,
                                                               new_outFloat.indexTemp == old_outFloat.indexTemp),
                                         1 == 1))  # , new_outInt.indexStart == old_outInt.indexStart))
            else:
                add_solver(solver, z3.If(z3_repair_expr, z3.If(cond, new_outFloat.indexTemp == old_outFloat.indexTemp + 1,
                                                               new_outFloat.indexTemp == old_outFloat.indexTemp),
                                         1 == 1))  # , new_outInt.indexStart == old_outInt.indexStart))
    # for z3_repair_expr, (old_outInt, new_outInt) in assert_outInt.items():
        #     add_solver(solver, z3.If(z3_repair_expr, new_outInt.indexStart == old_outInt.indexTemp, 1==1))#, new_outInt.indexStart == old_outInt.indexStart))
        #
        # for z3_repair_expr, (old_outFloat, new_outInt) in assert_outFloat.items():
        #     add_solver(solver, z3.If(z3_repair_expr, new_outFloat.indexStart == old_outFloat.indexTemp, 1==1))#, new_outFloat.indexStart == old_outFloat.indexStart))

# endregion

# region: ITE statement

# def add_assignITE(prog, path, solver: Solver, last_cond, z3_cond, label, index, vari, name, op, bool_data, bool_dataP,
#                   align_pred_fnc, isCorrect, ce_index: str, mode=None, repairs=None, candidates=None):
#     cond_expr, then_expr, else_expr = op.args[0], op.args[1], op.args[2]
#     assert type(
#         else_expr) is model.Var and else_expr.name == name, 'Verification: ITE assumption of empty else branch violated'
#
#     # Create a new dummy blockCond
#     labelITE = label + '@ite' + str(index)
#     varExprs = [(name, then_expr)]
#
#     # TODO: handle repairs for ITE
#
#     add_blockCond(prog, path, solver, z3_cond, labelITE, cond_expr, varExprs, vari, align_pred_fnc, isCorrect, block=block,
#                   parent_dataP=bool_dataP, mode=mode, repairs=repairs, ce_index=ce_index, candidates=candidates)
#
#     # Attach it to orig block's data
#     bool_dataOrig, bool_blockITE = Bools('ce{}-data{} ce{}-block{}'.format(ce_index, label, ce_index, labelITE))
#
#     if mode == 'repair':
#         ite_mode = 'vcgen'
#     else:
#         ite_mode = mode
#
#     add_solver(solver, Implies(bool_dataOrig, bool_blockITE), mode=ite_mode)


# endregion

# region: Block predicate cond

def add_cond(path, solver: Optimize, bool_cond, z3_prevCond, currCond,
             vari, isCorrect, ce_index: str, mode=None, repairs=None, candidates=None, cond_type=None):
    '''Add block cond'''

    if mode == 'vcgen':
        z3_cond = SMT.z3_cond(solver, currCond, vari, isCorrect, ce_index=ce_index)
        if z3_prevCond is not None:
            z3_cond = z3.And(z3_cond, z3_prevCond)
        add_solver(solver, bool_cond == z3_cond)

    elif mode == 'repair' or mode == 'apply_repair':
        if cond_type is None:
            cond_space = candidates.conds['loop'] + candidates.conds['if']
        else:
            cond_space = candidates.conds[cond_type]
        # cond_space = candidates.conds['loop'] + candidates.conds['if']
        for index, cond in enumerate([currCond] + cond_space):
            if str(currCond) == str(cond) and index > 0:
                continue
            # if "%" in str(cond) and index > 0:
            #     continue
            z3_repair = Bool('repair@{}@{}'.format(bool_cond, index))

            z3_repair_cond = SMT.z3_cond(solver, cond, vari, isCorrect, ce_index=ce_index)
            if z3_prevCond is not None:
                z3_repair_cond = z3.And(z3_repair_cond, z3_prevCond)

            add_solver(solver, Implies(z3_repair, bool_cond == z3_repair_cond), mode='vcgen')

            if mode == 'repair':
                add_solver(solver, z3_repair, mode=mode)
                path.add_reps_candidate('repair@{}'.format(bool_cond), index, ('$cond', cond))
            elif mode == 'apply_repair':
                if str(z3_repair) in repairs:
                    add_solver(solver, z3_repair, mode=mode)
                else:
                    add_solver(solver, z3_repair == False, mode=mode)

    return bool_cond


# endregion

# region: Main block

def add_block(prog, path, solver: Optimize, last_cond, bool_data, bool_dataP, z3_cond, label, varExprs, vari,
              align_pred_fnc, isCorrect, ce_index: str, block=None, parent_dataP=None, mode=None, repairs=None, candidates=None,
              last_block=False):
    '''Add block statements'''
    last_line = False
    for indexE in range(len(varExprs)):
        if indexE == len(varExprs) - 1:
            last_line = True
        name, expr = varExprs[indexE]

        if '$in' in name:
            continue
        add_assignNormal(prog, path, solver, last_cond, label, vari, name, expr, bool_data, bool_dataP, isCorrect,
                         parent_dataP, indexE, block=block, mode=mode, repairs=repairs, candidates=candidates, ce_index=ce_index,
                         last_block=last_block, last_line=last_line)


# endregion


# region: Block/Cond

def add_blockCond(prog, path, solver: Optimize, z3_prevCond, label, currCond, varExprs, vari, align_pred_fnc, isCorrect,
                  ce_index: str, parent_dataP=None, mode=None, repairs=None, candidates=None, last_block=False):
    '''parentBlock: Used when ITE invokes this function to create sub-block.'''
    bool_cond, bool_data, bool_dataP, bool_block = Bools(
        'ce{}-cond{} ce{}-data{} ce{}-data{}@else ce{}-block{}'.format(ce_index, label, ce_index, label, ce_index,
                                                                       label, ce_index, label))
    last_cond = 'ce{}-cond{}'.format(int(ce_index) - 1, label)

    fnc = prog.fncs[path.fncName]

    if isCorrect:
        block = path.blocks_c[path.get_index(label[1:], isCorrect)]
    else:
        block = path.blocks_i[path.get_index(label[1:], isCorrect)]

    cond_type = None

    if Concretize.is_forLoop(fnc, block.cond.loc) or Concretize.is_whileLoop(fnc, block.cond.loc):
        cond_type = 'loop'
    elif Concretize.is_ifCond(fnc, block.cond.loc):
        cond_type = 'if'

    z3_cond = add_cond(path, solver, bool_cond, z3_prevCond, currCond, vari, isCorrect,
                           mode=mode, repairs=repairs, candidates=candidates, ce_index=ce_index, cond_type=cond_type)

    # Add block statements

    add_block(prog, path, solver, last_cond, bool_data, bool_dataP, z3_cond, label, varExprs, vari, align_pred_fnc,
              isCorrect, block=block,
              parent_dataP=parent_dataP, mode=mode, repairs=repairs, candidates=candidates, ce_index=ce_index,
              last_block=last_block)

    query = bool_block == z3.And(
        bool_cond == bool_data,  # If cond is True, then data should be True
        z3.Not(bool_cond) == bool_dataP)  # If cond is False, dataP should be True (variable values retained)

    add_solver(solver, query)

    return z3_cond

# endregion
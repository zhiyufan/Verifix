from srcU.ClaraP import model
from typing import Union, List, Set
from srcU.Verifix.Repair import Error, ReplExpr
from srcU.Verifix.CFG.Automata import PPA, Path
import copy
import z3


def get_valid_repairs(path):
    model = path.model['repair']

    tmp_repairs = copy.deepcopy(path.repair_space)
    # repair set for each line
    for repair_line, repair_candidates in tmp_repairs.items():
        # specific repair at a line
        for repair_idx in repair_candidates.keys():
            if not is_repair_true(model, repair_line, repair_idx):
                del path.repair_space[repair_line][repair_idx]
                continue
            if is_orig_expr_true(model,
                                 repair_line) and repair_idx != 0:  # and str(path.repair_space[repair_line][repair_idx]) == str(path.repair_space[repair_line][0]):
                del path.repair_space[repair_line][repair_idx]
                continue

    repair_list = []
    for repair_line, repair_candidates in path.repair_space.items():
        repair_list.append(list(['{}@{}'.format(repair_line, repair_idx) for repair_idx in repair_candidates.keys()]))
    return get_repair_pairs(repair_list, init_depth=0, max_depth=len(repair_list))


def get_repair_pairs(repair_list, cp=[], init_depth=0, max_depth=3):
    if init_depth >= max_depth:
        return [cp]
    repairs = []
    for i in repair_list[init_depth]:
        for li in get_repair_pairs(repair_list, [i], init_depth + 1, max_depth=max_depth):
            repairs.append(cp + li)
    return repairs


def sort_by_num(elem):
    splitter = elem.rfind('@')
    idx = elem[splitter + 1:]
    if idx == '1':
        rank_idx = 1
    else:
        rank_idx = 10
    spi = elem.split('@')
    rank_block = spi[2]
    if 'cond' in spi[1]:
        type = 'cond'
        rank_type = 1
    else:
        type = 'data'
        rank_type = 2

    if type == 'data':
        rank_line = spi[-2]
    else:
        rank_line = 0

    return rank_type, rank_block, rank_line, rank_idx


def update_repairs(prog: model.Program, path: Path, repair_pairs: list, repair_expr):

    repair_pairs.sort(key=sort_by_num)
    rd_idx = 0
    for repair_type_block_var_line_repairIndex in repair_pairs:
        splitter = repair_type_block_var_line_repairIndex.rfind('@')
        prefix = repair_type_block_var_line_repairIndex[:splitter]
        idx = repair_type_block_var_line_repairIndex[splitter + 1:]
        spi = repair_type_block_var_line_repairIndex.split('@')
        path.repairs_tmp.append({prefix: repair_expr[prefix]})
        if 'cond' in spi[1]:
            type = 'cond'
        else:
            type = 'data'

        block = Error.find_block_by_label(path, spi[2], True)
        lhs = repair_expr[prefix][int(idx)][0]
        rhs = repair_expr[prefix][int(idx)][1]
        if type == 'cond' and idx != '0':
            block.set_cond(prog, rhs)
            block.set_cond_updated()
            block.set_changed()
        elif type == 'data':
            desc = prog.fncs[block.cond.fncName].locdescs[block.cond.loc]
            if 'update of the \'for\' loop' in desc and 'ite' in str(rhs):
                    i=-1
                    for blocki in path.blocks_i:
                        if blocki != block:
                            i +=1
                    pre_block = path.blocks_i[i]
                    pre_block.varExprs.addexpr(prog, lhs, rhs)
                    block.varExprs.pop(prog,index=-1)
            else:
                block.varExprs.update(prog, int(spi[4]), lhs, rhs)
                block.set_changed()

            # block.varExprs.update(prog, int(spi[4]), lhs, rhs)
            # block.set_changed()

def generate_rd(prog, path, lhs, rhs, idx):
    type = prog.fncs[path.fncName].types[str(lhs)]
    arg_0 = model.Const(type)
    arg_1 = rec_geneate_rd(idx)
    new_rhs = model.Op('ListHead', arg_0, arg_1)
    return new_rhs


def rec_geneate_rd(idx):
    if idx == 0:
        return model.Var('$in')
    arg_1 = model.Op('ListTail', rec_geneate_rd(idx - 1))
    return arg_1


def is_repair_true(model, repair_line, repair_idx):
    z3_repair = z3.Bool('{}@{}'.format(repair_line, repair_idx))
    return model[z3_repair]


def is_orig_expr_true(model, repair_line):
    return is_repair_true(model, repair_line, 0)

from srcU.Verifix.CFG import Automata, Minimize
from srcU.ClaraP import model

def insert_dummy_line_ppaLi(ppa_li):
    for ppa in ppa_li:
        insert_dummy_line_ppa(ppa)
        prog = ppa.cfgI.prog
        Minimize.index_ite(prog)

def insert_dummy_line_ppa(ppa: Automata.PPA):
    for path_label in ppa.paths:
        path = ppa.paths[path_label]
        insert_dummy_line_path(ppa, path)


def insert_dummy_line_path(ppa: Automata.PPA, path: Automata.Path):

    blockC = path.blocks_c
    blockI = path.blocks_i

    all = 0
    max = 0
    hasLoopC = False
    hasLoopI = False
    for block in blockC:
        desc = ppa.cfgC.prog.fncs[block.cond.fncName].locdescs[block.cond.loc]
        if 'update of the \'for\' loop' in desc:
            hasLoopC = True
            continue
        sum = len(block.get_varExprs(ppa.cfgC.prog))
        if sum > max:
            max = sum
        all += sum

    sum_i = 0
    for block in blockI:
        desc = ppa.cfgI.prog.fncs[block.cond.fncName].locdescs[block.cond.loc]
        if 'update of the \'for\' loop' in desc:
            hasLoopI = True
            continue
        sum_i += len(block.get_varExprs(ppa.cfgI.prog))
    if hasLoopC == True and hasLoopI == False:
        all += 1
    while(sum_i < all and len(blockI) > 0):
        sum_block = 0
        for block in blockI:
            desc = ppa.cfgI.prog.fncs[block.cond.fncName].locdescs[block.cond.loc]
            varExpr = block.get_varExprs(ppa.cfgI.prog)
            lines = len(varExpr)
            if 'update of the \'for\' loop' in desc:
                if lines > 1:
                    block.del_varExprs(ppa.cfgI.prog)
                    lines = 0
                insert_dummy_line_block(ppa.cfgI.prog, block, 1 - lines)
                continue
            else:
                insert_dummy_line_block(ppa.cfgI.prog, block, 1)
                sum_block += len(block.get_varExprs(ppa.cfgI.prog))
        sum_i = sum_block
    # for block in blockI:
    #     desc = ppa.cfgI.prog.fncs[block.cond.fncName].locdescs[block.cond.loc]
    #     varExpr = block.get_varExprs(ppa.cfgI.prog)
    #     lines = len(varExpr)
    #     if 'update of the \'for\' loop' in desc:
    #         if lines > 1:
    #             block.del_varExprs(ppa.cfgI.prog)
    #             lines = 0
    #         insert_dummy_line_block(ppa.cfgI.prog, block, 1 - lines)
    #         continue
    #     if lines < max:
    #         insert_dummy_line_block(ppa.cfgI.prog, block, 1)
    # for block in blockI:
    #     desc = ppa.cfgI.prog.fncs[block.cond.fncName].locdescs[block.cond.loc]
    #     varExpr = block.get_varExprs(ppa.cfgI.prog)
    #     lines = len(varExpr)
    #     if 'update of the \'for\' loop' in desc:
    #         if lines > 1:
    #             block.del_varExprs(ppa.cfgI.prog)
    #             lines = 0
    #         insert_dummy_line_block(ppa.cfgI.prog, block, 1 - lines)
    #         continue
    #     if lines < max:
    #         insert_dummy_line_block(ppa.cfgI.prog, block, max - lines)

def insert_dummy_line_block(prog: model.Program, block, num):
    for i in range(num):
        var_expr = block.get_varExprs(prog)
        var_expr.insert(0, ('dummy', model.Var('dummy')))

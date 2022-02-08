from srcU.Verifix.CFG import CFG, Automata
from srcU.ClaraP import model

def remove_dummy_line_ppa(ppa: Automata.PPA):
    for path_label in ppa.paths:
        path = ppa.paths[path_label]
        remove_dummy_line_path(ppa, path)


def remove_dummy_line_path(ppa: Automata.PPA, path: Automata.Path):
    blockI = path.blocks_i
    for block in blockI:
        remove_dummy_line_block(ppa.cfgI.prog, block)


def remove_dummy_line_block(prog: model.Program, block: CFG.Block):
    var_expr = block.get_varExprs(prog)
    var_expr = [(var, expr) for var, expr in var_expr if str(expr) != var]
    block.set_varExprs(prog, var_expr)

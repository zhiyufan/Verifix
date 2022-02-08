from srcU.ClaraP import model
from srcU.Verifix.Repair import Error, ReplExpr
from srcU.Verifix.CFG.Automata import PPA, Path
from srcU.Verifix.CFG import Concretize
'''
Optimization #1: Restrict RHS expressions in incorrect to the aligned RHS expressions from reference
Optimization #2: Restrict conditionals to type (loop conditional replacements are borrowed from reference loops, similar for if-conditionals)
'''

class RepairSpace:

    def __init__(self, rep_conds, rep_datas):
        self.conds = rep_conds
        self.datas = rep_datas

    def __str__(self):
        return ''


def construct_repair_space(ppa: PPA, path: Path, error: Error.Error):
    repair_conds = construct_repair_cond(ppa, path, error)
    repair_datas = construct_repair_data(ppa, path, error)
    repair_candidates = RepairSpace(repair_conds, repair_datas)

    return repair_candidates


def construct_repair_data(ppa_orig: PPA, path: Path, error: Error.Error):
    # special var
    data_exprs = {'$out': [], '$ret': [], '$in': [], '$break':[], '$continue':[], 'ipValcheck_prime': [], 'retValcheck_prime': [],
                '$outInt': [], '$outFloat': []}

    # init var
    for varI in ppa_orig.cfgI.prog.getfnc(path.fncName).types.keys():
        data_exprs[varI] = []

    for blockC in error.data_blocksC:
        for (varC, exprC) in blockC.get_varExprs(ppa_orig.cfgC.prog):
            # if varC not in error.get_varC():
            #     continue
            exprI_new = ReplExpr.replace_expr(ppa_orig, ppa_orig, path, exprC, history=[])
            if varC == 'break' or varC == 'continue':
                # continue
                data_exprs['$break'] += [exprI_new]

            align_pred_fnc = path.get_align_pred_fnc(ppa_orig)
            for vC, vI in align_pred_fnc.items():
                if vC.name == varC and varC != "$in": # Optimization-1:
                    varI = align_pred_fnc[vC]
                    data_exprs[str(varI)] += [exprI_new]
    return data_exprs


def construct_repair_cond(ppa: PPA, path: Path, error: Error.Error):
    '''Eg: num<j, num%j==0, num%j!=0, ...'''
    conc_exprs = {'loop': [], 'if': [model.Op('True'), model.Op('False')]}#[model.Op('True'), model.Op('False')]
    # conc_exprs = {'loop': [], 'if': []}#[model.Op('True'), model.Op('False')]
    # For each correct block, extract the condExpr

    for indexC, blockC in enumerate(error.cond_blocksC):
        # Ignore [True] block
        if not blockC.cond.isCondTrue:
            # extract Conds
            exprC = blockC.get_cond(ppa.cfgC.prog)
            fnc = ppa.cfgC.prog.fncs[blockC.cond.fncName]
            exprI_new = ReplExpr.replace_expr(ppa, ppa, path, exprC, history=[])

            exprC_loc = blockC.cond.loc
            if Concretize.is_forLoop(fnc, exprC_loc) or Concretize.is_whileLoop(fnc, exprC_loc):
                conc_exprs['loop'] += [exprI_new]
            elif Concretize.is_ifCond(fnc, exprC_loc):
                conc_exprs['if'] += [exprI_new]
            # conc_exprs.append(exprI_new)

    return conc_exprs

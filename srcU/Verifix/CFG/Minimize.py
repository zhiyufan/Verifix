'''ToDo: 
- Merge True-empty blocks (optimization step, to be performed in the end)
- Merge [C1] followed by [True] into [C1]
'''

from srcU.ClaraP import parser, model
from srcU.Verifix.CFG import Concretize

#region: Fix end-states

def add_endState(fnc:parser.Function):
    '''Given a function, add an end state. Make each dead-end point towards this.'''
    endloc = max(fnc.loctrans.keys()) + 1
    fnc.addloc(loc=endloc, desc='EndState')

    for loc in sorted(fnc.locexprs.keys()):
        if loc != endloc:
            if fnc.loctrans[loc][True] is None and fnc.loctrans[loc][False] is None:
                fnc.addtrans(loc, True, endloc)
                
    return endloc

def fix_returnTrans(prog:parser.Program):
    '''If return value assigned, transition to end state'''
    # locexprs, locdescs, loctrans

    # For each func
    for fncKey, fnc in prog.fncs.items():
        endloc = add_endState(fnc) # Add an end state
        fnc.endloc = endloc
        
        # For each block
        for loc in sorted(fnc.locexprs.keys()):
            for (var, expr) in fnc.locexprs[loc]: # If it contains
                if var == model.VAR_RET: # Return value assignment
                    fnc.rmtrans(loc, True) # Remove old trans
                    assert fnc.loctrans[loc][False] is None, \
                        "Error in returnTrans assignment (has False transition): '%s'" % (loc,)
                    fnc.addtrans(loc, True, endloc) # Transition to end-state

#endregion        

#region: Merge True blocks
def mergeTrue_fnc(fnc:parser.Function):
    prevLocs = []
    nextLocs = [fnc.initloc]    

    while len(nextLocs) != 0:
        currLoc = nextLocs.pop(0)
        prevLocs.append(currLoc)
        locTrue, locFalse = fnc.loctrans[currLoc][True], fnc.loctrans[currLoc][False]

        # Enqueue
        if locTrue is not None and locTrue not in prevLocs:
            nextLocs.append(locTrue)
        if locFalse is not None and locFalse not in prevLocs:
            nextLocs.append(locFalse)
    
        # Case A: Start of function, with only True trans
        if currLoc == fnc.initloc and locFalse is None and locTrue is not None: 
            if len(fnc.locexprs[currLoc]) == 0: # and no expressions in beginning
                fnc.initloc = locTrue
                fnc.rmloc(currLoc)

        # Case B: Check if next block is a True block, to be merged
        else: 
            pass
            # for cond in [True, False]:
            #     nextLoc = fnc.loctrans[currLoc][cond]

            #     if nextLoc is not None:
            #         nextLocTrue, nextLocFalse = fnc.loctrans[nextLoc][True], fnc.loctrans[nextLoc][False]
                    
            #         if nextLocTrue is not None and nextLocFalse is None: # Next loc is True
            #             fnc.locexprs[currLoc] += fnc.locexprs[nextLocTrue]

def mergeTrue(prog:parser.Program):
    for fncKey, fnc in prog.fncs.items():
        mergeTrue_fnc(fnc)

#endregion

#region: ITE

def checkIf_simple(fnc:model.Function, locIn, locOut):
    '''Checks if the if-cond is simple: No transition in false branch, and true branch = locOut '''
    return fnc.loctrans[locIn][False] is None and fnc.loctrans[locIn][True] == locOut

def checkIf_simple_rec(fnc:model.Function, locIn, locOut):
    #check whether the true transition of the if stmt lead to another if check, only when all nested if stmts do not have break, continue, return. It is true
    if fnc.loctrans[locIn][False] is None and fnc.loctrans[locIn][True] == locOut:
        return True
    elif fnc.loctrans[locIn][True] != locOut:
        # if Concretize.is_ifCond(fnc.loctrans[locIn][True])
        a = fnc.loctrans[locIn][True]
        if Concretize.is_ifCond(fnc, a):
            locCond, locThen, locOut, locElse = Concretize.get_ifLoc(fnc, a)
            return checkIf_simple_rec(fnc, locThen, locOut) and (locElse is None or checkIf_simple_rec(fnc, locElse, locOut))
        else:
            return False



def replIf_ite_cond(fnc:model.Function, locCond):
    '''Extract cond expr and prep locCond for replacement'''
    # Extract exprCond
    varCond, exprCond = Concretize.get_condVarExpr(fnc, locCond)        

    # Prep locCond for replacement
    fnc.locexprs[locCond] = []
    fnc.locdescs[locCond] = fnc.locdescs[locCond].replace('condition of the if-statement', 'ITE')

    return exprCond

def replIf_ite_exprs(fnc:model.Function, locCond, locIn, exprCond):
    '''Replace each (var, expr) inside locIn with ite(cond, expr, var)'''
    if locIn is not None:
        for var, expr in fnc.locexprs[locIn]:
            arg1, arg2, arg3 = exprCond, expr, model.Var(var) # If cond, then expr, else var (retain old var)
            expr_ite = model.Op('ite', *[arg1, arg2, arg3])
            fnc.addexpr(locCond, var, expr_ite)

def replIf_ite_exprs_rec(fnc:model.Function, locCond, locIn, exprCond):
    '''Replace each (var, expr) inside locIn with ite(cond, expr, var)'''
    if locIn is not None:
        if Concretize.is_ifCond(fnc, fnc.loctrans[locIn][True]):
            newlocCond, locThen, locOut, locElse = Concretize.get_ifLoc(fnc, fnc.loctrans[locIn][True])
            replIf_ite_locIn(fnc, newlocCond, locThen, locElse, locOut, exprCond)
            # fnc.loctrans[locCond][True] = newlocCond
            # fnc.loctrans[locCond][False] = None
        for var, expr in fnc.locexprs[locIn]:
            arg1, arg2, arg3 = exprCond, expr, model.Var(var) # If cond, then expr, else var (retain old var)
            expr_ite = model.Op('ite', *[arg1, arg2, arg3])
            fnc.addexpr(locCond, var, expr_ite)

def replIf_ite_locIn(fnc:model.Function, locCond, locThen, locElse, locOut, preCond=None):
    '''For each (var,expr) inside basic-block at locIn, replace with ite(exprCond). Also fix the transitions'''
    # Fetch cond
    condThen = replIf_ite_cond(fnc, locCond) # Extract cond & empty locCond
    condElse = model.Op(parser.Parser.NOTOP, condThen)

    if preCond != None:
        condThen = model.Op('&&', preCond, condThen)
        condElse = model.Op('&&', preCond, condElse)
        
    # Repl exprs with ite
    replIf_ite_exprs_rec(fnc, locCond, locThen, condThen) # Repl all exprs inside locIn with ite
    replIf_ite_exprs_rec(fnc, locCond, locElse, condElse) # Repl all exprs inside locIn with ite
  

    # Fix trans
    if locThen and Concretize.is_iteCond(fnc, fnc.loctrans[locThen][True]):
        for var, ite in fnc.locexprs[fnc.loctrans[locThen][True]]:
            fnc.addexpr(locCond, var, ite)
        fnc.rmloc(fnc.loctrans[locThen][True])

    if locElse and Concretize.is_iteCond(fnc, fnc.loctrans[locElse][True]):
        for var, ite in fnc.locexprs[fnc.loctrans[locElse][True]]:
            fnc.addexpr(locCond, var, ite)
        fnc.rmloc(fnc.loctrans[locElse][True])

    fnc.loctrans[locCond][True] = locOut
    fnc.loctrans[locCond][False] = None

    # Delete locs
    fnc.rmloc(locThen)
    if locElse:
        fnc.rmloc(locElse)

    locAfter = fnc.loctrans[locCond][True]
    locAfterOut = fnc.loctrans[locAfter][True]

    for var, ite in fnc.locexprs[locAfter]:
        fnc.addexpr(locCond, var, ite)
    fnc.rmloc(locAfter)
    fnc.loctrans[locCond][True] = locAfterOut

def replIf_ite(prog:parser.Program):
    '''Replace all simple non-branching if-cond with ite Op'''
    # For each loc in fnc
    for fnc in prog.fncs.values():
        locs = list(fnc.loctrans.keys())
        for loc in locs:
            
            # If it is a conditional loc
            if Concretize.is_ifCond(fnc, loc):
                locCond, locThen, locOut, locElse = Concretize.get_ifLoc(fnc, loc)

                # The then and else part are "simple" - exits to locOut
                if checkIf_simple_rec(fnc, locThen, locOut):
                    if locElse is None or checkIf_simple_rec(fnc, locElse, locOut):
                        
                        # replace to ite                        
                        replIf_ite_locIn(fnc, locCond, locThen, locElse, locOut)

def merge_ite_iter(prog:parser.Program):

    exist_unmerged = True
    while(exist_unmerged):
        exist_unmerged = merge_ite_prog(prog)


def merge_ite_prog(prog:parser.Program):
    for fnc in prog.fncs.values():
        locs = list(fnc.loctrans.keys())
        for loc in locs:
            if Concretize.is_iteCond(fnc, loc):
                merged = merge_ite(fnc, loc)
                if merged:
                    return True
    return False



def merge_ite(fnc, loc):
    locOut = fnc.loctrans[loc][True]
    if Concretize.is_iteCond(fnc, locOut):
        fnc.locexprs[loc] += fnc.locexprs[locOut]
        fnc.loctrans[loc][True] = fnc.loctrans[locOut][True]
        fnc.rmloc(locOut)
        return True
    return False

def merge_none_false_branch_blocks(prog):
    for fnc in prog.fncs.values():
        locs = list(fnc.loctrans.keys())
        for loc in locs:
            while(Concretize.is_none_false_branch(fnc, loc)):
                merge_block(fnc, loc)
    return False

def merge_block(fnc, loc):

    locOut = fnc.loctrans[loc][True]

    fnc.locexprs[loc] += fnc.locexprs[locOut]
    fnc.loctrans[loc][True] = fnc.loctrans[locOut][True]
    fnc.loctrans[loc][False] = fnc.loctrans[locOut][False]
    fnc.rmloc(locOut)

    return True

def index_ite(prog):
    for fnc in prog.fncs.values():
        locs = list(fnc.loctrans.keys())
        for loc in locs:
            preexpr = None
            num_of_input = 0
            for index, (var, expr) in enumerate(fnc.locexprs[loc]):
                if Concretize.is_ite(fnc, expr):
                    if Concretize.is_ite(fnc, preexpr):
                        if expr.args[0] == preexpr.args[0]:
                            expr.condIdx = preexpr.condIdx
                        else:
                            expr.condIdx = index - num_of_input
                    else:
                        expr.condIdx = index - num_of_input
                if var == '$in':
                    num_of_input += 1
                preexpr = expr
#endregion


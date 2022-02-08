from srcU.ClaraP import parser, model, c_parser

from typing import Union, List
import re

def raise_exceptionExpr(expr):
    raise Exception('Unknown expr {} in concretize!'.format(expr))



class Concrete:
    def __init__(self, exprStr, flag_noAssign=False, flag_break=False, flag_noOp=False, flag_addEOL=True):
        '''flag_noAssign: don't print a "var = expr" format
        flag_break: don't execute future locs inside this block'''
        self.exprStr = exprStr
        self.flag_noAssign = flag_noAssign
        self.flag_break = flag_break
        self.flag_addEOL = flag_addEOL
        self.flag_noOp = flag_noOp

    def __str__(self):
        return self.exprStr

#region: Concretize Ops

def concretize_op_noArgs(op:model.Op, var:str, ignoreSpl) -> Concrete:  
    if op.name in ['break', 'continue']:
        return Concrete(op.name, flag_noAssign=True, flag_break=True)

    elif op.name == 'True':
        return Concrete('1')
    elif op.name == 'False':
        return Concrete('0')
        
    raise_exceptionExpr(op)


def concretize_op_unary(op:model.Op, var:str, ignoreSpl) -> Concrete:
    '''TODO: Update ListHead and ListTail - approximated for now'''
    expr1 = op.args[0]
    
    if op.name in ['!', '-', '+']:
        expr1_str = concretize_expr_rec(expr1, var, ignoreSpl)
        exprStr1 = expr1_str.exprStr
        if not (type(expr1) is model.Var or type(expr1) is model.Const):
            exprStr1 = '(' + expr1_str.exprStr + ')'
        return Concrete('{} {}'.format(op.name, exprStr1))

    elif op.name in c_parser.CParser.LIB_FNCS:
        return concretize_funcCall(op.name, op.args, var, ignoreSpl)

    elif op.name == 'ListTail': # ListTail($in)
        raise_exceptionExpr(op)



    raise_exceptionExpr(op)

def concretize_op_binary(op:model.Op, var:str, ignoreSpl) -> Concrete:
    '''TODO: Update ListHead and ListTail - approximated for now'''
    expr1, expr2 = op.args[0], op.args[1]
    if op.name == '=':
        expr1_str, expr2_str = concretize_expr_rec(expr1, var, ignoreSpl), concretize_expr_rec(expr2, var, ignoreSpl)
        exprStr1, exprStr2 = expr1_str.exprStr, expr2_str.exprStr
        return Concrete('{}={}'.format(exprStr1, exprStr2))

    elif op.name in ['+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||']:
        expr1_str, expr2_str = concretize_expr_rec(expr1, var, ignoreSpl), concretize_expr_rec(expr2, var, ignoreSpl)
        exprStr1, exprStr2 = expr1_str.exprStr, expr2_str.exprStr
        if not (type(expr1) is model.Var or type(expr1) is model.Const):
            exprStr1 = '(' + expr1_str.exprStr + ')'
        if not (type(expr2) is model.Var or type(expr2) is model.Const):
            exprStr2 = '(' + expr2_str.exprStr + ')'
        return Concrete('{} {} {}'.format(exprStr1, op.name, exprStr2))

    elif op.name == 'ListHead': # ListHead(int, $in)
        if expr1.value == 'int':
            return Concrete('scanf("{}", &{})'.format('%d', var), flag_noAssign=True)
        elif expr1.value == 'float':
            return Concrete('scanf("{}", &{})'.format('%f', var), flag_noAssign=True)
        elif expr1.value == 'char' or expr1.value == '*':
            return Concrete('scanf("{}", &{})'.format('%c', var), flag_noAssign=True)
        elif expr1.value == 'string':
            return Concrete('scanf("{}", &{})'.format('%c', var), flag_noAssign=True)
    elif op.name == 'StrAppend':
        if expr1.name == '$out':
            return concretize_expr_rec(expr2, var, ignoreSpl)

    elif op.name in c_parser.CParser.LIB_FNCS:
        return concretize_funcCall(op.name, op.args, var, ignoreSpl)

    elif op.name == 'cast':
        # corner case when cast type
        expr1_str = expr1.value
        expr2_str = concretize_expr_rec(expr2, var, ignoreSpl)
        return Concrete('({}){}'.format(expr1_str, expr2_str))

    elif op.name == '[]':
        expr1_str = expr1.name
        expr2_str = concretize_expr_rec(expr2, var, ignoreSpl)

        return Concrete('{}[{}]'.format(expr1_str, expr2_str))

    elif op.name == 'ArrayCreate':
        return concretize_array_create(expr1, expr2, var, ignoreSpl)

    raise_exceptionExpr(op)
    
def concretize_op_nary(op:model.Op, var:str, ignoreSpl) -> Concrete:
    if op.name == 'StrFormat':
        expr_str = ','.join([concretize_expr_rec(expr, var, ignoreSpl).exprStr for expr in op.args])
        return Concrete(expr_str)

    elif op.name == 'ite':
        exprStr_cond = concretize_expr_rec(op.args[0], var, ignoreSpl=True)
        exprStr_then = concretize_expr_str(op.args[1], var, ignoreSpl=False)

        expr_str = 'if({}) {}'.format(exprStr_cond, exprStr_then)
        if len(op.args) == 3 and str(op.args[2]) != var: # else exits
            exprStr_else = concretize_expr_str(op.args[2], var, ignoreSpl=False)
            expr_str = 'if({}) {} else {}'.format(exprStr_cond, exprStr_then, exprStr_else)        
            
        return Concrete(expr_str, flag_noAssign=True, flag_addEOL=False)

    elif op.name == 'ArrayAssign':
        if 'ListHead' in str(op.args[2]):
            length = concretize_expr_rec(op.args[1], var, ignoreSpl)
            var_str = op.args[0].name + '[' + str(length) + ']'
            expr = concretize_expr_rec(op.args[2], var_str, ignoreSpl)
            return expr
        else:
            idx = concretize_expr_rec(op.args[1], var, ignoreSpl)
            expr = concretize_expr_rec(op.args[2], var, ignoreSpl)
            return Concrete('{}[{}] = {}'.format(op.args[0], idx, expr))

    raise_exceptionExpr(op)

def concretize_op(op:model.Op, var:str, ignoreSpl) -> Concrete:
    if op.name in ['StrFormat', 'ite']:
        return concretize_op_nary(op, var, ignoreSpl)

    elif len(op.args) == 0:
        return concretize_op_noArgs(op, var, ignoreSpl)

    elif len(op.args) == 1:
        return concretize_op_unary(op, var, ignoreSpl)

    elif len(op.args) == 2:
        return concretize_op_binary(op, var, ignoreSpl)

    else:
        return concretize_op_nary(op, var, ignoreSpl)
    
    raise_exceptionExpr(op)

#endregion


#region: Concretize expr

def concretize_ret(expr:model.Expr, var:str) -> Concrete:
    # If expr is an unknown $ret
    try:
        if expr.name == '$ret':
            return Concrete('return 0', flag_noAssign=True)
    except AttributeError:
        pass
    
    expr_str = concretize_expr_rec(expr, var, ignoreSpl=True)

    # If expr is not to be assigned
    if expr_str.flag_noAssign:
        return expr_str

    # Else, return the expr        
    return Concrete('return {}'.format(expr_str), flag_noAssign=True)

def concretize_out(expr:model.Expr, var:str) -> Concrete:
    expr_str = concretize_expr_rec(expr, var, ignoreSpl=True)

    # If expr is not to be assigned
    if expr_str.flag_noAssign:
        return expr_str

    # Else, return the expr 
    return Concrete('printf({})'.format(expr_str), flag_noAssign=True)


def concretize_expr_rec(expr:model.Expr, var:str, ignoreSpl) -> Concrete:
    if expr == 'True' or expr is True:
        raise_exceptionExpr(expr)
    elif expr == 'False' or expr is False:
        raise_exceptionExpr(expr)

    # Special return case
    elif not ignoreSpl and var == '$ret': 
        return concretize_ret(expr, var)

    # Skip input list manipulations
    elif not ignoreSpl and var == '$in': 
        return Concrete('', flag_noOp=True) 
    
    # Special output case
    elif not ignoreSpl and var == '$out':  
        return concretize_out(expr, var)

    # Constant
    elif type(expr) is model.Const:
        return Concrete(expr.value)

    # Normal variable
    elif type(expr) is model.Var:        
        return Concrete(expr.name)

    # Func call
    elif type(expr) is model.Op and expr.name == 'FuncCall':
        return concretize_funcCall_op(expr, var, ignoreSpl)

    # Op
    elif type(expr) is model.Op:
        return concretize_op(expr, var, ignoreSpl)

    raise raise_exceptionExpr(expr)

def concretize_expr_str(expr:model.Expr, var:str, ignoreSpl, flag_addEOL=True, flag_noAssign=False) -> str:
    expr_str = concretize_expr_rec(expr, var, ignoreSpl=ignoreSpl)

    if isinstance(expr, model.Op) and 'Array' in expr.name:
            blockStr = expr_str.exprStr

     # if special case (either caller or callee don't want to assign), print the expr as it is (no assignment)
    elif expr_str.flag_noAssign or var == '_' or flag_noAssign:
        blockStr = '{}'.format(expr_str)

    # Else, assign expr to variable
    elif var == expr_str.exprStr:
        return ''

    else:
        blockStr = '{} = {}'.format(var, expr_str)

# If both caller and callee want to add a semi-colon
    if flag_addEOL and expr_str.flag_addEOL:
        blockStr += ';'

    return blockStr

#endregion

#region: concretize cond/data
def get_condVarExpr(fnc:model.Function, loc:int):
    '''Fetch a single condVar and condExpr'''

    if len(fnc.locexprs[loc]) == 1:
        condVar, condExpr = fnc.locexprs[loc][0]

    elif len(fnc.locexprs[loc]) == 2:
        var1, expr1 = fnc.locexprs[loc][0]
        var2, expr2 = fnc.locexprs[loc][1]

        if var2 == '$cond' and str(expr2) == str(var1):
            condVar, condExpr = var2, model.Op('==', expr2, expr1)
        else:
            raise Exception('Concretize: Cond locexprs with two exprs %s' % (fnc.locexprs[loc]))

    else:
        raise Exception('Concretize: Cond locexprs has more than two %s' % (fnc.locexprs[loc]))

    assert condVar == '$cond', 'Concretize: $cond variable does not exist' % (fnc.locexprs[loc])
    return condVar, condExpr

def concretize_cond(fnc:model.Function, loc:int, ignoreSpl):
    condVar, condExpr = None, None
    condExprStr = ''

    for var, expr in fnc.locexprs[loc]:
        # Store the $cond, to add later
        if var == '$cond':
            assert condVar != var, 'Concretize: multiple $cond variables exist! %s' % (fnc.locexprs[loc])
            condVar, condExpr = var, expr

        # Add other statements by appending a comma "," at the end
        else:
            exprStr = concretize_expr_str(expr, var, ignoreSpl, flag_addEOL=False, flag_noAssign=False)
            condExprStr += exprStr + ', '

    assert condVar is not None, 'Concretize: $cond variable does not exist' % (fnc.locexprs[loc])    
    exprStr = concretize_expr_str(condExpr, condVar, ignoreSpl, flag_addEOL=False, flag_noAssign=True)
    condExprStr += exprStr

    return condExprStr


def concretize_block(fnc:model.Function, loc:int, seen:list, lines:list, flag_addLines=True, flag_addEOL=True):
    '''TODO: Handle flag_break properly - returning string for now'''
    blocks_str = []
    flagBreak = False

    if loc in fnc.locexprs:
        expr_str = None

        for (var, expr) in fnc.locexprs[loc]:
            if var == '$in':
                continue
            expr_str = concretize_expr_str(expr, var, ignoreSpl=False, flag_addEOL=flag_addEOL)
            blocks_str.append((expr_str))

            # if expr_str is not None:
            #     flagBreak = flagBreak or expr_str.flag_break

    if flag_addLines:
        lines.extend(blocks_str)

    return '\n'.join(blocks_str), flagBreak


#endregion

#region: concretize function

def concretize_headers(prog:model.Program, lines):
    headers = ['stdio.h', 'stdlib.h', 'math.h']
    for header in headers:
        lines.append('#include<{}>'.format(header))

def concretize_funcDecl(prog:model.Program, lines):
    for fnc in prog.fncs.values():
        params_str = ','.join([typeStr +' '+ name for name, typeStr in fnc.params])
        func_decl = '{} {}({});'.format(fnc.rettype, fnc.name, params_str)

        lines.append(func_decl)

def concretize_funcDef(fnc, lines):
    param_names = [name for name, typeStr in fnc.params]
    params_str = ','.join([typeStr +' '+ name for name, typeStr in fnc.params])
    func_def = '{} {}({}) {{'.format(fnc.rettype, fnc.name, params_str)
    var_decls = [] # Decl all variables, except function args
    for var_name, type_str in fnc.types.items():
        if var_name not in param_names:
            if len(re.findall(r"\[[\s\S]*\]", type_str)) > 0:
                pass
            else:
                var_decls.append('{} {};'.format(type_str, var_name))
    lines.append(func_def)
    lines.extend(var_decls)

def concretize_funcCall(name:str, args, var:str, ignoreSpl):
    exprStr = '{}({})'.format(name, 
        ','.join([concretize_expr_rec(arg, var, ignoreSpl).exprStr for arg in args]))

    return Concrete(exprStr)

def concretize_funcCall_op(op:model.Op, var:str, ignoreSpl):
    return concretize_funcCall(op.args[0], op.args[1:], var, ignoreSpl)

#endregion

#region: concretize for loop

def get_forLoc(fnc:model.Function, locCond:int):
    lineNum = re.findall(r'line (\d+)',fnc.locdescs[locCond])[0]
    
    # locIn and locOut are obtained from trans of cond block
    locIn, locOut = fnc.loctrans[locCond][True], fnc.loctrans[locCond][False]

    # loop update needs a search over all desc with same lineNum
    locUpdate = None
    for loc, desc in fnc.locdescs.items():
        if desc.strip() == "update of the 'for' loop at line %s" % (lineNum):
            locUpdate = loc
            break

    return locCond, locUpdate, locIn, locOut
    

def concretize_forLoop(fnc:model.Function, loc:int, locStops:List[int], seen:list, lines:list):
    locCond, locUpdate, locIn, locOut = get_forLoc(fnc, loc)
    condStr = concretize_cond(fnc, locCond, ignoreSpl=False)
    updateStr, flagBreak = concretize_block(fnc, locUpdate, seen, lines, flag_addLines=False, flag_addEOL=False)

    # Add loop cond and update
    lines.append('for(; {}; {}) {{'.format(condStr, updateStr))
    seen.extend([locCond, locUpdate])

    # Recurse inside loop body
    concretize_loc(fnc, locIn, locStops + [locOut], seen, lines)
    lines.append('}')

    # Recurse after loop body
    concretize_loc(fnc, locOut, locStops, seen, lines)

#endregion

#region: Concretize while loop

def get_whileLoc(fnc:model.Function, locCond:int):    
    # locIn and locOut are obtained from trans of cond block
    locIn, locOut = fnc.loctrans[locCond][True], fnc.loctrans[locCond][False]

    return locCond, locIn, locOut

def concretize_whileLoop(fnc:model.Function, loc:int, locStops:List[int], seen:list, lines:list):
    locCond, locIn, locOut = get_whileLoc(fnc, loc)
    condStr = concretize_cond(fnc, locCond, ignoreSpl=False)

    # Add loop cond and update
    lines.append('while({}) {{'.format(condStr))
    seen.extend([locCond])

    # Recurse inside loop body
    concretize_loc(fnc, locIn, locStops + [locOut], seen, lines)
    lines.append('}')

    # Recurse after loop body
    concretize_loc(fnc, locOut, locStops, seen, lines)

#endregion

#region: Concretize do while loop

def get_doWhileLoc(fnc:model.Function, locIn:int):
    locCond = fnc.loctrans[locIn][True]
    locOut = fnc.loctrans[locCond][False]
    return locCond, locOut

def concretize_doWhileLoop(fnc:model.Function, loc:int, locStops:List[int], seen:list, lines:list):
    locCond, locOut = get_doWhileLoc(fnc, loc)
    condStr = concretize_cond(fnc, locCond, ignoreSpl=False)

    # Add do and update
    lines.append('do{')

    # Recurse inside the body
    concretize_block(fnc, loc, seen, lines)
    lines.append('}}while({});'.format(condStr))
    seen.extend([locCond])
    # Recurse after the loop body
    concretize_loc(fnc, locOut, locStops, seen, lines)

#endregion

#region: Concretize conditional

def get_ifLoc(fnc:model.Function, locCond:int):
    lineNum = re.findall(r'line (\d+)',fnc.locdescs[locCond])[0]
    
    # locIn and locOut are obtained from trans of cond block
    locIn, locElse = fnc.loctrans[locCond][True], fnc.loctrans[locCond][False]

    # Verify locElse points to an else branch
    if locElse is None or 'inside the else-branch starting' not in fnc.locdescs[locElse]:
        locElse = None

    # locOut needs a search over all desc with same lineNum
    locOut = None
    for loc, desc in fnc.locdescs.items():
        if desc.strip() == "after the if-statement beginning at line %s" % (lineNum):
            locOut = loc
            break

    return locCond, locIn, locOut, locElse

def concretize_if(fnc:model.Function, loc:int, locStops:List[int], seen:list, lines:list):
    locCond, locIn, locOut, locElse = get_ifLoc(fnc, loc)
    condStr = concretize_cond(fnc, locCond, ignoreSpl=False)

    # Add if cond 
    lines.append('if({}) {{'.format(condStr))
    seen.extend([locCond])

    # Recurse inside if-branch
    concretize_loc(fnc, locIn, locStops + [locOut], seen, lines)
    lines.append('}')

    # Add else-branch, if it exists
    if locElse is not None:
        lines.append('else {')
        concretize_loc(fnc, locElse, locStops + [locOut], seen, lines)
        lines.append('}')

    # Recurse after if-cond 
    concretize_loc(fnc, locOut, locStops, seen, lines)
    

#endregion


#region: Check for branches

def is_forLoop(fnc:model.Function, loc:int):
    if loc in fnc.locdescs:
        return "the condition of the 'for' loop" in fnc.locdescs[loc]

def is_whileLoop(fnc:model.Function, loc:int):
    if loc in fnc.locdescs:
        return "the condition of the 'while' loop" in fnc.locdescs[loc]

def is_doWhileLoop(fnc:model.Function, loc:int):
    if loc in fnc.locdescs:
        return "inside the body of the 'do-while' loop" in fnc.locdescs[loc]

def is_loop(fnc:model.Function, loc:int):
    return is_forLoop(fnc, loc) or is_whileLoop(fnc, loc)

def is_ifCond(fnc:model.Function, loc:int):
    if loc in fnc.locdescs:
        return "the condition of the if-statement" in fnc.locdescs[loc]

def is_iteCond(fnc:model.Function, loc:int):
    if loc in fnc.locdescs:
        return "the ITE" in fnc.locdescs[loc]

def is_none_false_branch(fnc:model.Function, loc:int):
    if loc in fnc.locdescs:

        if 'EndState' in fnc.locdescs[loc]:
            return False

        if 'EndState' in fnc.locdescs[fnc.loctrans[loc][True]]:
            return False

        if fnc.loctrans[loc][False] == None and 'for' not in fnc.locdescs[fnc.loctrans[loc][True]] and 'while' not in fnc.locdescs[fnc.loctrans[loc][True]] and 'if' not in fnc.locdescs[fnc.loctrans[loc][True]]:
            return True

def is_cond(fnc, currLoc):
    isCondLoc = model.VAR_COND in [var for (var, expr) in fnc.locexprs[currLoc]]
    return isCondLoc

def is_ite(fnc, op):
    if op is None or not isinstance(op, model.Op):
        return False
    isIte = 'ite' in op.name
    return isIte
#endregion

#region: concretize prog

def concretize_loc(fnc:model.Function, loc:int, locStops:List[int], seen, lines):
    '''restrict_noBranch = restrict exploration to non-branch blocks'''
    # Early exit if already seen
    if loc in seen or loc is None: 
        return
    seen.append(loc)

    # Case-1: Loop struct
    if is_forLoop(fnc, loc):
        concretize_forLoop(fnc, loc, locStops, seen, lines)

    elif is_whileLoop(fnc, loc):
        concretize_whileLoop(fnc, loc, locStops, seen, lines)
        
    elif is_doWhileLoop(fnc, loc):
        concretize_doWhileLoop(fnc, loc, locStops, seen, lines)
    
    # Case-2: if-conditional 
    elif is_ifCond(fnc, loc):
        concretize_if(fnc, loc, locStops, seen, lines)

    # Case-3: Single non-branching block
    else:
        locTrue, locFalse = fnc.loctrans[loc][True], fnc.loctrans[loc][False]
        assert locFalse is None,\
            'Concretize: Non-branch block has False branch %s' % (loc)
        
        block_str, flagBreak = concretize_block(fnc, loc, seen, lines) # Concretize the block
        if not flagBreak: # Unless a return or break or continue statement was encountered
            if locTrue not in locStops: # Or some visitor wants to stop at a particular loc
                concretize_loc(fnc, locTrue, locStops, seen, lines) # Concretizing the next loc
    

def concretize_prog(prog:model.Program):
    '''Given a model.Program, concretize it''' 
    lines = []
    
    # Concretize headers and all func decls first (to produce compilable prog)
    concretize_headers(prog, lines)
    concretize_funcDecl(prog, lines)
    
    for fnc in prog.fncs.values():
        seen = []

        # Concretize a function def, and all blocks starting from initloc
        concretize_funcDef(fnc, lines)
        concretize_loc(fnc, fnc.initloc, [fnc.endloc], seen, lines)

        lines.append('}')

    # print('\n'.join(lines))
    return '\n'.join(lines)

#endregion

#region: concretize array
def concretize_array_create(range, type, var:str, ignoreSpl):


    range_str = concretize_expr_rec(range, var, ignoreSpl=ignoreSpl)
    type_str = concretize_expr_rec(type, var, ignoreSpl=ignoreSpl)

    return Concrete('{} {}[{}]'.format(type_str, var, range_str))


from srcU.ClaraP import parser, model, c_parser

from typing import Union, List
import re
from zss import Node, simple_distance


def raise_exceptionExpr(expr):
    raise Exception('Unknown expr {} in ast!'.format(expr))


class AST:
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


# region: Concretize Ops

def ast_op_noArgs(op: model.Op, var: str, ignoreSpl):
    if op.name in ['break', 'continue']:
        return [Node(op.name)]
        # return AST(op.name, flag_noAssign=True, flag_break=True)

    elif op.name == 'True':
        return [Node('1')] #AST('1')
    elif op.name == 'False':
        return [Node('0')]

    raise_exceptionExpr(op)


def ast_op_unary(op: model.Op, var: str, ignoreSpl) -> Node:
    '''TODO: Update ListHead and ListTail - approximated for now'''
    expr1 = op.args[0]
    node = Node(op.name)
    if op.name in ['!', '-', '+']:
        expr1_node = ast_expr_rec(expr1, var, ignoreSpl)
        node.addkid(expr1_node)
        #exprStr1 = expr1_str.exprStr
        # if not (type(expr1) is model.Var or type(expr1) is model.Const):
        #     exprStr1 = '(' + expr1_str.exprStr + ')'
        return [node] #AST('{} {}'.format(op.name, exprStr1))

    elif op.name in c_parser.CParser.LIB_FNCS:
        return ast_funcCall(op.name, op.args, var, ignoreSpl)

    elif op.name == 'ListTail':  # ListTail($in)
        raise_exceptionExpr(op)

    elif op.name == 'ArrayCreate':
        expr1_node = ast_expr_rec(expr1, var, ignoreSpl)
        node.addkid(expr1_node)
        return [node]

    raise_exceptionExpr(op)


def ast_op_binary(op: model.Op, var: str, ignoreSpl):
    '''TODO: Update ListHead and ListTail - approximated for now'''
    expr1, expr2 = op.args[0], op.args[1]

    if op.name in ['+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||']:
        node = Node(op.name)
        expr1_node, expr2_node = ast_expr_rec(expr1, var,ignoreSpl), ast_expr_rec(expr2, var,ignoreSpl)
        node.addkid(expr1_node)
        node.addkid(expr2_node)

        return [node]
    elif op.name == 'ListHead':  # ListHead(int, $in)
            node = Node(op.name)
            node.addkid([Node(str(expr1))])
            node.addkid([Node(str(expr2))])
            return [node]

    elif op.name == 'StrAppend':
        if expr1.name == '$out':
            # might have problem here
            return ast_expr_rec(expr2, var, ignoreSpl)
        elif expr1.name == 'StrAppend':
            expr1_node = ast_op(expr1, var, ignoreSpl)
            expr2_node = ast_op(expr2, var, ignoreSpl)
            node = Node(op.name)
            node.addkid(expr1_node)
            node.addkid(expr2_node)
            return [node]
            # return ast_op_binary(expr1, var, ignoreSpl)
    elif op.name in c_parser.CParser.LIB_FNCS:
        return ast_funcCall(op.name, op.args, var, ignoreSpl)

    elif op.name == 'cast':
        # corner case when cast type
        return ast_funcCall(op.name, op.args, var, ignoreSpl)

    elif op.name == '[]':
        node = Node(op.name)
        expr1_node = [Node(expr1.name)]
        expr2_node = ast_expr_rec(expr2, var, ignoreSpl)
        node.addkid(expr1_node)
        node.addkid(expr2_node)
        return [node]

    elif op.name == 'ArrayCreate':
        node = Node(op.name)
        expr1_node = ast_expr_rec(expr1, var, ignoreSpl)
        expr2_node = ast_expr_rec(expr2, var, ignoreSpl)

        node.addkid(expr1_node)
        node.addkid(expr2_node)
        return [node]

    raise_exceptionExpr(op)


def ast_op_nary(op: model.Op, var: str, ignoreSpl):
    if op.name == 'StrFormat':
        node = Node('StrFormat')
        for expr in op.args:
            expr_node = ast_expr_rec(expr, var, ignoreSpl)
            node.addkid(expr_node)
        #expr_str = ','.join([ast_expr_rec(expr, var, ignoreSpl).exprStr for expr in op.args])
        return [node]

    elif op.name == 'ite':
        node = Node('If')
        exprNode_cond = ast_expr_rec(op.args[0], var, ignoreSpl=True)
        exprNode_then = ast_expr_str(op.args[1], var, ignoreSpl=False)
        node.addkid(exprNode_cond)
        node.addkid(exprNode_then)
        #expr_str = 'if({}) {}'.format(exprStr_cond, exprStr_then)
        if len(op.args) == 3 and str(op.args[2]) != var:  # else exits
            exprNode_else = ast_expr_str(op.args[2], var, ignoreSpl=False)
            node.addkid(exprNode_else)
            #expr_str = 'if({}) {} else {}'.format(exprStr_cond, exprStr_then, exprStr_else)
        return [node]
        # return AST(expr_str, flag_noAssign=True, flag_addEOL=False)

    elif op.name == 'ArrayAssign':
        if 'ListHead' in str(op.args[2]):
            length_node = ast_expr_rec(op.args[1], var, ignoreSpl)
            var_str = op.args[0].name + '[' + str(length_node[0].label) + ']'
            expr_node = ast_expr_rec(op.args[2], var_str, ignoreSpl)

            node = Node(op.name)

            node.addkid(length_node)
            node.addkid(expr_node)
            return [node]
        else:
            idx_node = ast_expr_rec(op.args[1], var, ignoreSpl)
            expr_node = ast_expr_rec(op.args[2], var, ignoreSpl)

            node = Node(op.name)
            node.addkid(idx_node)
            node.addkid(expr_node)
            return [node]

    raise_exceptionExpr(op)


def ast_op(op: model.Op, var: str, ignoreSpl):
    if op.name in ['StrFormat', 'ite']:
        return ast_op_nary(op, var, ignoreSpl)

    elif len(op.args) == 0:
        return ast_op_noArgs(op, var, ignoreSpl)

    elif len(op.args) == 1:
        return ast_op_unary(op, var, ignoreSpl)


    elif len(op.args) == 2:
        return ast_op_binary(op, var, ignoreSpl)

    else:
        return ast_op_nary(op, var, ignoreSpl)

    raise_exceptionExpr(op)


# endregion


# region: Concretize expr

def ast_ret(expr: model.Expr, var: str) -> Node:
    # If expr is an unknown $ret
    try:
        if expr.name == '$ret':
            return [Node("Return")] #AST('return 0', flag_noAssign=True)
    except AttributeError:
        pass

    expr_str = ast_expr_rec(expr, var, ignoreSpl=True)

    return expr_str

def ast_out(expr: model.Expr, var: str):

    expr_node = ast_expr_rec(expr, var, ignoreSpl=True)

    return expr_node

def ast_expr_rec(expr: model.Expr, var: str, ignoreSpl):

    if expr == 'True' or expr is True:
        raise_exceptionExpr(expr)
    elif expr == 'False' or expr is False:
        raise_exceptionExpr(expr)

    # Special return case
    elif not ignoreSpl and var == '$ret':
        return ast_ret(expr, var)

    # Skip input list manipulations
    elif not ignoreSpl and var == '$in':
        return [Node('')]
#        return AST('', flag_noOp=True, flag_addEOL=False)

    # Special output case
    elif not ignoreSpl and var == '$out':
        return ast_out(expr, var)

    # Constant
    elif type(expr) is model.Const:
        return [Node(str(expr))]

    # Normal variable
    elif type(expr) is model.Var:
        return [Node(str(expr))]

    # Func call
    elif type(expr) is model.Op and expr.name == 'FuncCall':
        return ast_funcCall_op(expr, var, ignoreSpl)

    # Op
    elif type(expr) is model.Op:
        return ast_op(expr, var, ignoreSpl)

    raise raise_exceptionExpr(expr)


def ast_expr_str(expr: model.Expr, var: str, ignoreSpl, flag_addEOL=True, flag_noAssign=False):

    expr_node = ast_expr_rec(expr, var, ignoreSpl=ignoreSpl)

    return expr_node


# endregion

# region: ast cond/data
def get_condVarExpr(fnc: model.Function, loc: int):
    '''Fetch a single condVar and condExpr'''
    assert len(fnc.locexprs[loc]) == 1, 'Concretize: Cond locexprs more than one %s' % (fnc.locexprs[loc])
    var, expr = fnc.locexprs[loc][0]

    assert var == '$cond', 'Concretize: $cond variable does not exist' % (fnc.locexprs[loc])
    return var, expr


def ast_cond(fnc: model.Function, loc: int, ignoreSpl):
    condVar, condExpr = None, None
    condExprStr = ''

    for var, expr in fnc.locexprs[loc]:
        # Store the $cond, to add later
        if var == '$cond':
            assert condVar != var, 'Concretize: multiple $cond variables exist! %s' % (fnc.locexprs[loc])
            condVar, condExpr = var, expr

        # Add other statements by appending a comma "," at the end
        else:
            exprStr = ast_expr_str(expr, var, ignoreSpl, flag_addEOL=False, flag_noAssign=False)
            condExprStr += exprStr + ', '

    assert condVar is not None, 'Concretize: $cond variable does not exist' % (fnc.locexprs[loc])
    condNode = [Node(str(condVar))]
    exprNode = ast_expr_str(condExpr, condVar, ignoreSpl, flag_addEOL=False, flag_noAssign=True)
    node = Node('Assign')
    node.addkid(condNode)
    node.addkid(exprNode)
    #condExprStr += exprStr

    return [node]


def ast_block(fnc: model.Function, loc: int, seen: list, flag_addLines=True, flag_addEOL=True):
    blocks_str = []
    flagBreak = False

    block_node = []
    if loc in fnc.locexprs:
        expr_str = None

        for (var, expr) in fnc.locexprs[loc]:
            stmt_node = Node('Assign')
            expr_node = ast_expr_str(expr, var, ignoreSpl=False, flag_addEOL=flag_addEOL)
            stmt_node.addkid([Node(str(var))])
            stmt_node.addkid(expr_node)
            #parent_node.addkid(stmt_node)
            block_node.append(stmt_node)
        # if expr_str is not None:
        #     flagBreak = flagBreak or expr_str.flag_break
    return block_node, flagBreak


# endregion

# region: ast function

def ast_headers(prog: model.Program, lines):
    headers = ['stdio.h', 'stdlib.h', 'math.h']
    for header in headers:
        lines.append('#include<{}>'.format(header))


def ast_funcDecl(prog: model.Program, lines):
    for fnc in prog.fncs.values():
        params_str = ','.join([typeStr + ' ' + name for name, typeStr in fnc.params])
        func_decl = '{} {}({});'.format(fnc.rettype, fnc.name, params_str)

        lines.append(func_decl)


def ast_funcDef(fnc, lines):
    param_names = [name for name, typeStr in fnc.params]
    params_str = ','.join([typeStr + ' ' + name for name, typeStr in fnc.params])
    func_def = '{} {}({}) {{'.format(fnc.rettype, fnc.name, params_str)
    var_decls = ['{} {};'.format(type_str, var_name) for var_name, type_str in fnc.types.items()
                 if var_name not in param_names]  # Decl all variables, except function args

    lines.append(func_def)
    lines.extend(var_decls)


def ast_funcCall(name: str, args, var: str, ignoreSpl):
    funcCall_node = Node('funcCall')
    for arg in args:
        expr_node = ast_expr_rec(arg, var, ignoreSpl)
        funcCall_node.addkid(expr_node)

    return [funcCall_node]


def ast_funcCall_op(op: model.Op, var: str, ignoreSpl):
    return ast_funcCall(op.args[0], op.args[1:], var, ignoreSpl)


# endregion

# region: ast for loop

def get_forLoc(fnc: model.Function, locCond: int):
    lineNum = re.findall(r'line (\d+)', fnc.locdescs[locCond])[0]

    # locIn and locOut are obtained from trans of cond block
    locIn, locOut = fnc.loctrans[locCond][True], fnc.loctrans[locCond][False]

    # loop update needs a search over all desc with same lineNum
    locUpdate = None
    for loc, desc in fnc.locdescs.items():
        if desc.strip() == "update of the 'for' loop at line %s" % (lineNum):
            locUpdate = loc
            break

    return locCond, locUpdate, locIn, locOut


def ast_forLoop(fnc: model.Function, loc: int, locStops: List[int], seen: list):
    locCond, locUpdate, locIn, locOut = get_forLoc(fnc, loc)
    condNode = ast_cond(fnc, locCond, ignoreSpl=False)
    updateNode, flagBreak = ast_block(fnc, locUpdate, seen, flag_addLines=False, flag_addEOL=False)

    # Add loop cond and update
    seen.extend([locCond, locUpdate])

    # Recurse inside loop body
    inside_loop_node = ast_loc(fnc, locIn, locStops + [locOut], seen)
    node = Node('For')
    node.addkid(condNode)
    node.addkid(updateNode)
    node.addkid(inside_loop_node)

    # Recurse after loop body
    after_loop_node = ast_loc(fnc, locOut, locStops, seen)
    return [node] + after_loop_node
# endregion

# region: Concretize while loop

def get_whileLoc(fnc: model.Function, locCond: int):
    # locIn and locOut are obtained from trans of cond block
    locIn, locOut = fnc.loctrans[locCond][True], fnc.loctrans[locCond][False]

    return locCond, locIn, locOut


def ast_whileLoop(fnc: model.Function, loc: int, locStops: List[int], seen: list):
    locCond, locIn, locOut = get_whileLoc(fnc, loc)
    condNode = ast_cond(fnc, locCond, ignoreSpl=False)

    node = Node('While')
    # Add loop cond and update
    seen.extend([locCond])
    node.addkid(condNode)
    # Recurse inside loop body
    body_node = ast_loc(fnc, locIn, locStops + [locOut], seen)
    node.addkid(body_node)
    # Recurse after loop body
    next_loc_node = ast_loc(fnc, locOut, locStops, seen)

    return [node] + next_loc_node



# endregion

# region: Concretize do while loop

def get_doWhileLoc(fnc: model.Function, locIn: int):
    locCond = fnc.loctrans[locIn][True]
    locOut = fnc.loctrans[locCond][False]
    return locCond, locOut


def ast_doWhileLoop(fnc: model.Function, loc: int, locStops: List[int], seen: list):
    locCond, locOut = get_doWhileLoc(fnc, loc)

    node = Node('doWhile')
    condNode = ast_cond(fnc, locCond, ignoreSpl=False)

    # Recurse inside the body
    bodyNode, flagbreak = ast_block(fnc, loc, seen)

    node.addkid(condNode)
    node.addkid(bodyNode)

    seen.extend([locCond])
    # Recurse after the loop body
    next_loc_node = ast_loc(fnc, locOut, locStops, seen)

    return [node] + next_loc_node

# region: Concretize conditional

def get_ifLoc(fnc: model.Function, locCond: int):
    lineNum = re.findall(r'line (\d+)', fnc.locdescs[locCond])[0]

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


def ast_if(fnc: model.Function, loc: int, locStops: List[int], seen: list):
    locCond, locIn, locOut, locElse = get_ifLoc(fnc, loc)
    condNode = ast_cond(fnc, locCond, ignoreSpl=False)

    # Add if cond
    seen.extend([locCond])

    if_node = Node('If')
    if_node.addkid(condNode)
    # Recurse inside if-branch
    then_node = ast_loc(fnc, locIn, locStops + [locOut], seen)

    if_node.addkid(then_node)
    # Add else-branch, if it exists
    if locElse is not None:
        else_node = ast_loc(fnc, locElse, locStops + [locOut], seen)
        if_node.addkid(else_node)
    # Recurse after if-cond
    next_loc_node = ast_loc(fnc, locOut, locStops, seen)
    return [if_node] + next_loc_node

# endregion

# region: Concretize Array

def ast_array_create(expr1, expr2, var, ignoreSpl):

    pass

# region: Check for branches

def is_forLoop(fnc: model.Function, loc: int):
    if loc in fnc.locdescs:
        return "the condition of the 'for' loop" in fnc.locdescs[loc]


def is_whileLoop(fnc: model.Function, loc: int):
    if loc in fnc.locdescs:
        return "the condition of the 'while' loop" in fnc.locdescs[loc]


def is_doWhileLoop(fnc: model.Function, loc: int):
    if loc in fnc.locdescs:
        return "inside the body of the 'do-while' loop" in fnc.locdescs[loc]


def is_loop(fnc: model.Function, loc: int):
    return is_forLoop(fnc, loc) or is_whileLoop(fnc, loc)


def is_ifCond(fnc: model.Function, loc: int):
    if loc in fnc.locdescs:
        return "the condition of the if-statement" in fnc.locdescs[loc]


def is_iteCond(fnc: model.Function, loc: int):
    if loc in fnc.locdescs:
        return "the ITE" in fnc.locdescs[loc]


# endregion

# region: ast prog

def ast_loc(fnc: model.Function, loc: int, locStops: List[int], seen):
    '''restrict_noBranch = restrict exploration to non-branch blocks'''
    # Early exit if already seen
    if loc in seen or loc is None:
        return []
    seen.append(loc)

    # Case-1: Loop struct
    if is_forLoop(fnc, loc):
        return ast_forLoop(fnc, loc, locStops, seen)

    elif is_whileLoop(fnc, loc):
        return ast_whileLoop(fnc, loc, locStops, seen)

    elif is_doWhileLoop(fnc, loc):
        return ast_doWhileLoop(fnc, loc, locStops, seen)
    # Case-2: if-conditional
    elif is_ifCond(fnc, loc):
        return ast_if(fnc, loc, locStops, seen)

    # Case-3: Single non-branching block
    else:
        locTrue, locFalse = fnc.loctrans[loc][True], fnc.loctrans[loc][False]
        assert locFalse is None, \
            'Concretize: Non-branch block has False branch %s' % (loc)

        block_node, flagBreak = ast_block(fnc, loc, seen)  # Concretize the block
        next_loc_node = []
        if not flagBreak:  # Unless a return or break or continue statement was encountered
            if locTrue not in locStops:  # Or some visitor wants to stop at a particular loc
                next_loc_node = ast_loc(fnc, locTrue, locStops, seen)  # Concretizing the next loc
        return block_node + next_loc_node


def ast_prog(prog: model.Program):
    '''Given a model.Program, ast it'''
    root = Node("root")

    for fnc in prog.fncs.values():
        seen = []
        fnc_node = Node(fnc.name)
        node = ast_loc(fnc, fnc.initloc, [fnc.endloc], seen)
        fnc_node.addkid(node)
        root.addkid([fnc_node])

    return [root]

def ast_add_node_list(parent_node: Node, node_list: list):
    for node in node_list:
        parent_node.addkid(node)
    return parent_node
#
def zss_node_cnt(zss_node_list):
    s = 1
    for node_list in zss_node_list:
        for node in node_list:
            s += zss_node_cnt(node.children)
    return s

def zss_tree_edit_distance(node_a, node_b):

    return simple_distance(node_a, node_b, label_dist=label_weight, get_children=get_children_from_list, get_label=get_label_from_node)

def label_weight(l1, l2):
    if l1 == l2:
        return 0
    else:
        return 1

def get_children_from_list(node_list):
    children = []
    for node in node_list:
        children += node.children
    return children
    # return node_list[0].children

def get_label_from_node(node_list):
    if len(node_list) > 0:
        return node_list[0].label
    return ''

def tree_edit_dist(prog_a, prog_b):
    p_a = ast_prog(prog_a)
    p_b = ast_prog(prog_b)
    return zss_tree_edit_distance(p_a, p_b)

def patch_size(prog):
    prog = ast_prog(prog)
    return zss_node_cnt([prog])

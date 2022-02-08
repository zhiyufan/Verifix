from srcU.ClaraP import model

from srcU.Helpers import Helper as H
from z3 import *

import re

#region: Z3 conversion for vars
def raise_exceptionOp(op):
    raise Exception('Unknown Op type {}:{} in converting to SMT!'.format(op.name, op))

def check_nameList(name):
    if '$in' in name or '$out' in name:
        return True
    return False

class SMT_Var:
    def __init__(self, name, vari, isCorrect=None, myType=None, mode=None):
        self.name_orig = name
        self.vari = vari
        self.name = name +'@'+ str(len(vari[name]))
        self.indexStart, self.indexTemp = None, None        
        self.myType, self.smtVar = None, None 
        self.mode = mode
        self.isCorrect = isCorrect
        self.set_type(myType)
        self.set_smtVar()        

    def set_type(self, myType):
        if myType == 'char':
            self.myType = 'int'
        elif myType is not None:
            self.myType = myType
        elif '$in' in self.name: # Input stream is treated as Int Array
            self.myType = 'list'
        elif '$out' in self.name: # Output stream is treated as String
            self.myType = 'str'
        elif '$ret' in self.name:
            self.myType = 'float'

        else: # Default is Int
            self.myType = 'int'

    def set_smtVar(self):

        if 'int[' in self.myType:
            self.smtVar = z3.Array(self.name, z3.IntSort(), z3.IntSort())

        elif self.myType == 'str':
            self.smtVar = z3.String(self.name)

        elif self.myType == 'list':
            # need to consider char and float
            if 'outFloat' in self.name:
                self.smtVar = z3.Array(self.name, z3.RealSort(), z3.RealSort())
            else:
                self.smtVar = z3.Array(self.name, z3.IntSort(), z3.IntSort())
            # self.smtVar = z3.Array(self.name, z3.FPSort(8,24), z3.FPSort(8,24))
            if self.mode != 'vcgen' and self.isCorrect == False:
                # ce_idx = self.name.split('-')[0]
                # self.array_name = ce_idx + '-I-$inIdx@'
                self.array_name = self.name_orig + 'Idx@'
                self.array_idx = len(self.vari[self.name_orig])
                self.indexStart = z3.Int(self.array_name + str(self.array_idx))
                self.indexTemp = z3.Int(self.array_name + str(self.array_idx))
            elif 'out' in self.name:
                self.array_name = self.name_orig + 'Idx@'
                self.array_idx = len(self.vari[self.name_orig])
                self.indexStart = z3.Int(self.array_name + str(self.array_idx))
                self.indexTemp = z3.Int(self.array_name + str(self.array_idx))
            else:
                self.indexStart = 0
                self.indexTemp = 0
        elif self.myType == 'float':
            self.smtVar = z3.Real(self.name)
            # self.smtVar = z3.FP(self.name,Float32())

        else:
            self.smtVar = z3.Int(self.name)

    def increIndex(self):
        if self.mode != 'vcgen' and self.isCorrect == False and self.myType == 'list':
            self.array_idx += 1
            self.indexTemp = z3.Int(self.array_name + str(self.array_idx))
            # self.indexTemp = z3.FP(self.array_name + str(self.array_idx), Float32())
        else:
            self.indexTemp = self.indexStart

def z3_name(name:str, isCorrect, ce_index:str):

    if name == 'break' or name == 'continue':
        name = '$'+name
    if isCorrect:
        return 'ce{}-C-'.format(ce_index) + name
    return 'ce{}-I-'.format(ce_index) + name

def z3_name_check(name:str, ce_index:str):
    '''Returns True if the name follows correct program's naming convention. Otherwise False'''
    if len(name) > 0:
        firstdash = name.find('-')
        firstChar = name[:firstdash+2]

        if firstChar == 'ce{}-C'.format(ce_index):
            return True
        if firstChar == 'ce{}-I'.format(ce_index):
            return False
    
    raise Exception('SMT: Invalid z3 naming convention')


def z3_varNew(solver, name, vari, isCorrect, myType=None, mode=None) -> (SMT_Var, SMT_Var):
    '''Create new var and append'''
    if name not in vari:
        vari[name] = []
        oldVar = None
    else:
        oldVar = vari[name][-1]
        if myType is None:
            myType = oldVar.myType
    newVar = SMT_Var(name, vari, isCorrect=isCorrect, myType=myType, mode=mode)
    vari[name].append(newVar)
    return oldVar, newVar

def z3_varExisting(solver, var:model.Var, vari, isCorrect, ce_index:str, var_type=None, mode=None, cond_idx=0):
    '''Return existing var. If it doesn't exists, create a new one and return.'''
    # name = 'ce{}-'.format(ce_index) + z3_name(var.name, isCorrect)

    name = z3_name(var.name, isCorrect, ce_index=ce_index)
    if name not in vari:
        z3_varNew(solver, name, vari, isCorrect, myType=var_type, mode=mode)
    if cond_idx == 0:
        return vari[name][-1]
    else:
        return vari[name][cond_idx]
def z3_smt2var(smtVar, vari):
    name = str(smtVar)
    for key in vari:
        for var in vari[key]:
            if var.name == name:
                return var

#endregion

#region: Z3 conversion for Ops

def z3_op_noArgs(solver, op:model.Op, vari, isCorrect, ce_index:str):
    if op.name == 'True':
        return z3_true(vari, ce_index=ce_index)
    elif op.name == 'False':
        return z3_false(vari, ce_index=ce_index)
    elif op.name == 'break':
        return 0
    elif op.name == 'continue':
        return 0
    
    raise_exceptionOp(op)

def z3_op_unary(solver, op:model.Op, vari, isCorrect, ce_index:str):
    '''TODO: Update ListHead and ListTail - approximated for now'''
    expr1 = op.args[0]
    
    if op.name == '!':
        cond = z3_cond(solver, expr1, vari, isCorrect, ce_index=ce_index)
        return Not(cond)
    elif op.name == '-':
        return - z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index)
    elif op.name == '+':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index)

    elif op.name in ['sqrt', 'sqrtf']:
        x = z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index)
        return x
        # return x ** (1/2)

    elif op.name == 'ListTail': # ListTail($in)
        smtVar = z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index)
        var = z3_smt2var(smtVar, vari)
        # var.indexTemp += 1
        if type(var.indexTemp) is int:
            pass
            # var.indexTemp += 1
        else:
            var.indexTemp = vari['ce{}-I-$inIdx'.format(ce_index)][-1].smtVar
        return smtVar    

    elif op.name in ['abs', 'fabs']:
        x = z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index)
        return z3_abs(x)


    raise_exceptionOp(op)

def z3_abs(x):
    if x.is_int():
        return If(x >= 0, x, -x)
    else:
        return 0

def z3_op_binary(solver:z3.Optimize, op:model.Op, vari, isCorrect, ce_index:str, mode=None, cond_idx=0):
    '''TODO: Update ListHead and ListTail - approximated for now'''
    expr1, expr2 = op.args[0], op.args[1]

    if op.name == '=':
        # TODO: currently using hack. x=1 => 1 (is returned. ideally assign to x and then return)
        return z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index)

    elif op.name == '+':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) + z3_gen_rational(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '-':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) - z3_gen_rational(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '*':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) * z3_gen_rational(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '/':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) * z3_gen_rational(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)

    elif op.name == '%':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) % z3_gen_rational(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)

    elif op.name == 'pow':
        return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) * z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
        # return z3_gen_rational(solver, expr1, vari, isCorrect, ce_index=ce_index) ** z3_gen_rational(solver, expr2, vari, isCorrect, ce_index=ce_index)

    elif op.name == '<':
        return z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) < z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '<=':
        return z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) <= z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '>':
        return z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) > z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '>=':
        return z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) >= z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    elif op.name == '==' or op.name == '=':
        try:
            return z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) == z3_gen(solver, expr2, vari, isCorrect,
                                                                                       ce_index=ce_index, cond_idx=cond_idx)
        except:
            a = z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
            b = z3_gen(solver, expr2, vari, isCorrect,ce_index=ce_index, cond_idx=cond_idx)
            if isinstance(a, ArrayRef):
                a = 0
            elif isinstance(b, ArrayRef):
                b = 0
            return a == b
    elif op.name == '!=':
        return z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx) != z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)

    elif op.name == '&&':
        cond1, cond2 = z3_cond(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx), z3_cond(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
        return z3.And(cond1, cond2)

    elif op.name == '||':
        cond1, cond2 = z3_cond(solver, expr1, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx), z3_cond(solver, expr2, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
        return z3.Or(cond1, cond2)

    elif op.name == 'ListHead': # ListHead(int, $in)
        smtVar = z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index, mode=mode)
        var = z3_smt2var(smtVar, vari)
        idx = var.indexTemp
        if type(var.indexTemp) is int:
            var.indexTemp += 1
        return z3.Select(smtVar, idx)

    elif op.name == 'StrAppend': # StrAppend($out, StrFormat(...))
        val1 = z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index)
        val2 = z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index)

        if isinstance(val1, tuple) and isinstance(val2, tuple):
            outStr = z3.Concat(val1[0], val2[0])
            return outStr, val2[1], val2[2]

        outStr = z3.Concat(val1, val2[0])
        return outStr, val2[1], val2[2]

    elif op.name == 'cast':
        val1, val2 = z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index), z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index)
        return z3_typeCast(val1, val2)

    elif op.name == '[]':
        val = z3_array_select(solver, expr1, expr2, vari, isCorrect, ce_index=ce_index)
        return val

    elif op.name in 'ArrayCreate':
        x = z3_array_create(solver, expr1, expr2, vari, isCorrect, ce_index=ce_index)
        return x
    raise_exceptionOp(op)

def z3_op(solver, op:model.Op, vari, isCorrect, ce_index:str, mode=None, cond_idx=0):
    '''BINARY_OPS pending {'^', '&', '!'}'''
    if op.name == 'StrFormat':
        return z3_op_strFormat(solver, op, vari, isCorrect, ce_index=ce_index)

    elif len(op.args) == 0:
        return z3_op_noArgs(solver, op, vari, isCorrect, ce_index=ce_index)

    elif len(op.args) == 1:
        return z3_op_unary(solver, op, vari, isCorrect, ce_index=ce_index)

    elif len(op.args) == 2:
        return z3_op_binary(solver, op, vari, isCorrect, ce_index=ce_index, mode=mode, cond_idx=cond_idx)

    elif len(op.args) == 3 and op.name == 'ite':
        return z3_ite(solver, op, vari, isCorrect, ce_index=ce_index)

    elif len(op.args) == 3 and op.name == 'ArrayAssign':
        return z3_array_assign(solver, op, vari, isCorrect, ce_index=ce_index)

    raise_exceptionOp(op)

#endregion

#region: Z3 test & gen for special cases

def z3_cond(solver, expr:model.Expr, vari, isCorrect, ce_index:str, cond_idx=0):
    '''Special z3_gen: If expr is not a valid boolean expr (Eg: if flag), then convert it to one (Eg: flag != 0)'''

    try: # If valid cond
        if cond_idx == 0:
            cond = z3_gen(solver, expr, vari, isCorrect, ce_index=ce_index)
        else:
            cond = z3_gen(solver, expr, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
        Not(cond)
        return cond
    except z3types.Z3Exception: # Else make it cond by comparing against 0 (In C, any non-zero number is true)
        # return True
        cond = z3_gen(solver, expr, vari, isCorrect, ce_index=ce_index)
        return cond != 0

def z3_gen_rational(solver:z3.Optimize, expr:model.Expr, vari, isCorrect, ce_index:str, cond_idx=0):
    '''Use this for Arithmetic ops: when only SMT variable or rational (integer/float) are acceptable, and not strings.'''
    if cond_idx == 0:
        res = z3_gen(solver, expr, vari, isCorrect, ce_index=ce_index)
    else:
        res = z3_gen(solver, expr, vari, isCorrect, ce_index=ce_index, cond_idx=cond_idx)
    if type(res) is str:
        return float(res)
    return res

def z3_array_create(solver:z3.Optimize, expr1:model.Expr, expr2:model.Expr, vari, isCorrect, ce_index:str):

    length = z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index, var_type=str(expr2))
    res = K(IntSort(), -100)
    return res

def z3_array_select(solver:z3.Optimize, expr1:model.Var, expr2:model.Var, vari, isCorrect, ce_index:str):
    array = z3_gen(solver, expr1, vari, isCorrect, ce_index=ce_index)
    idx = z3_gen(solver, expr2, vari, isCorrect, ce_index=ce_index)

    return z3.Select(array,idx)

def z3_array_assign(solver:z3.Optimize, expr:model.Op, vari, isCorrect, ce_index:str):

    array = z3_gen(solver, expr.args[0], vari, isCorrect, ce_index=ce_index)
    idx = z3_gen(solver, expr.args[1], vari, isCorrect, ce_index=ce_index)
    value = z3_gen(solver, expr.args[2], vari, isCorrect, ce_index=ce_index)
    try:
        return z3.Store(array, idx, value)
    except:
        print('error array assign')

def z3_true(vari, ce_index:str):
    return vari['ce{}-C-$ret'.format(ce_index)][0] == vari['ce{}-C-$ret'.format(ce_index)][0]

def z3_false(vari, ce_index:str):
    return vari['ce{}-C-$ret'.format(ce_index)][0] != vari['ce{}-C-$ret'.format(ce_index)][0]

def z3_charToASCII(s):
    try:
        pattern1 = '^\\\'([ -~])\\\'$'
        s = re.match(pattern1, s).groups()[0]
        return z3.IntVal(ord(s))
    except:
        pattern2 = '^"([ -~])"$'
        s2 = re.match(pattern2, s).groups()[0]
        return z3.IntVal(10000)


def z3_typeCast(type, val):
    if type == 'int':
        try:
            return ToInt(val)
        except:
            return val
    return val
#endregion

#region: Z3 Str Format

def z3_op_strFormat(solver:z3.Optimize, op:model.Op, vari, isCorrect, ce_index:str):
    '''Eg: StrFormat("%d", i)'''
    # Extract string-formats and its args

    stri = op.args[0].value[1:-1]
    args = op.args[1:]
    strs = re.split(r'%[0-9]*\.?[0-9]*[c|d|f]', stri)
    # %m.k
    formats = re.findall(r'%([0-9]*\.?[0-9]*[c|d|f])', stri)
    if len(strs) < len(args) + 1:
        args = args[:len(strs)-1]

    z3_out_ints = []
    z3_out_floats = []
    for arg, type in zip(args, formats):
        if 'd' in type or 'c' in type:
            z3_out_ints.append(z3_gen(solver, arg, vari, isCorrect, ce_index=ce_index))
        elif 'f' in type:
            z3_out_floats.append(z3_gen(solver, arg, vari, isCorrect, ce_index=ce_index))

    z3_out_str = z3.StringVal(stri)

    # else:
    #     # Create a concatinated list of str[0] + converted(arg[0]) + ... + str[n-1]
    #     li = [strs[0]]
    #     for stri, arg, (m, k, type) in zip(strs[1:], args, formats):
    #         if type == 'd' or type == 'c':
    #             conv = z3_gen(solver, arg, vari, isCorrect, ce_index=ce_index)
    #             outi = z3.IntToStr(conv)
    #             # outi = z3.If(conv >= 0, z3.IntToStr(conv), z3.Concat(["-", " ",z3.IntToStr(conv)]))
    #             # print(3)
    #         else:
    #             # outi = z3_toStr(solver, arg, m, k, type, vari, isCorrect, ce_index=ce_index)
    #             conv = z3_gen(solver, arg, vari, isCorrect, ce_index=ce_index)
    #             outi = fp2str(conv)
    #         li += [outi, stri]
    #     strVal = z3.Concat(*li)
    # z3_out_float = None

    return z3_out_str, z3_out_ints, z3_out_floats

#endregion

#region: Z3 ite

def z3_ite(solver, op:model.Op, vari, isCorrect, ce_index:str):
    # cond = z3_cond(solver, op.args[0], vari, isCorrect, ce_index=ce_index, cond_idx=op.condIdx)
    cond = z3_cond(solver, op.args[0], vari, isCorrect, ce_index=ce_index)

    then = z3_gen(solver, op.args[1], vari, isCorrect, ce_index=ce_index)
    els = z3_gen(solver, op.args[2], vari, isCorrect, ce_index=ce_index)

    if isinstance(then, tuple):
        return z3.If(cond, then[0], els), then[1], then[2], cond
    else:
        return z3.If(cond, then, els)

#endregion

#region: Z3 toString uninterprete

def fp2str(x):
    z = z3.fpToIEEEBV(x)
    n = z.size()
    bits = [Extract(i, i, z) for i in range(n)]
    bvs = [IntToStr(BV2Int(b)) for b in bits]
    bvs.reverse()
    binary_str = Concat(*bvs)
    return binary_str

def z3_toStr(solver:z3.Optimize, x:model.Expr, m:str, k:str, var_type:str, vari, isCorrect, ce_index:str):
    argX = z3_gen(solver, x, vari, isCorrect, ce_index=ce_index)
    inputName = z3_name('toStrIp{}'.format(x), isCorrect, ce_index=ce_index)
    inputArg = z3.Real('{}@{}'.format(inputName, str(argX).split("@")[-1]))
    solver.add(argX == inputArg)
    args = [inputArg]
    # args = [argX]
    defs = []

    ret_str = z3_name('toStrRe{}'.format(x), isCorrect, ce_index=ce_index)
    ret_str_new = z3.String('{}@{}'.format(ret_str, str(argX).split("@")[-1]))

    if var_type == 'f':
        defs += [RealSort()]
    elif var_type == 'd':
        defs += [IntSort()]
    else:
        raise Exception('SMT:unknown format specifier type')

    if m != '':
        args += [int(m)]
        defs += [IntSort()]
    if k != '':
        args += [int(k)]
        defs += [IntSort()]
    func_toStr = z3.Function('toStr', *defs, StringSort())
    solver.add(func_toStr(*args) == ret_str_new)
    return ret_str_new
#endregion

#region: Z3 conversion for function call

def z3_func(solver:z3.Optimize, expr:model.Op, vari, isCorrect, ce_index:str):
    # Define func

    fncName = expr.args[0].name
    args = [z3_gen(solver, arg, vari, isCorrect, ce_index=ce_index) for arg in expr.args[1:]]
    types = [z3.IntSort() for arg in args] + [z3.IntSort()] # params + return value
    func = z3.Function(fncName, *types)
    # Define return val
    inputName = z3_name('ipVal'+fncName.replace('@', ''), isCorrect, ce_index=ce_index)
    input_args = [z3_varNew(solver, inputName, vari, isCorrect)[-1].smtVar]
    for arg1, arg2 in zip(input_args, args):
        solver.add(arg1 == arg2)
    retName = z3_name('retVal'+fncName.replace('@', ''), isCorrect, ce_index=ce_index)

    retVarOld, retVarNew = z3_varNew(solver, retName, vari, isCorrect)

    # Add assertion retVal = funcCall
    solver.add(func(*input_args) == retVarNew.smtVar)

    # Return the retVal for future conversions
    return retVarNew.smtVar
    # return func(*args)
#endregion

#region: SAT/SMT Recursive conversion

def z3_gen(solver:z3.Optimize, expr:model.Expr, vari, isCorrect, ce_index:str, var_type=None, mode=None, cond_idx=0):
    if expr == 'True' or expr is True:
        return z3_true(vari, ce_index=ce_index)
    elif expr == 'False' or expr is False:
        return z3_false(vari, ce_index=ce_index)

    elif type(expr) is model.Const:
        if H.checkInt(expr.value):
            return z3.IntVal(expr.value)
            # return z3.FPVal(expr.value,Float32())
        elif H.checkFloat(expr.value):
            return z3.RealVal(expr.value)
            # return z3.FPVal(expr.value,Float32())
        elif H.checkChar(expr.value):
            return z3_charToASCII(expr.value)
        elif str(expr.value) == '?':
            return 1
        return expr.value

    elif type(expr) is model.Var:
        if cond_idx == 0:
            var = z3_varExisting(solver, expr, vari, isCorrect, ce_index=ce_index, var_type=var_type, mode=mode)
        else:
            var = z3_varExisting(solver, expr, vari, isCorrect, ce_index=ce_index, var_type=var_type, mode=mode, cond_idx=cond_idx)
        if type(var) is SMT_Var:
            # var.increIndex()
            return var.smtVar
        return var

    elif type(expr) is model.Op and expr.name == 'FuncCall':
        return z3_func(solver, expr, vari, isCorrect, ce_index=ce_index)

    elif type(expr) is model.Op:
        return z3_op(solver, expr, vari, isCorrect, ce_index=ce_index, mode=mode, cond_idx=cond_idx)

    raise Exception('Unknown expr type {}:{} in converting to SMT!'.format(type(expr), expr))

#endregion

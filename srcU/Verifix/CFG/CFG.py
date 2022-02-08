from srcU.ClaraP import parser, model
from srcU.Verifix.CFG import Minimize, Concretize

import textwrap
import string
from typing import List

#region: Interface between CFG and Struct

class Cond:
    def __init__(self, fncName:str, loc:int, isCondNegated=False, isCondTrue=False):
        assert type(fncName) is str
        self.fncName = fncName        
        self.loc = loc
        self.isCondNegated = isCondNegated
        self.isCondTrue = isCondTrue
        self.isUpdated = False

    def to_str(self, prog:model.Program):
       return str(self.get_cond(prog))
    
    def get_varExpr(self, prog:model.Program):
        fnc = prog.fncs[self.fncName]
        assert len(fnc.locexprs[self.loc]) == 1, "Cond violation: %s" % fnc.locexprs[self.loc]
        var, expr = fnc.locexprs[self.loc][0] # Extract the condition
        assert var == model.VAR_COND, "Cond violation: %s" % fnc.locexprs[self.loc]

        return var, expr

    def get_cond(self, prog:model.Program) -> model.Expr:
        # Case-1: True (non-branching block)
        if self.isCondTrue:
            return model.Op('True')
        
        var, expr = self.get_varExpr(prog)

        # Case-2: Negated (else branch)
        if self.isCondNegated: 
            return model.Op(parser.Parser.NOTOP, expr)

        # Case-3: then branch
        return expr

    def set_cond(self, prog:model.Program, newExpr):
        # Case-1: True (non-branching block)
        if self.isCondTrue:
            return
            # raise Exception('Cannot assign cond to [True] block!')
        
        var, expr = self.get_varExpr(prog)

        # Case-2: Negated (else branch)
        if self.isCondNegated:
            
            if type(newExpr) is model.Op and newExpr.name == parser.Parser.NOTOP: # If the cond is already negated
                newExpr = newExpr.args[0] # Avoid double negation, by fetching newExpr.expr
            else: # Otherwise
                newExpr = model.Op(parser.Parser.NOTOP, newExpr) # negate the newExpr

        # Case-3: then branch
        prog.fncs[self.fncName].locexprs[self.loc][0] = (var, newExpr)
        if newExpr.name == 'True':
            self.isCondTrue = True
        

class VarExprs:
    def __init__(self, fncName:str, loc:int):
        assert type(fncName) is str
        self.fncName = fncName
        self.loc = loc

    def to_str(self, prog:model.Program):
        varExprs = self.get_varExprs(prog)
        return '\n'.join(['\n%s = %s' % (var, expr.tostring())
            for (var, expr) in varExprs])  

    def get_length(self, prog:model.Program):
        return len(prog.fncs[self.fncName].locexprs[self.loc])

    def get_varExprs(self, prog:model.Program):
        if self.loc is None:
            return []
        return prog.fncs[self.fncName].locexprs[self.loc]

    def del_varExprs(self, prog:model.Program):
        prog.fncs[self.fncName].locexprs[self.loc] = []

    def set_varExprs(self, prog:model.Program, varExpr):
        prog.fncs[self.fncName].locexprs[self.loc] = varExpr

    def pop(self, prog:model.Program, index):
        prog.fncs[self.fncName].locexprs[self.loc].pop(index)

    def update(self, prog:model.Program, index, var, expr):
        prog.fncs[self.fncName].locexprs[self.loc][index] = (var, expr)

    def insert(self, prog:model.Program, index, var, expr):
        li = prog.fncs[self.fncName].locexprs[self.loc]
        li.insert(index, (var, expr))

    def remove(self, prog:model.Program, index):
        li = prog.fncs[self.fncName].locexprs[self.loc]
        li.pop(index)

    def addexpr(self, prog:model.Program, var, expr, idx=None):
        prog.fncs[self.fncName].addexpr(self.loc, var, expr, idx)

#endregion

#region: Point and Block

class Point:
    def __init__(self, index:int, fncName:str, loc:int, isPrimed=False):
        assert type(fncName) is str
        self.index = index
        self.isPrimed  = isPrimed
        self.label = 'q'+str(index)
        if self.isPrimed:
            self.label += '\''

        self.fncName = fncName
        self.loc = loc

    def __str__(self):
        return Point.get_label(self.fncName, self.loc)

    @staticmethod
    def get_label(fncName:str, loc:int):
        return fncName +'.'+ str(loc)

class Block:
    def __init__(self, index:int, src:Point, dest:Point, fncName:str, condLoc:int, exprLoc:int, 
            isCondNegated=False, isCondTrue=False, isPrimed=False, isAfterFor=False):
        assert type(fncName) is str
        self.index = index
        self.isPrimed = isPrimed
        self.label = Block.get_label(index)
        if self.isPrimed:
            self.label += '\''

        self.src = src
        self.dest = dest
        self.cond = Cond(fncName, condLoc, isCondNegated=isCondNegated, isCondTrue=isCondTrue)
        self.varExprs = VarExprs(fncName, exprLoc)
        self.isAfterFor = isAfterFor
        self.changed = False

    def set_changed(self):
        self.changed = True

    def get_length(self, prog:model.Program):
        return self.varExprs.get_length(prog)

    def get_hash(self, prog:model.Program):
        return '{}_{}_[{}]\n{}'.format(
                self.src, self.dest, self.cond.to_str(prog), self.varExprs.to_str(prog))

    def set_cond(self, prog, condExpr):
        self.cond.set_cond(prog, condExpr)

    def set_cond_updated(self):
        self.cond.isUpdated = True

    def get_cond(self, prog):
        return self.cond.get_cond(prog)

    def get_varExprs(self, prog):
        return self.varExprs.get_varExprs(prog)

    def del_varExprs(self, prog):
        self.varExprs.del_varExprs(prog)

    def set_varExprs(self, prog, varExprs):
        self.varExprs.set_varExprs(prog, varExprs)

    def to_str(self, prog:model.Program):
        stri = '{} [{}]\n{}'.format(self.label, self.cond.to_str(prog), self.varExprs.to_str(prog))
        return textwrap.fill(stri, 100)

    @staticmethod
    def get_label(index:int) -> str:
        length = len(string.ascii_uppercase)
        labels = string.ascii_uppercase
        
        if index < length:
            return labels[index]
        else:
            rem = int(index / length)
            mod = index % length
            return labels[rem] + labels[mod]

#endregion

#region: CFG class

class CFG:
    def __init__(self, prog:model.Program, isPrimed=False):
        self.prog = prog
        self.isPrimed = isPrimed

        self.entryPoints = {} # Per function, entry Point
        self.exitPoints  = {} # Per function, exit Point
        self.points = {}
        self.blocks = {}
        self.block2edge = {} # {fnc:{loc1:{True:block1, False:block2}}}
        self.edge2block = {} # {fnc:{label:loc}}
        self.label2block = {} # {label1:block1}
        self.label2point = {} # {label1:point}
        self.loc2point = {} # {fnc:{loc:point}}
        self.loopPoints = {} # {fnc:{point1}}, list of points which have cyclic edges

        self.invariants = {} # {block_label:[invariants]}

        self.createCFG()
        self.addLoopPoints()
   

    def get_blockLabel(self, label):
        for block in self.blocks.values():
            if block.label == label:
                return block

    def get_loc2label(self, fncName, loc):
        point = self.loc2point[fncName][loc]
        return point.label

    def addLoopPoints_fnc(self, fncName, recDict):
        if type(recDict) is tuple: # Found loc
            self.loopPoints[fncName][recDict] = 0
        else: # else if dictionary, recurse
            for key, value in recDict.items():
                self.addLoopPoints_fnc(fncName, key)
                self.addLoopPoints_fnc(fncName, value)

    def addLoopPoints(self):
        for fncName in self.prog.loops:
            self.loopPoints[fncName] = {}
            self.addLoopPoints_fnc(fncName, self.prog.loops[fncName])

    def createCFG(self):
        for fnc in self.prog.fncs.values():
            visitedNodes = []
            nextNodes = [fnc.initloc]
            self.iterFnc(fnc, visitedNodes, nextNodes)

    def iterFnc(self, fnc, visitedNodes, nextNodes):
        while len(nextNodes) > 0:
            currLoc = nextNodes.pop(0)
            self.getPoint(fnc, currLoc)
            visitedNodes.append(currLoc)

            trueLoc = fnc.loctrans[currLoc][True]
            falseLoc = fnc.loctrans[currLoc][False]

            if Concretize.is_cond(fnc, currLoc): # If conditional block
                self.addEdge_cond(fnc, visitedNodes, nextNodes, currLoc, trueLoc, falseLoc)
            else: # Elif normal block
                self.addEdge_normal(fnc, visitedNodes, nextNodes, currLoc, trueLoc, falseLoc)

        self.entryPoints[fnc.name] = self.points[Point.get_label(fnc.name, fnc.initloc)]
        self.exitPoints[fnc.name] = self.points[Point.get_label(fnc.name, fnc.endloc)]

    def getPoint(self, fnc, loc):
        index = len(self.points) + 1
        label = Point.get_label(fnc.name, loc)
        if label not in self.points:
            newPoint = Point(index, fnc.name, loc, self.isPrimed)
            self.points[label] = newPoint
            self.label2point[newPoint.label] = newPoint
            
            if fnc.name not in self.loc2point:
                self.loc2point[fnc.name] = {}
            self.loc2point[fnc.name][loc] = newPoint

        return self.points[label]

    def getBlocks_src(self, src:Point) -> List[Block]:
        '''Given a src point, return all blocks/edges originating from src'''
        return [block
            for block in self.blocks.values()
                if block.src.label == src.label]

    def getBlocks_dest(self, dest:Point) -> List[Block]:
        '''Given a dest point, return all blocks/edges reaching at dest'''
        return [block
            for block in self.blocks.values()
                if block.dest.label == dest.label]

    def getBlocks_Cond(self, src:Point, isCondNegated:bool, isCondTrue:bool) -> List[Block]:
        '''Given a src point, return blocks which satisfy given condition requirements'''
        return [block
            for block in self.blocks.values()
                if block.src.label == src.label and block.cond.isCondNegated == isCondNegated and block.cond.isCondTrue == isCondTrue]

    def add_block2edge(self, fnc, loc:int, isTrue:bool, newBlock:Block):
        fncName = fnc.name
        if fncName not in self.block2edge:
            self.block2edge[fncName] = {}
            self.edge2block[fncName] = {}
        if loc not in self.block2edge[fncName]:
            self.block2edge[fncName][loc] = {True:None, False:None}

        self.block2edge[fncName][loc][isTrue] = newBlock
        self.edge2block[fncName][newBlock.label] = loc

    def addBlock(self, fnc, condLoc, exprLoc, srcLoc, destLoc, isTrue=True, isCondNegated=False, isCondTrue=False, isAfterFor=False):
        index = len(self.blocks)
        src = self.getPoint(fnc, srcLoc)
        dest = self.getPoint(fnc, destLoc)
        isAfterFor = False
        if 'update' in fnc.locdescs[src.loc]:
            isAfterFor = True
        newBlock = Block(index, src, dest, fnc.name, condLoc, exprLoc, 
            isPrimed=self.isPrimed, isCondNegated=isCondNegated, isCondTrue=isCondTrue, isAfterFor=isAfterFor)

        label = newBlock.get_hash(self.prog)
        if label not in self.blocks:
            self.blocks[label] = newBlock
            self.add_block2edge(fnc, exprLoc, isTrue, newBlock)
            self.label2block[newBlock.label] = newBlock

        return newBlock
    
    def addEdge_normal(self, fnc:parser.Function, visitedNodes:list, nextNodes:list,
            currLoc:int, trueLoc:int, falseLoc:int):
        assert falseLoc is None # Assume normal blocks have no transition on False

        if trueLoc is not None:
            self.addBlock(fnc, currLoc, currLoc, currLoc, trueLoc,
                isTrue=True, isCondNegated=False, isCondTrue=True)

        self.enqueue(visitedNodes, nextNodes, trueLoc)

    def addEdge_cond(self, fnc:parser.Function, visitedNodes:list, nextNodes:list,
            currLoc:int, trueLoc:int, falseLoc:int):
        # Skip to trueNext and falseNext by adding "[condloc] trueloc" and "[!condloc] falseloc"
        trueNext = fnc.loctrans[trueLoc][True]
        falseNext = fnc.loctrans[falseLoc][True]

        assert fnc.loctrans[trueLoc][False] is None # Assuming no false edges in the block
        assert fnc.loctrans[falseLoc][False] is None # following a conditional block

        # If this is a loop conditional loc
        if Concretize.is_loop(fnc, currLoc): 
            falseNext = falseLoc # Retain falseloc node (loop-exit is a primary node)
            falseLoc = None # The expr locations of a false loop-exit is empty.

        self.addBlock(fnc, currLoc, trueLoc, currLoc, trueNext,
            isTrue=True, isCondNegated=False, isCondTrue=False)
        self.addBlock(fnc, currLoc, falseLoc, currLoc, falseNext,
            isTrue=True, isCondNegated=True, isCondTrue=False)

        self.enqueue(visitedNodes, nextNodes, trueNext) # Visit True's next
        self.enqueue(visitedNodes, nextNodes, falseNext) # And False's next

    def enqueue(self, visitedNodes:list, nextNodes:list, loc:int):
        if loc is not None and loc not in visitedNodes:
            nextNodes.append(loc)

#endregion


def get_optCFG(prog:parser.Program, isPrimed=False):

    Minimize.mergeTrue(prog)
    Minimize.fix_returnTrans(prog)
    Minimize.replIf_ite(prog)
    Minimize.merge_ite_iter(prog)
    Minimize.merge_none_false_branch_blocks(prog)
    Minimize.index_ite(prog)
    cfg = CFG(prog, isPrimed)
    return cfg

    

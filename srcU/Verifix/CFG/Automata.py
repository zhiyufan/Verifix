import pandas as pd

from graphviz import Digraph
from typing import List
import copy, textwrap

from srcU.Verifix.CFG import CFG

from srcU.ClaraP import model

#region: Classes 

class Node:
    def __init__(self, p1:CFG.Point, p2:CFG.Point):
        self.p1 = p1
        self.p2 = p2
        
        self.label = p1.label + p2.label

    def __str__(self):
        return self.label


class Path:
    def __init__(self, src:Node, dest:Node, blocks_c:List[CFG.Block], blocks_i:List[CFG.Block], fncName):
        self.src = src
        self.dest = dest
        self.blocks_c = blocks_c
        self.blocks_i = blocks_i
        self.fncName = fncName

        self.isValid = None
        self.solver = {'vcgen':None, 'errorloc': None, 'repair':None}
        self.model = {'vcgen':None, 'errorloc': None, 'repair':None}

        self.repairs_tmp = []
        self.errors = [] # List of Error (objects)
        # j-j flag-r [B;B'] B;B'
        self.repair_space = {} # List of Repair objects
        # B'.cond = newCond, B'.locExpr.j1=newJ1, B'j2=newJ2, B'.r=newR

    def add_reps_candidate(self, line, idx, expr):
        if 'ce0' not in line:
            return
        self.repair_space.setdefault(line, {})
        self.repair_space[line][idx] = expr

    def get_align_pred_fnc(self, ppa):
        return ppa.align_pred[self.fncName]

    def get_index(self, label, isCorrect):
        def get_index_block(blocks, label)        :
            for index, block in enumerate(blocks):
                if block.label == label:
                    return index

        if isCorrect:
            return get_index_block(self.blocks_c, label)
        return get_index_block(self.blocks_i, label)
            

    def get_labelsC(self):
        return ''.join([b.label for b in self.blocks_c])

    def get_labelsI(self):
        return ''.join([b.label for b in self.blocks_i])

    def get_var_type(self, prog, key):

        if key == 'break' or key == 'continue':
            return 'int'
        if key == '$outInt' or key == '$outFloat':
            return 'list'

        types = prog.fncs[self.fncName].types
        if str(key) in types:
            return types[str(key)]

    def __str__(self):
        labelsC = self.get_labelsC()
        labelsI = self.get_labelsI()
        return '{};{}'.format(labelsC, labelsI)

    def __deepcopy__(self, memo):
        '''ignore to copy solver'''
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k in ['solver', 'model']:
                setattr(result, k, {'vcgen':None, 'errorloc': None, 'repair':None})
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result
    
    def get_label(self, ppa):
        progC, progI = ppa.cfgC.prog, ppa.cfgI.prog
        blocks_str = []

        for prog, blocks,isPrimed in zip([progC, progI], [self.blocks_c, self.blocks_i], [False, True]):
            for block in blocks:
                newCond = block.get_cond(prog)
                stats = []

                # Prime the cond
                if isPrimed and isinstance(newCond, model.Expr):
                    newCond = copy.deepcopy(newCond)
                    newCond.prime(newCond.vars())
                
                # Prime each var/expr
                for var, expr in block.get_varExprs(prog):
                    newExpr = expr
                
                    if isPrimed and isinstance(expr, model.Expr):
                        var = var + '\''
                        newExpr = copy.deepcopy(expr)
                        newExpr.prime(newExpr.vars())                        

                    # Append the stats
                    stats.append('%s := %s;' % (var, newExpr.tostring())) 
                # Append the entire block str
                stri = '{} [{}] {}'.format(block.label, str(newCond), ' '.join(stats))
                blocks_str.append(textwrap.fill(stri, 100))


        return '\n'.join(blocks_str)


class PPA:
    def __init__(self, cfgC, cfgI):
        self.cfgC, self.cfgI = cfgC, cfgI
        self.nodes = {}
        self.paths = {}
        self.align_pred = {} # {fnc: {varC:varI}}
        self.entryNodes = {} # {fnc1: entryNode1}

    def add_entryNode(self):
        for nodeLabel in self.nodes:
            node = self.nodes[nodeLabel]
            fnc1, fnc2 = self.cfgC.prog.fncs[node.p1.fncName], self.cfgI.prog.fncs[node.p2.fncName]

            # Search for the nodePair which maps to initloc of function
            if node.p1.loc == fnc1.initloc and node.p2.loc == fnc2.initloc:

                # Add this node as entryNode for that function
                self.entryNodes[node.p1.fncName] = node

    def get_maxIndex_block(self, isCorrect):
        index = -1
        for path in self.paths.values():

            blocks = path.blocks_i
            if isCorrect:
                blocks = path.blocks_c

            for block in blocks:
                index = max(index, block.index)
        
        return index

    def addNode(self, p1:CFG.Point, p2:CFG.Point):
        newNode = Node(p1, p2)
        label = str(newNode)
        if label not in self.nodes:
            self.nodes[label] = newNode

        return self.nodes[label]

    def addPath(self, src:Node, dest:Node, blocks_c:List[CFG.Block], blocks_i:List[CFG.Block], fncName):
        newPath = Path(src, dest, blocks_c, blocks_i, fncName)
        label = str(newPath)
        if label not in self.paths:
            self.paths[label] = newPath

        return self.paths[label]

    def addBlockI(self, path, newBlockI):
        '''Insert a new blockI into the path, while maintaining the right labels'''
        oldLabel = str(path) # Store the old label
        path.blocks_i.append(newBlockI) # Append the new block to path
        self.paths.pop(oldLabel) # Delete old label/path
        self.paths[str(path)] = path # Add new label/path

#endregion

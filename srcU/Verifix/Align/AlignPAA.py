import pandas as pd
import itertools, copy
from collections import OrderedDict
from typing import Union, List

from srcU.ClaraP.model import Var, Op, Const
from srcU.Verifix.CFG import CFG, Automata
from srcU.Verifix.Align import AlignPred

#region: Local helper functions

def get_paths_rec(cfg:CFG.CFG, major_nodes:list, src:CFG.Point, dest:CFG.Point, visited:dict):
    '''Enumerate all paths/transitions starting at src and ending at dest. Makes use of a visited store to avoid repeated recursion.'''
    blocks_li = []    

    # Search for blocks that have specified src
    for block in cfg.blocks.values():
        if block.src == src:

            # If dest is reached, terminate the recursion
            if block.dest == dest: 
                blocks_li.append([block])

            # Otherwise, if the dest is not a "major" node (non-cyclic)
            elif block.dest.label not in major_nodes:

                # If this node was visited earlier, use the stored value                
                if block.dest.label in visited:  
                    blocks_tmp = visited[block.dest.label]           

                # Otherwise, recurse
                else:              
                    blocks_tmp = get_paths_rec(cfg, major_nodes, block.dest, dest, visited)

                # Merge & append to current-block + recurse-blocks to blocks_li
                for blocks in blocks_tmp:
                    blocks_li.append([block] + blocks)
    
    # print(src.label, dest.label, visited.keys(), ' '.join([''.join([block.label for block in blocks]) for blocks in blocks_li]))
    visited[src.label] = blocks_li
    return blocks_li

#endregion

#region: Align nodes

def gen_alignPoints(res, pointsC, pointsI, align_nodes):
    for fncName in pointsC:
        if fncName not in pointsI: # Same function names exist
            res.exception = 'structural mismatch'
            # raise Exception('structural mismatch')

        if fncName not in align_nodes:
            align_nodes[fncName] = {}

        labelC, labelI = pointsC[fncName].label, pointsI[fncName].label
        align_nodes[fncName][labelC] = labelI # {fncName:{labelC:labelI}}

def gen_alignLoop_rec(res, cfgC, cfgI, loopsC:OrderedDict, loopsI:OrderedDict, align_nodes, fncName):
    '''Important for loopsC and loopsI to be ordered'''
    # Nesting levels differ? Struct mismatch
    if len(loopsC) != len(loopsI):
        res.exception = 'structural mismatch'
        # raise Exception('structural mismatch')

    for key_loopC, key_loopI in zip(loopsC.keys(), loopsI.keys()): 
        # Extract the locs tuple
        loccond_c, locexit_c, locnext_c = key_loopC
        loccond_i, locexit_i, locnext_i = key_loopI

        # Get the point labels
        labelcond_c, labelcond_i = cfgC.get_loc2label(fncName, loccond_c), cfgI.get_loc2label(fncName, loccond_i)
        labelexit_c, labelexit_i = cfgC.get_loc2label(fncName, locexit_c), cfgI.get_loc2label(fncName, locexit_i)

        # Align the loop-entry and loop-exit nodes
        align_nodes[fncName][labelcond_c] = labelcond_i
        align_nodes[fncName][labelexit_c] = labelexit_i
        
        # Recurse nesting
        loopsC_rec, loopsI_rec = loopsC[key_loopC], loopsI[key_loopI]        
        gen_alignLoop_rec(res, cfgC, cfgI, loopsC_rec, loopsI_rec, align_nodes, fncName)

def gen_alignLoop(res, cfgC, cfgI, align_nodes):
    for fncName in cfgC.prog.loops: # For each reference function       
        # Reference function doesn't exist in incorrect code? Struct mismatch
        if fncName not in cfgI.prog.loops:
            res.exception = 'structural mismatch'
            return
            # raise Exception('structural mismatch')
        
        # Recurse through nested loops
        loopsC, loopsI = cfgC.prog.loops[fncName], cfgI.prog.loops[fncName]
        gen_alignLoop_rec(res, cfgC, cfgI, loopsC, loopsI, align_nodes, fncName)

def gen_alignNodes(res, cfgC, cfgI):
    '''TODO: Make it independent of functions?'''
    align_nodes = {} # {fnc: {q1:q1'}}
    
    if len(cfgC.entryPoints) != len(cfgI.entryPoints) \
        or len(cfgC.exitPoints) != len(cfgI.exitPoints):
        res.exception = 'structural mismatch'
        # raise Exception('structural mismatch')
    
    # Map Entry and Exit points per func call
    gen_alignPoints(res, cfgC.entryPoints, cfgI.entryPoints, align_nodes)
    gen_alignPoints(res, cfgC.exitPoints, cfgI.exitPoints, align_nodes)

    # Map loop points
    gen_alignLoop(res, cfgC, cfgI, align_nodes)

    # print('Aligned nodes: ', align_nodes)
    return align_nodes

#endregion

#region: Align paths

def copy_ppa(fncName, ppa_oldLi:List[Automata.PPA], ppa_newLi:List[Automata.PPA], src_c:CFG.Point, src_i:CFG.Point, 
    dest_c:CFG.Point, dest_i:CFG.Point, aligned_paths):
    for ppa_old in ppa_oldLi:
        ppa_new = copy.deepcopy(ppa_old)

        for aligned_path in aligned_paths:                    
            blocks_c, blocks_i = aligned_path
            src = ppa_new.addNode(src_c, src_i)
            dest = ppa_new.addNode(dest_c, dest_i)
            ppa_new.addPath(src, dest, blocks_c, blocks_i, fncName)

        ppa_newLi.append(ppa_new)


def align_paths(ppa_oldLi: List[Automata.PPA], src_c: CFG.Point, src_i: CFG.Point, dest_c: CFG.Point, dest_i: CFG.Point,
                paths_c: List[List[CFG.Block]], paths_i: List[List[CFG.Block]], fncName):

    # Are there any paths to align?
    if len(paths_c) + len(paths_i) == 0:
        return ppa_oldLi
    
    ppa_newLi = []
    # List of known permutations
    if len(paths_c) == 0 and len(paths_i) == 1:
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i, [([], paths_i[0])])  # e-1

    elif len(paths_c) == 1 and len(paths_i) == 0:
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i, [(paths_c[0], [])])  # 1-e

    elif len(paths_c) == 1 and len(paths_i) == 1:
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i, [(paths_c[0], paths_i[0])])  # 1-1

    elif len(paths_c) == 1 and len(paths_i) == 2:
        # copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
        #          [(paths_c[0], paths_i[0]), (paths_c[0], paths_i[1])])  # 1-1, 1-2
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[0]), ([], paths_i[1])])  # 1-1, e-2
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[1]), ([], paths_i[0])])  # e-1, 1-2

    elif len(paths_c) == 2 and len(paths_i) == 1:
        # copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
        #          [(paths_c[0], paths_i[0]), (paths_c[1], paths_i[0])])  # 1-1, 2-1
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[0]), (paths_c[1], [])])  # 1-1, 2-e
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], []), (paths_c[1], paths_i[0])])  # 1-e, 2-1

    elif len(paths_c) == 2 and len(paths_i) == 2:
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[0]), (paths_c[1], paths_i[1])])  # 1-1, 2-2
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[1]), (paths_c[1], paths_i[0])])  # 1-2, 2-1

    elif len(paths_c) == 2 and len(paths_i) == 3:
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[0]), (paths_c[1], paths_i[1]), ([], paths_i[2])])  # 1-1, 2-2, e-3
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[1]), (paths_c[1], paths_i[0]), ([], paths_i[2])])  # 1-2, 2-1, e-3

        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[0]), (paths_c[1], paths_i[2]), ([], paths_i[1])])  # 1-1, 2-3, e-2
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[2]), (paths_c[1], paths_i[0]), ([], paths_i[1])])  # 1-3, 2-1, e-2

        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[2]), (paths_c[1], paths_i[1]), ([], paths_i[0])])  # 1-3, 2-2, e-1
        copy_ppa(fncName, ppa_oldLi, ppa_newLi, src_c, src_i, dest_c, dest_i,
                 [(paths_c[0], paths_i[1]), (paths_c[1], paths_i[2]), ([], paths_i[0])])  # 1-2, 2-3, e-1

    else:
        raise Exception(
            'Aligning path error: Unspecified action for len(paths_c)={} and len(paths_i)={}'.format(len(paths_c),
                                                                                                     len(paths_i)))

    return ppa_newLi

#endregion

#region: Align edge by type

def get_paths_break(prog, paths:List[List[CFG.Block]]):
    '''Return list of all paths that end in a break'''
    paths_brk, paths_oth = [], []

    for path in paths:
        breakFlag = False

        for block in path:
            for var, expr in block.get_varExprs(prog):
                if var == 'break':
                    breakFlag = True
                    break

            if breakFlag: break
            
        if breakFlag: paths_brk.append(path)
        else: paths_oth.append(path)

    return paths_brk, paths_oth

def get_paths_return(prog, paths:List[List[CFG.Block]]):
    '''Return list of all paths that end in a return'''
    paths_ret, paths_oth = [], []

    for path in paths:
        breakFlag = False
        
        for block in path:
            for var, expr in block.get_varExprs(prog):
                if var == 'ret':
                    breakFlag = True
                    break

            if breakFlag: break

        if breakFlag: paths_ret.append(path)
        else: paths_oth.append(path)

    return paths_ret, paths_oth

def align_paths_type(ppa_oldLi: List[Automata.PPA], cfgC, cfgI, src_c: CFG.Point, src_i: CFG.Point, dest_c: CFG.Point, dest_i: CFG.Point,
                paths_c: List[List[CFG.Block]], paths_i: List[List[CFG.Block]], fncName):
    '''Align by edge-type'''
    paths_c_oth, paths_i_oth = paths_c, paths_i
    ppa_newLi = ppa_oldLi

    # Align break paths
    paths_c_brk, paths_c_oth = get_paths_break(cfgC.prog, paths_c_oth)
    paths_i_brk, paths_i_oth = get_paths_break(cfgI.prog, paths_i_oth)
    ppa_newLi = align_paths(ppa_newLi, src_c, src_i, dest_c, dest_i, paths_c_brk, paths_i_brk, fncName)

    # Align return paths
    paths_c_ret, paths_c_oth = get_paths_return(cfgC.prog, paths_c_oth)
    paths_i_ret, paths_i_oth = get_paths_return(cfgI.prog, paths_i_oth)
    ppa_newLi = align_paths(ppa_newLi, src_c, src_i, dest_c, dest_i, paths_c_ret, paths_i_ret, fncName)

    # Align "other" (normal/continue) paths
    ppa_newLi = align_paths(ppa_newLi, src_c, src_i, dest_c, dest_i, paths_c_oth, paths_i_oth, fncName)

    return ppa_newLi

def align_paths_rec(ppa_oldLi:List[Automata.PPA], src_c:CFG.Point, src_i:CFG.Point, dest_c:CFG.Point, dest_i:CFG.Point,
        paths_c:List[List[CFG.Block]], paths_i:List[List[CFG.Block]], fncName):
    '''ToDo: Incomplete'''
    
    if len(paths_c) >= 4 or len(paths_i) >= 4:
        raise Exception('Aligning paths: too many combinations')



#endregion

#region: Main function for automata alignment

def generate_ppaLi(res, cfgC, cfgI, align_nodes, debug=False):
    '''Given cfg for correct and incorrect, generate all possible PAAs.'''
    ppa_li = [Automata.PPA(cfgC, cfgI)]    

    for fncName in align_nodes: # For each func
        for src_cL in align_nodes[fncName]: # For each src node
            src_iL = align_nodes[fncName][src_cL]
            
            for dest_cL in align_nodes[fncName]: # For each dest node
                dest_iL = align_nodes[fncName][dest_cL]                       
                
                # Get actual nodes
                src_c, dest_c = cfgC.label2point[src_cL], cfgC.label2point[dest_cL]
                src_i, dest_i = cfgI.label2point[src_iL], cfgI.label2point[dest_iL]
                
                # Get actual paths
                major_nodes = list(align_nodes[fncName].keys()) + list(align_nodes[fncName].values())
                paths_c = get_paths_rec(cfgC, major_nodes, src_c, dest_c, {})
                paths_i = get_paths_rec(cfgI, major_nodes, src_i, dest_i, {})

                # Generate the PPA if there exists any path
                # print(src_cL, dest_cL, src_iL, dest_iL, len(paths_c), len(paths_i), len(ppa_li))                  
                if len(paths_c) + len(paths_i) > 0: 
                    # print(src_c.label, dest_c.label)
                    # print([[i.label for i in path] for path in paths_c])
                    ppa_li = align_paths_type(ppa_li, cfgC, cfgI, src_c, src_i, dest_c, dest_i, paths_c, paths_i, fncName)
    
    for ppa in ppa_li:
        ppa.align_pred = AlignPred.get_alignPred(res, ppa, cfgC, cfgI, debug=debug)
        ppa.add_entryNode()

    # print('#Possible PPA = ', len(ppa_li))
    return ppa_li

#endregion

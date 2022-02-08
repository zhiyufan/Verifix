from srcU.Verifix.CFG import CFG, Concretize
from srcU.Verifix.CFG.Automata import PPA, Path
from srcU.ClaraP import model


# region: Delete Path

def repair_noPath(ppa:PPA, path:Path):
    '''Delete invalid path'''
    if len(path.blocks_c) == 0: # If it is an invalid path (doesn't correspond with correct transition)

        for blockI in path.blocks_i: # For each block in this invalid transition
            # if blockI.changed:
            #     continue
            condI = blockI.cond
            fncI = ppa.cfgI.prog.fncs[condI.fncName]

            blockI.del_varExprs(ppa.cfgI.prog) # Delete the statements inside it

            # If it neither a "True" block nor a Loop block
            if not condI.isCondTrue and not Concretize.is_loop(fncI, condI.loc):
                blockI.set_cond(ppa.cfgI.prog, model.Op('False')) # Simply set the condition of block as false
                # break # And stop future edits; Since if first block is false, then following blocks won't be executed either
        return True

# def repair_noPath(ppa:PPA, path:Path):
#     '''Delete invalid path'''
#     if len(path.blocks_c) == 0: # If it is an invalid path (doesn't correspond with correct transition)
#
#         # Delete the statements from model
#         blockI = path.blocks_i[-1] # Pick the last incorrect block
#         blockI.del_varExprs(ppa.cfgI.prog) # Delete all the statements inside it
#
#         # condI = blockI.cond
#         # fncI = ppa.cfgI.prog.fncs[condI.fncName]
#         # # Delete the edge from automata
#         # if not condI.isCondTrue and not Concretize.is_loop(fncI, condI.loc):
#         #     blockI.set_cond(ppa.cfgI.prog, model.Op('False'))  # Simply set the condition of block as false
#         ppa.paths.pop(str(path))
#
#         return True

#endregion

#region: Insert Path - fix transitions

def repair_newPath_newLocs(ppa, path):
    '''Create new locs with dummy lineNum of 10000+x'''
    fnc = ppa.cfgI.prog.fncs[path.fncName]
    currLoc = max(fnc.loctrans.keys()) + 1
    lineNum = 10000 + currLoc

    currLoc = fnc.addloc(desc='the condition of the if-statement at line %s' % (lineNum))
    trueLoc = fnc.addloc(desc='inside the if-branch starting at line %s' % (lineNum))
    afterIfLoc = fnc.addloc(desc='after the if-statement beginning at line %s' % (lineNum))

    return fnc, currLoc, trueLoc, afterIfLoc

def repair_newPath_transTo(ppa, path, fnc, currLoc, trueLoc, afterIfLoc, blockLoop):
    '''Fix transitions to new locs. IsLoopCond flag tells if currLoc is a loop'''
    srcLoc = path.src.p2.loc
    if fnc.initloc == srcLoc: # Fix initloc trans
        fnc.initloc = currLoc

    # If edge involves a loop condition
    locLoopInsideNext = None
    if blockLoop: 
        locLoopCond = blockLoop.cond.loc
        locLoopInside = fnc.loctrans[locLoopCond][True]
        locLoopInsideNext = fnc.loctrans[locLoopInside][True]
        srcLoc = locLoopInsideNext # Fix transitions inside loop instead

    # All transitions to srcLoc now point to new if-cond
    for loc in fnc.loctrans: 
        if fnc.loctrans[loc][True] == srcLoc:
            fnc.loctrans[loc][True] = currLoc
        if fnc.loctrans[loc][False] == srcLoc:
            fnc.loctrans[loc][False] = currLoc

    return locLoopInsideNext

def repair_newPath_transFrom(ppa, path, fnc, currLoc, trueLoc, afterIfLoc, blockLoop, locLoopInsideNext):
    '''Fix transitions from new locs'''
    
    fnc.loctrans[currLoc][True] = trueLoc
    fnc.loctrans[currLoc][False] = afterIfLoc
    fnc.loctrans[trueLoc][True] = afterIfLoc#path.dest.p2.loc

    # If edge involves a loop condition
    if blockLoop: 
        fnc.loctrans[afterIfLoc][True] = locLoopInsideNext 
    else:
        fnc.loctrans[afterIfLoc][True] = path.src.p2.loc 

#endregion

#region: Insert Path - fix cond/data of other paths

def repair_newPath_origPath(ppa, path, fnc, currLoc, trueLoc, afterIfLoc):
    '''Search for the other orig path that originates from src, and map its cond-loc to currLoc (where new if-cond was added)'''
    count = 0

    for origPath in ppa.paths.values():
        if origPath != path and origPath.src == path.src:
            count += 1

            assert len(origPath.blocks_i) > 0, 'Repair newPath: assumption of atleast one blockI in original path is violated'
            blockI = origPath.blocks_i[0]

            assert blockI.cond.isCondTrue, 'Repair newPath: assumption of blockI.cond being True in original path is violated'
            blockI.cond = CFG.Cond(fnc.name, currLoc, isCondNegated=True) # Set its cond = !(newBlock's cond)            

    assert count == 1, 'Repair newPath: assumption of single origPath violated, %s multiple origPaths exist!' % (count)

def repair_newPath_block(ppa, path, fnc, currLoc, trueLoc, afterIfLoc, blockLoop):
    '''Add new block'''
    # Create new block with "$cond" expr
    fnc.addexpr(currLoc, '$cond', model.Op('True'))
    newBlock = ppa.cfgI.addBlock(fnc, currLoc, trueLoc, currLoc, afterIfLoc, 
        isTrue=True, isCondNegated=False, isCondTrue=False)
    var_expr = newBlock.get_varExprs(ppa.cfgI.prog)
    var_expr.insert(0, ('dummy', model.Var('dummy')))
    var_expr.insert(0, ('dummy', model.Var('dummy')))
    # Insert this block into path & update the label
    ppa.addBlockI(path, newBlock)

    # Update block-cond of the alternate (original) path, if it isn't loopCond
    if not blockLoop:
        repair_newPath_origPath(ppa, path, fnc, currLoc, trueLoc, afterIfLoc)

#endregion

#region: Insert Path - handle if/loop seperately

def repair_newPath_loopCond(ppa:PPA, path:Path):
    '''If pathC.cond is loop, then insert corresponding loop condition into pathI'''
    condC = path.blocks_c[0].cond
    fncC = ppa.cfgC.prog.fncs[condC.fncName]
    
    # Is the first block of reference path a loop-cond?
    if Concretize.is_loop(fncC, condC.loc):
        # Get the corresponding incorrect CFG src-point and CFG blocks originating from this src-point
        srcPointI = path.src.p2
        blocks = ppa.cfgI.getBlocks_Cond(srcPointI, isCondNegated=condC.isCondNegated, isCondTrue=condC.isCondTrue)

        # Add the incorrect loop condition to the path
        blockLoop = blocks[0] # Any such block is fine, since they are all the same  
        ppa.addBlockI(path, blockLoop)

        # Fix the transitions 
        return blockLoop
    

def repair_newPath(ppa:PPA, path:Path):
    '''Add non existing path'''
    if len(path.blocks_i) == 0:
        # If the pathC is a loop edge, add loopCond to pathI
        blockLoop = repair_newPath_loopCond(ppa, path)

        # Create new if locs and their transitions
        fnc, currLoc, trueLoc, afterIfLoc = repair_newPath_newLocs(ppa, path) # Create new locs        
        locLoopInsideNext = repair_newPath_transTo(ppa, path, fnc, currLoc, trueLoc, afterIfLoc, blockLoop) # Fix transitions into new locs - run this before "from"
        repair_newPath_transFrom(ppa, path, fnc, currLoc, trueLoc, afterIfLoc, blockLoop, locLoopInsideNext) # Fix transitions from new locs        

        # Insert the new if block and fix other edge conds
        repair_newPath_block(ppa, path, fnc, currLoc, trueLoc, afterIfLoc, blockLoop) # Add the cond block
        return True

#endregion

#region: Ins/Del path

def repair_edge(ppa:PPA, path:Path):
    flag_noPath = repair_noPath(ppa, path)   # Delete existing path
    flag_newPath = repair_newPath(ppa, path) # Insert new path

    if flag_noPath or flag_newPath:
        errorStr = '{}->edge'.format(path.get_labelsI())
        path.errors.append(errorStr)
        path.repairs_tmp.append(errorStr)
        return True
    return False
#endregion


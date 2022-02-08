from srcU.Verifix.CFG import CFG, Automata
from srcU.Verifix.Verify import VCGen, VCGen_Block, SMT
from z3 import *
from typing import Union, List


# endregion

# region: checker

def solver_result(path, mode):

    path.solver[mode].set("timeout", 10000)  # 1000 ms
    res = path.solver[mode].check()
    return res


def verify(path, mode, preCE=[]):
    '''TODO: If UNKNOWN, try passing the exact values of variables to Z3'''
    res = solver_result(path, mode)

    if res == unsat:
        path.isValid = True
    else:
        # TODO unknow but exist model

        path.isValid = False

        path.model[mode] = path.solver[mode].model()

        if mode == 'vcgen' or mode == 'apply_repair':
            preCE.append(path.model[mode])
    return path.isValid

# endregion

# region: VCGen Block

def vcgen_block(prog, path, solver: z3.Optimize, blocks: List[CFG.Block],
                vari: dict, align_pred_fnc: dict, isCorrect: bool, ce_index: str, mode=None, repairs=None,
                candidates=None):
    z3_prevCond = None
    bools = []
    # For each block
    last_block = False
    for idx, block in enumerate(blocks):
        if idx == len(blocks) - 1:
            last_block = True
        # label
        label = '@' + block.label
        bool_block = Bool('ce{}-block{}'.format(ce_index, label))
        bools.append(bool_block)

        # Collect control and add data-check
        z3_prevCond = VCGen_Block.add_blockCond(prog, path, solver, z3_prevCond, label, block.get_cond(prog),
                                                block.get_varExprs(prog),
                                                vari, align_pred_fnc, isCorrect, mode=mode, repairs=repairs,
                                                candidates=candidates, ce_index=ce_index, last_block=last_block)

    # Add overall blocksC/blocksI
    if isCorrect:
        bool_name = 'ce{}-blocksC'.format(ce_index)
    else:
        bool_name = 'ce{}-blocksI'.format(ce_index)

    query = Bool(bool_name) == And(bools)
    if mode == 'repair':
        block_mode = 'vcgen'
    else:
        block_mode = mode
    VCGen_Block.add_solver(solver, query, mode=block_mode)


# endregion

# region: VCGen Path

def vcgen_path(ppa: Automata.PPA, path: Automata.Path, repairs=[], preCE=[], candidates=[], mode=None):
    '''Default: Run in VCGen mode. Given an oldModel, run in CE mode'''
    # z3.set_param("parallel.enable", True)
    # z3.set_option("parallel.threads.max", 10)
    # z3.set_param("timeout", 5000)

    # z3.Z3_reset_memory()
    if mode == 'repair':
        solver = z3.Optimize()
    else:
        solver = z3.Optimize()
        # solver = z3.Solver()
    if mode == 'repair':
        num_loop = len(preCE)
    else:
        num_loop = 1

    for idx in range(num_loop):
        idx = str(idx)
        vari = VCGen.get_vari(solver, ppa, path, ce_index=idx)
        align_pred_fnc = path.get_align_pred_fnc(ppa)

        # Add Pre-Conditions
        VCGen.add_preCond(solver, vari, ppa, path, align_pred_fnc, mode=mode, ce_index=idx)
        # VCGen.add_invariants(solver, vari, ppa, path, mode=mode, ce_index=idx)

        old_inIdx, new_inIdx = SMT.z3_varNew(solver, 'ce{}-I-$inIdx'.format(idx), vari, isCorrect=False, myType='int')
        old_outIntIdx, new_outIntIdx = SMT.z3_varNew(solver, 'ce{}-I-$outIntIdx'.format(idx), vari, isCorrect=False, myType='int')
        old_outFloatIdx, new_outFloatIdx = SMT.z3_varNew(solver, 'ce{}-I-$outFloatIdx'.format(idx), vari, isCorrect=False, myType='int')

        old_inIdxc, new_inIdxc = SMT.z3_varNew(solver, 'ce{}-C-$inIdx'.format(idx), vari, isCorrect=True, myType='int')
        old_outIntIdxc, new_outIntIdxc = SMT.z3_varNew(solver, 'ce{}-C-$outIntIdx'.format(idx), vari, isCorrect=True, myType='int')
        old_outFloatIdxc, new_outFloatIdxc = SMT.z3_varNew(solver, 'ce{}-C-$outFloatIdx'.format(idx), vari, isCorrect=True, myType='int')

        solver.add(new_inIdx.smtVar == new_inIdxc.smtVar)
        solver.add(new_outIntIdx.smtVar == new_outIntIdxc.smtVar)
        solver.add(new_outFloatIdx.smtVar == new_outFloatIdxc.smtVar)
        solver.add(new_inIdx.smtVar == 0)
        solver.add(new_outIntIdx.smtVar == 0)
        solver.add(new_outFloatIdx.smtVar == 0)

        # Add blocks
        vcgen_block(ppa.cfgC.prog, path, solver, path.blocks_c, vari, align_pred_fnc, isCorrect=True, mode='vcgen',
                    repairs=repairs, candidates=candidates, ce_index=idx)
        vcgen_block(ppa.cfgI.prog, path, solver, path.blocks_i, vari, align_pred_fnc, isCorrect=False, mode=mode,
                    repairs=repairs, candidates=candidates, ce_index=idx)

        # Add Post-Condition
        VCGen.add_postCond(solver, vari, align_pred_fnc, mode='vcgen', ce_index=idx)

        # Add final Condition
        if mode == 'repair':
            VCGen.add_finalCE(solver, ce_index=idx)
            VCGen.add_counterexample(solver, ce_index=idx, preCE=preCE)
        else:
            VCGen.add_finalVC(solver, ce_index=idx)
            VCGen.add_counterexample_reverse(solver, ce_index=idx, preCE=preCE)

        final_cond = Bool('ce{}-final'.format(idx))
        VCGen_Block.add_solver(solver, final_cond)

    if mode == 'repair':
        VCGen.add_post_bool(solver, path, num_loop)

    path.solver[mode] = solver



def verify_path(ppa: Automata.PPA, path: Automata.Path, preCE=[], candidates=[], repairs=[], mode=None):

    vcgen_path(ppa, path, preCE=preCE, candidates=candidates, repairs=repairs, mode=mode)
    return verify(path, mode=mode, preCE=preCE)


# endregion

# region: VCGen PPA


def verify_ppa(ppa: Automata.PPA, debug=False):
    numValid = 0
    sat_labels, unsat_labels = '', ''

    # For each path starting from source-node
    for path_label in ppa.paths:
        path = ppa.paths[path_label]
        # Verify it

        # if 'DG' not in path_label:
        #     continue
        import time
        start = time.time()
        verify_path(ppa, path, preCE=[], mode='vcgen')
        # print('before repair verification', time.time()-start)
        # If valid
        if path.isValid:
            numValid += 1
            unsat_labels += str(path) + ' * '
        else:  # Else invalid
            sat_labels += str(path) + ' * '

    if debug:
        print('SAT paths:', sat_labels)
        print('UNSAT paths:', unsat_labels)
        print('#Valid Paths = {}/{}\n'.format(numValid, len(ppa.paths)))

    return numValid, len(ppa.paths)

# endregion

from srcU.Verifix.Repair import Error, RepairEdge, RepairFormula, RepairSpace
from srcU.Verifix.Verify import Verification
from srcU.Verifix.CFG.Automata import PPA, Path
from srcU.Verifix.Process import Preprocessing
import copy, time, sys

import pandas as pd

def repair_path(ppa_orig: PPA, path_orig: Path, time_bound=60):
    '''Given an incorrect path, repeat until failure: localization -> repair -> validate'''
    CE = []
    final_repair = None
    timeout = False
    no_repair_exist = False
    start = time.time()
    # print('start repair')
    # Construct all repair space
    error = Error.Error(ppa_orig, path_orig, preCE=CE)
    repair_candidates = RepairSpace.construct_repair_space(ppa_orig, path_orig, error)
    idx = 0

    while not (final_repair is not None or timeout or no_repair_exist):
        exception = None
        # print(idx)

        start1 = time.time()
        ppa_tmp = copy.deepcopy(ppa_orig)
        path_tmp = copy.deepcopy(path_orig)

        # Step-1: VCGen, find one counter-example by pre /\ inv /\ blocksC /\ blocksI /\ not post
        Verification.verify_path(ppa_tmp, path_tmp, mode='vcgen', preCE=CE)
        # print(time.time()-start1)
        # print(1)
        for ce in CE:
            if len(ce) == 0:
                exception = 'Unknown, without CE in Verification'
        if exception != None:
            idx += 1
            break
        else:

            # repair_time = time.time()
            # Step-2: Feed all repair candidates by all_CE /\ blocksC /\ blocksI /\ all repairs (soft) /\ post
            repair_pairs, exception = select_repairs(ppa_tmp, path_tmp, preCE=CE, candidates=repair_candidates)
            repair_query = str(path_tmp.solver['repair'].sexpr())
            # print(time.time()-repair_time)
            # print(2)
            if len(repair_pairs) == 0:
                no_repair_exist = True

            # Step-3 Validate correctness of all repair pairs by pre /\ blocksC /\ blocksI-repaired /\ not post.
            final_repair, repair_space = validate_repairs(ppa_tmp, path_tmp, preCE=CE, repair_pairs=repair_pairs,
                                                          candidates=repair_candidates)

            timeout = (time.time() - start) > time_bound
            idx += 1

    if final_repair is not None:
        try:
            RepairFormula.update_repairs(ppa_orig.cfgI.prog, path_orig, final_repair, repair_space)
        except:
            exception = 'Update Failure'
    elif timeout:
        exception = 'timeout after {} when repair PATH {}'.format(time.time() - start, str(path_orig))

    return ppa_orig, ppa_orig.paths[str(path_orig)], exception


def select_repairs(ppa: PPA, path: Path, preCE=[], candidates=None):
    repair_pairs = []
    exception = None
    isUNSAT = Verification.verify_path(ppa, path, mode='repair', preCE=preCE, candidates=candidates)
    if isUNSAT:
        exception = 'unsat, maxSMT'
    else:
        try:
            repair_pairs = RepairFormula.get_valid_repairs(path)
        except:
            exception = "unknown, maxSMT"
    return repair_pairs, exception


def validate_repairs(ppa: PPA, path: Path, preCE=[], repair_pairs=None, candidates=None):
    for idx, repair_pair in enumerate(repair_pairs):
        validate_ppa = copy.deepcopy(ppa)
        validate_path = copy.deepcopy(path)
        RepairFormula.update_repairs(validate_ppa.cfgI.prog, validate_path, repair_pair, validate_path.repair_space)
        isValid = Verification.verify_path(validate_ppa, validate_path, preCE=preCE, mode='vcgen', repairs=repair_pair,
                                           candidates=candidates)

        if isValid:
            return repair_pair, path.repair_space
    return None, {}


# region: Repair PPA
def repair(ppa: PPA, times=3000, debug=False):
    path_labels = copy.deepcopy(list(ppa.paths.keys()))
    exception = []
    for path_label in path_labels:
        path = ppa.paths[path_label]

        # Verify it
        import time
        ppa_tmp = copy.deepcopy(ppa)
        path_tmp = copy.deepcopy(path)

        is_valid = Verification.verify_path(ppa_tmp, path_tmp, preCE=[], mode='vcgen')

        start = time.time()
        if not is_valid:
            RepairEdge.repair_edge(ppa, path)
            # print('repair edge finished, verify again')
            ppa_tmp = copy.deepcopy(ppa_tmp)
            path_tmp = copy.deepcopy(path_tmp)
            is_valid = Verification.verify_path(ppa_tmp, path_tmp, preCE=[], mode='vcgen')
        # If paths is still invalid, repair inside block (cond/data)
        # print('finished verify ', time.time() - start )
        if not is_valid:
            Preprocessing.insert_dummy_line_path(ppa, path)
            ppa, path, exception_path = repair_path(ppa, path, time_bound=times)
            is_valid = Verification.verify_path(ppa, path, preCE=[], mode='vcgen')
            if exception_path is not None:
                exception.append(exception_path)

        if debug:
            res_str = '{} : success = {} ; errors = {} ; repairs = {}'.format(path, is_valid, path.errors, path.repairs_tmp)
            print(res_str)


    num_valid, num_total = Verification.verify_ppa(ppa, debug=debug)

    if len(exception) == 0:
        exception = None
    else:
        exception = str(exception)
    return ppa, num_valid, num_total, exception

# endregion

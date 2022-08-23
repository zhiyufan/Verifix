import sys, time
import argparse
from srcU.Helpers import FetchData
from srcU.Verifix import Result
from scripts import claraRepair, verifixRepair


def main(args):
    mode = args.m
    if mode == 'repair':
        repair(args)
    elif mode == 'reproduce':
        reproduce(args)
    else:
        print('No valid mode to run')

def repair(args):
    path_to_ref = args.pc
    path_to_inc = args.pi
    path_to_tests = args.tc
    codeText_c = open(path_to_ref).read()
    codeText_i = open(path_to_inc).read()
    test_cases = FetchData.read_testCases(path_to_tests)
    res = Result.Result(progName='example')
    verifixRepair.repair(res, codeText_c, codeText_i, test_cases, progName='example', debug=True)

def reproduce(args):
    debug = args.debug
    jobs = args.parallel
    lab_ids = ['Lab-3', 'Lab-4', 'Lab-5', 'Lab-6']
    pids = [
        # 2810, 2811, 2812, 2813,
        # 2824, 2825, 2827, 2828, 2830, 2831, 2832, 2833,
        2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871,
        # 2932, 2933, 2934, 2935, 2936, 2937, 2938, 2939
    ]
    code_id = None
    # code_id = ['270138']
    df_codes = FetchData.read_itsp_data(lab_ids=lab_ids, problem_ids=pids, code_id=code_id)

    if args.tool == 'verifix':
        verifixRepair.reproduce_verifix(df_codes, jobs=jobs, debug=debug)
    elif args.tool == 'clara':
        claraRepair.reproduce_clara(df_codes, jobs=jobs, debug=debug)
    else:
        print('Please select a tool to reproduce, clara/verifix')

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='Verifix args description')
        parser.add_argument('-m', type=str, help='Mode to run, either repair or reproduce')
        parser.add_argument('-pc', type=str, help='path to reference solution')
        parser.add_argument('-pi', type=str, help='path to incorrect solution')
        parser.add_argument('-tc', type=str, help='path to test cases')
        parser.add_argument('-tool', type=str, help='which tool to reproduce clara/verifix')
        parser.add_argument('-debug', type=str2bool, default=False, help='enable debug mode? true/false, default is false')
        parser.add_argument('-parallel', type=int, default=1, help='number of programs to repair at one time, default is 1')
        args = parser.parse_args()
        startTime = time.time()
        main(args)
        print('\nTime-Taken = {} s'.format(round(time.time() - startTime, 2)))
        sys.exit(0)
    except Exception as err:
        print('Error occured: %s' % (err,), file=sys.stderr)
        sys.exit(1)
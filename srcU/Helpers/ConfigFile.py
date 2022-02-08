import os

# --------- Init ------------#

full_path = os.path.realpath(__file__)
currPath, configFilename = os.path.split(full_path)

path_base = currPath + '/../../'

# --------- Dataset ------------#

path_data = path_base + 'data/'
path_itsp = path_data + 'itsp/'
path_itsp_tests = path_itsp + 'test/'

path_itsp_result = path_base + 'result/'
path_clara_cluster= '/home/zhiyu/software/ITSP/dataset/cluster_prog_'
path_clara_cluster_output= '/home/zhiyu/software/ITSP/dataset/cluster_output_'

# --------- Timeouts seconds ------------#
timeout_compile = 5
timeout_execute = 10 

timeout_verifix = 300
timeout_clara = 300

# --------- Parallel Run ------------#
path_tmp = '/tmp/'

if not os.path.exists(path_tmp): os.makedirs(path_tmp)

# --------- Clang Path ------------#
Clang_Include = '/usr/bin/../lib/clang/6.0/include/'
ClangArgs = ['-static', '-lm', '-Wall', '-funsigned-char', '-Wno-unused-result', '-O', '-Wextra', '-std=c99', "-I"+Clang_Include]


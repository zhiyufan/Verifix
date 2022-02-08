from srcU.Helpers import ConfigFile as CF, Helper as H

def get_fnameC(fname='temp'):
    fname_c = '{}{}.c'.format(CF.path_tmp, fname)
    fname_out = '{}{}.out'.format(CF.path_tmp, fname)
    return fname_c, fname_out

#region: Compile prog

def compile_prog(codeText, fname='temp', debug=False, timeout=CF.timeout_compile, raiseExp=True):
    # Write file
    fname_c, fname_out = get_fnameC(fname)
    open(fname_c, 'w').write(codeText)

    # Run Clang
    cmd_list = ['clang', fname_c] + CF.ClangArgs + ['-o', fname_out]
    success, outs = H.subprocess_run(cmd_list, 
        blame_str='Compilation', timeout=timeout, debug=debug, raiseExp=raiseExp)

    # Delete file
    H.del_file(fname_c)
    
    return success

#endregion

#region: Execute prog

def execute_prog(codeText, test_cases, fname='temp', debug=False, timeout=CF.timeout_execute, raiseExp=True):
    flag_compile = compile_prog(codeText, fname=fname, debug=debug, raiseExp=raiseExp)
    flag_execute = True
    fname_c, fname_out = get_fnameC(fname)

    if flag_compile:
        for test_input, test_output in test_cases:

            success, outs = H.subprocess_run([fname_out], prog_input=test_input, 
                blame_str='Execute', timeout=timeout, debug=debug, raiseExp=raiseExp)            
            flag = success and str(test_output).strip() == outs.strip() # Run was successful and output matches gold standard            
            flag_execute = flag_execute and flag

            if debug: 
                print('test_input={}, match={}, test_output={}, act_output={}'.format(test_input, flag, test_output, outs))

            if not flag_execute:
                break

    # Delete file
    H.del_file(fname_c)
    H.del_file(fname_out)
            
    return flag_compile and flag_execute

#endregion

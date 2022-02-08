from srcU.Helpers import ConfigFile as CF, Helper as H

import pandas as pd
import matplotlib


# region: Plot helpers

def get_color():
    colors = matplotlib.cm.get_cmap('tab10').colors  # Blue, Orange, Green, Purple

    blueD, blueL = colors[0], colors[9]
    orange, green, red = colors[1], colors[2], colors[3]
    purple, brown, pink = colors[4], colors[5], colors[6]
    grey, yellow = colors[7], colors[8]

    return [red, blueD, orange, green]

def get_color_pair():
    colors = matplotlib.cm.get_cmap('tab20').colors # Blue, Orange, Green, Purple

    blueD, blueL        = colors[0], colors[1]
    redD, redL = colors[6], colors[7]

    return [blueD, redL]

def countVal(df, col, val, col2=None):
    df_filter = df[df[col] == val]

    if col2 is not None:
        df_filter = df_filter[df_filter[col2] == val]

    return len(df_filter)


def calc_perc(num, den, r=2):
    if den == 0: return None
    return round(100 * num / den, r)


def addStack(stack, key, val):
    if key not in stack:
        stack[key] = []
    stack[key].append(val)


# endregion

# region: Plot DF

def fetch_dfPlot_stats(df_group):
    # Fetch numbers
    codeSaves = len(df_group)
    compile_success = countVal(df_group, 'result_compile', True)
    compile_failure = codeSaves - compile_success
    evaluation_success = countVal(df_group, 'result_execute', True)
    evaluation_failure = compile_success - evaluation_success

    codes = df_group[(df_group['result_compile'] == True) & (df_group['result_execute'] == False)]['code_buggy']
    avg_loc = H.avg([H.loc(c) for c in codes], rounding=0)

    return codeSaves, compile_success, compile_failure, evaluation_success, evaluation_failure, avg_loc


# def fetch_dfPlot_rows(df_group, percent, rows, codeSaves, compile_success, compile_failure, evaluation_success, evaluation_failure):
#     # Store abs numbers
#     rows.append([percent, 'codeSaves', codeSaves, calc_perc(codeSaves, codeSaves, r=0)])
#     rows.append([percent, 'compile_success', compile_success, calc_perc(compile_success, codeSaves, r=0)])
#     rows.append([percent, 'evaluation_failure', evaluation_failure, calc_perc(evaluation_failure, compile_success, r=0)])
#     rows.append([percent, 'verifix_test', verifix_test, calc_perc(verifix_test, evaluation_failure, r=0)])
#     rows.append([percent, 'verifix_complete', verifix_comp, calc_perc(verifix_comp, evaluation_failure, r=0)])
#     rows.append([percent, 'verifix_partial', verifix_part, calc_perc(verifix_part, evaluation_failure, r=0)])
#     rows.append([percent, 'verifix_success', verifix_success, calc_perc(verifix_success, evaluation_failure, r=0)])
#     rows.append([percent, 'clara_success', clara_success, calc_perc(clara_success, evaluation_failure, r=0)])

def fetch_dfPlot_verifix(df_group, end, stacksV, evaluation_failure, avg_loc):
    # Calc numbers
    struct_mismatch = countVal(df_group, 'verifix_exception', 'structural mismatch')
    struct_match = evaluation_failure - struct_mismatch
    verifix_test = countVal(df_group, 'verifix_test', True)
    verifix_comp = countVal(df_group, 'verifix_complete', True)
    verifix_success = countVal(df_group, 'verifix_complete', True, col2='verifix_test')
    verifix_part = countVal(df_group, 'verifix_partial', True)
    df_success = df_group[(df_group['verifix_complete'] == True) & ((df_group['verifix_test'] == True))]
    avg_time = H.avg(df_success['verifix_time_taken'], rounding=0)
    avg_patch_size = H.avg(df_success['relative_patch_size'])
    verifix_failure = evaluation_failure - verifix_part

    # Add to Stack
    addStack(stacksV, 'tool', 'Verifix')
    addStack(stacksV, 'count', evaluation_failure)
    addStack(stacksV, 'avg_loc', avg_loc)
    addStack(stacksV, 'percent', end)
    # addStack(stacksC, 'evaluation_success', calc_perc(evaluation_success, compile_success, r=0))
    addStack(stacksV, 'Verifix CFA match', calc_perc(struct_match, evaluation_failure, r=0))
    addStack(stacksV, 'verifix_time_taken', avg_time)
    # addStack(stacksV, 'repair_failure', calc_perc(verifix_failure, evaluation_failure, r=0))
    addStack(stacksV, 'Verifix success', calc_perc(verifix_success, evaluation_failure, r=0))
    addStack(stacksV, 'Verifix success count', verifix_success)
    addStack(stacksV, 'Verifix failure', verifix_failure)


    verifix_failure -= struct_mismatch

    addStack(stacksV, 'Verifix failure w/o sm', verifix_failure)

    addStack(stacksV, 'Verifix avg patch size', avg_patch_size)

def fetch_dfPlot_clara(df_group, end, stacksC, evaluation_failure):
    struct_mismatch = countVal(df_group, 'clara_exception', 'clara.repair.StructMismatch')
    struct_match = evaluation_failure - struct_mismatch
    clara_success = countVal(df_group, 'clara_result', 1)
    # clara_failure = evaluation_failure - clara_success
    df_success = df_group[df_group['clara_result'] == 1]
    avg_time = H.avg(df_success['clara_time_taken'], rounding=0)

    # Stack 1
    addStack(stacksC, 'tool', 'Clara')
    addStack(stacksC, 'count', evaluation_failure)
    addStack(stacksC, 'percent', end)
    # addStack(stacksC, 'evaluation_success', calc_perc(evaluation_success, compile_success, r=0))
    addStack(stacksC, 'Clara CFG match', calc_perc(struct_match, evaluation_failure, r=0))
    addStack(stacksC, 'clara_time_taken', avg_time)
    # addStack(stacks, 'repair_failure', calc_perc(clara_failure, evaluation_failure, r=0))
    addStack(stacksC, 'Clara success', calc_perc(clara_success, evaluation_failure, r=0))


def fetch_dfPlot_range(df_codes, begin, end, rows, stacksC, stacksV):
    df_group = df_codes[(df_codes['time_percent'] > begin) &
                        (df_codes['time_percent'] <= end)]

    codeSaves, compile_success, compile_failure, evaluation_success, evaluation_failure, avg_loc = fetch_dfPlot_stats(
        df_group)
    # fetch_dfPlot_rows(df_group, end, rows, codeSaves, compile_success, compile_failure, evaluation_success, evaluation_failure)
    fetch_dfPlot_verifix(df_group, end, stacksV, evaluation_failure, avg_loc)
    # fetch_dfPlot_clara(df_group, end, stacksC, evaluation_failure)


def fetch_dfPlot(df_codes, window=1):
    rows, stacksC, stacksV = [], {}, {}

    prevPercent = -1
    for percent in range(window, 101):
        begin = percent - window
        end = percent

        fetch_dfPlot_range(df_codes, begin, end, rows, stacksC, stacksV)
        prevPercent = percent

    # df_plot = pd.DataFrame(rows, columns=['time_percentile', 'column', 'count', 'percentage'])
    df_stacksC, df_stacksV = pd.DataFrame(stacksC), pd.DataFrame(stacksV)

    return df_stacksC, df_stacksV

# endregion
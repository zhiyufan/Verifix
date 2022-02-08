from srcU.Helpers import Helper as H, ConfigFile as CF

import pandas as pd

#region: summary

def summary_all(df, pids=None):
    total = 0
    if pids is not None:
        df = df[df['problem_id'].isin(pids)]

    for i, row in df.iterrows():
        total += 1
        lab_name = row['labName']

    if pids is None or len(pids) > 1:
        return ['All', '-', total]
    return [lab_name, pids[0], total]

def summary_verifix(df, pids):
    total = 0
    countR = 0
    time = 0
    rps = 0
    if pids is not None:
        df = df[df['problem_id'].isin(pids)]
    
    for i, row in df.iterrows():
        total += 1
        if row['isRepair_partial'] == 1 and row['isRepair_complete'] == 1 or \
                row['isRepair_partial'] == 1 and row['isRepair_evaluate'] == 1:# and row['isRepair_evaluate'] == 1:
            countR += 1
            rps += row['relative_patch_size']
            time += row['timeTaken']

    percR = H.perc(countR, total, rounding=1)
    timeAve = H.div(time, countR, rounding=1)

    rps = H.div(rps, countR)

    return [countR, percR, timeAve, rps]

def summary_clara(df, pids):
    total = 0
    countT, rps = 0, 0
    timeS, timeF = 0, 0
    if pids is not None:
        df = df[df['problem_id'].isin(pids)]
    
    for i, row in df.iterrows():
        total += 1
        if row['clara_result'] == 1:
            countT += 1
            timeS += row['clara_time_taken']
        # if row['clara_result'] == 1: timeS += row['timeTaken']
        # else: timeF += row['timeTaken']
        # if row['clara_result'] == 1: rps += row['clara_patch_size']
    
    percT = H.perc(countT, total, rounding=1)
    timeS = H.div(timeS, countT, rounding=1)
    timeF = H.div(timeF, total - countT, rounding=1)
    rps = H.div(rps, countT)

    # return [countT, percT, timeS, timeF, rps]
    return [countT, percT, timeS, rps]#, timeS, timeF, rps]

#endregion

#region: Accuracy

def get_result_pid(df_verifix, df_clara, pids=None):
    result = summary_all(df_clara, pids)
    result += summary_clara(df_clara, pids)
    result += summary_verifix(df_verifix, pids)    

    return result

def get_result(df_verifix, df_clara, pids=None):
    results = []
    if pids is None:
        pids = df_clara['problem_id'].unique()
    # lab3 = [2810, 2811, 2812, 2813]
    # lab4 = [2824, 2825, 2827, 2828, 2830, 2831, 2832, 2833]
    # lab5 = [2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871]
    # lab6 = [2932, 2933, 2934, 2935, 2936, 2937, 2938, 2939]
    #
    # for pid in [lab3, lab4, lab5, lab6]:
    #     result = get_result_pid(df_verifix, df_clara, pids=pid)
    #     results.append(result)

    for pid in pids:
        result = get_result_pid(df_verifix, df_clara, pids=[pid])
        results.append(result)

    result = get_result_pid(df_verifix, df_clara, pids=pids)
    results.append(result)

    df_result = pd.DataFrame(results,
                             columns=['Lab', 'pid', '#Assign'] +
                                     ['#C-T', '%C-T', 'C-time', 'C-rps'] +
                                     ['#V_T', '%V-T', 'V-time', 'V-rps']
                             )
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 2000)
    return df_result
#endregion

#region: Patch-size

def get_patchSize_v(df, pids=None):
    if pids is not None:
        df = df[df['problem_id'].isin(pids)]

    df = df[df['isRepair_evaluate'] == 1]
    return df

def get_patchSize_c(df, pids=None):
    if pids is not None:
        df = df[df['problem_id'].isin(pids)]

    df = df[df['clara_result'] == 1]
    return df

def update_hist(hist, key):
    key = key
    if key not in hist:
        hist[key] = 0
    hist[key] += 1

def calc_hist(df):
    hist = {}

    step = 10
    for start in range(0, 100, step):
        start = start/100
        stop = start+step/100

        for rps in df['relative_patch_size']:
            if rps > start and rps <= stop:
                update_hist(hist, stop)

    return pd.DataFrame(hist.items(), columns=['rps', 'freq'])

def get_patchSize(df1, df2):
    '''Return list of patch-size in intersection'''
    cids1 = list(df1['code_id'].values)
    cids2 = list(df2['code_id'].values)

    df1 = df1[df1['code_id'].isin(cids2)]
    df2 = df2[df2['code_id'].isin(cids1)]

    hist1 = calc_hist(df1)
    hist2 = calc_hist(df2)

    return hist1, hist2

#endregion

#region: all dfs

def get_dfs(lab_ids, pids):
    path = CF.path_itsp_result
    df_gold, df_verifix, df_clara = None, None, None
    import os
    for lab_id in lab_ids:
        for assign_id in pids:
            if os.path.exists('{}results_verifix_{}_{}_fse17.xlsx'.format(path, lab_id, assign_id)):
                df_verifix_temp = pd.read_excel('{}results_verifix_{}_{}_fse17.xlsx'.format(path, lab_id, assign_id))
            else:
                df_verifix_temp = None

            if os.path.exists('{}results_clara_{}_{}.xlsx'.format(path, lab_id, assign_id)):
                df_clara_temp = pd.read_excel('{}results_clara_{}_{}.xlsx'.format(path, lab_id, assign_id))
            else:
                df_clara_temp = None

            if df_verifix is None:
                df_verifix, df_clara = df_verifix_temp, df_clara_temp
            else:
                df_verifix = df_verifix.append(df_verifix_temp)
                df_clara = df_clara.append(df_clara_temp)
    return df_gold, df_verifix, df_clara

#endregion

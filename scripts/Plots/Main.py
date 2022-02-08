from srcU.Plots import Plot_fse17

def plot():
    rpids = [2810, 2811, 2812, 2813,
             2824, 2825, 2827, 2828, 2830, 2831, 2832, 2833,
             2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871,
             2932, 2933, 2934, 2935, 2936, 2937, 2938, 2939
             ]

    lab_ids = ['Lab-3', 'Lab-4','Lab-5','Lab-6']  # Run specific labs?
    # lab_ids = ['Lab-4']  # Run specific labs?
    df_gold, df_verifix, df_clara = Plot_fse17.get_dfs(lab_ids, rpids)
    df_result = Plot_fse17.get_result(df_verifix, df_clara, pids=None)
    print(df_result)


if __name__ == '__main__':
    plot()
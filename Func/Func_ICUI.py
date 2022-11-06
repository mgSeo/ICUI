from Func import Func_Stage_A as stage_A
from Func import Func_Stage_B as stage_B

import pandas as pd
import numpy as np
# import math
# import warnings
# warnings.filterwarnings('ignore')
# from gettext import find
# import imp
# from operator import index
# from re import L
# from unittest import result
# from pulp import *
# from pyparsing import col

def func(ev,w_obj):
    fces_ts, fces_cluster = FCES(ev)

    P_A,SoC_A = stage_A.func(fces_ts,fces_cluster,w_obj)
    P_B,SoC_B = stage_B.func(P_A,fces_cluster,ev)

    # Check, Stage_B feasiblity.
    ## ok: done, no: go to while loop

    # while, tol < some level.
    Updater()
    stage_A.updated()
    stage_B.relaxed()
    ## check tol


    return 0

def FCES(ev):
    arr_set = sorted(ev['serviceFrom'].unique().tolist())
    # def DataFrame
    time_series_list = ['demand', 'pcs', 'minimumSOC','capacity']
    header = []
    dur = 0
    for arr in range(len(arr_set)):
        for l in time_series_list:
            header.append('arr_{}_'.format(arr) + l)
        idx = ev[ev['serviceFrom']==arr_set[0]].index
        if ev['serviceTo'][idx].max()-arr_set[0] + 1 > dur:
            dur = ev['serviceTo'][idx].max()-arr_set[0] + 1
    fces_ts = pd.DataFrame(np.zeros([dur,len(header)]),columns=header)

    cluster_header = ['From', 'To','initialSOC','eff','duration','n_ev','capacity']
    fces_cluster = pd.DataFrame(np.zeros([len(arr_set), len(cluster_header)]),columns=cluster_header)
    # def Value of Dataframe, cluster
    for arr in range(len(arr_set)):
        idx = ev[ev['serviceFrom']==arr_set[arr]].index
        fces_cluster.loc[arr,'From'] = arr_set[arr]
        fces_cluster.loc[arr,'To'] = ev['serviceTo'][idx].max()
        fces_cluster.loc[arr,'initialSOC'] = sum(ev['initialSOC'][idx] * ev['capacity'][idx] / 100)
        fces_cluster.loc[arr,'eff'] = ev['eff'][idx].mean()        
        fces_cluster.loc[arr,'duration'] = fces_cluster['To'][arr] - fces_cluster['From'][arr] + 1
        fces_cluster.loc[arr,'n_ev'] = len(idx)
        fces_cluster.loc[arr,'capacity'] = ev['capacity'][idx].sum()
        fces_cluster.loc[arr,'maximumSOC'] = sum(ev['maximumSOC'][idx]/100*ev['capacity'][idx])

    # def Value of Dataframe, time-series(ts)
    for arr in range(len(arr_set)):
        idx = ev[ev['serviceFrom']==arr_set[arr]].index
        temp = pd.DataFrame(np.zeros([int(fces_cluster['duration'][arr]),len(time_series_list)]),columns=time_series_list)
        for v in range(int(fces_cluster['n_ev'][arr])):
            vdx = idx[v]
            lists = ['capacity','pcs']
            for l in lists:
                temp.loc[:ev['duration'][vdx]-1,l] += ev[l][vdx]
            temp.loc[ev['duration'][vdx]-1:,'minimumSOC'] += ev['minimumSOC'][vdx]/100 * ev['capacity'][vdx]
            temp.loc[ev['duration'][vdx]-1:,'demand'] += ev['goalSOC'][vdx]/100 * ev['capacity'][vdx]
        temp_header = []
        for l in time_series_list:
            temp_header.append('arr_{}_'.format(arr)+l)
        fces_ts.loc[:int(fces_cluster['duration'][arr]-1),temp_header] = temp.to_numpy()
    
    return fces_ts, fces_cluster

def Updater():
    return 0
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
    tol = 2
    while 1:
        # Check feasiblity
        if len(SoC_B[SoC_B > 92+tol]) == 0 and len(SoC_B[SoC_B< 8-tol]) == 0: break # Stage-A is feasible

        # Not Feasible.
        fault = Updater(SoC_B,fces_cluster,ev)
        stage_A.updated()
        P_B,SoC_B = stage_B.func(P_A,fces_cluster,ev)
    ## check tol


    return 0
def Updater(SoC_B,fces_cluster,ev):
    header = ['F_id','idx','amount']
    fault =  pd.DataFrame(np.zeros([1,len(header)]),columns=header)
    f = 0
    for fdx in range(len(fces_cluster)):
        ev_set = ev[ev['serviceFrom']==fces_cluster['From'][fdx]]
        ev_set = ev_set.reset_index()
        for vdx in range(len(ev_set)):
            # SoC_B['ev_{}'.format(ev_set['id'][vdx])]
            # I1 = SoC_B[ SoC_B['ev_{}'.format(ev_set['id'][vdx])][ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]] > ev_set['maximumSOC'][vdx]].index
            # I1 = SoC_B[ SoC_B.loc[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx],'ev_{}'.format(ev_set['id'][vdx])] > ev_set['maximumSOC'][vdx]].index
            # I2 = SoC_B[ SoC_B.loc[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx],'ev_{}'.format(ev_set['id'][vdx])] < ev_set['minimumSOC'][vdx]].index
            I1 = SoC_B[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]][ SoC_B['ev_{}'.format(ev_set['id'][vdx])][ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]] > ev_set['maximumSOC'][vdx]].index
            I2 = SoC_B[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]][ SoC_B['ev_{}'.format(ev_set['id'][vdx])][ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]] < ev_set['minimumSOC'][vdx]].index
            # I2 = SoC_B[ SoC_B.loc[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx],'ev_{}'.format(ev_set['id'][vdx])] < ev_set['minimumSOC'][vdx]].index
            
            if len(I1) == 0 and len(I2) == 0: continue
            else:
                fault.loc[f,'F_id'] = fdx

                if len(I1) != 0 and len(I2) == 0:
                    fault.loc[f,'idx'] = I1[0]
                    amount = SoC_B['ev_{}'.format(ev_set['id'][vdx])][I1[0]] - ev_set['maximumSOC'][vdx] # unit: [%]
                elif len(I1) == 0 and len(I2) != 0:
                    fault.loc[f,'idx'] = I2[0]
                    amount = -ev_set['minimumSOC'][vdx] - SoC_B['ev_{}'.format(ev_set['id'][vdx])][I2[0]] # unit: [%]
                elif len(I1) != 0 and len(I2) != 0:
                    if I1[0] < I2[0]:
                        fault.loc[f,'idx'] = I1[0]
                        amount = SoC_B['ev_{}'.format(ev_set['id'][vdx])][I1[0]] - ev_set['maximumSOC'][vdx] # unit: [%]
                    else:
                        fault.loc[f,'idx'] = I2[0]
                        amount = -ev_set['minimumSOC'][vdx] - SoC_B['ev_{}'.format(ev_set['id'][vdx])][I2[0]] # unit: [%]

                fault.loc[f,'amount'] = amount/100*ev_set['capacity'][vdx]
                f += 1
    fault_sorted =  pd.DataFrame(np.zeros([1,len(header)]),columns=header)
    f = 0
    for id in range(24):
        id_idx = fault[fault['F_id']==id].index
        idx_set = sorted(fault['idx'][id_idx].unique())
        for ii in idx_set:
            fault_sorted.loc[f,'F_id'] = id
            fault_sorted.loc[f,'idx'] = ii
            fault_sorted.loc[f,'amount'] = fault[(fault['F_id']==id) & (fault['idx']==ii)]['amount'].sum()
            f += 1        

    return fault_sorted

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
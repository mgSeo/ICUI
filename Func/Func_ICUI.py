from Func import Func_Stage_A as stage_A
from Func import Func_Stage_B as stage_B

import pandas as pd
import numpy as np

def func(ev,w_obj,tol):
    fces_ts, fces_cluster = FCES(ev,tol)

    P_A,SoC_A = stage_A.func(fces_ts,fces_cluster,w_obj)
    header = ['F_id','V_id','idx','amount']
    Fault =  pd.DataFrame(columns=header)
    iter = 0
    while 1:
        P_B,SoC_B,fault = stage_B.func(P_A,fces_cluster,ev,tol)
        fault.to_csv('Fault_{}.csv'.format(iter))
        ## Check feasiblity
        if len(fault) == 0: # means solution is feasible
            ss = 1
            break
        ## solution is Infeasible
        # Update Stage-A
        Fault = pd.concat([Fault,fault])
        Fault = Fault.reset_index()
        Fault = Fault.drop(['index'], axis=1)
        Fault = fault_arranger(Fault)
        P_A,SoC_A = stage_A.updated(fces_ts,fces_cluster,w_obj,Fault,P_A)
        
        print('Iteration: {}, '.format(iter) + 'Total Number of Fault: {}, '.format(len(Fault)) + 'Increased: {}'.format(len(fault)))
        iter += 1
        
    return P_A, SoC_A, P_B, SoC_B
def Updater(SoC_B,fces_cluster,ev):
    header = ['F_id','idx','amount']
    fault =  pd.DataFrame(np.zeros([1,len(header)]),columns=header)
    f = 0
    tol = 1
    for fdx in range(len(fces_cluster)):
        ev_set = ev[ev['serviceFrom']==fces_cluster['From'][fdx]]
        ev_set = ev_set.reset_index()

        for vdx in range(len(ev_set)):
            I1 = SoC_B[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]][ SoC_B['ev_{}'.format(ev_set['id'][vdx])][ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]] > ev_set['maximumSOC'][vdx] + tol].index
            I2 = SoC_B[ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]][ SoC_B['ev_{}'.format(ev_set['id'][vdx])][ev_set['serviceFrom'][vdx]:ev_set['serviceTo'][vdx]] < ev_set['minimumSOC'][vdx] - tol].index
            
            if len(I1) == 0 and len(I2) == 0: continue
            else:
                fault.loc[f,'F_id'] = fdx

                if len(I1) != 0 and len(I2) == 0:
                    fault.loc[f,'idx'] = I1[0] - ev_set['serviceFrom'][vdx]
                    amount = SoC_B['ev_{}'.format(ev_set['id'][vdx])][I1[0]] - ev_set['maximumSOC'][vdx] # unit: [%]
                elif len(I1) == 0 and len(I2) != 0:
                    fault.loc[f,'idx'] = I2[0] - ev_set['serviceFrom'][vdx]
                    amount = -(ev_set['minimumSOC'][vdx] - SoC_B['ev_{}'.format(ev_set['id'][vdx])][I2[0]]) # unit: [%]
                elif len(I1) != 0 and len(I2) != 0:
                    if I1[0] < I2[0]:
                        fault.loc[f,'idx'] = I1[0] - ev_set['serviceFrom'][vdx]
                        amount = SoC_B['ev_{}'.format(ev_set['id'][vdx])][I1[0]] - ev_set['maximumSOC'][vdx] # unit: [%]
                    else:
                        fault.loc[f,'idx'] = I2[0] - ev_set['serviceFrom'][vdx]
                        amount = -(ev_set['minimumSOC'][vdx] - SoC_B['ev_{}'.format(ev_set['id'][vdx])][I2[0]]) # unit: [%]

                fault.loc[f,'amount'] = amount/100*ev_set['capacity'][vdx]
                f += 1
    
    return fault

def fault_arranger(fault):
    header = ['F_id','V_id','idx','amount']
    fault_sorted =  pd.DataFrame(np.zeros([1,len(header)]),columns=header)
    f = 0
    F_id_set = sorted(fault['F_id'].unique())
    for fdx in F_id_set:
        fault_set = fault[fault['F_id']==fdx]
        # fault_set = fault_set.reset_index()
        idx_set = sorted(fault_set['idx'].unique())
        for ii in idx_set:
            fault_sorted.loc[f,'F_id'] = fdx
            fault_sorted.loc[f,'V_id'] = 0
            fault_sorted.loc[f,'idx'] = ii
            amount_idx = fault_set[fault_set['idx'] == ii].index
            fault_sorted.loc[f,'amount'] = fault_set['amount'][amount_idx].sum()
            f += 1

    fault_sorted[['F_id','idx']] = fault_sorted[['F_id','idx']].astype('int')

    return fault_sorted

def FCES(ev,tol):
    arr_set = sorted(ev['serviceFrom'].unique().tolist())
    ## Cluster
    cluster_header = ['From', 'To','initialSOC','eff','duration','n_ev','capacity']
    fces_cluster = pd.DataFrame(np.zeros([len(arr_set), len(cluster_header)]),columns=cluster_header)
    # def Value of Dataframe, cluster
    for arr in range(len(arr_set)):
        idx = ev[ev['serviceFrom']==arr_set[arr]].index
        fces_cluster.loc[arr,'From'] = arr_set[arr]
        fces_cluster.loc[arr,'To'] = ev['serviceTo'][idx].max()
        fces_cluster.loc[arr,'initialSOC'] = sum(ev['initialSOC'][idx] / 100 * ev['capacity'][idx])
        fces_cluster.loc[arr,'eff'] = ev['eff'][idx].mean()
        fces_cluster.loc[arr,'duration'] = fces_cluster['To'][arr] - fces_cluster['From'][arr] + 1
        fces_cluster.loc[arr,'n_ev'] = len(idx)
        fces_cluster.loc[arr,'capacity'] = ev['capacity'][idx].sum()
        fces_cluster.loc[arr,'maximumSOC'] = sum((ev['maximumSOC'][idx]-tol)/100*ev['capacity'][idx])
    header = ['From', 'To','duration','n_ev']
    fces_cluster[header] = fces_cluster[header].astype('int')

    ## Time-series Cluster
    time_series_list = ['pcs', 'minimumSOC','capacity']
    header = []
    for arr in range(len(arr_set)):
        for l in time_series_list:
            header.append('arr_{}_'.format(arr) + l)
    #     idx = ev[ev['serviceFrom']==arr_set[0]].index
        # if ev['serviceTo'][idx].max()-arr_set[0] + 1 > dur:
        #     dur = ev['serviceTo'][idx].max()-arr_set[0] + 1
    fces_ts = pd.DataFrame(np.zeros([ev['duration'].max(),len(header)]),columns=header)

    for arr in range(len(arr_set)):
        idx = ev[ev['serviceFrom']==arr_set[arr]].index
        # temp = pd.DataFrame(np.zeros([int(fces_cluster['duration'][arr]),len(time_series_list)]),columns=time_series_list)
        for v in range(fces_cluster['n_ev'][arr]):
            vdx = idx[v]
            lists = ['capacity','pcs']
            for l in lists:
                fces_ts.loc[:ev['duration'][vdx]-1,'arr_{}_'.format(arr)+l] += ev[l][vdx]
            fces_ts.loc[:ev['duration'][vdx]-2,'arr_{}_'.format(arr)+'minimumSOC'] += (ev['minimumSOC'][vdx]+tol)/100 * ev['capacity'][vdx]
            fces_ts.loc[ev['duration'][vdx]-1:fces_cluster['duration'][arr]-1,'arr_{}_'.format(arr)+'minimumSOC'] += (ev['goalSOC'][vdx]+tol)/100 * ev['capacity'][vdx]

            # fces_ts.loc[ev['duration'][vdx]-1:fces_cluster['duration'][arr]-1,'arr_{}_'.format(arr)+'demand'] += ev['goalSOC'][vdx]/100 * ev['capacity'][vdx]
    return fces_ts, fces_cluster
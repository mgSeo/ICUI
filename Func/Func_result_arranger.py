import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB

def A(p,fces_ts,fces_cluster):
    arr_set = fces_cluster.From.unique()
    
    header = []
    for vdx in range(len(arr_set)):
        header.append('arr_{}'.format(vdx))
    
    Fleet_P = pd.DataFrame(np.zeros([96,len(header)]),columns=header)
    SoC = pd.DataFrame(np.zeros([96,len(header)]),columns=header)    

    for vdx in range(len(arr_set)):
        soe = fces_cluster['initialSOC'][vdx] 
        for idx in range(int(fces_cluster['duration'][vdx])):
            soe += p[vdx][idx].x

            t = idx + fces_cluster.From[vdx]
            Fleet_P['arr_{}'.format(vdx)][t] = p[vdx][idx].x
            SoC['arr_{}'.format(vdx)][t] = soe / fces_ts['arr_{}_capacity'.format(vdx)][idx] * 100

    return Fleet_P

def B(p,ev):
    header = []
    for vdx in range(len(ev)):
        header.append('ev_{}'.format(ev.id[vdx]))
    
    EV_P = pd.DataFrame(np.zeros([96,len(header)]),columns=header)
    SoC = pd.DataFrame(np.zeros([96,len(header)]),columns=header)    

    for vdx in range(len(ev)):
        soe = ev['initialSOC'][vdx]*ev['capacity'][vdx]/100
        for idx in range(int(ev['duration'][vdx])):
            soe += p[vdx][idx].x

            t = idx + ev.serviceFrom[vdx]
            EV_P['ev_{}'.format(ev.id[vdx])][t] = p[vdx][idx].x
            SoC['ev_{}'.format(ev.id[vdx])][t] = soe / ev['capacity'][vdx] * 100

    return EV_P, SoC
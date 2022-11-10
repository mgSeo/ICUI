import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB

def A(p,fces_ts,fces_cluster):
    arr_set = fces_cluster.From.unique()
    
    header = []
    for fdx in range(len(arr_set)):
        header.append('arr_{}'.format(fdx))
    
    Fleet_P = pd.DataFrame(np.zeros([96,len(header)]),columns=header)
    SoC = pd.DataFrame(np.zeros([96,len(header)]),columns=header)    

    for fdx in range(len(arr_set)):
        soe = fces_cluster['initialSOC'][fdx]
        for idx in range(fces_cluster['duration'][fdx]):
            soe += p[fdx][idx].x

            t = idx + fces_cluster.From[fdx]
            Fleet_P['arr_{}'.format(fdx)][t] = p[fdx][idx].x
            SoC['arr_{}'.format(fdx)][t] = soe / fces_cluster['capacity'][fdx] * 100
            # SoC['arr_{}'.format(fdx)][t] = soe / fces_ts['arr_{}_capacity'.format(fdx)][idx] * 100

    return Fleet_P, SoC

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
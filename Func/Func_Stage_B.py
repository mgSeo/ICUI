import gurobipy as gp
from gurobipy import GRB
import pandas as pd
from Func import Func_result_arranger as arranger

def func(P_A,fces_cluster,ev):
    arr_set = fces_cluster.From.unique()
    
    P_B = pd.DataFrame()
    SoC = pd.DataFrame()
    for vdx in range(len(arr_set)):
        arr = arr_set[vdx]

        ev_set = ev[ev['serviceFrom']==arr]
        P_A_set = P_A['arr_{}'.format(vdx)]
        P_b,soc = dispatch(P_A_set,ev_set)
        P_B = pd.concat([P_B,P_b],axis=1)
        SoC = pd.concat([SoC,soc],axis=1)
    return P_B,SoC


def dispatch(P_A,ev):
    ev = ev.reset_index()
    ### Define varable:
    B = gp.Model('Stage-B')
    p = [B.addVars(range(int(ev.duration[vdx])), ub=ev['pcs'][vdx], lb=-ev['pcs'][vdx]) for vdx in range(len(ev))] # EV Power {vdx,t}
    goalSoC = B.addVars(range(len(ev)), lb=0)
    
    relax_param = 1 # non-relaxed
    relax_param = 0 # non-relaxed
    B = constraints(B,p,goalSoC,P_A,ev,relax_param)    
    B.ModelSense = GRB.MINIMIZE
    B = objective_function(B,goalSoC,ev)
    B.optimize()

    EV_P,SoC = arranger.B(p,ev)
    
    return EV_P, SoC

def dispatch_relaxed():
    return 0

def objective_function(B,goalSoC,ev):
    # goal SoC
    obj_goal_soc = 0
    for vdx in range(len(ev)):
        obj_goal_soc += goalSoC[vdx]
    B.setObjective(obj_goal_soc*99999)
    return B

def constraints(B,p,goalSoC,P_A,ev,relax_param):
    ### Constraints:
    # Power 같게 (FCES <=> EV)
    for t in range(max(ev['serviceTo'])):
        X = 0
        temp = 0
        for vdx in range(len(ev)):
            if ev['serviceFrom'][vdx] <= t < ev['serviceTo'][vdx]:
                idx = t - ev['serviceFrom'][vdx]
                X += p[vdx][idx]
                temp = 1
        if temp == 1: 
            B.addConstr(X == P_A[t])
            # B.addConstr(P_A[t] - X >= 0)
            # B.addConstr(P_A[t] - X <= 0)
    
    # Goal SoE
    for vdx in range(len(ev)):
        soe = ev['initialSOC'][vdx]*ev['capacity'][vdx]/100
        for idx in range(ev['duration'][vdx]):
            soe += p[vdx][idx]
        # Goal SoE
        B.addConstr(goalSoC[vdx] >= ev['goalSOC'][vdx]*ev['capacity'][vdx]/100 - soe)
        B.addConstr(goalSoC[vdx] >= soe - ev['goalSOC'][vdx]*ev['capacity'][vdx]/100)

    # SoE
    if relax_param == 1:
        for vdx in range(len(ev)):
            soe = ev['initialSOC'][vdx]*ev['capacity'][vdx]/100
            for idx in range(ev['dur'][vdx]):
                # SoE upper & lower bound
                soe += p[vdx][idx]
                B.addConstr(soe >= ev.minimumSOC[vdx])
                B.addConstr(soe <= ev.maximumSOC[vdx])                
    return B
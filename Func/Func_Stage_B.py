import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import numpy as np
from Func import Func_result_arranger as arranger
from Func import Func_fault_soc_arranger as fault_arranger
global tol

def func(P_A,fces_cluster,ev,tol):
    arr_set = fces_cluster.From.unique()
    
    P_B = pd.DataFrame()
    SoC = pd.DataFrame()
    header = ['F_id','V_id','idx','amount']
    Fault =  pd.DataFrame(np.zeros([1,len(header)]),columns=header)
    for fdx in range(len(arr_set)):
        arr = arr_set[fdx]

        ev_set = ev[ev['serviceFrom']==arr]
        P_A_set = P_A['arr_{}'.format(fdx)]
        SolCount,P_b,soc = dispatch(P_A_set,ev_set)
        if SolCount == 0:
            Fault.loc[fdx,'F_id'] = fdx
            P_b, soc, solcount, fault = dispatch_relaxed(P_A_set,ev_set,fdx,tol)
            if solcount == 0:
                for h in header[1:]:
                    Fault.loc[fdx,h] = fault[h]
                continue

        P_B = pd.concat([P_B,P_b],axis=1)
        SoC = pd.concat([SoC,soc],axis=1)
    return P_B,SoC,Fault


def dispatch(P_A,ev):
    ev = ev.reset_index()
    ### Define varable:
    B = gp.Model('Stage-B')
    B.Params.LogToConsole = 0
    p = [B.addVars(range(ev.duration[vdx]), ub=ev['pcs'][vdx], lb=-ev['pcs'][vdx]) for vdx in range(len(ev))] # EV Power {vdx,t}
    goalSoC = B.addVars(range(len(ev)), lb=0)
    
    relax_param = 1 # non-relaxed
    # relax_param = 0 # relaxed
    B = constraints(B,p,goalSoC,P_A,ev,relax_param)    
    B.ModelSense = GRB.MINIMIZE
    B = objective_function(B,goalSoC,ev)
    B.optimize()
    if B.SolCount == 0:
        return B.SolCount, 0, 0

    EV_P,SoC = arranger.B(p,ev)
    return B.SolCount, EV_P, SoC

def dispatch_relaxed(P_A,ev,fdx,tol):
    ev = ev.reset_index()
    ### Define varable:
    B_relaxed = gp.Model('Stage-B')
    B_relaxed.Params.LogToConsole = 0
    p = [B_relaxed.addVars(range(ev.duration[vdx]), ub=ev['pcs'][vdx], lb=-ev['pcs'][vdx]) for vdx in range(len(ev))] # EV Power {vdx,t}
    goalSoC = B_relaxed.addVars(range(len(ev)), lb=0)
    
    relax_param = 0 # relaxed
    B_relaxed = constraints(B_relaxed,p,goalSoC,P_A,ev,relax_param)    
    B_relaxed.ModelSense = GRB.MINIMIZE
    B_relaxed = objective_function(B_relaxed,goalSoC,ev)
    
    iter = 0
    while 1:
        B_relaxed.optimize()

        if B_relaxed.SolCount == 0:
            return 0, 0, B_relaxed.SolCount, updated_error
        
        P_b,SoC_b = fault_arranger.B(p,ev)
        # SoC_b.to_csv('soc_b_iter_{}.csv'.format(iter))

        if len(SoC_b[SoC_b > 92+tol]) == 0 and len(SoC_b[SoC_b< 8-tol]) == 0:
            return P_b, SoC_b, B_relaxed.SolCount, 0
        
        # In-feasible
        B_relaxed.reset() # Reset the model to an unsolved state, discarding any previously computed solution information.
        B_relaxed, updated_error = violation_updator(B_relaxed,p,ev,P_b,SoC_b,fdx,tol)
        
        iter += 1

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
    for t in range(max(ev['serviceTo'])+1):
        X = 0
        temp = 0
        for vdx in range(len(ev)):
            if ev['serviceFrom'][vdx] <= t <= ev['serviceTo'][vdx]:
                idx = t - ev['serviceFrom'][vdx]
                X += p[vdx][idx]
                temp = 1
        if temp == 1: 
            B.addConstr(X == P_A[t])
    
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
            soe = ev['initialSOC'][vdx]/100*ev['capacity'][vdx]
            for idx in range(ev['duration'][vdx]):
                # SoE upper & lower bound
                soe += p[vdx][idx]
                B.addConstr(soe >= ev.minimumSOC[vdx]/100*ev['capacity'][vdx])
                B.addConstr(soe <= ev.maximumSOC[vdx]/100*ev['capacity'][vdx])                
    return B

def violation_updator(B_relaxed,p,ev,P_b,SoC_b,fdx,tol):
    # find fault
    header = ['F_id','V_id','idx','amount']
    fault =  pd.DataFrame(np.zeros([1,len(header)]),columns=header)
    f = 0
    for vdx in range(len(ev)):
        I1 = SoC_b[ev['serviceFrom'][vdx]:ev['serviceTo'][vdx]][ SoC_b['ev_{}'.format(ev['id'][vdx])][ev['serviceFrom'][vdx]:ev['serviceTo'][vdx]] > ev['maximumSOC'][vdx] + tol].index
        I2 = SoC_b[ev['serviceFrom'][vdx]:ev['serviceTo'][vdx]][ SoC_b['ev_{}'.format(ev['id'][vdx])][ev['serviceFrom'][vdx]:ev['serviceTo'][vdx]] < ev['minimumSOC'][vdx] - tol].index
        
        if len(I1) == 0 and len(I2) == 0: continue
        else:
            fault.loc[f,'F_id'] = fdx
            fault.loc[f,'V_id'] = vdx
            if len(I1) != 0 and len(I2) == 0:
                fault.loc[f,'idx'] = I1[0] - ev['serviceFrom'][vdx]
                amount = SoC_b['ev_{}'.format(ev['id'][vdx])][I1[0]] - ev['maximumSOC'][vdx] # unit: [%]
            elif len(I1) == 0 and len(I2) != 0:
                fault.loc[f,'idx'] = I2[0] - ev['serviceFrom'][vdx]
                amount = -(ev['minimumSOC'][vdx] - SoC_b['ev_{}'.format(ev['id'][vdx])][I2[0]]) # unit: [%]
            elif len(I1) != 0 and len(I2) != 0:
                if I1[0] < I2[0]:
                    fault.loc[f,'idx'] = I1[0] - ev['serviceFrom'][vdx]
                    amount = SoC_b['ev_{}'.format(ev['id'][vdx])][I1[0]] - ev['maximumSOC'][vdx] # unit: [%]
                else:
                    fault.loc[f,'idx'] = I2[0] - ev['serviceFrom'][vdx]
                    amount = -(ev['minimumSOC'][vdx] - SoC_b['ev_{}'.format(ev['id'][vdx])][I2[0]]) # unit: [%]
            fault.loc[f,'amount'] = amount/100*ev['capacity'][vdx]
            f += 1

    # 1 set 만 제외하고 나머지는 날려야함.
    idx_set = fault[fault['idx'] == fault['idx'].min()]
    idx_set = idx_set.reset_index()
    idx_set = idx_set.loc[0]

    # update constraint
    vdx = int(idx_set['V_id'])
    cum_p = sum([p[vdx][idx] for idx in range(int(idx_set['idx']+1))])
    intime = ev['serviceFrom'][vdx]
    pre_p = P_b['ev_{}'.format(ev['id'][idx_set['V_id']])][intime:intime+int(idx_set['idx']+1)].sum()

    if idx_set['amount'] >= 0:
        B_relaxed.addConstr(cum_p <= pre_p - idx_set['amount'])
    else:
        B_relaxed.addConstr(cum_p >= pre_p - idx_set['amount'])

    # idx_set: previously updated error
    return B_relaxed, idx_set
import gurobipy as gp
from gurobipy import GRB
from Func import Func_result_arranger as arranger

def func(fces_ts,fces_cluster,w_obj):
    A = gp.Model('Stage-A')
    A.Params.LogToConsole = 0
    # ev Power {vdx,m,t}
    p = [A.addVars(range(fces_cluster.duration[vdx])) for vdx in range(len(fces_cluster))]
    # ev goal soc
    # goalsoc_ev = model.addVars(range(len(ev)), lb=0)
    
    for vdx in range(len(fces_cluster)):
        for idx in range(fces_cluster['duration'][vdx]):
            p[vdx][idx].ub = fces_ts['arr_{}_pcs'.format(vdx)][idx]
            p[vdx][idx].lb = -fces_ts['arr_{}_pcs'.format(vdx)][idx]

    A = constraints(A,p,fces_ts,fces_cluster)
    
    A.ModelSense = GRB.MINIMIZE
    A = objective_function(A,w_obj,p,fces_ts,fces_cluster)   
    A.optimize()

    P_A, SoC_A = arranger.A(p,fces_ts,fces_cluster)
    return P_A, SoC_A
    
def objective_function(A,w_obj,p,fces_ts,fces_cluster):
    obj_smp = 0
    for t in range(96):
        X = 0
        for vdx in range(len(fces_cluster)):
            if fces_cluster['From'][vdx] <= t <= fces_cluster['To'][vdx]:
                idx = t - fces_cluster['From'][vdx]
                X += p[vdx][idx]
        obj_smp += X * w_obj[0][t]
    A.setObjective(obj_smp)
    return A

def constraints(A,p,fces_ts,fces_cluster):
    # SoC boundaries
    for vdx in range(len(fces_cluster)):
        soe = fces_cluster['initialSOC'][vdx] 
        for idx in range(fces_cluster['duration'][vdx]):
            soe += p[vdx][idx]
            A.addConstr(soe <= fces_cluster['maximumSOC'][vdx])
            A.addConstr(soe >= fces_ts['arr_{}_minimumSOC'.format(vdx)][idx])

    # Demand Curve ∋ Goal-SoC
    for vdx in range(len(fces_cluster)):
        demand_set = fces_ts['arr_{}_demand'.format(vdx)].unique()
        # for d in range(1,len(demand_set)):
        for d in range(1,2):
            point = fces_ts[fces_ts['arr_{}_demand'.format(vdx)] == demand_set[d]].index[0]
            soe = fces_cluster['initialSOC'][vdx] + sum([p[vdx][idx] for idx in range(point+1)])
            A.addConstr(soe >= demand_set[d])

    return A

def updated(fces_ts,fces_cluster,w_obj,fault,P_A):
    updated_A = gp.Model('Stage-A')
    updated_A.Params.LogToConsole = 0
    # ev Power {vdx,m,t}
    p = [updated_A.addVars(range(fces_cluster.duration[vdx])) for vdx in range(len(fces_cluster))]

    for vdx in range(len(fces_cluster)): # upper and lower bound
        for idx in range(fces_cluster['duration'][vdx]):
            p[vdx][idx].ub = fces_ts['arr_{}_pcs'.format(vdx)][idx]
            p[vdx][idx].lb = -fces_ts['arr_{}_pcs'.format(vdx)][idx]

    updated_A = constraints(updated_A,p,fces_ts,fces_cluster)
    updated_A = constraint_update(updated_A,p,fces_ts,fces_cluster,fault,P_A)
    updated_A.ModelSense = GRB.MINIMIZE
    updated_A = objective_function(updated_A,w_obj,p,fces_ts,fces_cluster)   
    updated_A.optimize()
    try:
        P_A, SoC_A = arranger.A(p,fces_ts,fces_cluster)
    except:
        fault.to_csv('error_fault.csv')
        P_A.to_csv('error_P_A.csv')
        fces_ts.to_csv('error_FCES_ts.csv')
        fces_cluster.to_csv('error_FCES_cluster.csv')
        ss=1
    return P_A, SoC_A

def constraint_update(updated_A,p,fces_ts,fces_cluster,fault,P_A):
    header = ['F_id','V_id','idx']
    fault[header] = fault[header].astype('int') # float -> int

    for fdx in fault['F_id'][:7]:
        cum_p = sum([p[fdx][idx] for idx in range(fault['idx'][fdx]+1)])
        intime = fces_cluster['From'][fdx]
        pre_p = P_A['arr_{}'.format(fdx)][intime:intime+fault['idx'][fdx]+1].sum()

        if fault['amount'][fdx] >= 0:
            updated_A.addConstr(cum_p <= pre_p - fault['amount'][fdx])
        else:
            updated_A.addConstr(cum_p >= pre_p - fault['amount'][fdx])

    return updated_A
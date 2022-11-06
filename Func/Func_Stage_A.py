import gurobipy as gp
from gurobipy import GRB
from Func import Func_result_arranger as arranger

def func(fces_ts,fces_cluster,w_obj):
    A = gp.Model('Stage-A')

    # ev Power {vdx,m,t}
    p = [A.addVars(range(int(fces_cluster.duration[vdx]))) for vdx in range(len(fces_cluster))]
    # ev goal soc
    # goalsoc_ev = model.addVars(range(len(ev)), lb=0)
    
    for vdx in range(len(fces_cluster)):
        for idx in range(int(fces_cluster['duration'][vdx])):
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
        for idx in range(int(fces_cluster['duration'][vdx])):
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

def updates():
    return 0
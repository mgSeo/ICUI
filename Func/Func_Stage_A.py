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

    Fleet_P = arranger.A(p,fces_ts,fces_cluster)
    return Fleet_P
    
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
    # soc
    for vdx in range(len(fces_cluster)):
        soe = fces_cluster['initialSOC'][vdx] 
        for idx in range(int(fces_cluster['duration'][vdx])):
            soe += p[vdx][idx]
            A.addConstr(soe <= fces_ts['arr_{}_maximumSOC'.format(vdx)][idx])
            A.addConstr(soe >= fces_ts['arr_{}_minimumSOC'.format(vdx)][idx])
        
    # demand
    # update

    return A
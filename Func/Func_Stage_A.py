import gurobipy as gp
from gurobipy import GRB
from Func import Func_result_arranger as arranger

def func(fces_ts,fces_cluster,w_obj):
    A = gp.Model('Stage-A')
    A.Params.LogToConsole = 0
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

def updated(fces_ts,fces_cluster,w_obj,fault,preP_A):
    updated_A = gp.Model('Stage-A')
    updated_A.Params.LogToConsole = 0
    # ev Power {vdx,m,t}
    p = [updated_A.addVars(range(int(fces_cluster.duration[vdx]))) for vdx in range(len(fces_cluster))]
    # ev goal soc
    # goalsoc_ev = model.addVars(range(len(ev)), lb=0)
    
    for vdx in range(len(fces_cluster)):
        for idx in range(int(fces_cluster['duration'][vdx])):
            p[vdx][idx].ub = fces_ts['arr_{}_pcs'.format(vdx)][idx]
            p[vdx][idx].lb = -fces_ts['arr_{}_pcs'.format(vdx)][idx]

    updated_A = constraints(updated_A,p,fces_ts,fces_cluster)
    updated_A = constraint_update(updated_A,p,fces_ts,fces_cluster,fault,preP_A)
    updated_A.ModelSense = GRB.MINIMIZE
    updated_A = objective_function(updated_A,w_obj,p,fces_ts,fces_cluster)   
    updated_A.optimize()

    P_A, SoC_A = arranger.A(p,fces_ts,fces_cluster)
    return P_A, SoC_A

def constraint_update(updated_A,p,fces_ts,fces_cluster,fault,preP_A):
    # Strengthens
    for fdx in range(len(fces_cluster)):
    # for fdx in range(15):
        # if fdx == 15: continue
        fault_set = fault[fault['F_id']==fdx]
        fault_set = fault_set.reset_index()

        for f in range(len(fault_set)):
            IDX = int(fault_set['idx'][f] + 1)
            cum_p = sum([p[fdx][idx] for idx in range(IDX)])
            if fault_set['amount'][f] > 0:
                updated_A.addConstr(cum_p <= preP_A['arr_{}'.format(fdx)][:int(IDX+fces_cluster['From'][fdx])].sum() - fault_set['amount'][f])
            elif fault_set['amount'][f] < 0:
                updated_A.addConstr(cum_p >= preP_A['arr_{}'.format(fdx)][:int(IDX+fces_cluster['From'][fdx])].sum() - fault_set['amount'][f])

    return updated_A
    # preP_A['arr_{}'.format(vdx)]
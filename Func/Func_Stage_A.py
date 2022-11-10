import gurobipy as gp
from gurobipy import GRB
from Func import Func_result_arranger as arranger

def func(fces_ts,fces_cluster,w_obj):
    A = gp.Model('Stage-A')
    A.Params.LogToConsole = 0
    # ev Power {fdx,m,t}
    p = [A.addVars(range(fces_cluster.duration[fdx])) for fdx in range(len(fces_cluster))]
    # ev goal soc
    # goalsoc_ev = model.addVars(range(len(ev)), lb=0)
    
    for fdx in range(len(fces_cluster)):
        for idx in range(fces_cluster['duration'][fdx]):
            p[fdx][idx].ub = fces_ts['arr_{}_pcs'.format(fdx)][idx]
            p[fdx][idx].lb = -fces_ts['arr_{}_pcs'.format(fdx)][idx]

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
        for fdx in range(len(fces_cluster)):
            if fces_cluster['From'][fdx] <= t <= fces_cluster['To'][fdx]:
                idx = t - fces_cluster['From'][fdx]
                X += p[fdx][idx]
        obj_smp += X * w_obj[0][t]
    A.setObjective(obj_smp)
    return A

def constraints(A,p,fces_ts,fces_cluster):
    # SoC boundaries
    for fdx in range(len(fces_cluster)):
        soe = fces_cluster['initialSOC'][fdx] 
        for idx in range(fces_cluster['duration'][fdx]):
            soe += p[fdx][idx]
            A.addConstr(soe <= fces_cluster['maximumSOC'][fdx])
            A.addConstr(soe >= fces_ts['arr_{}_minimumSOC'.format(fdx)][idx])

    # Demand Curve ∋ Goal-SoC
    # for fdx in range(len(fces_cluster)):
    #     demand_set = fces_ts['arr_{}_demand'.format(fdx)].unique()
    #     # for d in range(1,len(demand_set)):
    #     for d in range(1,len(demand_set)):
    #         point = fces_ts[fces_ts['arr_{}_demand'.format(fdx)] == demand_set[d]].index[0]
    #         soe = fces_cluster['initialSOC'][fdx] + sum([p[fdx][idx] for idx in range(point+1)])
    #         A.addConstr(soe >= demand_set[d])

    return A

def updated(fces_ts,fces_cluster,w_obj,fault,P_A):
    updated_A = gp.Model('Stage-A')
    updated_A.Params.LogToConsole = 0
    # ev Power {fdx,m,t}
    p = [updated_A.addVars(range(fces_cluster.duration[fdx])) for fdx in range(len(fces_cluster))]

    for fdx in range(len(fces_cluster)): # upper and lower bound
        for idx in range(fces_cluster['duration'][fdx]):
            p[fdx][idx].ub = fces_ts['arr_{}_pcs'.format(fdx)][idx]
            p[fdx][idx].lb = -fces_ts['arr_{}_pcs'.format(fdx)][idx]

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
    for f in range(len(fault)):
        F_id = fault['F_id'][f]
        IDX = fault['idx'][f]

        cum_p = sum([p[F_id][idx] for idx in range(IDX+1)])
        intime = fces_cluster['From'][F_id]
        pre_p = P_A['arr_{}'.format(F_id)][intime : intime+IDX+1].sum()

        if fault['amount'][f] >= 0:
            updated_A.addConstr(cum_p <= pre_p - fault['amount'][f])
        else:
            updated_A.addConstr(cum_p >= pre_p - fault['amount'][f])

    return updated_A
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import pandas as pd
import numpy as np
import numpy.matlib
## Parameters:
filename = 'data/Data_Step2.csv'
EV = pd.read_csv(filename)
filename = 'data/SMP.csv'
smp = pd.read_csv(filename)
smp_15term = np.repeat(smp['SMP0105'].to_numpy(), [4])
obj = pd.DataFrame(smp_15term)
step = 4 # default = 4%, == SoC 좌우 이동 범위. 값이 클수록 충전률/방전률이 커짐

## Functions:
from Func import Func_pipeline as pipeline
from Func import Func_ICUI as icui

ev,cluster = pipeline.func(EV, step)
icui.func(ev,obj)
x = cbs.func(ev,cluster,obj)

ss=1


## read data and make dataframe


## parameter config ###########################################
folder = '' # Choose folder
path = './input/' + folder
result_path = './result_pulp/'
start_time = time.time()
T = 96*2
    
###############################################################

EV, D, CPC, Tou, Cost = pipeline(path,T)

## Cluster-based-Massive Fleet Scheduler ######################
import Cluster_based_scheduler as CBS
step = 4
cluster = CBS.def_cluster(EV,step)
Batt_consider = 0
CPC_consider = 0
Fleet_schedule, EV_schedule = CBS.Scheduler(EV,cluster,D,T,Tou,Batt_consider,CPC['Cluster'],CPC_consider)
Fleet_schedule.to_csv('./result_check/'+'CBS.csv')
EV_schedule.to_csv('./result_check/'+'CBS_each.csv')

## Arbitrage Fleet Scheduler ######################
import Arbitrage as Arb
Batt_consider = 0
CPC_consider = 0
Fleet_schedule, EV_schedule = Arb.Scheduler(EV,D,T,Tou,Cost,Batt_consider,CPC['Arb'],CPC_consider)
Fleet_schedule.to_csv('./result_check/'+'arb.csv')
# Cost <- Peak, Peak contracted power, Batt
# test

print("---{}s seconds---".format(time.time()-start_time))

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
tol = 2
step = 4 # default = 4%, == SoC 좌우 이동 범위. 값이 클수록 충전률/방전률이 커짐

## Functions:
from Func import Func_pipeline as pipeline
from Func import Func_ICUI as icui

ev,cluster = pipeline.func(EV, step)
P_A, SoC_A, P_B, SoC_B = icui.func(ev,obj,tol)

ss=1
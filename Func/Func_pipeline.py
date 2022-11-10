import pandas as pd
pd.set_option('mode.chained_assignment',  None)
import math
def func(ev, step):
    # Pre-process
    delta = 2
    

    # 1h -> 15min
    ev['serviceFrom'] = ev.serviceFrom*4
    ev['serviceTo'] = ev.serviceTo*4

    # re-arrange the 'serviceTo'
    idx = ev[ev['serviceFrom'] >= ev['serviceTo']].index
    ev['serviceTo'][idx] = 95 # 최대 horizon: ~24시

    ev['duration'] = ev.serviceTo - ev.serviceFrom + 1
    idx = ev['duration'] > 2    
    ev['minimumSOC'] = 8
    ev['maximumSOC'] = 92

    # Def number of clusters
    ev['pcs'] = ev['pcs']/4
    pcs = ev['pcs'].unique()

    header = ['pcs','step','n_ev','min','max','n_cluster','eff','interval','From','To']
    cluster = pd.DataFrame(columns=header)
    cluster.pcs = pcs
    ev['cluster'] = 0
    for k in range(len(pcs)):
        idx = ev[ev['pcs'] == pcs[k]].index
        ev['cluster'][idx] = k

    # Def n_moves of CBS
    for k in range(len(pcs)):
        idx = ev[ev['cluster'] == k].index
        move_range = ev['pcs'][idx[0]]/max(ev['capacity'][idx])*100
        if move_range < step:
            cluster.loc[k,'step'] = math.floor(move_range)
        else:
            cluster.loc[k,'step'] = step        
        cluster.loc[k,'n_ev'] = len(idx)
        cluster.loc[k,'min'] = 8 # soc min range        
        cluster.loc[k,'max'] = 92 # soc max range
        cluster.loc[k,'n_cluster'] = (cluster['max'][k]-cluster['min'][k]) / cluster.step[k] + 1; # number of cluster
        cluster.loc[k,'eff'] = ev.eff[idx].mean() # eff
        cluster.loc[k,'interval'] = math.floor(cluster.pcs[k] / max(ev.capacity[idx]) * 100 / cluster.step[k]); # 1 time-frame에 이동가능한 범위
        cluster.loc[k,'From'] = min(ev.serviceFrom[idx]); # clsuter's serviceFrom
        cluster.loc[k,'To'] = max(ev.serviceTo[idx]); # clsuter's serviceTo
        demand = (ev.goalSOC[idx]-ev.initialSOC[idx])*ev.capacity[idx]/100
        demand[demand <= 0] = 0
        capability = ev['duration'][idx] - demand/(cluster['step'][k]*cluster['interval'][k]) # 충전요구량 도달 가능성
        c_idx = capability[capability<0].index                
        ev['goalSOC'][c_idx] = ev.goalSOC[c_idx] + capability[c_idx]*(cluster.step[k]*cluster.interval[k] + delta)
    
    
    cluster['duration'] = cluster.To - cluster.From + 1 # cluster's duration
    header = ['serviceFrom','serviceTo','duration']
    ev[header] = ev[header].astype('int')

    return ev,cluster
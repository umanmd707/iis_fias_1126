"""Reproducible event-driven flexible-job-shop experiment; all inputs synthetic.
P2 combines energy-aware routing and idle sleep; P3 routes only; P4 sleeps only.
"""
import argparse,csv,heapq,json,math
from pathlib import Path
import numpy as np

IDLE=np.array([1.5,1.8,2.0,2.2,2.5,2.8,3.1,3.4]); ACTIVE=np.array([3.2,3.8,4.2,4.6,5.0,5.4,5.8,6.2]); SETUP=np.array([2.1,2.4,2.7,2.9,3.2,3.5,3.8,4.0]); SPEED=np.array([.85,.91,.96,1.00,1.04,1.09,1.14,1.20]); BASE=np.array([8.,12.,18.,24.,30.]); NM=8

# Workload is terminating, with event-based arrivals; operational policies see identical draw sequences.
def make_input(seed, n_jobs, spacing, cv=.15):
    rg=np.random.default_rng(seed)
    fam=rg.integers(0,3,n_jobs)
    releases=np.cumsum(rg.exponential(spacing,n_jobs)); releases-=releases[0]
    sigma=np.sqrt(np.log1p(cv*cv)); draws=rg.lognormal(-sigma*sigma/2,sigma,(n_jobs,5,8))
    return fam,releases,draws

def eligible(fam, op, rf):
    start=(int(fam)*2+int(op)*3)%NM
    return [(start+k*3)%NM for k in range(rf)] # stride 3 covers 8 machines

def run_case(seed=2026, rf=3, workload='medium',policy='P0',n_jobs=72,cv=.15, log_events=False, sleep_after_min=15., sleep_power_ratio=.20, wakeup_min=2.):
    spacing={'low':10.0,'medium':6.0,'high':3.5}[workload]
    fam,releases,draws=make_input(seed,n_jobs,spacing,cv)
    # Energy integral integrates all machines across every event interval; even machines never used consume idle energy.
    t=0.; seq=0; ev=[]; ready=[]; busy=np.zeros(NM,bool); state=np.array(['idle']*NM,dtype=object)
    last_family=np.full(NM,-1); last_change=np.zeros(NM); state_energy=np.zeros(NM); state_minutes={s:np.zeros(NM) for s in ('idle','setup','active','sleep')}
    op=np.zeros(n_jobs,dtype=int); completed=0; completion=np.zeros(n_jobs)
    logs=[]; sleep_events=0; setup_events=0; total_processing=0.; total_setup=0.
    # 15-minute idle threshold; sleep/standby is 20% of idle power. Wake-up costs 2 min and setup-state power.
    sleep_after=sleep_after_min; wakeup=wakeup_min
    for j,rel in enumerate(releases):
        heapq.heappush(ev,(float(rel),seq,'arrival',j,-1));seq+=1
    def record(dt):
        nonlocal t
        if dt< -1e-8: raise AssertionError('time inversion')
        for m in range(NM):
            if state[m]=='active': kw=ACTIVE[m]
            elif state[m]=='setup':kw=SETUP[m]
            elif state[m]=='sleep':kw=IDLE[m]*sleep_power_ratio
            else:kw=IDLE[m]
            state_energy[m]+=kw*dt/60.
            state_minutes[state[m]][m]+=dt
        t+=dt
    def change_state(m,ss):
        nonlocal seq,sleep_events
        if state[m]==ss: return
        if log_events: logs.append({'seed':seed,'rf':rf,'workload':workload,'policy':policy,'event_time_min':round(t,6),'machine':f'M{m+1}','state_from':state[m],'state_to':ss})
        state[m]=ss;last_change[m]=t
        if policy in ('P2','P4') and ss=='idle':
            heapq.heappush(ev,(t+sleep_after,seq,'sleep',-1,m));seq+=1
    # Terminating experiment: stop at the final job completion, not after pending housekeeping events.
    while completed < n_jobs:
        if not ev: raise RuntimeError('deadlock: no events')
        nxt=ev[0][0]; record(max(0.,nxt-t))
        at=[]
        while ev and abs(ev[0][0]-t)<1e-7:at.append(heapq.heappop(ev))
        for _,_,kind,j,m in at:
            if kind=='arrival':ready.append((j,0))
            elif kind=='done':
                busy[m]=False;last_family[m]=int(fam[j]);op[j]+=1
                change_state(m,'idle')
                if op[j]<5:ready.append((j,int(op[j])))
                else:completed+=1;completion[j]=t
            elif kind=='sleep':
                if policy in ('P2','P4') and not busy[m] and state[m]=='idle' and t-last_change[m]>=sleep_after-1e-8:
                    change_state(m,'sleep');sleep_events+=1
        # Dispatch all possible candidates. Select oldest ready job first. This isolates assignment rule.
        changed=True
        while changed:
            changed=False
            idle=[m for m in range(NM) if not busy[m]]
            if not idle or not ready:break
            for index,(j,k) in enumerate(ready):
                ms=[m for m in eligible(fam[j],k,rf) if m in idle]
                if not ms:continue
                vals=[]
                for m in ms:
                    dur=BASE[k]*SPEED[m]*draws[j,k,m]
                    setup=3. if last_family[m]>=0 and last_family[m]!=fam[j] else 0.
                    wake=wakeup if state[m]=='sleep' else 0.
                    total_dur=dur+setup+wake
                    active_energy=(dur*ACTIVE[m]+setup*SETUP[m]+wake*SETUP[m])/60.
                    if policy in ('P0','P1','P4'):
                        score=total_dur
                    else:
                        # Restrict assignment to within 20% of fastest feasible processing + setup;
                        # rank by local incremental energy while accounting for extended runtime.
                        fastest=min(BASE[k]*SPEED[z]*draws[j,k,z]+(3. if last_family[z]>=0 and last_family[z]!=fam[j] else 0.)+(wakeup if state[z]=='sleep' else 0.) for z in ms)
                        score=active_energy+0.020*total_dur if total_dur <=1.20*fastest else 1e8+total_dur
                    vals.append((score,m,dur,setup,wake))
                _,m,dur,setup,wake=min(vals)
                busy[m]=True
                total_processing+=dur;total_setup+=setup;setup_events+=int(setup>0)
                if setup+wake>0:change_state(m,'setup')
                else:change_state(m,'active')
                # Explicit state transitions at setup completion (event never frees machine)
                if setup+wake>0:
                    heapq.heappush(ev,(t+setup+wake,seq,'begin_active',j,m));seq+=1
                heapq.heappush(ev,(t+setup+wake+dur,seq,'done',j,m));seq+=1
                ready.pop(index);changed=True;break
        # Transition from setup to active for simultaneously due start events.
        # begin_active events at event times are handled in the normal event handler below.
        # Processing time still included in done; if event not handled, energy would be incorrectly charged setup.
        for _,_,kind,j,m in at:
            if kind=='begin_active':change_state(m,'active')
    if completed!=n_jobs or np.any(op!=5):raise AssertionError('job completion conservation')
    if np.any(state_energy<0):raise AssertionError('negative energy')
    if ready or np.any(busy):raise AssertionError('unfinished work at stop')
    if not math.isclose(t, float(max(completion)),abs_tol=1e-7):raise AssertionError('electricity horizon exceeds last completion')
    state_minutes_sum=sum(state_minutes.values())
    if not np.allclose(state_minutes_sum,t,atol=1e-7):raise AssertionError('machine-state durations do not reconcile with observation horizon')
    expected_energy=(state_minutes['idle']*IDLE + state_minutes['active']*ACTIVE + state_minutes['setup']*SETUP + state_minutes['sleep']*IDLE*sleep_power_ratio)/60.
    if not np.allclose(expected_energy,state_energy,atol=1e-9):raise AssertionError('state energy does not reconcile')
    # The unprocessed event queue may hold stale sleep transitions, which must not extend energy accounting.
    pending_events_after_completion=sum(1 for x in ev if x[0]>t+1e-8)
    makespan=float(max(completion)-min(releases));total_energy=float(state_energy.sum());emission=.40*total_energy
    # Per-job resource consumption is identical across policies because process routing doesn't alter resource coefficients.
    water_coeff=np.array([.5,2.,8.]);water=float(np.sum(water_coeff[fam]))
    # Synthetic, seed-derived expected waste mass (kg) held constant across policies; not a causal effect.
    waste=float(np.sum((fam+1)*.02))
    out={'seed':seed,'rf':rf,'workload':workload,'policy':policy,'n_jobs':n_jobs,'cv':cv,'makespan_min':makespan,'throughput_per_hr':n_jobs/(makespan/60.),'total_kwh':total_energy,'kwh_per_job':total_energy/n_jobs,'total_kgco2e':emission,'kgco2e_per_job':emission/n_jobs,'water_l':water,'water_l_per_job':water/n_jobs,'waste_kg':waste,'waste_kg_per_job':waste/n_jobs,'sleep_events':sleep_events,'setup_events':setup_events,'processing_machine_min':total_processing,'setup_machine_min':total_setup,'observation_end_min':t,'pending_events_after_completion':pending_events_after_completion,'max_machine_minutes_error':float(np.max(np.abs(state_minutes_sum-t))),'max_energy_reconciliation_error_kwh':float(np.max(np.abs(expected_energy-state_energy)))}
    return (out,logs) if log_events else out

def self_test():
    # Exact parity: monitoring must not change dispatch or accounting.
    for rf in (1,3,5):
        for workload in ('low','medium','high'):
            a=run_case(seed=66,rf=rf,workload=workload,policy='P0')
            b=run_case(seed=66,rf=rf,workload=workload,policy='P1')
            assert a['total_kwh']==b['total_kwh'] and a['makespan_min']==b['makespan_min']
            assert a==run_case(seed=66,rf=rf,workload=workload,policy='P0')
            for pol in ('P0','P1','P2','P3','P4'):
                x=run_case(seed=66,rf=rf,workload=workload,policy=pol)
                assert x['n_jobs']==72 and x['total_kwh']>0
                assert math.isclose(x['total_kgco2e'],.4*x['total_kwh'],rel_tol=1e-12)
                assert math.isclose(x['observation_end_min'],x['makespan_min'],abs_tol=1e-7)
                assert x['max_machine_minutes_error']<1e-7 and x['max_energy_reconciliation_error_kwh']<1e-9
            # Sleep disabled must reproduce the conventional policy exactly.
            nosleep=run_case(seed=66,rf=rf,workload=workload,policy='P4',sleep_after_min=1e9)
            assert nosleep['sleep_events']==0
            assert math.isclose(a['total_kwh'],nosleep['total_kwh'],abs_tol=1e-9)
            assert math.isclose(a['makespan_min'],nosleep['makespan_min'],abs_tol=1e-9)
    # Small terminating batch: no scheduled housekeeping event may extend the horizon.
    one=run_case(seed=19,rf=1,workload='high',policy='P4',n_jobs=1)
    assert math.isclose(one['observation_end_min'],one['makespan_min'],abs_tol=1e-8)
    assert one['pending_events_after_completion']>0
    print('PASS: P0/P1 parity, deterministic replay, state accounting, end-of-run cutoff, no-sleep parity, single-job boundary')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');p.add_argument('--output',default='data/run_summaries.csv');p.add_argument('--replications',type=int,default=30);p.add_argument('--event-log',action='store_true');args=p.parse_args()
    if args.test:self_test();raise SystemExit
    rows=[];events=[]
    for rf in (1,3,5):
        for w in ('low','medium','high'):
            for i in range(args.replications):
                seed=20261106+i
                for pol in ('P0','P1','P2','P3','P4'):
                    r=run_case(seed,rf,w,pol,log_events=args.event_log and i==0)
                    if isinstance(r,tuple): rr,ll=r;rows.append(rr);events.extend(ll)
                    else:rows.append(r)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    if events:
        with open(path.parent/'sample_state_transitions.csv','w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(events[0]));wr.writeheader();wr.writerows(events)
    print(f'Wrote {len(rows)} independent policy runs to {path}')

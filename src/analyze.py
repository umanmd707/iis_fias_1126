from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import t,ttest_1samp
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data';F=ROOT/'figures'
F.mkdir(exist_ok=True)
a=pd.read_csv(D/'run_summaries.csv')
index=['seed','rf','workload'];p=a.pivot(index=index,columns='policy',values=['total_kwh','makespan_min','kwh_per_job','throughput_per_hr']);rows=[]
for (seed,rf,w),sub in p.iterrows():
    r={'seed':seed,'rf':rf,'workload':w}
    for pol in ('P2','P3','P4'):
        r[f'energy_{pol}_pct']=100*(sub['total_kwh'][pol]/sub['total_kwh']['P0']-1)
        r[f'makespan_{pol}_pct']=100*(sub['makespan_min'][pol]/sub['makespan_min']['P0']-1)
        r[f'energy_{pol}_kwh']=sub['total_kwh'][pol]-sub['total_kwh']['P0']
        r[f'makespan_{pol}_min']=sub['makespan_min'][pol]-sub['makespan_min']['P0']
    rows.append(r)
df=pd.DataFrame(rows);df.to_csv(D/'paired_effects.csv',index=False)

def ci(vals):
    x=np.asarray(vals,float);avg=x.mean();h=t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x));return avg,avg-h,avg+h

# Cluster-independent unit for overall inference is master seed (n=30), averaged across all 9 factorial cells.
seed_summary=df.groupby('seed').mean(numeric_only=True)
summary=[]
for pol in ('P2','P3','P4'):
    for metric in ('energy','makespan'):
        col=f'{metric}_{pol}_pct';mean,lo,hi=ci(seed_summary[col]);pv=ttest_1samp(seed_summary[col],0).pvalue
        summary.append({'policy':pol,'metric':metric,'mean_relative_change_pct':mean,'95CI_lower':lo,'95CI_upper':hi,'t_p_two_sided':pv,'independent_seed_blocks':len(seed_summary)})
summary_df=pd.DataFrame(summary);summary_df.to_csv(D/'overall_inference.csv',index=False)
bycell=[]
for (rf,w),g in df.groupby(['rf','workload']):
    for pol in ('P2','P3','P4'):
        e,elo,ehi=ci(g[f'energy_{pol}_pct']);m,mlo,mhi=ci(g[f'makespan_{pol}_pct'])
        bycell.append(dict(rf=rf,workload=w,policy=pol,energy_pct=e,energy_lo=elo,energy_hi=ehi,makespan_pct=m,makespan_lo=mlo,makespan_hi=mhi))
bycell=pd.DataFrame(bycell);bycell.to_csv(D/'cell_effects.csv',index=False)

# Descriptive factorial interaction on matched percent deltas. Cluster-robust inference by common seed.
fit=smf.ols('energy_P2_pct ~ C(rf)*C(workload)',data=df).fit(cov_type='cluster',cov_kwds={'groups':df['seed']})
with open(D/'factorial_model.txt','w') as f:
    f.write('OLS on paired percent change; cluster-robust SE by master seed\n'+str(fit.summary()))
# Difference-in-differences for policy effect at RF1 vs RF5 per seed, averaged over workloads.
wide=df.groupby(['seed','rf'])['energy_P2_pct'].mean().unstack('rf')
interaction=wide[1]-wide[5]
interaction_mean,interaction_lo,interaction_hi=ci(interaction)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':220})
styles={'low':('o','Low'),'medium':('s','Medium'),'high':('^','High')}
fig,ax=plt.subplots(figsize=(5.2,3.1))
for w,(mark,lab) in styles.items():
    g=bycell[(bycell.policy=='P2')&(bycell.workload==w)].sort_values('rf')
    ax.errorbar(g.rf,g.energy_pct,yerr=[g.energy_pct-g.energy_lo,g.energy_hi-g.energy_pct],marker=mark,capsize=3,label=lab,linewidth=1.4)
ax.axhline(0,color='gray',lw=.8);ax.set(xlabel='Eligible machines per operation (routing flexibility)',ylabel='P2 vs P0 electricity (%)',xticks=[1,3,5]);ax.legend(title='Workload',frameon=False,ncol=3,loc='lower right',fontsize=7);fig.tight_layout();fig.savefig(F/'fig1_routing_workload_energy.pdf');fig.savefig(F/'fig1_routing_workload_energy.png');plt.close(fig)

fig,ax=plt.subplots(figsize=(5.2,3.05))
for pol,name in (('P2','Combined'),('P3','Routing only'),('P4','Sleep only')):
    g=df.groupby(['rf','seed'])[f'energy_{pol}_pct'].mean().reset_index()
    mean=g.groupby('rf')[f'energy_{pol}_pct'].mean()
    lo=[];hi=[]
    for rf in [1,3,5]:
        _,lower,upper=ci(g[g.rf==rf][f'energy_{pol}_pct']);lo.append(lower);hi.append(upper)
    ax.errorbar([1,3,5],mean.values,yerr=[mean.values-np.array(lo),np.array(hi)-mean.values],marker={'P2':'o','P3':'s','P4':'^'}[pol],capsize=2.5,label=name)
ax.axhline(0,color='gray',lw=.8);ax.set(xlabel='Routing flexibility',ylabel='Electricity vs P0 (%)',xticks=[1,3,5]);ax.legend(frameon=False,ncol=1,fontsize=8);fig.tight_layout();fig.savefig(F/'fig2_policy_ablation.pdf');fig.savefig(F/'fig2_policy_ablation.png');plt.close(fig)

fig,ax=plt.subplots(figsize=(5.2,3.1));color={'low':'tab:blue','medium':'tab:orange','high':'tab:green'}
for w,(mark,lab) in styles.items():
    g=bycell[(bycell.policy=='P2')&(bycell.workload==w)].sort_values('rf')
    ax.errorbar(g.rf,g.makespan_pct,yerr=[g.makespan_pct-g.makespan_lo,g.makespan_hi-g.makespan_pct],marker=mark,capsize=2.5,label=lab)
ax.axhline(0,color='gray',lw=.8);ax.axhline(5,color='gray',ls=':',lw=.8,label='5% tolerance');ax.set(xlabel='Routing flexibility',ylabel='P2 vs P0 makespan (%)',xticks=[1,3,5]);ax.legend(frameon=False,ncol=2,fontsize=7);fig.tight_layout();fig.savefig(F/'fig3_makespan_constraint.pdf');fig.savefig(F/'fig3_makespan_constraint.png');plt.close(fig)

# Carbon sensitivity: constant grid factor -> emissions scale in absolute units without altering relative savings.
co2=[]
for factor in (.1,.4,.8):
    for pol in ('P0','P2'):
        z=a[a.policy==pol]
        co2.append(dict(grid_factor_kg_per_kwh=factor,policy=pol,mean_kgco2e_per_job=float(z.kwh_per_job.mean()*factor)))
pd.DataFrame(co2).to_csv(D/'grid_sensitivity.csv',index=False)

# Processing-time variability sensitivity using the same 30 independent blocks in each condition.
from fias_sim import run_case
sensitivity=[]
for cv in (.05,.30):
    for rf in (1,3,5):
        for w in ('low','medium','high'):
            for seed in range(20261106,20261136):
                a0=run_case(seed,rf,w,'P0',cv=cv);a2=run_case(seed,rf,w,'P2',cv=cv)
                sensitivity.append(dict(seed=seed,cv=cv,rf=rf,workload=w,energy_pct=100*(a2['total_kwh']/a0['total_kwh']-1),makespan_pct=100*(a2['makespan_min']/a0['makespan_min']-1)))
pd.DataFrame(sensitivity).to_csv(D/'cv_sensitivity.csv',index=False)

# Summary valid only for these synthetic model specifications.
checks={
 'run_count':int(len(a)),'matched_pairs':int(len(df)),'seed_blocks':int(len(seed_summary)),
 'P0_P1_exact_parity':bool((p['total_kwh']['P0']==p['total_kwh']['P1']).all() and (p['makespan_min']['P0']==p['makespan_min']['P1']).all()),
 'P2_pairs_below_5pct_makespan_penalty':int((df.makespan_P2_pct<=5).sum()),
 'P2_pairs_with_electricity_reduction':int((df.energy_P2_pct<0).sum()),
 'rf1_minus_rf5_energy_effect_percentage_points':float(interaction_mean),
 'rf1_minus_rf5_95CI_lower':float(interaction_lo),
 'rf1_minus_rf5_95CI_upper':float(interaction_hi),
}
with open(D/'checks.json','w') as f:import json;json.dump(checks,f,indent=2)
print(summary_df.to_string(index=False,float_format=lambda v:f'{v:.3f}'))
print('checks:',checks)
print('cell results P2:\n',bycell[bycell.policy=='P2'].to_string(index=False,float_format=lambda v:f'{v:.2f}'))

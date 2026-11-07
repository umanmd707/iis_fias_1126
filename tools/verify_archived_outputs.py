"""Check archival data shapes, control-policy parity, invariants and paper's primary estimates.
Works against CSV files in data/ without changing artifacts.
"""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
a = pd.read_csv(ROOT / 'data' / 'run_summaries.csv')
assert len(a) == 1350, 'primary run count differs from paper'
assert set(a.policy) == {'P0','P1','P2','P3','P4'}
assert set(a.rf) == {1,3,5}
assert set(a.workload) == {'low','medium','high'}
assert len(set(a.seed)) == 30
assert (a.n_jobs == 72).all()
assert np.allclose(a.total_kgco2e,0.4 * a.total_kwh)
assert np.allclose(a.observation_end_min,a.makespan_min)
assert (a.max_machine_minutes_error < 1e-7).all()
assert (a.max_energy_reconciliation_error_kwh < 1e-9).all()
p = a.pivot(index=['seed','rf','workload'],columns='policy',values=['total_kwh','makespan_min'])
assert len(p) == 270
for metric in ('total_kwh','makespan_min'):
    assert (p[metric]['P0'] == p[metric]['P1']).all(), 'monitoring-only parity'
e = 100 * (p.total_kwh.P2 / p.total_kwh.P0 - 1)
m = 100 * (p.makespan_min.P2 / p.makespan_min.P0 - 1)
es = e.groupby(level='seed').mean().mean()
ms = m.groupby(level='seed').mean().mean()
assert abs(es - (-5.979974)) < 1e-5, f'electricity mean: {es}'
assert abs(ms - 0.196977) < 1e-5, f'makespan mean: {ms}'
assert int((e<0).sum()) == 219
assert int((m<=5).sum()) == 270
print(f'PASS archive: {len(a)} runs; {len(p)} matched blocks; mean electricity {es:.6f}%; mean makespan {ms:.6f}%')

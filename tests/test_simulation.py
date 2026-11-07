"""Independent regression and invariance checks for the FIA-S terminating DES."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fias_sim import run_case

class TestTerminatingDES(unittest.TestCase):
    def test_horizon_state_reconciliation(self):
        for seed in (17,66,20261106):
            for rf in (1,3,5):
                for policy in ('P0','P2','P4'):
                    r=run_case(seed=seed,rf=rf,workload='medium',policy=policy)
                    self.assertAlmostEqual(r['observation_end_min'],r['makespan_min'],places=7)
                    self.assertLess(r['max_machine_minutes_error'],1e-7)
                    self.assertLess(r['max_energy_reconciliation_error_kwh'],1e-9)
    def test_one_job_pending_housekeeping_does_not_extend_energy(self):
        r=run_case(seed=19,rf=1,workload='high',policy='P4',n_jobs=1)
        self.assertGreater(r['pending_events_after_completion'],0)
        self.assertAlmostEqual(r['observation_end_min'],r['makespan_min'],places=7)
    def test_monitoring_only_parity(self):
        for w in ('low','medium','high'):
            p0=run_case(69,5,w,'P0')
            p1=run_case(69,5,w,'P1')
            self.assertEqual(p0['total_kwh'],p1['total_kwh'])
            self.assertEqual(p0['makespan_min'],p1['makespan_min'])
    def test_disabling_sleep_reproduces_conventional(self):
        for seed in (23,66):
            p0=run_case(seed,3,'high','P0')
            p4=run_case(seed,3,'high','P4',sleep_after_min=1e9)
            self.assertEqual(p4['sleep_events'],0)
            self.assertAlmostEqual(p0['total_kwh'],p4['total_kwh'],places=9)
            self.assertAlmostEqual(p0['makespan_min'],p4['makespan_min'],places=9)
    def test_determinism_carbon_and_job_conservation(self):
        r=run_case(19,1,'low','P2')
        self.assertEqual(r,run_case(19,1,'low','P2'))
        self.assertEqual(r['n_jobs'],72)
        self.assertAlmostEqual(r['total_kgco2e'],.4*r['total_kwh'],places=10)

if __name__=='__main__': unittest.main()

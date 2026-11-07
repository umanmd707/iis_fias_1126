# FIA-S experiment protocol 

## Synthetic reference system

- Eight heterogeneous machines with power arrays defined in `src/fias_sim.py` (`IDLE`, `ACTIVE`, `SETUP`) and machine-speed factors (`SPEED`).
- Three job families, five operations per job, 72 jobs per run; machine eligibility is deterministic as a function of family, operation, and routing flexibility.
- Lognormal task multipliers, nominal means of 8, 12, 18, 24, 30 minutes, coefficient of variation 0.15 for the primary study.
- Exponential job-release spacing: 10, 6, 3.5 minutes for low, medium, high workloads.
- Setup duration 3 minutes on family change. Sleep: after 15 minutes idle, 20% of idle power, 2-minute wakeup overhead.
- The terminating observation horizon is **final job completion**. Idle, processing, setup, and sleep power are integrated until that time only.

## Design and controls

- Routing flexibility `rf` in {1,3,5}, workload in {low,medium,high}.
- Thirty common seeds: integers 20261106–20261135.
- Five policies per matched input: P0 operational shortest-duration assignment; P1 monitoring-only (same decisions as P0); P2 energy-aware assignment + sleep; P3 energy-aware assignment only; P4 operational assignment + sleep.
- Primary: 3×3×30×5 = 1,350 policy runs, 270 matched five-policy conditions.
- Additional sensitivity: CV in {0.05,0.30}, 3×3×30×2 = 540 evaluations, P0 and P2 only.
- Constant operational electricity emission factor 0.40 kg CO2e/kWh is a *scenario parameter*, not a verified regional factor. Supplementary factors 0.10 and 0.80 scale absolute emissions only.
- Direct water/waste coefficients are policy-independent and **cannot demonstrate savings from FIA-S** in this implementation.

## Analysis

- Paired relative change: 100×(policy/baseline − 1).
- To avoid pseudoreplication, average each of the nine routing/workload cell changes per common seed, then estimate the 95% Student t interval over 30 seed-level block means.
- Cell-level intervals use the 30 matched seeds. The script additionally estimates a categorical routing × workload interaction with seed-clustered standard errors.
- Makespan ≤ +5% is evaluated after each run and is a **study-defined ex-post tolerance**; it is not mathematically enforced by the policy.

## Verification versus validation

- Reproducibility/verification: unit tests, fixed-seed replay, energy/time reconciliation, P0–P1 parity, sleep-disabled P4/P0 parity, terminating event horizon.
- External calibration / industrial validity: not completed. Results must not be described as measured savings at a real facility.

# FIA-S: Sustainable Shop Floor Manufacturing Simulation

**Research title:** FIA-S: Extending the Synergism of Flexibility, Integration, and Automation for Sustainable Shop Floor Manufacturing

**Researchers:** Alejandra Bonito and Uman Ahmed Mohammed

This repository contains a reproducible discrete-event simulation of a synthetic flexible manufacturing system. The implementation compares five machine-assignment and idle-power-control policies under matched workloads, and provides the generated run summaries, statistical analyses, figures, and verification tests.

## Study scope

The reference system consists of eight heterogeneous machines, three job families, five operations per job, and 72 jobs in each terminating simulation. Routing flexibility takes values of 1, 3, or 5 eligible machines per operation. Three workload conditions are defined by mean inter-release intervals of 10, 6, and 3.5 minutes. Processing durations are stochastic, with a lognormal coefficient of variation of 0.15 in the main experiment.

The five policies are:

| Policy | Description |
|---|---|
| P0 | Operational FIA baseline: shortest estimated completion duration |
| P1 | Monitoring-only: identical scheduling decisions to P0 |
| P2 | Energy-aware routing with automatic machine idle sleep |
| P3 | Energy-aware routing without sleep control |
| P4 | Operational routing with automatic sleep control |

Machines under P2 and P4 may enter sleep after 15 minutes idle, draw 20% of ordinary idle power during sleep, and incur a 2-minute wake-up duration. These are experimental assumptions, not calibrated machine specifications.

## Reproduce the study

Python 3.10+ is required. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/fias_sim.py --test
python tools/verify_archived_outputs.py
```

To regenerate the primary data and statistical figures:

```bash
python src/fias_sim.py --replications 30 --event-log --output data/run_summaries.csv
python src/analyze.py
python tools/verify_archived_outputs.py
```

The regeneration commands overwrite tracked output datasets and figures. Use a separate branch or working copy to retain the archived outputs for comparison.

## Experimental design and results

The main experiment contains **1,350 runs**: three routing levels × three workloads × 30 matched seeds × five policies. The 30 seeds are integers 20261106–20261135. A further 540 runs examine processing-time variability.

For the combined P2 policy relative to P0, the simulated mean paired electricity change is **−5.98%** (95% seed-block confidence interval **−6.35% to −5.61%**), with a mean makespan change of **+0.20%** (95% interval **+0.01% to +0.39%**). Among 270 matched P2 comparisons, 219 used less electricity; all met the study-defined +5% makespan screening threshold. The principal energy benefit arises from idle-state sleep control; routing-only P3 does not show a meaningful mean reduction.

## Model boundary and interpretation

Electricity is integrated from each machine's state-dependent power (active, setup, idle, or sleep) until the final job completes. Operational electricity-related CO₂e uses a **synthetic constant 0.40 kg CO₂e/kWh**; this is not a location-specific grid factor. Water and material-waste coefficients are independent of control policy, so no policy-induced water or waste savings are demonstrated.

The observations are outputs of a **synthetic, uncalibrated manufacturing model**. They are not factory measurements, not evidence of industrial emissions reductions, and not full lifecycle carbon estimates. The +5% makespan limit is checked after simulation rather than guaranteed by the controller. Equipment-level calibration and field validation are outside the scope of this dataset.

## Repository structure

| Path | Description |
|---|---|
| `src/fias_sim.py` | Event-driven manufacturing model, data generation, dispatch policies, CLI |
| `src/analyze.py` | Paired inference, sensitivity analysis, charts |
| `tests/test_simulation.py` | Regression and invariant tests |
| `tools/verify_archived_outputs.py` | Numerical archive verification |
| `data/run_summaries.csv` | Primary run-level data (1,350 observations) |
| `data/cv_sensitivity.csv` | Processing-time variation experiment (540 observations) |
| `data/paired_effects.csv` | Paired comparisons against baseline |
| `data/overall_inference.csv` | Seed-block uncertainty estimates |
| `data/cell_effects.csv` | Effects by routing level and workload |
| `data/sample_state_transitions.csv` | Sample event-state records |
| `data/checks.json` | Model integrity diagnostics |
| `figures/` | Simulation-generated charts in PNG and PDF |
| `docs/EXPERIMENT_PROTOCOL.md` | Detailed experimental assumptions and analysis |

## Verification

The checks cover deterministic fixed-seed replay, all-job completion, event-horizon termination, time and energy reconciliation, P0/P1 monitoring parity, and equivalence of P4 and P0 when sleep is disabled. These checks assess implementation consistency; they do not substitute for industrial validation.

## License

MIT License. See [LICENSE](LICENSE).

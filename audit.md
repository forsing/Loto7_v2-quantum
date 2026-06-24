# Loto Serbia 7/39 - Randomness Audit

Draw date: `2026-06-24`
Question: Is there measurable non-random structure, and does it survive out-of-sample validation?

## Short Answer

- Measured structure strength: `weak`.
- Randomness fingerprint: `near_uniform`.
- Randomness-test interpretation: The history shows measurable deviations from a simple random baseline. This is a signal to backtest, not proof of predictability.
- Out-of-sample verdict: Best model 'hybrid_gap_pair' beat the uniform baseline in walk-forward mean hits.
- Best walk-forward model: `hybrid_gap_pair`.

## Evidence

- Draws loaded: `4638` from `1990-01-01` to `2002-09-12`.
- Data quality usable: `True`.
- Duplicate draw dates: `0`.
- Range/size/duplicate-number errors: `0` / `0` / `0`.
- Frequency max |z|: `2.79`.
- Normalized entropy: `0.9998`.
- Top pair lift: `1.31`.
- Top triple lift: `2.03`.
- Serial lag max delta: `0.02`.
- Distribution drift JS: `0.0006`.
- Best model mean hits: `1.270` vs uniform `1.236`.
- Best model 2+ rate: `36.33%` vs uniform `35.78%`.
- Best model 3+ rate: `9.54%` vs uniform `9.19%`.
- Calibration null trials: `500`.
- Frequency chi-square calibrated p: `0.0240`.
- Pair max-lift calibrated p: `0.2216`.
- Triple max-lift calibrated p: `0.5569`.
- Temporal lag calibrated p: `0.2555`.
- Drift JS calibrated p: `0.6587`.
- Runs max-z calibrated p: `0.1816`.
- Gap anomaly calibrated p: `0.2016`.
- Calendar effect calibrated p: `0.0379`.
- Candidate mode: `sampled`.
- Exact search used: `False`.
- Total combination space: `15380937`.
- Evaluated combinations: `6000`.
- Candidate count used by optimizer: `6000`.

## What This Means

If a signal appears before calibration but fails calibrated null testing, it is probably random noise.
If a calibrated signal appears but fails walk-forward validation, it is probably not reusable.
If it also improves out-of-sample metrics, the system may use it as a weak weighting signal. It is still not a guarantee.
Plain fingerprint summary: The calibrated null test did not find a strong reusable deviation from uniform randomness.

## Generated Tickets

01. [8, x, 13, y, 32, z, 37]

## Ticket Set Historical Fit

- Union coverage: `7/39`.
- Max pairwise overlap: `0`.
- Max number reuse: `1`.
- Pair/triple coverage count: `21` / `35`.
- Best-main average: `1.28`.
- 2+ rate: `38.22%`.
- 3+ rate: `13.38%`.

## Nested Predictive Validation

- Leakage guard: `tickets generated only from draws before the tested draw`.
- Test draws: `52`.
- Best-main average: `1.15`.
- 2+ rate: `40.38%`.
- 3+ rate: `3.85%`.
- Selected models: `{'hybrid_gap_pair': 49, 'gap_overdue': 3}`.

## Local qc25 Simulator

- Profile: `long`
- Backend: `aer_simulator`
- Qubits/layers/batch/shots: `25` / `4` / `4` / `8192`
- Repeat jobs: `1`
- Total shots: `32768`
- Encode values (pos 1–5 u kolu, 6–7 izvedene): `[5, 10, 15, 20, 25]`
- Top quantum combo (7): `[1, x, 7, y, 22, z, 24]` (p=0.0014)
Lokalni Aer simulator (qc25, 5×5 kubita). Kolo ne „razume” loto — audit/backtest je sloj razumevanja.

## Plain Warning

This is a statistical audit and risk-optimized ticket generator. It does not prove that lottery draws are predictable.

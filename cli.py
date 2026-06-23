from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from config import DEFAULT_COLUMNS, DEFAULT_CSV, RNG_SEED
from calibration import calibrated_randomness_fingerprint
from data import load_draws
from data_quality import validate_draw_history
from lotteries import LOTTERY
from quantum_profiles import LOCAL_QC25_QUBITS, resolve_quantum_profile
from simulator import run_profiled_sampling
from math_model import (
    backtest_summary,
    hit_distribution,
    number_scores,
    optimize_tickets,
    optimize_tickets_with_metadata,
    ticket_set_metrics,
)
from randomness import audit_pool_randomness, score_vector, walk_forward_models
from validation import nested_ticket_backtest


def prompt(value: str | None, label: str) -> str:
    if value:
        return value
    answer = input(f"{label}: ").strip()
    if not answer:
        raise SystemExit(f"{label} is required.")
    return answer


def _run_quantum_layer(
    args: argparse.Namespace,
    weights: list[float],
    output_path: str | None,
) -> tuple[list[int], dict]:
    output_counts = Path(output_path).with_suffix(".counts.json") if output_path else None
    profile = resolve_quantum_profile(args.quantum_profile, LOCAL_QC25_QUBITS)
    return run_profiled_sampling(
        qubits=args.qubits or profile["qubits"],
        layers=args.layers or profile["layers"],
        batch_circuits=args.batch_circuits or profile["batch_circuits"],
        shots=args.shots or profile["shots"],
        seed_weights=weights,
        output_counts=output_counts,
        repeat_jobs=args.repeat_jobs or profile["repeat_jobs"],
        profile=args.quantum_profile,
        csv_path=args.csv,
        seed=args.seed,
    )


def cmd_predict(args: argparse.Namespace) -> None:
    spec = LOTTERY
    target_date = prompt(args.date, "Draw date YYYY-MM-DD")
    try:
        date.fromisoformat(target_date)
    except ValueError as exc:
        raise SystemExit("--date must be YYYY-MM-DD") from exc

    draws = load_draws(spec, args.csv)
    if len(draws) < 30:
        raise SystemExit(f"Need at least 30 historical draws. Loaded {len(draws)}.")

    main_scores = number_scores(draws, spec.main)
    seed_bits: list[int] | None = None
    quantum_job = None
    if not args.no_quantum:
        seed_bits, quantum_job = _run_quantum_layer(args, main_scores.tolist(), args.output)

    tickets = optimize_tickets(spec, draws, columns=args.columns, seed_bits=seed_bits, seed=args.seed)
    history = backtest_summary(tickets, draws[-min(len(draws), args.backtest_draws) :])
    set_metrics = ticket_set_metrics(tickets, spec.main)
    baseline = hit_distribution(spec.main.maximum - spec.main.minimum + 1, spec.main.pick, args.columns)

    payload = {
        "warning": "Research/entertainment only. Lottery outcomes are random; no guarantee is made.",
        "lottery": spec.name,
        "draw_date": target_date,
        "columns": args.columns,
        "tickets": [ticket.as_dict() for ticket in tickets],
        "ticket_set_metrics": set_metrics,
        "history": history,
        "baseline": {
            "random_any_2_plus": baseline["any_2_plus"],
            "random_any_3_plus": baseline["any_3_plus"],
        },
        "source": {
            "draws_loaded": len(draws),
            "first_draw": str(draws[0].date),
            "last_draw": str(draws[-1].date),
            "note": spec.source_note,
        },
        "quantum": quantum_job,
    }

    text = human_report(payload)
    print(text)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".md").write_text(text, encoding="utf-8")
        print(f"\nWrote {out}")
        print(f"Wrote {out.with_suffix('.md')}")


def cmd_audit(args: argparse.Namespace) -> None:
    spec = LOTTERY
    target_date = prompt(args.date, "Draw date YYYY-MM-DD")
    try:
        date.fromisoformat(target_date)
    except ValueError as exc:
        raise SystemExit("--date must be YYYY-MM-DD") from exc

    draws = load_draws(spec, args.csv)
    if len(draws) < 30:
        raise SystemExit(f"Need at least 30 historical draws. Loaded {len(draws)}.")

    quality = validate_draw_history(draws, spec)
    columns = args.columns
    null_trials = args.null_trials if args.null_trials is not None else (2000 if args.deep_calibration else 500)
    randomness = audit_pool_randomness(draws, spec.main, "main")
    fingerprint = calibrated_randomness_fingerprint(
        draws,
        spec.main,
        "main",
        null_trials=null_trials,
        seed=args.seed,
    )
    walk = walk_forward_models(draws, spec, field="main", train_min=args.train_min)
    baseline = hit_distribution(spec.main.maximum - spec.main.minimum + 1, spec.main.pick, columns)

    best_model_scores = score_vector(draws, spec, "main", walk["best_model"])
    seed_bits = None
    quantum_job = None
    if not args.no_quantum:
        seed_bits, quantum_job = _run_quantum_layer(args, best_model_scores.tolist(), args.output)

    tickets, search_report = optimize_tickets_with_metadata(
        spec,
        draws,
        columns=columns,
        seed_bits=seed_bits,
        seed=args.seed,
        score_override=best_model_scores,
        candidate_mode=args.candidate_mode,
        exact_top_k=args.exact_top_k,
        max_exact_combinations=args.max_exact_combinations,
    )
    ticket_backtest = backtest_summary(tickets, draws[-min(len(draws), args.backtest_draws) :])
    nested_backtest = nested_ticket_backtest(
        spec,
        draws,
        columns=columns,
        train_min=args.train_min,
        seed=args.seed,
        candidate_pool=args.nested_candidate_pool,
        max_test_draws=args.nested_test_draws,
    )
    set_metrics = ticket_set_metrics(tickets, spec.main)
    payload = {
        "warning": "Research/entertainment only. Lottery outcomes are random; no guarantee is made.",
        "right_question": "Is there measurable non-random structure, and does it survive out-of-sample validation?",
        "lottery": spec.name,
        "draw_date": target_date,
        "columns": columns,
        "randomness_audit": randomness,
        "randomness_fingerprint": fingerprint,
        "calibration": fingerprint.get("calibration"),
        "data_quality": quality,
        "null_trials": null_trials,
        "walk_forward": walk,
        "selected_generation_model": walk["best_model"],
        "candidate_search": search_report,
        "tickets": [ticket.as_dict() for ticket in tickets],
        "ticket_set_metrics": set_metrics,
        "ticket_backtest": ticket_backtest,
        "nested_ticket_backtest": nested_backtest,
        "baseline": {
            "random_any_2_plus": baseline["any_2_plus"],
            "random_any_3_plus": baseline["any_3_plus"],
        },
        "source": {
            "draws_loaded": len(draws),
            "first_draw": str(draws[0].date),
            "last_draw": str(draws[-1].date),
            "note": spec.source_note,
        },
        "quantum": quantum_job,
    }
    text = audit_report(payload)
    print(text)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".md").write_text(text, encoding="utf-8")
        print(f"\nWrote {out}")
        print(f"Wrote {out.with_suffix('.md')}")


def quantum_report_rows(payload: dict) -> list[str]:
    q = payload.get("quantum")
    if not q:
        return []
    rows = [
        "",
        "## Local qc25 Simulator",
        "",
        f"- Profile: `{q.get('profile', 'custom')}`",
        f"- Backend: `{q.get('backend', 'aer_simulator')}`",
        f"- Qubits/layers/batch/shots: `{q.get('qubits')}` / `{q.get('layers')}` / `{q.get('batch_circuits')}` / `{q.get('shots_per_circuit')}`",
        f"- Repeat jobs: `{q.get('repeat_jobs', 1)}`",
        f"- Total shots: `{q.get('total_requested_shots', q.get('total_shots', ''))}`",
    ]
    if q.get("encode_values"):
        rows.append(f"- Encode values (pos 1–5 u kolu, 6–7 izvedene): `{q['encode_values']}`")
    top = q.get("top_combos") or []
    if top:
        rows.append(f"- Top quantum combo (7): `{top[0]['combo']}` (p={top[0]['probability']:.4f})")
    rows.append(
        "Lokalni Aer simulator (qc25, 5×5 kubita). Kolo ne „razume” loto — audit/backtest je sloj razumevanja."
    )
    return rows


def audit_report(payload: dict) -> str:
    audit = payload["randomness_audit"]
    fingerprint = payload["randomness_fingerprint"]
    walk = payload["walk_forward"]
    best = walk["models"][walk["best_model"]]
    uniform = walk["models"]["uniform"]
    calibration = fingerprint.get("calibration") or {}
    candidate_search = payload.get("candidate_search") or {}
    nested = payload.get("nested_ticket_backtest") or {}
    quality = payload.get("data_quality") or {}
    rows = [
        f"# {payload['lottery']} - Randomness Audit",
        "",
        f"Draw date: `{payload['draw_date']}`",
        f"Question: {payload['right_question']}",
        "",
        "## Short Answer",
        "",
        f"- Measured structure strength: `{audit['verdict']['signal_strength']}`.",
        f"- Randomness fingerprint: `{', '.join(fingerprint['randomness_type']['dominant_types'])}`.",
        f"- Randomness-test interpretation: {audit['verdict']['plain']}",
        f"- Out-of-sample verdict: {walk['verdict']['plain']}",
        f"- Best walk-forward model: `{walk['best_model']}`.",
        "",
        "## Evidence",
        "",
        f"- Draws loaded: `{payload['source']['draws_loaded']}` from `{payload['source']['first_draw']}` to `{payload['source']['last_draw']}`.",
        f"- Data quality usable: `{quality.get('usable', True)}`.",
        f"- Duplicate draw dates: `{len(quality.get('duplicate_dates', []))}`.",
        f"- Range/size/duplicate-number errors: `{len(quality.get('range_errors', []))}` / `{len(quality.get('size_errors', []))}` / `{len(quality.get('duplicate_number_errors', []))}`.",
        f"- Frequency max |z|: `{audit['frequency']['max_abs_z']:.2f}`.",
        f"- Normalized entropy: `{fingerprint['entropy']['normalized_entropy']:.4f}`.",
        f"- Top pair lift: `{audit['pair_lift']['max_lift']:.2f}`.",
        f"- Top triple lift: `{fingerprint['triple_lift']['max_lift']:.2f}`.",
        f"- Serial lag max delta: `{fingerprint['serial_dependence']['max_abs_lift_delta']:.2f}`.",
        f"- Distribution drift JS: `{fingerprint['drift']['js_divergence']:.4f}`.",
        f"- Best model mean hits: `{best['mean_hits']:.3f}` vs uniform `{uniform['mean_hits']:.3f}`.",
        f"- Best model 2+ rate: `{best['any_2_plus'] * 100:.2f}%` vs uniform `{uniform['any_2_plus'] * 100:.2f}%`.",
        f"- Best model 3+ rate: `{best['any_3_plus'] * 100:.2f}%` vs uniform `{uniform['any_3_plus'] * 100:.2f}%`.",
    ]
    if calibration:
        rows.extend(
            [
                f"- Calibration null trials: `{payload['null_trials']}`.",
                f"- Frequency chi-square calibrated p: `{calibration['frequency_chi_square']['empirical_p']:.4f}`.",
                f"- Pair max-lift calibrated p: `{calibration['pair_max_lift']['empirical_p']:.4f}`.",
                f"- Triple max-lift calibrated p: `{calibration['triple_max_lift']['empirical_p']:.4f}`.",
                f"- Temporal lag calibrated p: `{calibration['lag_max_delta']['empirical_p']:.4f}`.",
                f"- Drift JS calibrated p: `{calibration['drift_js']['empirical_p']:.4f}`.",
                f"- Runs max-z calibrated p: `{calibration['runs_max_abs_z']['empirical_p']:.4f}`.",
                f"- Gap anomaly calibrated p: `{calibration['gap_max_abs_lift']['empirical_p']:.4f}`.",
                f"- Calendar effect calibrated p: `{calibration['calendar_max_js']['empirical_p']:.4f}`.",
            ]
        )
    if candidate_search:
        rows.extend(
            [
                f"- Candidate mode: `{candidate_search['candidate_mode']}`.",
                f"- Exact search used: `{candidate_search['exact_used']}`.",
                f"- Total combination space: `{candidate_search['total_combinations']}`.",
                f"- Evaluated combinations: `{candidate_search['evaluated_combinations']}`.",
                f"- Candidate count used by optimizer: `{candidate_search['candidate_count']}`.",
            ]
        )
    rows.extend(
        [
            "",
            "## What This Means",
            "",
            "If a signal appears before calibration but fails calibrated null testing, it is probably random noise.",
            "If a calibrated signal appears but fails walk-forward validation, it is probably not reusable.",
            "If it also improves out-of-sample metrics, the system may use it as a weak weighting signal. It is still not a guarantee.",
            f"Plain fingerprint summary: {fingerprint['plain_language']['summary']}",
            "",
            "## Generated Tickets",
            "",
        ]
    )
    for idx, ticket in enumerate(payload["tickets"], start=1):
        rows.append(f"{idx:02d}. {ticket['main']}")
    rows.extend(
        [
            "",
            "## Ticket Set Historical Fit",
            "",
            f"- Union coverage: `{payload['ticket_set_metrics']['union_size']}/{payload['ticket_set_metrics']['pool_size']}`.",
            f"- Max pairwise overlap: `{payload['ticket_set_metrics']['max_pairwise_overlap']}`.",
            f"- Max number reuse: `{payload['ticket_set_metrics']['max_number_reuse']}`.",
            f"- Pair/triple coverage count: `{payload['ticket_set_metrics']['pair_coverage_count']}` / `{payload['ticket_set_metrics']['triple_coverage_count']}`.",
            f"- Best-main average: `{payload['ticket_backtest']['best_main_mean']:.2f}`.",
            f"- 2+ rate: `{payload['ticket_backtest']['any_2_plus'] * 100:.2f}%`.",
            f"- 3+ rate: `{payload['ticket_backtest']['any_3_plus'] * 100:.2f}%`.",
        ]
    )
    if nested:
        rows.extend(
            [
                "",
                "## Nested Predictive Validation",
                "",
                f"- Leakage guard: `{nested['leakage_guard']}`.",
                f"- Test draws: `{nested['test_draws']}`.",
                f"- Best-main average: `{nested.get('best_main_mean', 0.0):.2f}`.",
                f"- 2+ rate: `{nested.get('any_2_plus', 0.0) * 100:.2f}%`.",
                f"- 3+ rate: `{nested.get('any_3_plus', 0.0) * 100:.2f}%`.",
                f"- Selected models: `{nested.get('selected_models', {})}`.",
            ]
        )
    rows.extend(quantum_report_rows(payload))
    rows.extend(
        [
            "",
            "## Plain Warning",
            "",
            "This is a statistical audit and risk-optimized ticket generator. It does not prove that lottery draws are predictable.",
        ]
    )
    return "\n".join(rows) + "\n"


def human_report(payload: dict) -> str:
    rows = [
        f"# {payload['lottery']} - Quantum Lotto Lab",
        "",
        f"Draw date: `{payload['draw_date']}`",
        f"Columns: `{payload['columns']}`",
        "",
        "## Human-readable expectation",
        "",
        f"- Random baseline for at least one 2+ hit: `{payload['baseline']['random_any_2_plus'] * 100:.2f}%`.",
        f"- Random baseline for at least one 3+ hit: `{payload['baseline']['random_any_3_plus'] * 100:.2f}%`.",
    ]
    history = payload.get("history") or {}
    set_metrics = payload.get("ticket_set_metrics") or {}
    if history:
        rows.extend(
            [
                f"- Historical best-main average on the backtest window: `{history['best_main_mean']:.2f}`.",
                f"- Historical 2+ rate on the generated set: `{history['any_2_plus'] * 100:.2f}%`.",
                f"- Historical 3+ rate on the generated set: `{history['any_3_plus'] * 100:.2f}%`.",
            ]
        )
    if set_metrics:
        rows.extend(
            [
                f"- Union coverage: `{set_metrics['union_size']}/{set_metrics['pool_size']}`.",
                f"- Max pairwise overlap: `{set_metrics['max_pairwise_overlap']}`.",
            ]
        )
    rows.extend(quantum_report_rows(payload))
    rows.extend(["", "## Tickets", ""])
    for idx, ticket in enumerate(payload["tickets"], start=1):
        rows.append(f"{idx:02d}. {ticket['main']}")
    rows.extend(
        [
            "",
            "## Plain warning",
            "",
            "Istraživački / zabavni alat. Nema garancije dobitka.",
        ]
    )
    return "\n".join(rows) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantum-loto-lab-v2")
    sub = parser.add_subparsers(dest="cmd", required=True)

    audit = sub.add_parser(
        "audit", help="Loto Serbia 7/39 — audit, walk-forward, tiket."
    )
    audit.add_argument("--date", help="Draw date YYYY-MM-DD.")
    audit.add_argument("--csv", default=DEFAULT_CSV, help="Historical draw CSV.")
    audit.add_argument("--columns", type=int, default=DEFAULT_COLUMNS)
    audit.add_argument("--train-min", type=int, default=80)
    audit.add_argument("--backtest-draws", type=int, default=157)
    audit.add_argument("--nested-test-draws", type=int, default=52)
    audit.add_argument("--nested-candidate-pool", type=int, default=800)
    audit.add_argument(
        "--deep-calibration", action="store_true", help="Use more null simulations for randomness calibration."
    )
    audit.add_argument("--null-trials", type=int, default=None, help="Override null simulation count.")
    audit.add_argument("--candidate-mode", choices=["sampled", "exact"], default="sampled")
    audit.add_argument("--exact-top-k", type=int, default=10000)
    audit.add_argument("--max-exact-combinations", type=int, default=60000000)
    audit.add_argument("--seed", type=int, default=RNG_SEED)
    audit.add_argument(
        "--no-quantum",
        action="store_true",
        help="Isključi lokalni qc25 Aer simulator (podrazumevano je uključen).",
    )
    audit.add_argument("--quantum-profile", choices=["standard", "long", "deep", "extreme"], default="long")
    audit.add_argument("--repeat-jobs", type=int, default=None)
    audit.add_argument("--qubits", type=int, default=None)
    audit.add_argument("--layers", type=int, default=None)
    audit.add_argument("--batch-circuits", type=int, default=None)
    audit.add_argument("--shots", type=int, default=None)
    audit.add_argument("--output", default="audit.json")
    audit.set_defaults(func=cmd_audit)

    predict = sub.add_parser("predict", help="Loto Serbia 7/39 — generiši tiket.")
    predict.add_argument("--date", help="Draw date YYYY-MM-DD.")
    predict.add_argument("--csv", default=DEFAULT_CSV, help="Historical draw CSV.")
    predict.add_argument("--columns", type=int, default=DEFAULT_COLUMNS)
    predict.add_argument("--backtest-draws", type=int, default=157)
    predict.add_argument("--seed", type=int, default=RNG_SEED)
    predict.add_argument(
        "--no-quantum",
        action="store_true",
        help="Isključi lokalni qc25 Aer simulator (podrazumevano je uključen).",
    )
    predict.add_argument("--quantum-profile", choices=["standard", "long", "deep", "extreme"], default="long")
    predict.add_argument("--repeat-jobs", type=int, default=None)
    predict.add_argument("--qubits", type=int, default=None)
    predict.add_argument("--layers", type=int, default=None)
    predict.add_argument("--batch-circuits", type=int, default=None)
    predict.add_argument("--shots", type=int, default=None)
    predict.add_argument("--output", default="prediction.json")
    predict.set_defaults(func=cmd_predict)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()



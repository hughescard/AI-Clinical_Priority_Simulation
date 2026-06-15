from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.final_validation import (  # noqa: E402
    build_llm_usage_summary,
    evaluate_report_validity,
    normalize_csv_list,
    resolve_run_configuration,
    run_final_validation,
    temporary_llm_environment,
    validate_provider_configuration,
    write_final_validation_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run report-ready final experimental validation.")
    parser.add_argument("--quick", action="store_true", help="Use the quick validation preset.")
    parser.add_argument("--algorithms", help="Comma-separated algorithm ids.")
    parser.add_argument("--scenarios", help="Comma-separated scenario ids.")
    parser.add_argument("--data-source", default="synthetic", help="Dataset source id.")
    parser.add_argument("--seed-start", type=int, default=42, help="First replication seed.")
    parser.add_argument("--replications", type=int, help="Replications per scenario.")
    parser.add_argument("--duration-minutes", type=int, help="Simulation duration in minutes.")
    parser.add_argument(
        "--llm-provider",
        choices=["ollama", "mistral", "openai", "mock"],
        default=None,
        help="LLM provider used during enrichment. Defaults to ollama for final validation.",
    )
    parser.add_argument("--llm-fallback-order", help="Comma-separated fallback order.")
    parser.add_argument(
        "--llm-fallback-to-mock",
        dest="llm_fallback_to_mock",
        action="store_true",
        default=True,
        help="Append mock as the final fallback when possible.",
    )
    parser.add_argument(
        "--no-llm-fallback-to-mock",
        dest="llm_fallback_to_mock",
        action="store_false",
        help="Disable automatic mock fallback.",
    )
    parser.add_argument("--ollama-base-url", help="Override the Ollama base URL.")
    parser.add_argument("--ollama-model", help="Override the Ollama model name.")
    parser.add_argument("--ollama-timeout-seconds", type=float, help="Ollama request timeout.")
    parser.add_argument("--cache-path", help="Override the final validation cache file path.")
    parser.add_argument(
        "--fail-on-llm-fallback",
        action="store_true",
        help="Fail the run if any LLM fallback occurs.",
    )
    parser.add_argument(
        "--max-llm-fallbacks",
        type=int,
        help="Maximum allowed fallback count before the run is considered report-invalid.",
    )
    parser.add_argument(
        "--use-advanced-resources",
        action="store_true",
        help="Enable the advanced resource preset for final validation.",
    )
    parser.add_argument("--output-dir", help="Optional explicit output directory.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = resolve_run_configuration(
        quick_mode=args.quick,
        algorithms=normalize_csv_list(args.algorithms, []) if args.algorithms else None,
        scenarios=normalize_csv_list(args.scenarios, []) if args.scenarios else None,
        replications=args.replications,
        duration_minutes=args.duration_minutes,
        data_source=args.data_source,
        seed_start=args.seed_start,
        llm_provider=args.llm_provider,
        llm_fallback_order=normalize_csv_list(args.llm_fallback_order, []) if args.llm_fallback_order else None,
        llm_fallback_to_mock=args.llm_fallback_to_mock,
        ollama_base_url=args.ollama_base_url,
        ollama_model=args.ollama_model,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
        cache_path=args.cache_path,
        use_advanced_resources=args.use_advanced_resources,
        output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        fail_on_llm_fallback=args.fail_on_llm_fallback,
        max_llm_fallbacks=args.max_llm_fallbacks,
    )

    cache_reused = Path(config.cache_path).exists()
    if cache_reused:
        print(f"Warning: existing LLM cache will be reused: {config.cache_path}", file=sys.stderr)

    provider_validation = validate_provider_configuration(config)

    with temporary_llm_environment(config):
        run_payload = run_final_validation(config)

    llm_usage_summary = build_llm_usage_summary(run_payload["results_by_scenario"])
    validity = evaluate_report_validity(config, llm_usage_summary)

    written_files = write_final_validation_outputs(
        config,
        provider_validation=provider_validation,
        cache_reused=cache_reused,
        results_by_scenario=run_payload["results_by_scenario"],
        analyses_by_scenario=run_payload["analyses_by_scenario"],
        overall_algorithm_summary=run_payload["overall_algorithm_summary"],
    )

    print(f"Final validation outputs written to: {config.output_dir}")
    for filename, path in written_files.items():
        print(f"- {filename}: {path}")
    if config.fail_on_llm_fallback and not validity["report_valid_llm_run"]:
        print(
            "LLM fallback occurred during final validation. Results are not report-valid. "
            "Increase timeout, improve provider reliability, or rerun with a clean cache.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

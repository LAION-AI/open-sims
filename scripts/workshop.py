"""Explicit local entry point for finite content-authoring runs.

API keys are process-environment variables. This CLI never accepts a key value
as an argument and never automatically publishes a model's own work.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from living_world.workshop.library import Library
from living_world.workshop.providers import ApiProvider, DemoProvider, ProviderConfig, ProviderError
from living_world.workshop.runner import Runner, RunLimits, authoring_prompt
from living_world.workshop.schema import ContentPack, GapProposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "workshop.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Finite proposal -> implementation -> validation run")
    run.add_argument("--provider", choices=["demo", "openai", "gemini", "openrouter"], default="demo")
    run.add_argument("--model", help="Exact ID from the current provider model list")
    run.add_argument("--focus", action="append", required=True, help="One job per occurrence")
    run.add_argument("--workers", type=int, default=3)
    run.add_argument("--max-jobs", type=int, default=3)
    run.add_argument("--max-calls", type=int, default=6)
    run.add_argument("--max-output-tokens", type=int, default=4096)
    run.add_argument("--rpm", type=int, default=12)
    run.add_argument("--allow-external", action="store_true")
    models = sub.add_parser("models", help="Fetch available model IDs; no generation")
    models.add_argument("--provider", choices=["openai", "gemini", "openrouter"], required=True)
    models.add_argument("--allow-external", action="store_true")
    sub.add_parser("status")
    handoff = sub.add_parser("handoff", help="Prepare structured work for a Codex subscription session; does not spawn a CLI or access its credentials")
    handoff.add_argument("--focus", required=True)
    handoff.add_argument("--model", default="gpt-6-luna")
    submit = sub.add_parser("submit", help="Stage a data pack produced by a Codex/developer session")
    submit.add_argument("--job", required=True)
    submit.add_argument("--file", required=True)
    approve = sub.add_parser("publish", help="Explicitly approve a tested, visually inspected draft")
    approve.add_argument("--job", required=True)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--visual-reviewed", action="store_true")
    args = parser.parse_args()
    library = Library(args.database)
    try:
        if args.command == "run":
            limits = RunLimits(args.workers, args.max_jobs, args.max_calls, args.rpm)
            if len(args.focus) > args.max_jobs:
                raise ValueError("Too many --focus jobs for --max-jobs")
            if args.provider == "demo":
                provider = DemoProvider()
            else:
                if not args.model:
                    raise ValueError("An exact --model ID is required")
                provider = ApiProvider(ProviderConfig(args.provider, args.model, args.max_output_tokens), allow_external=args.allow_external)
                provider.verify_model()
            runner = Runner(library, provider, limits)
            try:
                result = runner.run(args.focus)
            except KeyboardInterrupt:
                runner.cancel()
                raise
            output = {"calls": result["calls"], "external": result["external"], "automatic_publication": False,
                      "jobs": [{k: job[k] for k in ("id", "focus", "state", "provider", "model", "error", "usage")} for job in result["jobs"]]}
        elif args.command == "models":
            output = ApiProvider(ProviderConfig(args.provider, "model-list"), allow_external=args.allow_external).models()
        elif args.command == "handoff":
            jid = library.create_job(args.focus, "codex-handoff", args.model)
            output = {"job": jid, "status": "queued_for_codex_session", "automatic_spawn": False,
                      "discovery_prompt": authoring_prompt(jid, args.focus, library.inventory()),
                      "proposal_schema": GapProposal.model_json_schema(), "content_schema": ContentPack.model_json_schema(),
                      "next": "Let the Codex coordinator delegate this brief, then submit the JSON pack through this CLI. Code changes require separate code review/tests."}
        elif args.command == "submit":
            source = Path(args.file)
            if source.stat().st_size > 1_000_000:
                raise ValueError("Pack file exceeds 1 MB")
            output = library.stage(args.job, json.loads(source.read_text(encoding="utf-8")))
        elif args.command == "publish":
            output = library.publish(args.job, args.reviewer, visual_reviewed=args.visual_reviewed)
        else:
            output = {"jobs": library.jobs(), "inventory": library.inventory()}
        print(json.dumps(output, ensure_ascii=True, indent=2))
    except (ValueError, ProviderError, OSError) as exc:
        parser.exit(2, str(exc)+"\n")
    finally:
        library.close()


if __name__ == "__main__":
    main()

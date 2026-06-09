#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.env import get_paths
from lib.feedback import append_feedback
from lib.pipeline import run_search
from lib.profile_store import init_profile, load_profile, profile_to_markdown, refine_profile
from lib.privacy import redact_profile
from lib.schema import FeedbackEvent, now_iso


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="last7days_rent.py",
        description="last7days = 帮助用户 7 天完成租房。本地 private profile + P0 房源信号聚合 CLI。",
    )
    subparsers = parser.add_subparsers(dest="command")

    profile = subparsers.add_parser("profile", help="管理本地 private profile")
    profile_sub = profile.add_subparsers(dest="profile_command")

    profile_init = profile_sub.add_parser("init", help="从公司/办公点/园区开始创建 profile")
    profile_init.add_argument("--company")
    profile_init.add_argument("--office-anchor")
    profile_init.add_argument("--address-hint")
    profile_init.add_argument("--city")
    profile_init.add_argument("--budget-min", type=int)
    profile_init.add_argument("--budget-max", type=int)
    profile_init.add_argument("--commute-minutes", type=int, default=35)
    profile_init.add_argument("--rental-mode", choices=["whole", "shared", "either"], default="either")

    profile_show = profile_sub.add_parser("show", help="显示本地 profile")
    profile_show.add_argument("--redacted", action="store_true", help="只显示脱敏摘要")

    profile_refine = profile_sub.add_parser("refine", help="用取舍题更新 profile 权重")
    profile_refine.add_argument("--decision", choices=["commute", "trust", "brand", "speed", "quiet"])
    profile_refine.add_argument("--weight", type=float)

    search = subparsers.add_parser("search", help="生成近 7 天候选短名单和 evidence package")
    search.add_argument("--fixture", action="store_true", help="使用离线 fixture，不请求网络")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--output-dir")

    feedback = subparsers.add_parser("feedback", help="记录用户反馈并影响下一轮排序")
    feedback.add_argument("--listing-id", required=True)
    feedback.add_argument(
        "--event-type",
        required=True,
        choices=[
            "rented",
            "expired",
            "too_far",
            "too_expensive",
            "lead_gen_suspected",
            "reject_agent",
            "untrusted_source",
            "real_viewable",
            "track",
        ],
    )
    feedback.add_argument("--source-id")
    feedback.add_argument("--notes")

    report = subparsers.add_parser("report", help="显示最近一次报告路径")
    report.add_argument("--latest", action="store_true", default=True)

    return parser


def cmd_profile(args: argparse.Namespace) -> int:
    if args.profile_command == "init":
        profile = init_profile(
            company=args.company,
            office_anchor=args.office_anchor,
            address_hint=args.address_hint,
            city=args.city,
            budget_min=args.budget_min,
            budget_max=args.budget_max,
            commute_minutes=args.commute_minutes,
            rental_mode=args.rental_mode,
        )
        print(profile_to_markdown(profile, redacted=True))
        return 0
    if args.profile_command == "show":
        profile = load_profile()
        if not profile:
            print("尚未找到本地 profile。请先运行 profile init，并从公司/办公点/园区开始建档。", file=sys.stderr)
            return 1
        data = redact_profile(profile.to_dict()) if args.redacted else profile.to_dict()
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.profile_command == "refine":
        profile = refine_profile(decision=args.decision, weight=args.weight)
        print(profile_to_markdown(profile, redacted=True))
        return 0
    print("缺少 profile 子命令。", file=sys.stderr)
    return 2


def cmd_search(args: argparse.Namespace) -> int:
    result = run_search(fixture=args.fixture, limit=args.limit, output_dir=args.output_dir)
    print(result.chat_summary)
    print(f"Markdown report: {result.markdown_path}")
    print(f"JSON evidence: {result.evidence_path}")
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    event = FeedbackEvent(
        event_id=f"fb-{now_iso()}",
        listing_id=args.listing_id,
        event_type=args.event_type,
        notes=args.notes,
        source_id=args.source_id,
    )
    path = append_feedback(event)
    print(f"Feedback saved: {path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    reports = sorted(get_paths().reports_dir.glob("*.md"))
    if not reports:
        print("尚未生成报告。请先运行 search --fixture。", file=sys.stderr)
        return 1
    print(reports[-1])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "profile":
        return cmd_profile(args)
    if args.command == "search":
        return cmd_search(args)
    if args.command == "feedback":
        return cmd_feedback(args)
    if args.command == "report":
        return cmd_report(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

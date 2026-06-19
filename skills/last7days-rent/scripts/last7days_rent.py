#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.agent_evidence import ingest_evidence_file, validate_evidence_file
from lib.anchor_pack import build_search_brief, load_anchor_pack
from lib.env import get_paths
from lib.feedback import append_feedback
from lib.listing_pool import load_pool
from lib.profile_store import init_profile, load_profile, profile_to_markdown, refine_profile
from lib.profile_wizard import answer_question, commit_wizard, inspect_wizard, next_question, start_wizard
from lib.privacy import redact_profile
from lib.render import write_html_report
from lib.schema import FeedbackEvent, now_iso
from lib.sources.registry import source_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="last7days_rent.py",
        description="last7days = 面向一线/新一线互联网大厂同学的办公点锚定租房助手。Agent-native profile wizard + runtime evidence + HTML 工作台。",
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
    profile_init.add_argument("--min-bedrooms", type=int, help="最少卧室数；一居室以上传 1，两居室以上传 2")

    profile_show = profile_sub.add_parser("show", help="显示本地 profile")
    profile_show.add_argument("--redacted", action="store_true", help="只显示脱敏摘要")

    profile_refine = profile_sub.add_parser("refine", help="用取舍题更新 profile 权重")
    profile_refine.add_argument("--decision", choices=["commute", "trust", "brand", "speed", "quiet"])
    profile_refine.add_argument("--weight", type=float)

    wizard = profile_sub.add_parser("wizard", help="问答式 profile wizard")
    wizard_sub = wizard.add_subparsers(dest="wizard_command")
    wizard_start = wizard_sub.add_parser("start", help="启动 profile wizard")
    wizard_start.add_argument("--scenario", default="beijing_jd_hq_anchor_example")
    wizard_start.add_argument("--goal-seed", help="例如：北京京东总部亦庄经海路，一居室，预算 6000 RMB 以内，通勤 45 分钟内")
    wizard_sub.add_parser("next", help="输出下一道问题 JSON")
    wizard_answer = wizard_sub.add_parser("answer", help="提交一道问题的答案")
    wizard_answer.add_argument("--question-id", required=True)
    wizard_answer.add_argument("--value", required=True)
    wizard_answer.add_argument("--answer-note")
    wizard_inspect = wizard_sub.add_parser("inspect", help="查看当前 wizard 状态")
    wizard_inspect.add_argument("--format", choices=["summary", "json"], default="summary")
    wizard_sub.add_parser("commit", help="写入 profile.json")

    plan = subparsers.add_parser("plan", help="根据 profile 和 Anchor Pack 生成 Agent search brief")
    plan.add_argument("--profile", help="profile JSON 路径；默认读取本地 profile")
    plan.add_argument("--anchor-id", default="beijing-jd-hq-yizhuang")
    plan.add_argument("--output")
    plan.add_argument("--explain", action="store_true")

    ingest = subparsers.add_parser("ingest", help="读取 Agent runtime evidence JSON 并合并 listing pool")
    ingest.add_argument("--evidence", required=True)
    ingest.add_argument("--output-pool")
    ingest.add_argument("--validate", action="store_true")

    render = subparsers.add_parser("render", help="把 listing pool 渲染为本地 HTML")
    render.add_argument("--pool")
    render.add_argument("--output")

    search = subparsers.add_parser(
        "search",
        help="兼容旧入口：请改用 plan -> runtime search -> ingest -> render",
        description="search 已不再执行旧式内置搜索；请使用 runtime-first 链路。",
    )

    sources = subparsers.add_parser("sources", help="查看可解析来源 registry")
    sources_sub = sources.add_subparsers(dest="sources_command")
    sources_sub.add_parser("list", help="列出 source registry")

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
            "contact_failed",
            "wrong_contact",
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
            min_bedrooms=args.min_bedrooms,
        )
        print(profile_to_markdown(profile, redacted=True))
        return 0
    if args.profile_command == "show":
        profile = load_profile()
        if not profile:
            print("尚未找到本地 profile。请先运行 profile wizard start，并从城市、公司/办公点/园区开始建档。", file=sys.stderr)
            return 1
        data = redact_profile(profile.to_dict()) if args.redacted else profile.to_dict()
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.profile_command == "refine":
        profile = refine_profile(decision=args.decision, weight=args.weight)
        print(profile_to_markdown(profile, redacted=True))
        return 0
    if args.profile_command == "wizard":
        return cmd_profile_wizard(args)
    print("缺少 profile 子命令。", file=sys.stderr)
    return 2


def cmd_profile_wizard(args: argparse.Namespace) -> int:
    if args.wizard_command == "start":
        state = start_wizard(scenario=args.scenario, goal_seed=args.goal_seed)
        print(json.dumps({"status": state["status"], "goal_seed": state["goal_seed"], "next": "profile wizard next"}, ensure_ascii=False, indent=2))
        return 0
    if args.wizard_command == "next":
        print(json.dumps(next_question(), ensure_ascii=False, indent=2))
        return 0
    if args.wizard_command == "answer":
        result = answer_question(args.question_id, args.value, answer_note=args.answer_note)
        print(result["message"])
        if result.get("next_question"):
            print(f"下一题：{result['next_question']}")
        else:
            print("profile 已确认，可以运行 profile wizard commit。")
        return 0
    if args.wizard_command == "inspect":
        state = inspect_wizard()
        if args.format == "json":
            print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            draft = state.get("draft_profile", {})
            housing = draft.get("housing_constraints", {})
            office = draft.get("office_anchor", {})
            print(f"办公锚点：{office.get('campus_name') or office.get('office_name') or '待确认'}")
            print(f"预算：{housing.get('budget_target', '待确认')} - {housing.get('budget_max', '待确认')}")
            print(f"户型：{housing.get('preferred_bedrooms', '待确认')}居")
            print(f"进度：{len(state.get('answered_question_ids', []))}/6")
        return 0
    if args.wizard_command == "commit":
        profile = commit_wizard()
        print(profile_to_markdown(profile, redacted=True))
        print(f"Profile saved: {get_paths().profile_json}")
        return 0
    print("缺少 wizard 子命令。", file=sys.stderr)
    return 2


def cmd_plan(args: argparse.Namespace) -> int:
    if args.profile:
        data = json.loads(Path(args.profile).expanduser().read_text(encoding="utf-8"))
    else:
        profile = load_profile()
        if not profile:
            print("尚未找到本地 profile。请先运行 profile wizard start/next/answer/commit。", file=sys.stderr)
            return 1
        data = profile.to_dict()
    brief = build_search_brief(data, load_anchor_pack(args.anchor_id))
    if args.explain:
        brief["explain"] = "Search brief 由 profile + anchor pack 派生；静态 fixture 不能替代真实 profile 字段。"
    output = json.dumps(brief, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).expanduser().write_text(output + "\n", encoding="utf-8")
        print(f"Search brief saved: {args.output}")
    else:
        print(output)
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    if args.validate:
        errors = validate_evidence_file(args.evidence)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        print(json.dumps({"ok": True}, ensure_ascii=False, indent=2))
        return 0
    try:
        pool, path = ingest_evidence_file(args.evidence, pool_path=args.output_pool)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Listing pool saved: {path}")
    print(f"Listings: {len(pool.get('listings', []))}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    paths = get_paths()
    pool_path = Path(args.pool).expanduser() if args.pool else paths.pools_dir / "jd-hq-beijing.listing-pool.json"
    if not pool_path.exists():
        print(f"找不到 listing pool: {pool_path}", file=sys.stderr)
        return 1
    pool = load_pool(pool_path)
    reports_dir = paths.reports_dir
    output = Path(args.output).expanduser() if args.output else reports_dir / "jd-hq-beijing-rentals.html"
    html_path = write_html_report(output.parent, output.stem, pool)
    print(f"HTML report: {html_path}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    print("search 已从默认路径移除。请使用：profile wizard -> plan -> Agent runtime search -> ingest -> render。", file=sys.stderr)
    return 2


def cmd_sources(args: argparse.Namespace) -> int:
    if args.sources_command == "list":
        print(json.dumps(source_registry(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print("缺少 sources 子命令。", file=sys.stderr)
    return 2


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
    reports = sorted(get_paths().reports_dir.glob("*.html"))
    if not reports:
        print("尚未生成 HTML 报告。请先运行 render。", file=sys.stderr)
        return 1
    print(reports[-1])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "profile":
            return cmd_profile(args)
        if args.command == "plan":
            return cmd_plan(args)
        if args.command == "ingest":
            return cmd_ingest(args)
        if args.command == "render":
            return cmd_render(args)
        if args.command == "search":
            return cmd_search(args)
        if args.command == "sources":
            return cmd_sources(args)
        if args.command == "feedback":
            return cmd_feedback(args)
        if args.command == "report":
            return cmd_report(args)
        parser.print_help()
        return 0
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

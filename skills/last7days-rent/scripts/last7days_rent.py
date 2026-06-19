#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.agent_evidence import ingest_evidence_data, ingest_evidence_file, load_evidence, validate_evidence, validate_evidence_file
from lib.anchor_pack import build_search_brief, load_anchor_pack
from lib.env import ensure_local_dirs, get_paths
from lib.feedback import append_feedback
from lib.listing_pool import load_pool, save_pool
from lib.profile_identity import (
    all_channel_matrix,
    attach_profile_to_pool,
    default_brief_path,
    default_pool_path,
    default_report_path,
    profile_hash,
    profile_slug,
    source_policy_matrix,
)
from lib.profile_store import init_profile, load_profile, profile_to_markdown, refine_profile
from lib.profile_wizard import answer_question, commit_wizard, inspect_wizard, next_question, start_wizard
from lib.privacy import redact_profile
from lib.render import write_html_report
from lib.schema import FeedbackEvent, now_iso
from lib.sources.registry import source_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="last7days_rent.py",
        description="last7days = 面向一线/新一线互联网大厂同学的 7 天快速租房助手。主路径：profile -> refresh -> personal HTML。",
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

    refresh = subparsers.add_parser("refresh", help="基于本地最新 profile 更新全渠道房源信息")
    refresh_mode = refresh.add_mutually_exclusive_group()
    refresh_mode.add_argument("--prepare", action="store_true", help="读取最新 profile，生成全渠道 search brief 和 runtime 执行说明")
    refresh_mode.add_argument("--evidence", help="校验并导入 Agent runtime evidence，然后自动渲染最新 HTML")
    refresh.add_argument("--anchor-id", default="beijing-jd-hq-yizhuang", help="当前可执行样例 Anchor Pack；未扩展前默认使用北京京东总部")
    refresh.add_argument("--output-brief", help="覆盖 refresh --prepare 的 search brief 输出路径")
    refresh.add_argument("--output-pool", help="覆盖 refresh --evidence 的 listing pool 输出路径")
    refresh.add_argument("--output-report", help="覆盖 refresh --evidence 的 HTML 输出路径")

    ingest = subparsers.add_parser("ingest", help="读取 Agent runtime evidence JSON 并合并 listing pool")
    ingest.add_argument("--evidence", required=True)
    ingest.add_argument("--output-pool")
    ingest.add_argument("--validate", action="store_true")

    render = subparsers.add_parser("render", help="把 listing pool 渲染为本地 HTML")
    render.add_argument("--pool")
    render.add_argument("--output")

    search = subparsers.add_parser(
        "search",
        help="兼容旧入口：请改用 refresh 主路径",
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
        next_action = "profile wizard commit" if state.get("current_step") == "done" else "profile wizard next"
        print(
            json.dumps(
                {
                    "status": state["status"],
                    "goal_seed": state["goal_seed"],
                    "current_step": state.get("current_step"),
                    "answered_question_ids": state.get("answered_question_ids", []),
                    "next": next_action,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
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


def cmd_refresh(args: argparse.Namespace) -> int:
    paths = ensure_local_dirs()
    profile = load_profile()
    if not profile:
        print("尚未找到本地 profile。请先运行 profile wizard start/answer/commit 建立本地租房 profile。", file=sys.stderr)
        return 1
    data = profile.to_dict()
    if args.evidence:
        return _refresh_with_evidence(args, paths, data)
    return _refresh_prepare(args, paths, data)


def _refresh_prepare(args: argparse.Namespace, paths, profile_data: dict) -> int:
    brief = build_search_brief(profile_data, load_anchor_pack(args.anchor_id))
    brief_path = Path(args.output_brief).expanduser() if args.output_brief else default_brief_path(paths, profile_data)
    brief["refresh_meta"] = {
        "profile_hash": profile_hash(profile_data),
        "profile_slug": profile_slug(profile_data),
        "profile_path": str(paths.profile_json),
        "brief_path": str(brief_path),
        "next_cli": f"python skills/last7days-rent/scripts/last7days_rent.py refresh --evidence <runtime-evidence.json>",
        "runtime_task": "按 search_batches 执行公开 web search/browser；把公开页面或用户授权输入整理为 evidence JSON。",
    }
    brief["all_channel_matrix"] = all_channel_matrix()
    brief["source_policy_matrix"] = source_policy_matrix()
    brief["runtime_audit_required_fields"] = [
        "query_context.brief_path 或 search_brief",
        "source_attempts",
        "attempted_queries",
        "execution_summary.queries_executed",
        "execution_summary.detail_pages_opened",
        "items[].source_id/source_name/source_domain",
        "items[].url_class",
        "items[].reject_reasons",
    ]
    brief["runtime_execution_instructions"] = [
        "按 search_batches 的 6 个 batch 顺序执行，不要只跑已熟悉渠道。",
        "每个 source 记录 attempted、blocked、zero_yield、not_attempted；页面阻断也要作为 rejected evidence 或 source_attempts 写回。",
        "公开平台、品牌公寓公开页、豆瓣/Wellcee 等公开社区可自动发现；小红书、公众号、微博、私域只按 policy 状态记录，不自动抓取。",
        "实际执行少于计划时，在 source_attempts 或 attempted_queries 中解释原因。",
    ]
    brief.setdefault("execution_contract", {})[
        "output"
    ] = "Agent runtime writes evidence JSON, then CLI validates and renders with refresh --evidence <runtime-evidence.json>."
    output = json.dumps(brief, ensure_ascii=False, indent=2, sort_keys=True)
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(output + "\n", encoding="utf-8")
    print(f"Search brief saved: {brief_path}")
    print("Next: use Agent runtime web search/browser or user-authorized links/screenshots, then run refresh --evidence <runtime-evidence.json>.")
    return 0


def _refresh_with_evidence(args: argparse.Namespace, paths, profile_data: dict) -> int:
    evidence_path = Path(args.evidence).expanduser()
    evidence = load_evidence(evidence_path)
    brief_path = default_brief_path(paths, profile_data)
    audit_warnings = _attach_latest_brief_if_missing(evidence, brief_path)
    audit_warnings.extend(_audit_warnings_for_evidence(evidence))
    errors = validate_evidence(evidence)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    pool_path = Path(args.output_pool).expanduser() if args.output_pool else default_pool_path(paths, profile_data)
    pool, pool_path = ingest_evidence_data(evidence, pool_path=pool_path)
    pool = attach_profile_to_pool(pool, profile_data, brief_path=brief_path if brief_path.exists() else None)
    pool.setdefault("pool_meta", {})["audit_warnings"] = audit_warnings
    pool.setdefault("execution_summary", {})["audit_warnings"] = audit_warnings
    save_pool(pool_path, pool)
    report_path = Path(args.output_report).expanduser() if args.output_report else default_report_path(paths, profile_data)
    html_path = write_html_report(report_path.parent, report_path.stem, pool)
    print(
        json.dumps(
            {
                "ok": True,
                "profile_hash": profile_hash(profile_data),
                "pool": str(pool_path),
                "report": str(html_path),
                "listings": len(pool.get("listings", [])),
                "rejected_items": len(pool.get("rejected_items", [])),
                "audit_warnings": audit_warnings,
                "coverage_summary": _coverage_summary(pool),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _attach_latest_brief_if_missing(evidence: dict, brief_path: Path) -> list[str]:
    warnings: list[str] = []
    if not isinstance(evidence.get("query_context"), dict):
        evidence["query_context"] = {}
    context = evidence["query_context"]
    has_search_brief = isinstance(evidence.get("search_brief"), dict)
    has_context_path = isinstance(context, dict) and bool(context.get("brief_path"))
    if has_search_brief or has_context_path:
        return warnings
    if brief_path.exists():
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        evidence["search_brief"] = brief
        context["brief_path"] = str(brief_path)
        warnings.append("evidence_missing_brief_context_attached_latest")
    else:
        warnings.append("evidence_missing_brief_context_no_latest_brief")
    return warnings


def _audit_warnings_for_evidence(evidence: dict) -> list[str]:
    warnings: list[str] = []
    if not isinstance(evidence.get("source_attempts"), list):
        warnings.append("missing_source_attempts_partial_audit")
    if not isinstance(evidence.get("attempted_queries"), list):
        warnings.append("missing_attempted_queries_partial_audit")
    execution = evidence.get("execution_summary")
    if not isinstance(execution, dict):
        warnings.append("missing_execution_summary_partial_audit")
    elif "detail_pages_opened" not in execution:
        warnings.append("missing_execution_summary_detail_pages_opened")
    return warnings


def _coverage_summary(pool: dict) -> dict:
    coverage = pool.get("source_coverage") if isinstance(pool.get("source_coverage"), dict) else {}
    return {
        "sources": coverage.get("source_count", 0),
        "planned": coverage.get("planned_source_count", 0),
        "attempted": coverage.get("attempted_source_count", 0),
        "effective": coverage.get("effective_source_count", 0),
        "blocked": coverage.get("blocked_source_count", 0),
        "not_attempted": coverage.get("not_attempted_source_count", 0),
    }


def cmd_ingest(args: argparse.Namespace) -> int:
    if args.validate:
        errors = validate_evidence_file(args.evidence)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1
        print(json.dumps({"ok": True}, ensure_ascii=False, indent=2))
        return 0
    try:
        profile = load_profile()
        profile_data = profile.to_dict() if profile else None
        default_pool = default_pool_path(get_paths(), profile_data) if profile_data and not args.output_pool else None
        pool, path = ingest_evidence_file(args.evidence, pool_path=args.output_pool or default_pool)
        if profile_data:
            pool = attach_profile_to_pool(pool, profile_data)
            save_pool(path, pool)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Listing pool saved: {path}")
    print(f"Listings: {len(pool.get('listings', []))}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    paths = get_paths()
    profile = load_profile()
    profile_data = profile.to_dict() if profile else None
    if args.pool:
        pool_path = Path(args.pool).expanduser()
    elif profile_data:
        pool_path = default_pool_path(paths, profile_data)
    else:
        pool_path = paths.pools_dir / "jd-hq-beijing.listing-pool.json"
    if not pool_path.exists():
        print(f"找不到 listing pool: {pool_path}", file=sys.stderr)
        return 1
    pool = load_pool(pool_path)
    if profile_data:
        pool = attach_profile_to_pool(pool, profile_data)
        save_pool(pool_path, pool)
    reports_dir = paths.reports_dir
    if args.output:
        output = Path(args.output).expanduser()
    elif profile_data:
        output = default_report_path(paths, profile_data)
    else:
        output = reports_dir / "jd-hq-beijing-rentals.html"
    html_path = write_html_report(output.parent, output.stem, pool)
    print(f"HTML report: {html_path}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    print("search 已从默认路径移除。请使用：profile wizard -> refresh --prepare -> Agent runtime search/browser -> refresh --evidence -> report。", file=sys.stderr)
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
        if args.command == "refresh":
            return cmd_refresh(args)
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

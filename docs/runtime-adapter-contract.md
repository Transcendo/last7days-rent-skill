# Runtime Adapter Contract

This contract lets `last7days-rent` run across Codex, Claude Code, OpenClaw, Hermes Agent, and unknown Agent runtimes without platform-specific branches in the core CLI.

## Principle

The skill does not detect runtime brand names. It only consumes:

- Runtime capabilities.
- Wizard answers.
- Search brief execution results.
- Evidence JSON.

`runtime_name` is debug metadata. Business logic must not branch on it.

## Capability Declaration

```json
{
  "runtime_meta": {
    "runtime_name": "unknown",
    "adapter_version": "0.1.0",
    "capabilities": [
      "interactive_choice",
      "web_search",
      "browser_open",
      "local_file_write",
      "structured_output"
    ]
  }
}
```

## Question Presentation

`profile wizard next` returns a single-choice JSON question. A runtime may render it with native UI. If it cannot, it renders Markdown choices.

The answer sent back to `profile wizard answer` must be the option `value`, or `A/B/C/D` when the runtime only supports text.

## Search Brief Execution

`plan` returns `profile_constraints`, `search_batches`, `run_budget`, `collection_rules`, and `execution_contract`.

The runtime should:

- Execute batches in order.
- Respect each batch's `queries`.
- Respect `max_results_per_query`.
- Open at most `max_detail_pages_total` pages.
- Stop when `target_main_recommendations` is reached, all batches are done, or consecutive batches add no main-list candidates.
- Keep blocked/login/captcha/app-wall URLs visible in evidence or execution summary. Do not bypass them.

If `web_search` is missing, ask the user for links, screenshots, or copied text.

Minimal search brief shape:

```json
{
  "anchor_id": "beijing-jd-hq-yizhuang",
  "profile_constraints": {
    "budget_target": 5000,
    "budget_max": 6000,
    "preferred_bedrooms": 1,
    "commute_minutes": 30,
    "source_strategy": "public_all_channels"
  },
  "search_batches": [
    {
      "batch_id": "p0_price_anchor",
      "intent": "price_anchor",
      "priority": 1,
      "sources": ["fang", "beike_lianjia", "lianjia_mobile_list", "wellcee"],
      "queries": [
        {
          "query_id": "p0_price_anchor-q01",
          "query": "site:fang.com/zf/bj 经海路 一居室 6000以内 租房 京东总部",
          "zone_id": "near_office",
          "expected_url_classes": ["platform_listing_detail", "platform_list_page"]
        }
      ],
      "max_results_per_query": 8,
      "max_detail_pages": 8
    }
  ],
  "run_budget": {
    "max_search_queries": 45,
    "max_detail_pages_total": 48,
    "target_main_recommendations": 5,
    "target_l1_or_better": 8
  },
  "collection_rules": {
    "l0_policy": "lead_pool_only",
    "main_recommendation_min_trust": "L1",
    "l1_requires_page_opened": true,
    "min_visible_core_fields_for_l1": 3
  }
}
```

## Evidence Handoff

The runtime must hand `ingest` a JSON object:

```json
{
  "runtime_meta": {},
  "query_context": {},
  "execution_summary": {
    "queries_executed": 0,
    "search_results_seen": 0,
    "detail_pages_opened": 0,
    "items_emitted": 0,
    "blocked_pages": 0
  },
  "source_attempts": [],
  "attempted_queries": [],
  "items": []
}
```

Each item must include:

- `evidence_id`
- `batch_id`
- `query_id`
- `query`
- `collected_via`
- `source_url`
- `source_name`
- `source_type`
- `page_opened`
- `title`
- `snippet`
- `raw_excerpt`
- `observed_at`
- `visible_fields`

Recommended fields:

- `canonical_url`
- `source_domain`
- `source_tier`
- `url_class`
- `listing_candidate_status`
- `normalized_fields`
- `field_confidence`
- `contact_path`
- `listing_status_hint`
- `runtime_actions`
- `reject_reasons`

Recommended audit fields outside `items`:

- `source_attempts`: one row per source with `source_id`, `attempted_queries`, optional `blocked_reasons` and `zero_yield_reasons`.
- `attempted_queries`: one row per executed query with `query_id`, `query`, `source_targets`, result counts, emitted item counts, and any zero-yield reason.

These fields let reports distinguish planned coverage, actual attempts, accepted evidence, and blocked/zero-yield sources. If omitted, the local report can only infer attempts from emitted items.

## Trust Rules

- L0: search result, snippet, copied text, or unopened page.
- L1: opened public page with at least three visible key fields.
- L2: two independent sources cross-confirm the same listing.
- L3: user contacted, scheduled, viewed, or explicitly confirmed status.

The same intermediary reposting across multiple platforms is not an independent source.

`candidate_l1` is a quality claim, not a platform default. Validation rejects fake L1 evidence unless all are true:

- `page_opened=true`.
- URL is public and not a login, captcha, app-wall, or search-result-only page.
- `source_url`, `observed_at`, and `raw_excerpt` are present.
- At least three visible core fields are present: price, area/layout, community/district, contact path, freshness.
- Raw phone numbers, WeChat ids, private group names, and poster/contact names are redacted.

L0 may appear in the HTML lead pool. It must not appear as verified or as a main recommendation.

## Validation

Run:

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest --evidence path/to/evidence.json --validate
```

Validation must return field-level errors for missing required fields or invalid URLs.

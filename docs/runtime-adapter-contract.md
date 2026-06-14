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

`plan` returns `search_batches`, `run_budget`, and `collection_rules`.

The runtime should:

- Execute batches in order.
- Respect `max_queries_per_batch`.
- Respect `max_results_per_query`.
- Open at most `max_detail_pages_total` pages.
- Stop when `target_accepted_listings` is reached, all batches are done, or consecutive batches add no main-list candidates.

If `web_search` is missing, ask the user for links, screenshots, or copied text.

## Evidence Handoff

The runtime must hand `ingest` a JSON object:

```json
{
  "runtime_meta": {},
  "query_context": {},
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
- `normalized_fields`
- `field_confidence`
- `contact_path`
- `listing_status_hint`

## Trust Rules

- L0: search result, snippet, copied text, or unopened page.
- L1: opened public page with at least three visible key fields.
- L2: two independent sources cross-confirm the same listing.
- L3: user contacted, scheduled, viewed, or explicitly confirmed status.

The same intermediary reposting across multiple platforms is not an independent source.

## Validation

Run:

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest --evidence path/to/evidence.json --validate
```

Validation must return field-level errors for missing required fields or invalid URLs.

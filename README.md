# SLIM Report Engine

## What this is

A Python-first reimplementation of a lab's report-generation logic.
Replaces (or sits beside) `modReportCreator.bas`, a ~2000-line VBA
macro that generates blank analysis report sheets from testing-request
workbooks. Reads a filled-in Testing Request workbook and writes the
blank analysis report workbook directly — no VBA involved at runtime.

See [DOMAIN_BRIEF.md](DOMAIN_BRIEF.md) for the actual business-logic
knowledge transfer (form layouts, database schema, report content
shapes, known quirks and bugs) — read that before writing any code
here, it exists specifically so this doesn't re-derive facts that
already cost real investigation time.

## Why Python, not VBA

VBA has no headless execution model — it only runs inside a live
Office host, so every test iteration is a real Excel COM round-trip
(5+ seconds to connect, no real debugger, no real stack traces).
Worse: distinct failure classes (a compile error, a missing COM
reference, an unhandled runtime error, a genuinely infinite loop) are
frequently indistinguishable from each other — all show up as "full
timeout, zero output." A prior effort (see the `Python-VBA-Bridge`
repo, a sibling of this one) built a harness to drive VBA from Python
for exactly this reason, and it helped, but iterating on business
logic *through* that loop is still slow and error-prone in ways pure
Python isn't.

## Architecture direction

- **Business logic lives in Python**: parsing rules (which cell means
  what, per form type), the customer/chemical/analysis resolution
  model, and the dispatch logic (which analysis maps to which report
  section, in what shape) — all pure computation, no Excel dependency
  until the final write. This mirrors a layer that already exists and
  is already isolated in the VBA prototype (Entity/Builder/dispatch
  classes with zero Excel/Range coupling) — it's a natural, not
  speculative, port target. The Customer/Chemical/Analysis/Element
  domain model and the Testing Request submission/sample parsing stack
  are not built here from scratch — they're pulled in from
  `slim-domain` (see below), which already has this as a tested Python
  port of the same VBA classes.
- **Python owns the write too**: `slim_report_engine/reporting/report_writer.py`
  writes the final report workbook directly via openpyxl — ported from
  `clsReportWriter.cls` + `modReportStyles.bas`. The original plan was
  to keep this VBA-side on the assumption that its styling logic was
  substantial, already-solved work worth reusing as-is; reading the
  actual source showed the opposite — `modReportStyles.bas` is a
  five-case named-style vocabulary (~30 lines), and `clsReportWriter`'s
  write loop is a bulk value write, a handful of sparse formula
  overrides, and one style-application call. Both were straightforward
  to port. No VBA bridge is needed: a lab machine just needs Python
  installed (see deployment, below) and runs the tool directly against
  an input workbook — there's no live COM server or subprocess protocol
  to design, since nothing needs to cross the VBA/Python boundary at
  runtime at all.

## Rollout plan

Prove the concept on one local machine first (this one). Once solid,
expand to 1-2 more, then lab-wide. Do NOT skip straight to lab-wide —
this hasn't been validated against the deployment problem yet (see
below).

## Known hard problem: deployment

Lab machines are not developer workstations — no assumption of a
maintained Python install or the discipline to keep one updated.
Leaning toward a frozen/bundled interpreter (PyInstaller or an
embeddable Python distribution) rather than requiring `pip install`
on each machine, with an explicit version check so a stale copy on
some machine fails loudly instead of silently drifting. Owning the
write directly removes the COM-server-registration concern this
section used to flag (there's no VBA/Python bridge left to register),
but a frozen/unsigned executable running on lab machines still merits
looping in IT/security before lab-wide rollout — PyInstaller builds in
particular are known to trip AV heuristics, worth clearing early rather
than discovering it during rollout.

## Explicitly out of scope for now

- The DM5 "routine" sample path (reads a schedule grid from the
  now-cloud-migrated Sample Login workbook) — deferred pending a
  separate conversation about that migration.
- Exotic/rare analysis types (organic-matrix, ICP-OES, and
  microwave-digestion element-panel variants; MS-Authentication anion
  rendering; most Titrations; all customer-specific edge cases).
- Wafer's anion-sheet variants (4/5/7 Anions) — not currently offered
  to customers, deprioritized on purpose.

## Relationship to `Python-VBA-Bridge`

That repo holds the real VBA source this project ports from (parsing
rules, resolution logic, report-content builders, and the writer/styles
this repo's `report_writer.py` was ported from) — the reference
implementation, not a runtime dependency. Since Python now owns the
write directly, nothing here calls back into VBA or Excel at runtime;
`Python-VBA-Bridge`'s own tooling (driving real VBA/Excel for
verification) isn't needed by this repo's own execution path anymore,
only as a place to go re-check a real template or macro behavior
against when porting something new.

## Relationship to `slim-domain`

`slim-domain` is a separate, shared package holding the
Customer/Chemical/Analysis/Element domain model (Entity → Repository →
Cache → Service) and the Testing Request submission/sample parsing
stack. It isn't specific to report generation — it's shared with at
least one other consuming app — so anything report-generation-specific
(the report section/row model, section builders) lives here instead,
consuming `slim-domain`'s entities as-is rather than duplicating or
modifying them.

## Setup

```bash
pip install -e ../slim-domain -e ".[dev]"
cp .env.template .env   # then edit if not using the SQLite default
python -m pytest
```

# PRECILAB Report Engine

## What this is

A Python-first reimplementation of PRECILAB's lab-report-generation
logic, with a thin VBA layer as the Excel front end. Replaces (or
sits beside) `modReportCreator.bas`, a ~2000-line VBA macro that
generates blank analysis report sheets from testing-request workbooks.

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
  section, in what shape) — all pure computation, no Excel dependency.
  This mirrors a layer that already exists and is already isolated in
  the VBA prototype (Entity/Builder/dispatch classes with zero
  Excel/Range coupling) — it's a natural, not speculative, port target.
- **VBA stays thin**: it owns the actual Excel object model writes
  (`Range`, styles, formulas, real-template row fidelity) and calls
  into the Python layer for "what to write," rather than deciding it
  itself. The already-built and template-verified VBA Writer layer
  (`clsReportWriter`, `modReportStyles`) is a candidate to keep as-is
  on this side of the boundary rather than re-derive.
- **Bridge mechanism**: not yet chosen. Leading candidate is a local
  Python COM server (`win32com.server`) VBA can `CreateObject`
  against; a subprocess + JSON-over-stdio fallback if COM server
  registration turns out to need admin rights we don't want to
  require on lab machines.

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
some machine fails loudly instead of silently drifting. IT/security
should be looped in before lab-wide rollout — a macro shelling out to
an executable or registering a COM server reads very differently to
AV/EDR than a plain macro, and that's worth clearing early.

## Explicitly out of scope for now

- The DM5 "routine" sample path (reads a schedule grid from the
  now-cloud-migrated Sample Login workbook) — deferred pending a
  separate conversation about that migration.
- Exotic/rare analysis types (organic-matrix, ICP-OES, and
  microwave-digestion element-panel variants; MS-Authentication anion
  rendering; most Titrations; all Qorvo/customer-specific edge cases).
- Wafer's anion-sheet variants (4/5/7 Anions) — not currently offered
  to customers, deprioritized on purpose.

## Relationship to `Python-VBA-Bridge`

That repo remains the tool for verifying VBA-side behavior actually
works in real Excel (template fidelity, formula computation, real
object-model quirks) — still needed for whatever stays VBA-side here.
This repo is not a replacement for it, just a different concern.

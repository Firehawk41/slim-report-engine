# SLIM Report Engine — Domain Brief

Everything below is verified against the real production files (real
Access schema dump, real intake forms' own dropdown lists, real
exported analysis catalog, real report templates via openpyxl) unless
explicitly marked "not yet verified." This is a knowledge-transfer
document, not a spec — it exists so a Python port doesn't have to
re-derive facts that already cost real investigation time.

## 1. What the program does

Generates blank lab-report worksheets from a filled-out "Testing
Request" intake workbook. A technician fills in a Testing Request form
(one of three kinds: Chemical, Water, Wafer) with one row per physical
sample and what analyses were requested. The macro reads that form,
resolves the customer/chemical/analyses against an Access database,
and produces one Excel sheet per output report — pre-formatted with
the right analyte list, headers, and footers, ready for a technician
to fill in results by hand later.

## 2. Input: the Testing Request workbook

Three request types, detected from cell `D3`'s literal title text:
`"Chemical Testing Request Form"`, `"Water Testing Request Form"`,
`"Wafer Testing Request Form"`. Each has a genuinely different column
layout — never assume one form's column position applies to another.

Real column map (1-based, confirmed from each real form's own file):

| Field                    | Chemical | Water | Wafer |
|--------------------------|----------|-------|-------|
| Date submitted           | I4       | I4    | G4    |
| Date received            | P5       | S5    | L5    |
| Invoice email main/CC    | N10/N11  | P10/P11 | J10/J11 |
| Credit card info         | I11      | J11   | G11   |
| Doc revision cell        | P49      | S51   | L45   |
| PO number (old revision) | I10      | J10   | —     |
| PO number (new revision) | H10      | H10   | G10   |
| Chemical name (per row)  | col 3    | fixed "Water" | col 4 |
| Analysis columns start   | col 4    | col 4 | col 5 |
| Additional Elements col  | col 5    | col 5 | col 6 |
| Processing time (per row)| col 11   | col 14 | col 9 |
| Requested time (per row) | col 13   | col 16 | — (not present) |
| Additional notes         | col 14   | col 17 | col 10 |

Fixed cells, same on all three form types:
`C10`=customer name, `C11`=address line 1, `C12`=address line 2,
`C13`=contact name, `C14` or `C15`=phone (version-dependent — check
`B14`/`B15` text to know which), `C15`=results-email main, `C17`=
results-email CC.

**Revision-letter versioning is real and must be handled**: the PO
number cell moved between form revisions. Read the revision letter out
of the doc-revision cell (pattern: find `"REV "` case-insensitively,
take the next character), compare against a threshold (`"T"` for
Chemical, `"I"` for Water — case-insensitive `>=` string comparison),
and pick old vs. new PO cell accordingly. Wafer has no old/new split.

**Sample table boundaries**: the header row usually says `"Sample ID"`
literally in column B (or C for Wafer) — if so, data starts 2 rows
below; there's a documented fallback (`FirstRow = 21` if that literal
isn't found) but it was never definitively confirmed as still
necessary — probably a legacy-form-version accommodation. The bottom
boundary is trickier: one real implementation searches for a literal
`"Examples"` row; another computes it as `(last non-empty cell in the
ID column) - 11` (a fixed footer-row count). These two heuristics
were NOT verified to always agree — pick one deliberately in the port,
don't assume they're interchangeable.

**A real, load-bearing gap found this session**: if a sample row's
Processing Time cell is blank, resolving it must either raise clearly
or default sensibly — the VBA implementation raises on an
unrecognized string with no graceful path, and every real form should
always have this filled in, but a defensive default is cheap insurance
in a fresh implementation.

## 3. Customer / Chemical / Analysis resolution

Three independent "form text → canonical database entity" resolution
processes, all following the same shape:

1. Look up the exact form text in a mapping table (fast path).
2. **On a miss**, prompt a human to either pick an existing entity or
   create a new one, then persist the new form-text mapping for next
   time (slow path). This is a real, load-bearing UI interaction in
   production — not just a cache-miss inconvenience. A Python port
   needs an equivalent human-resolution step somewhere, it can't just
   error out on an unrecognized customer/chemical name.

### Customer
Matched on THREE separate fields together: form customer name
(`C10`), address line 1 (`C11`), address line 2 (`C12`) — all must
match a stored mapping row for the fast path to fire. (An older,
still-live code path instead concatenates address line 1 + " " + line
2 into one field and matches that as a single string — the newer
model treats them as genuinely separate fields. Pick one; don't
silently support both without meaning to.)

### Chemical
Matched on ONE field: the form's chemical-matrix text (e.g. "Test Acid
Matrix" → chemical "Test Acid"). For Water, the "chemical" is the
hardcoded literal string `"Water"` — never actually read from a cell,
but it still needs a real chemical record in the database matching
that literal, because everything downstream expects a chemical ID.

### Analysis
This is the one genuinely surprising resolution: **each non-empty
cell's raw text, in every analysis column, is looked up as a form
name** — not the column header, the cell VALUE. A single form-name can
resolve to MULTIPLE analysis IDs at once (e.g. a "Premium package"
selection can expand to nine separate underlying analyses) — model
this as a one-to-many mapping from the start, not one-to-one. Also
check the additional-elements column's HEADER text (not just its
value) against the analysis table — a header can itself denote a
billable analysis ("Additional Elements" as its own line item).

The additional-elements column's VALUE (when present) is a separate,
freeform comma/space/period/newline-delimited list of element symbols
— split on all of `,`, `.`, ` `, and any newline variant, trim, and
resolve each token against the element catalog independently; symbols
that don't resolve should log a warning, not hard-fail (real forms
have typos here).

## 4. The real database shape

Real Access tables (structure confirmed via a DAO dump of the actual
production DB, not guessed) that this domain touches:

- `customers` (id, name, address fields...) + `form_customers` (a
  customer_id foreign key plus the exact form-text triple that maps to
  it — one-to-many, a customer can have many known form-text
  spellings)
- `chemicals` (id, name, prep-method fields) + `form_chemicals` (form
  text → chemical_id, one-to-many) + `ked_elements` (a chemical↔element
  junction table for a "KED" concept — read but not otherwise explored
  this session; the `chemicals` table also has a legacy unused
  `ked_elements` text column, superseded by this junction table, don't
  resurrect it)
- `analyses` (id, name, description) + `form_analyses` (id, form-text)
  + `form_analysis_mapping` (form_analysis_id ↔ database_analysis_id,
  genuinely many-to-many)
- `elements` (id, symbol, name) — the periodic-table catalog used for
  metals panels and additional-elements resolution
- `invoice_default_contacts` (customer_id, contact name/email,
  is_default, is_active) — a customer can have a standing default
  invoice contact that overrides whatever's typed on the form that day

**58 real analyses exist in production** (not invented for this
project — a real export exists, ask for it rather than inventing
placeholder names). They span far more than this session's VBA port
ever implemented: multiple element-panel variants (36/67/26/10/USP/
"List #2 36", plus organic-matrix, ICP-OES, microwave-digestion, and
"with reported replicates" sub-variants), anion panels (4/5/7, each
with a separate "+ MS Confirmation"/"+ Organic Anions" variant),
cation panels (6 Cations, NH4, Methylamines, and their combinations),
GBP, Silicon (Total/Dissolved), TOC, Alkalinity, Bacteria Count,
Conductivity, pH, Density, Liquid Particle Count, APHA Color, Assay,
Moisture (Karl Fischer), GC-FID, GC-MS, UV-Vis, Mixed Acid Assay,
various titrations, and more. A Python port should treat this catalog
as the real, authoritative scope — not the ~20 analyses this session's
VBA prototype got around to implementing.

## 5. Report content shapes (what actually gets built)

Every report sheet is built from a small set of recurring visual
"shapes." A useful mental model (and one worth keeping in a Python
port, whether or not the VBA class names survive): an ordered list of
**sections**, each section an ordered list of **rows**, each row a set
of (column → value) pairs plus a named visual style (bold+border
header, plain data row, etc.) and — for a couple of summary rows —
live formulas relative to the section's own row count, not hardcoded
absolute rows. The actual Excel-writing step (put these values in
these cells with these styles) is a separable concern from deciding
*which* sections/rows to build — keep that separation in the port,
it's what made this session's testing tractable at all.

Confirmed real shapes:

- **Metals/trace-element panel** (36/26/10/67/USP Elements, and a
  distinct "List #2 36 Elements" set — genuinely different elements,
  not a duplicate): a header, then one row per element (name + symbol,
  no other data yet since it's a *blank* report awaiting results),
  then AVERAGE/TOTAL summary rows with live formulas, then a footer.
  The 10/26/36-Elements selections in Chemical/Water render the
  *identical* 36-element list — only a summary label differs
  ("10 Tr.Elts" vs "36 Tr.Elts" etc.); don't build three separate
  element lists for what's really one list with three names.
- **Ion panel** (Anions/Cations/GBP): same header/row shape as metals
  but NO database backing (ions are fixed reference lists, not a
  business entity with an "add new one" workflow) and NO AVERAGE/TOTAL
  summary — the block just ends at its footer. Third results column is
  labeled "QL" here, "MDL" for metals.
- **Silicon**: up to three rows — "Silicon"/Si (Total), "Dissolved
  Silica"/SiO2 (Dissolved), and — ONLY when both are requested
  together — a third calculated "Colloidal Silica" row (the
  difference between the two). Uses the singular "Result"
  header text, not the plural used elsewhere — a genuine template
  inconsistency, not an error to "fix."
- **Single-parameter blocks** (TOC, Alkalinity, Bacteria Count, and
  several more): one row, simple header, footer naming the instrument/
  method. Combine freely with each other — no special cross-block
  logic needed when several appear on one sample.
- **Electrical Testing (Conductivity/pH)**: THREE distinct footer
  texts depending on whether Conductivity alone, pH alone, or both
  together were requested — not derivable generically, each real
  combination has its own real footer sentence.
- **Misc Analysis (pH/Density/LPC/APHA Color)**: independent atomic
  blocks that combine freely (no special-case combined footer, unlike
  Electrical). **Important unresolved ambiguity**: Misc Analysis's own
  "pH" block is a DIFFERENT block from Electrical Testing's "pH" block
  (confirmed both exist in the real template), but both resolve to the
  same database analysis named "pH" — resolving an analysis ID alone
  cannot tell you which block was actually requested. This needs a
  real design decision (e.g. carry the original form text alongside
  the resolved ID, not just the ID) — don't silently guess one.

## 6. Report-type-specific rules

### DM5 (a specific customer, two locations: DM5-N / DM5-S)
Not a generic Chemical/Water customer — it has its own dedicated
templates and sample-ID conventions. Two arrival paths:
- **Non-routine**: arrives via a normal Testing Request like any other
  sample — uses the SAME standard sample-ID format as everyone else
  (see §7).
- **Routine**: scheduled daily samples read off a schedule grid in a
  separate "Sample Login" workbook — **this workbook has been migrated
  to the cloud and is no longer directly readable the old way; this
  path is explicitly out of scope until that's resolved.**

DM5 chemicals fall into exactly 3 content shapes: a plain 36-element
metals panel (13 of the 21 known chemicals), a standalone "Assay"
block (5 chemicals — CSL9044C, W2000, W7808 across both locations),
and a composite shape combining the metals panel + a 4-anion block +
an embedded Assay block (3 chemicals — the "HF" family). The anion
order here (Chloride/Nitrate/Sulfate/Phosphate) is its OWN convention,
different from both the generic ion-panel order and Wafer's order —
three-plus distinct real orderings exist across this whole domain,
never assume one applies elsewhere.

Label quirks confirmed real and worth a deliberate decision (not
silently copied, not silently "fixed"): a couple of element names
carry trailing spaces and DM5-N's "W2000" displays as "2to1W2000"
while DM5-S's displays as plain "W2000"; DM5-S's "SurfEtch" displays
as "Surfetch" (lowercase). A downstream program (separate from this
macro) converts DM5 output to XML for a customer portal and depends
on exact output structure — DM5 output must match the real template
byte-for-byte, more strictly than other report types.

### Wafer
No "chemical" in the usual sense — a wafer's identity is (Reporting
Units, Wafer Size, Element/Anion-count selection, Processing Time).
Multiple physical samples sharing all four of those values land
**side by side as columns on ONE sheet** — one "Process Blank" column
plus one column per real sample, real samples in their original
request order. The bare "MDL"/"QL" summary header column sits at a
position that depends on how many sample columns are actually present
(confirmed formula: 6 + sample-count, derived from the real template's
own worst-case layout of 13 max sample columns with that header fixed
at column 19). Real element sets: standard 36, a genuinely different
"List #2 36" (drops 4 elements, adds 5 others), 67, and anion counts
4/5/7 (real but not currently offered to customers — low priority).
A genuine text quirk: the units note literally contains "10^10" written
as plain text "1010 " which gets stripped and replaced by superscripting
the trailing exponent character — but ONLY when Reporting Units is
exactly one specific string; a second real reporting-units option
exists that does NOT get this treatment, don't over-generalize the
condition.

### Chemical / Water
The generic, highest-volume path. **A real, deliberate, non-negotiable
convention difference**: Water's ion lists sort alphabetically;
Chemical's ion lists sort by real elution order off the analytical
column. Confirmed straight from the business owner as intentional
(customer familiarity, not worth the cost of standardizing) — never
unify these two orders.

## 7. Sample-ID string formats (multiple real, distinct conventions)

- **DM5 routine**: a predictable `mmddyy-Label-DM5N/DM5S[-Phase]`
  format, driven off the (currently out-of-scope) schedule grid.
- **DM5 non-routine, and generic Chemical/Water**: the SAME standard
  format — `mmddyy-ChemicalOrLabel-CustomerName-SampleID` — with a
  couple of substitution rules baked in (DM5-N's W2000 substitutes its
  display label; at least one other customer has its own display-name
  substitution specific to this string — real, but customer-specific;
  not enumerated here, see the internal-only version for specifics).
- **Wafer**: `mmddyy-WaferSize Wafers-CustomerName-<suffix>`, where
  `<suffix>` is the literal word "Process Blank" for the blank column
  or the raw sample-ID text the technician typed for a real sample
  column.

## 8. Known real bugs in the existing VBA (for reference — don't
   silently reproduce, but don't be surprised by them either if
   comparing against old output)

- A dictionary-building routine crashes on a genuinely empty query
  result set (an array-bounds error) — rare in practice since the
  queries involved are usually unfiltered whole-table joins, but real.
- A count-and-then-place pairing (used for the old Wafer sample-column
  mechanism) had a dead/no-op filter condition that silently
  over-counted matches — not relevant if a Python port builds exactly
  as many columns as it's given, which is the correct approach anyway.
- A couple of form-mapping "create new" writes in the newer VBA
  prototype's data layer target column names that don't match the
  real schema (would fail if ever executed) — a reminder to verify
  write paths against the real schema just as carefully as read paths.

## 9. Explicitly out of scope / deferred (by the business owner's own
   priority order, not an oversight)

1. DM5's routine schedule-grid path — blocked on the cloud migration
   of the source workbook, needs its own conversation first.
2. Exotic analysis variants: organic-matrix / ICP-OES / microwave-
   digestion / replicate-reporting element panels; anion "+MS
   Confirmation"/"+Organic Anions" variants; most Titrations; Assay/
   Moisture/GC-FID/GC-MS/UV-Vis/Mixed Acid Assay; Sn+2 Iodine
   Titration; Free Acid; TS-SLG.
3. Wafer's anion-count sheets (4/5/7 Anions) — real, but never
   actually offered to customers today.
4. All customer-specific bespoke report variants (e.g. one customer's
   proprietary titration specs with hardcoded numbers, another's
   special formatting rules) — real, deliberately last priority.

## 10. Where the real reference data lives

- A structural dump of the real Access schema (table/column/type/
  index, no row data) — ask for a fresh export if the new repo needs
  it; treat it as ground truth over any inferred schema.
- A real row-data export of `analyses`/`form_analyses`/
  `form_analysis_mapping` exists (58/98/~146 rows respectively) — get
  a copy rather than inventing placeholder analysis names, the real
  catalog has real gaps and quirks (e.g. one row has a real embedded
  multi-line value from what looks like a data-entry accident — parse
  with a real CSV/whatever-format reader, don't line-split naively).
- The real blank intake forms (Chemical/Water/Wafer) and real report
  templates (Chemical/Water generic, DM5-N, DM5-S, Wafer) exist as
  actual files — always read a form's own dropdown validation lists
  for real option values rather than guessing; every form checked this
  session turned out to differ from assumption in at least one detail.

"""Command-line entry point: reads a filled-in Testing Request workbook,
builds report content for every sample, writes the output workbook.

Designed to be invoked from a thin VBA trigger (per the project's
deployment decision — a familiar Excel button stays the UX for lab
technicians, but VBA no longer owns any content/formatting logic, just
the invocation). Reports success or failure via process exit code plus
an error message on stderr — the simplest contract a VBA
`WScript.Shell.Run(..., bWaitOnReturn:=True)` call can consume with no
custom protocol. See README.md's "Invocation from VBA" section for the
calling convention and an example VBA snippet.

EXIT CODES:
  0  success -- output workbook written, its path printed to stdout
  1  a recognized, actionable error (unresolved customer/chemical,
     unsupported analysis/DM5 chemical, empty submission, bad input
     file) -- the stderr message is meant to be shown to the
     technician directly, e.g. via MsgBox
  2  an unexpected error (a real bug, not a data problem) -- full
     traceback on stderr, not meant for a technician to action
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

import openpyxl

from infrastructure.database import make_engine, make_session
from slim_domain.domain.analysis.analysis_service import AnalysisService
from slim_domain.domain.chemical.chemical_service import ChemicalService
from slim_domain.domain.customer.customer_service import CustomerService
from slim_domain.domain.element.element_service import ElementService
from slim_domain.domain.tr.tr_form_input_resolver import (
    TRFormInputResolver,
    UnresolvedChemicalError,
    UnresolvedCustomerError,
)
from slim_domain.domain.tr.tr_submission_service import TRSubmissionService

from slim_report_engine.lab_identity import LAB_HEADER_LINES
from slim_report_engine.reporting import report_writer
from slim_report_engine.reporting.submission_report_builder import build_submission_sheets


class ReportEngineError(Exception):
    """A recognized, actionable failure. Message is safe to show a technician directly."""


def run(input_path: Path, output_path: Path, db_url: str | None = None) -> Path:
    engine = make_engine(db_url)
    session = make_session(engine)

    chemical_svc = ChemicalService(session)
    analysis_svc = AnalysisService(session)
    element_svc = ElementService(session)
    customer_svc = CustomerService(session)
    resolver = TRFormInputResolver(customer_svc, chemical_svc)
    submission_svc = TRSubmissionService(session, chemical_svc, analysis_svc, element_svc, resolver)

    try:
        submission = submission_svc.build_from_file(input_path)
    except (UnresolvedCustomerError, UnresolvedChemicalError) as e:
        raise ReportEngineError(
            f"{e} -- this needs to be added to the database before a report can be generated for it."
        ) from e
    except ValueError as e:
        raise ReportEngineError(f"could not read {input_path.name}: {e}") from e

    customer = customer_svc.load_customer(submission.customer_id)
    if customer is None:
        raise ReportEngineError(
            f"customer_id {submission.customer_id} was resolved during parsing but no longer loads "
            "-- this indicates a real bug, not a data problem."
        )

    try:
        sheets = build_submission_sheets(submission, customer, chemical_svc, analysis_svc, element_svc)
    except ValueError as e:
        raise ReportEngineError(str(e)) from e

    if not sheets:
        raise ReportEngineError(f"no samples found in {input_path.name} -- nothing to write.")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet in sheets:
        ws = wb.create_sheet(sheet.name)
        report_writer.apply_column_widths(ws, sheet.column_widths)
        report_writer.write_sections(ws, list(sheet.sections), start_row=1)
        report_writer.apply_header_footer(
            ws,
            center_header=sheet.header_title,
            customer_name=customer.name,
            customer_address_line1=customer.street_address,
            customer_address_line2=customer.city,
            lab_header_lines=LAB_HEADER_LINES,
        )
        for cell_address, value in sheet.extra_cell_stamps:
            ws[cell_address] = value

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a blank lab report workbook from a Testing Request workbook."
    )
    parser.add_argument("input", type=Path, help="path to the filled-in Testing Request .xlsx")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="output .xlsx path (default: <input>_report.xlsx, next to the input file)",
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="DB_URL override (default: .env's DB_URL, or sqlite:///report_engine.db)",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 1

    output_path = args.output or args.input.with_name(args.input.stem + "_report.xlsx")

    try:
        result_path = run(args.input, output_path, args.db)
    except ReportEngineError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception:
        traceback.print_exc()
        return 2

    print(str(result_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

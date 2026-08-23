"""
Clean Roll-Forward Planner & REAL_TARGET_BENCHMARK (Phase C2 / D3.2)
====================================================================
Location: foundation/tests/evaluation/rollforward_clean_planner_c2.py

Rebuilds Roll-Forward planning from independent evidence only.

Permitted inputs (enforced by `GroundTruthQuarantine`):
    FY2023 Local File          -- historical correspondence
    Master Template            -- target structure
    FY2024 FA&RPT              -- current source
    FY2024 Appendix I          -- current source

Forbidden input:
    HMV-26-Final Local File FY2024 (Ground Truth)

The quarantine is not a comment; it is an active guard that raises if the
Ground Truth path is opened while planning is in progress.

Every planning decision here is evidence-backed:

    table identity      -> multi-factor signature, never `tables[i]`
    historical state    -> position-free correspondence against FY2023
    source capability   -> content-derived dataset roles, never sheet names
    target state        -> derived from CURRENT SOURCE record counts only
    readiness           -> READY / BLOCKED / MANUAL_REVIEW, honestly

A BLOCKED case is a correct outcome. Nothing here optimises for READY count.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple
import warnings

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.mutation_precondition import (
    PostconditionHasher,
    TableAnatomy,
    TableAnatomyProfiler,
)
from applications.rollforward.semantic_binding import (
    BindingValidation,
    BindingVerdict,
    RowSemantics,
    SemanticBindingValidator,
    TargetRegionSchema,
    TargetSchemaDeriver,
)
from applications.rollforward.source_capability import (
    DatasetRole,
    SourceCapabilityProfiler,
    WorkbookCapabilityProfile,
)
from applications.rollforward.table_identity import (
    CorrespondenceConfidence,
    SemanticLabel,
    TableCorrespondence,
    TableCorrespondenceResolver,
    TableIdentityProfiler,
    TableIdentitySignature,
)

PATH_HIST = REPO_ROOT / "anonymize client/Demo files/Demo files/Compare LF/HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx"
PATH_TMPL = REPO_ROOT / "anonymize client/Demo files/Demo files/Compare LF/Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
PATH_FARPT = REPO_ROOT / "anonymize client/Demo files/Demo files/FA&RPTS & Appendix I/FA&RPTs/HMV-FA&RPT FY2024.xlsx"
PATH_APP1 = REPO_ROOT / "anonymize client/Demo files/Demo files/FA&RPTS & Appendix I/Appendix I/HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx"

# Named ONLY so the quarantine can refuse it. Never opened by this module.
PATH_GROUND_TRUTH_FORBIDDEN = REPO_ROOT / "anonymize client/Demo files/Demo files/Compare LF/HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx"

BENCHMARK_JSON = REPO_ROOT / "docs" / "evaluation" / "LocalFile_RollForward_Real_Target_Benchmark_v1_2026-08-23.json"


class GroundTruthContaminationError(RuntimeError):
    """Raised when planning attempts to read the Ground Truth document."""


class GroundTruthQuarantine:
    """Active guard: fails planning if the Ground Truth artifact is opened.

    Phase D3.1 finding P0-2 was undetectable because nothing enforced the
    evaluation-only rule. This makes the rule executable.
    """

    _armed = False
    _forbidden: Tuple[str, ...] = ()

    @classmethod
    def arm(cls, forbidden_paths: Sequence[Path]) -> None:
        cls._armed = True
        cls._forbidden = tuple(str(p.resolve()).lower() for p in forbidden_paths)

    @classmethod
    def disarm(cls) -> None:
        cls._armed = False
        cls._forbidden = ()

    @classmethod
    def check(cls, path: Path) -> None:
        if not cls._armed:
            return
        if str(Path(path).resolve()).lower() in cls._forbidden:
            raise GroundTruthContaminationError(
                f"Planning attempted to read the Ground Truth artifact '{Path(path).name}'. "
                "Ground Truth may only be loaded after profile, source-binding, manifest and "
                "mutation-plan freeze, execution and validation."
            )

    @classmethod
    def open_document(cls, path: Path) -> Document:
        cls.check(path)
        return Document(str(path))


class Readiness(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RecommendedStrategy(str, Enum):
    """Recommended only. None of the new operations is implemented."""
    INSERT_ROWS = "INSERT_ROWS"                          # implemented today
    REPLACE_DATA_REGION = "REPLACE_DATA_REGION"          # NOT IMPLEMENTED
    ACTIVATE_PLACEHOLDER = "ACTIVATE_PLACEHOLDER"        # NOT IMPLEMENTED
    UPDATE_CELLS = "UPDATE_CELLS"                        # NOT IMPLEMENTED
    DELETE_ROWS = "DELETE_ROWS"                          # NOT IMPLEMENTED, out of scope
    CARRY_FORWARD_STATIC = "CARRY_FORWARD_STATIC"
    NO_STRATEGY_DETERMINABLE = "NO_STRATEGY_DETERMINABLE"


IMPLEMENTED_STRATEGIES = {RecommendedStrategy.INSERT_ROWS, RecommendedStrategy.CARRY_FORWARD_STATIC}


@dataclass
class BenchmarkCase:
    """One template table, honestly classified from independent evidence."""
    case_id: str
    template_ordinal_display_only: int
    table_identity_key: str
    semantic_domain: str
    section_path: List[str]
    header_cells: List[str]

    historical_state: Dict[str, Any]
    template_state: Dict[str, Any]
    current_source_state: Dict[str, Any]
    target_state: Dict[str, Any]

    recommended_strategy: str
    strategy_is_implemented: bool
    readiness: str
    source_evidence: List[str]
    blocking_reasons: List[str]
    manual_review_reasons: List[str]
    real_postcondition_hash_current: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "template_ordinal_display_only": self.template_ordinal_display_only,
            "table_identity_key": self.table_identity_key,
            "semantic_domain": self.semantic_domain,
            "section_path": self.section_path,
            "header_cells": self.header_cells,
            "historical_state": self.historical_state,
            "template_state": self.template_state,
            "current_source_state": self.current_source_state,
            "target_state": self.target_state,
            "recommended_strategy": self.recommended_strategy,
            "strategy_is_implemented": self.strategy_is_implemented,
            "readiness": self.readiness,
            "source_evidence": self.source_evidence,
            "blocking_reasons": self.blocking_reasons,
            "manual_review_reasons": self.manual_review_reasons,
            "real_postcondition_hash_current": self.real_postcondition_hash_current,
        }


@dataclass
class CleanPlanResult:
    cases: List[BenchmarkCase]
    template_signatures: List[TableIdentitySignature]
    historical_signatures: List[TableIdentitySignature]
    correspondences: List[TableCorrespondence]
    workbooks: List[WorkbookCapabilityProfile]
    schemas: Dict[str, TargetRegionSchema]
    anatomies: Dict[int, TableAnatomy]
    bindings: Dict[str, BindingValidation]
    ground_truth_opened: bool = False


class CleanRollForwardPlanner:
    """Plans from FY2023 + Template + current sources. Never from Ground Truth."""

    @classmethod
    def plan(cls) -> CleanPlanResult:
        GroundTruthQuarantine.arm([PATH_GROUND_TRUTH_FORBIDDEN])
        try:
            return cls._plan_inner()
        finally:
            GroundTruthQuarantine.disarm()

    @classmethod
    def _plan_inner(cls) -> CleanPlanResult:
        # 1. Position-free identity for template and history.
        GroundTruthQuarantine.check(PATH_TMPL)
        GroundTruthQuarantine.check(PATH_HIST)
        tmpl_sigs = TableIdentityProfiler.profile_document(PATH_TMPL, "TEMPLATE")
        hist_sigs = TableIdentityProfiler.profile_document(PATH_HIST, "HIST_FY2023")
        correspondences = TableCorrespondenceResolver.correspond(tmpl_sigs, hist_sigs)
        corr_by_ordinal = {c.left.ordinal: c for c in correspondences}

        # 2. Content-derived capability of every current source.
        workbooks = [SourceCapabilityProfiler.profile_workbook(p) for p in (PATH_FARPT, PATH_APP1)]

        # 3. Target schema, anatomy and binding for every template table.
        doc = GroundTruthQuarantine.open_document(PATH_TMPL)
        schemas: Dict[str, TargetRegionSchema] = {}
        anatomies: Dict[int, TableAnatomy] = {}
        bindings: Dict[str, BindingValidation] = {}
        cases: List[BenchmarkCase] = []

        for sig in tmpl_sigs:
            case_id = f"rft-{sig.identity_key[:8]}"
            table = doc.tables[sig.ordinal]
            anatomy = TableAnatomyProfiler.profile(table, sig.ordinal)
            schema = TargetSchemaDeriver.derive(case_id, sig)
            schema.footer_row_idxs = anatomy.footer_row_idxs
            schema.placeholder_row_idxs = anatomy.placeholder_row_idxs
            binding = SemanticBindingValidator.validate(schema, workbooks)

            schemas[case_id] = schema
            anatomies[sig.ordinal] = anatomy
            bindings[case_id] = binding

            cases.append(cls._build_case(
                case_id=case_id, sig=sig, table=table, anatomy=anatomy,
                schema=schema, binding=binding,
                correspondence=corr_by_ordinal.get(sig.ordinal),
                workbooks=workbooks,
            ))

        return CleanPlanResult(
            cases=cases, template_signatures=tmpl_sigs, historical_signatures=hist_sigs,
            correspondences=correspondences, workbooks=workbooks, schemas=schemas,
            anatomies=anatomies, bindings=bindings, ground_truth_opened=False,
        )

    # ------------------------------------------------------------------

    @classmethod
    def _build_case(
        cls,
        case_id: str,
        sig: TableIdentitySignature,
        table: Any,
        anatomy: TableAnatomy,
        schema: TargetRegionSchema,
        binding: BindingValidation,
        correspondence: Optional[TableCorrespondence],
        workbooks: Sequence[WorkbookCapabilityProfile],
    ) -> BenchmarkCase:
        blocking: List[str] = []
        manual: List[str] = []

        # --- historical state (position-free correspondence) -------------
        if correspondence is None or correspondence.right is None:
            historical = {
                "correspondence": CorrespondenceConfidence.UNCORRELATED.value,
                "rows": None, "columns": None, "matched_factors": [],
                "note": ("No FY2023 table could be correlated to this template table by header "
                         "signature, semantic label, column schema or section context."),
            }
        else:
            r = correspondence.right
            historical = {
                "correspondence": correspondence.confidence.value,
                "score": round(correspondence.score, 4),
                "hist_ordinal_display_only": r.ordinal,
                "rows": r.row_count, "columns": r.column_count,
                "data_rows": max(r.row_count - 1, 0),
                "matched_factors": correspondence.matched_factors,
                "note": correspondence.rationale,
            }
            if correspondence.confidence == CorrespondenceConfidence.WEAK:
                manual.append(
                    f"Historical correspondence is WEAK (score {correspondence.score:.3f}); a "
                    f"reviewer must confirm that FY2023 table {r.ordinal} is the same table."
                )

        # --- template state ----------------------------------------------
        template_state = {
            "rows": anatomy.row_count,
            "columns": anatomy.column_count,
            "header_rows": anatomy.header_row_count,
            "data_region": list(anatomy.data_region),
            "footer_rows": list(anatomy.footer_row_idxs),
            "placeholder_rows": list(anatomy.placeholder_row_idxs),
            "row_semantics": schema.row_semantics.value,
            "column_roles": [{"index": c.index, "header": c.header, "role": c.role.value}
                             for c in schema.columns],
        }

        # --- current source state -----------------------------------------
        required = [r.value for r in schema.required_source_roles]
        source_records: Optional[int] = None
        if binding.verdict == BindingVerdict.VERIFIED:
            counts = []
            for wb in workbooks:
                for role in schema.required_source_roles:
                    for sheet in wb.sheets_with_role(role):
                        counts.append(sheet.record_count)
            source_records = max(counts) if counts else None

        current_source_state = {
            "required_dataset_roles": required,
            "binding_verdict": binding.verdict.value,
            "roles_found": [r.value for r in binding.roles_found],
            "candidate_sheets": binding.candidate_sheets,
            "source_record_count": source_records,
            "violations": binding.violations,
        }

        strategy = cls._recommend_strategy(schema, anatomy)
        needs_source = strategy not in (RecommendedStrategy.CARRY_FORWARD_STATIC,
                                        RecommendedStrategy.NO_STRATEGY_DETERMINABLE)

        if needs_source:
            if binding.verdict == BindingVerdict.MISSING_CURRENT_SOURCE:
                blocking.append(
                    f"MISSING_CURRENT_SOURCE: no bound workbook contains {required}. "
                    f"Content profiling of {sum(len(w.sheets) for w in workbooks)} sheets found "
                    f"no such dataset."
                )
            elif binding.verdict == BindingVerdict.INSUFFICIENT_EVIDENCE:
                blocking.append(
                    f"INSUFFICIENT_EVIDENCE: target domain {schema.expected_domain.value} declares "
                    f"no required source dataset role, so no source can be proven compatible."
                )
            elif binding.verdict != BindingVerdict.VERIFIED:
                blocking.append(f"{binding.verdict.value}: {'; '.join(binding.violations)}")

        # --- target state (derived from CURRENT SOURCE only) ---------------
        target_rows: Optional[int] = None
        target_basis = "UNKNOWABLE_FROM_APPROVED_INPUTS"
        if schema.row_semantics == RowSemantics.ENTITY_RECORD and source_records:
            target_rows = anatomy.header_row_count + source_records + len(anatomy.footer_row_idxs)
            target_basis = "header + current-source record count + footer"
        elif schema.row_semantics in (RowSemantics.STATISTIC, RowSemantics.KEY_VALUE):
            target_rows = anatomy.row_count
            target_basis = "fixed-shape table; row count does not change under roll-forward"

        target_state = {
            "rows": target_rows,
            "basis": target_basis,
            "derived_from_ground_truth": False,
            "note": ("Target row counts are derived from current-source record counts or from the "
                     "template's own fixed shape. The FY2024 Ground Truth was not consulted."),
        }

        # --- recommended strategy -------------------------------------------
        implemented = strategy in IMPLEMENTED_STRATEGIES

        if strategy == RecommendedStrategy.CARRY_FORWARD_STATIC:
            # A static region carries forward unchanged: execution is a verified
            # no-op, so it needs no current source. It is only trustworthy when
            # the FY2023 counterpart is EXACTLY the same table.
            exact = (correspondence is not None
                     and correspondence.confidence == CorrespondenceConfidence.EXACT
                     and correspondence.right is not None
                     and correspondence.right.row_count == anatomy.row_count
                     and correspondence.right.column_count == anatomy.column_count)
            if not exact:
                manual.append(
                    "Static carry-forward region whose FY2023 counterpart is not an exact "
                    "structural match; a reviewer must confirm the content still applies."
                )
        elif not implemented:
            blocking.append(
                f"STRATEGY_NOT_IMPLEMENTED: this region requires {strategy.value}, which the "
                f"D1 writeback engine does not provide (it implements INSERT_ROWS only). "
                f"Not implemented in this phase by instruction."
            )

        live_placeholders = [p for p in anatomy.placeholder_row_idxs
                             if p not in anatomy.footer_row_idxs]
        if live_placeholders and strategy == RecommendedStrategy.INSERT_ROWS:
            manual.append(
                f"Template rows {live_placeholders} are unfilled placeholders. Appending records "
                f"without consuming them would publish placeholders beside real data."
            )

        # --- readiness --------------------------------------------------------
        if blocking:
            readiness = Readiness.BLOCKED
        elif manual:
            readiness = Readiness.MANUAL_REVIEW
        else:
            readiness = Readiness.READY

        return BenchmarkCase(
            case_id=case_id,
            template_ordinal_display_only=sig.ordinal,
            table_identity_key=sig.identity_key,
            semantic_domain=schema.expected_domain.value,
            section_path=list(sig.section_path),
            header_cells=list(sig.header_cells),
            historical_state=historical,
            template_state=template_state,
            current_source_state=current_source_state,
            target_state=target_state,
            recommended_strategy=strategy.value,
            strategy_is_implemented=implemented,
            readiness=readiness.value,
            source_evidence=binding.evidence,
            blocking_reasons=blocking,
            manual_review_reasons=manual,
            real_postcondition_hash_current=PostconditionHasher.from_table(table),
        )

    @staticmethod
    def _recommend_strategy(schema: TargetRegionSchema, anatomy: TableAnatomy) -> RecommendedStrategy:
        rs = schema.row_semantics
        if rs == RowSemantics.STATISTIC:
            return RecommendedStrategy.ACTIVATE_PLACEHOLDER
        if rs == RowSemantics.KEY_VALUE:
            return RecommendedStrategy.ACTIVATE_PLACEHOLDER
        if rs == RowSemantics.ENTITY_RECORD:
            live = [p for p in anatomy.placeholder_row_idxs if p not in anatomy.footer_row_idxs]
            return RecommendedStrategy.REPLACE_DATA_REGION if live else RecommendedStrategy.INSERT_ROWS
        if rs == RowSemantics.CRITERION_STEP:
            return RecommendedStrategy.REPLACE_DATA_REGION
        if rs == RowSemantics.LINE_ITEM:
            return RecommendedStrategy.UPDATE_CELLS
        # Definitional / narrative tables carry forward unchanged. This is a
        # verified no-op, not an unsupported mutation.
        if schema.expected_domain in (SemanticLabel.PLI_FORMULA,
                                      SemanticLabel.FUNCTIONAL_ANALYSIS):
            return RecommendedStrategy.CARRY_FORWARD_STATIC
        if schema.expected_domain in (SemanticLabel.COVER_BLOCK,
                                      SemanticLabel.DOCUMENT_CHECKLIST):
            return RecommendedStrategy.UPDATE_CELLS
        return RecommendedStrategy.NO_STRATEGY_DETERMINABLE


# ============================================================================
# BENCHMARK ARTIFACT
# ============================================================================

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_benchmark(result: CleanPlanResult) -> Dict[str, Any]:
    counts: Dict[str, int] = {r.value: 0 for r in Readiness}
    for c in result.cases:
        counts[c.readiness] += 1

    return {
        "benchmark_id": "REAL_TARGET_BENCHMARK_V1",
        "phase": "C2 / D3.2 — Roll-Forward Planning Integrity Remediation",
        "generated_at": "2026-08-23",
        "planning_inputs": {
            "historical_fy2023": {"path": PATH_HIST.relative_to(REPO_ROOT).as_posix(),
                                  "sha256": _sha256(PATH_HIST)},
            "master_template": {"path": PATH_TMPL.relative_to(REPO_ROOT).as_posix(),
                                "sha256": _sha256(PATH_TMPL)},
            "current_source_farpt": {"path": PATH_FARPT.relative_to(REPO_ROOT).as_posix(),
                                     "sha256": _sha256(PATH_FARPT)},
            "current_source_appendix_i": {"path": PATH_APP1.relative_to(REPO_ROOT).as_posix(),
                                          "sha256": _sha256(PATH_APP1)},
        },
        "ground_truth": {
            "used_in_planning": False,
            "quarantine": "GroundTruthQuarantine armed for the whole planning run; "
                          "any attempt to open the Ground Truth raises GroundTruthContaminationError.",
            "document_not_opened": PATH_GROUND_TRUTH_FORBIDDEN.name,
        },
        "identity_policy": {
            "positional_table_identity_used": False,
            "method": "multi-factor position-free signature (section context, heading context, "
                      "header signature, column schema, row schema, merge topology, neighbouring "
                      "paragraphs, semantic labels)",
            "ordinal_role": "display and intra-document locator only",
            "resolver_proof": "TableCorrespondenceResolver.assert_no_positional_input()",
        },
        "source_capability": [wb.to_dict() for wb in result.workbooks],
        "readiness_summary": counts,
        "readiness_principle": "A BLOCKED case is a correct outcome. No case was promoted to "
                               "READY without independent evidence.",
        "cases": [c.to_dict() for c in result.cases],
    }


def run(write: bool = True) -> Tuple[CleanPlanResult, Dict[str, Any]]:
    result = CleanRollForwardPlanner.plan()
    benchmark = build_benchmark(result)
    if write:
        BENCHMARK_JSON.parent.mkdir(parents=True, exist_ok=True)
        BENCHMARK_JSON.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False), encoding="utf-8")
    return result, benchmark


if __name__ == "__main__":
    res, bm = run()
    print(f"[+] {BENCHMARK_JSON.relative_to(REPO_ROOT)}")
    print(f"\nReadiness: {bm['readiness_summary']}")
    print(f"\n{'ord':>3} {'domain':<24} {'tmpl':>5} {'hist':<14} {'src':>5} {'strategy':<22} {'readiness'}")
    for c in res.cases:
        h = c.historical_state
        hs = f"{h['correspondence'][:9]}:{h.get('rows') or '-'}"
        print(f"{c.template_ordinal_display_only:>3} {c.semantic_domain[:24]:<24} "
              f"{c.template_state['rows']:>5} {hs:<14} "
              f"{str(c.current_source_state['source_record_count'] or '-'):>5} "
              f"{c.recommended_strategy[:22]:<22} {c.readiness}")

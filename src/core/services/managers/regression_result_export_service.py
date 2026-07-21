"""Deterministic machine-readable exports for threshold comparisons."""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from numbers import Integral, Real
from typing import Any, Literal, TypeAlias, cast
from xml.etree import ElementTree as ET

import pandas as pd

RegressionResultFormat: TypeAlias = Literal["json", "junit"]

_FORMAT_NAME = "ring5.regression-results"
_SCHEMA_VERSION = 1
_RESULT_COLUMNS = (
    "metric",
    "baseline_name",
    "candidate_name",
    "baseline_value",
    "candidate_value",
    "absolute_change",
    "percentage_change",
    "direction",
    "threshold",
    "threshold_mode",
    "outcome",
)
_OUTCOMES = (
    "regression",
    "improvement",
    "unchanged",
    "missing_baseline",
    "missing_candidate",
    "missing_value",
    "not_comparable",
)
_INCOMPLETE_OUTCOMES = frozenset(
    {"missing_baseline", "missing_candidate", "missing_value", "not_comparable"}
)


class RegressionResultExportService:
    """Serialize comparison rows as versioned JSON or CI-friendly JUnit XML."""

    @classmethod
    def export(cls, comparison: pd.DataFrame, format: RegressionResultFormat) -> bytes:
        """Return a deterministic regression result document.

        Args:
            comparison: Long-form output from ``ComparisonService.compare``.
            format: ``"json"`` for the native schema or ``"junit"`` for JUnit XML.

        Returns:
            UTF-8 encoded JSON or XML with a trailing newline.

        Raises:
            ValueError: The format or comparison schema is invalid.
        """
        # [impl->req~ring5.automation.machine-readable-regression~1]
        if format not in ("json", "junit"):
            raise ValueError("format must be 'json' or 'junit'.")
        document = cls._document(comparison)
        if format == "json":
            return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        return cls._junit(document)

    @classmethod
    def _document(cls, comparison: pd.DataFrame) -> dict[str, object]:
        # [impl->req~ring5.automation.machine-readable-regression~1]
        if not isinstance(comparison, pd.DataFrame):
            raise ValueError("comparison must be a pandas DataFrame or ring5.Table.")
        missing = [column for column in _RESULT_COLUMNS if column not in comparison.columns]
        if missing:
            raise ValueError(f"Comparison result is missing columns: {', '.join(missing)}.")
        if comparison.empty:
            raise ValueError("Comparison result must contain at least one row.")

        baseline = cls._single_source(comparison["baseline_name"], "baseline_name")
        candidate = cls._single_source(comparison["candidate_name"], "candidate_name")
        key_columns = [column for column in comparison.columns if column not in _RESULT_COLUMNS]
        results = [cls._result(row, key_columns) for _, row in comparison.iterrows()]
        counts = {
            outcome: sum(result["outcome"] == outcome for result in results)
            for outcome in _OUTCOMES
        }
        return {
            "format": _FORMAT_NAME,
            "schema_version": _SCHEMA_VERSION,
            "sources": {"baseline": baseline, "candidate": candidate},
            "summary": {
                "total": len(results),
                "failures": counts["regression"],
                "incomplete": sum(counts[outcome] for outcome in _INCOMPLETE_OUTCOMES),
                "outcomes": counts,
            },
            "results": results,
        }

    @staticmethod
    def _single_source(values: pd.Series, field: str) -> str:
        sources = values.drop_duplicates().tolist()
        if len(sources) != 1 or not isinstance(sources[0], str) or not sources[0].strip():
            raise ValueError(f"Comparison result must contain one non-empty {field} value.")
        return sources[0].strip()

    @classmethod
    def _result(cls, row: pd.Series, key_columns: list[str]) -> dict[str, object]:
        metric = row["metric"]
        if not isinstance(metric, str) or not metric:
            raise ValueError("Comparison result contains an invalid metric.")
        direction = row["direction"]
        if direction not in ("higher", "lower"):
            raise ValueError("Comparison result contains an invalid direction.")
        threshold_mode = row["threshold_mode"]
        if threshold_mode not in ("percentage", "absolute"):
            raise ValueError("Comparison result contains an invalid threshold mode.")
        outcome = row["outcome"]
        if outcome not in _OUTCOMES:
            raise ValueError("Comparison result contains an invalid outcome.")

        threshold = cls._number(row["threshold"], "threshold", nullable=False)
        assert threshold is not None
        if threshold < 0:
            raise ValueError("Comparison result contains an invalid threshold.")
        return {
            "keys": {column: cls._key_value(row[column]) for column in key_columns},
            "metric": metric,
            "baseline_value": cls._number(row["baseline_value"], "baseline_value"),
            "candidate_value": cls._number(row["candidate_value"], "candidate_value"),
            "absolute_change": cls._number(row["absolute_change"], "absolute_change"),
            "percentage_change": cls._number(row["percentage_change"], "percentage_change"),
            "direction": direction,
            "threshold": threshold,
            "threshold_mode": threshold_mode,
            "outcome": outcome,
        }

    @staticmethod
    def _number(value: object, field: str, *, nullable: bool = True) -> float | int | None:
        if value is None or value is pd.NA:
            if nullable:
                return None
            raise ValueError(f"Comparison result contains an invalid {field}.")
        if isinstance(value, bool):
            raise ValueError(f"Comparison result contains an invalid {field}.")
        try:
            number = float(cast(Any, value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Comparison result contains an invalid {field}.") from exc
        if not math.isfinite(number):
            if nullable:
                return None
            raise ValueError(f"Comparison result contains an invalid {field}.")
        if isinstance(value, Integral):
            return int(value)
        return number

    @staticmethod
    def _key_value(value: object) -> object:
        if value is None or value is pd.NA:
            return None
        if isinstance(value, (str, bool)):
            return value
        if isinstance(value, Integral):
            return int(value)
        if isinstance(value, Real):
            number = float(value)
            return number if math.isfinite(number) else None
        if isinstance(value, (datetime, date, pd.Timestamp)):
            return value.isoformat()
        return str(value)

    @classmethod
    def _junit(cls, document: dict[str, object]) -> bytes:
        # [impl->req~ring5.automation.machine-readable-regression~1]
        sources = document["sources"]
        summary = document["summary"]
        results = document["results"]
        assert isinstance(sources, dict)
        assert isinstance(summary, dict)
        assert isinstance(results, list)
        baseline = str(sources["baseline"])
        candidate = str(sources["candidate"])

        suite = ET.Element(
            "testsuite",
            {
                "name": f"RING-5 regression: {baseline} to {candidate}",
                "tests": str(summary["total"]),
                "failures": str(summary["failures"]),
                "errors": "0",
                "skipped": str(summary["incomplete"]),
            },
        )
        properties = ET.SubElement(suite, "properties")
        cls._property(properties, "format", _FORMAT_NAME)
        cls._property(properties, "schema_version", _SCHEMA_VERSION)
        cls._property(properties, "baseline_source", baseline)
        cls._property(properties, "candidate_source", candidate)

        for result in results:
            assert isinstance(result, dict)
            keys = result["keys"]
            assert isinstance(keys, dict)
            labels = ", ".join(f"{key}={value}" for key, value in keys.items())
            name = str(result["metric"])
            if labels:
                name = f"{name} [{labels}]"
            case = ET.SubElement(
                suite,
                "testcase",
                {"classname": "ring5.regression", "name": name},
            )
            case_properties = ET.SubElement(case, "properties")
            for key, value in keys.items():
                cls._property(case_properties, f"key.{key}", value)
            for field in (
                "metric",
                "baseline_value",
                "candidate_value",
                "absolute_change",
                "percentage_change",
                "direction",
                "threshold",
                "threshold_mode",
                "outcome",
            ):
                cls._property(case_properties, field, result[field])

            outcome = result["outcome"]
            detail = (
                f"baseline={result['baseline_value']}, candidate={result['candidate_value']}, "
                f"threshold={result['threshold']} {result['threshold_mode']}"
            )
            if outcome == "regression":
                failure = ET.SubElement(
                    case,
                    "failure",
                    {"type": "regression", "message": "Regression threshold exceeded"},
                )
                failure.text = detail
            elif outcome in _INCOMPLETE_OUTCOMES:
                ET.SubElement(
                    case,
                    "skipped",
                    {"message": str(outcome).replace("_", " ").title()},
                )

        payload = cast(bytes, ET.tostring(suite, encoding="utf-8", xml_declaration=True))
        return payload + b"\n"

    @staticmethod
    def _property(parent: ET.Element, name: str, value: object) -> None:
        rendered = "null" if value is None else str(value)
        ET.SubElement(parent, "property", {"name": name, "value": rendered})

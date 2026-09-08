"""Primitive and envelope types for the frozen Foundation contract."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from .enums import ObjectType


JSON_SAFE_INTEGER = 9_007_199_254_740_991


def _valid_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def _valid_utc_timestamp(value: str) -> str:
    if not value.endswith("Z"):
        raise ValueError("timestamp must use the UTC Z suffix")
    datetime.fromisoformat(value[:-1] + "+00:00")
    return value


def _absolute_uri(value: str) -> str:
    if not urlsplit(value).scheme:
        raise ValueError("URI must be absolute")
    return value


ID = Annotated[
    StrictStr,
    Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
BusinessTargetID = Annotated[StrictStr, Field(pattern=r"^[A-Z][A-Z0-9_.]*$")]
SHA256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[StrictStr, Field(min_length=1)]
NullableText = Text | None
ExactText = StrictStr
DecimalString = Annotated[
    StrictStr, Field(pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
]
IntegerString = Annotated[StrictStr, Field(pattern=r"^-?(0|[1-9][0-9]*)$")]
LocalDate = Annotated[StrictStr, AfterValidator(_valid_date)]
Timestamp = Annotated[StrictStr, AfterValidator(_valid_utc_timestamp)]
URI = Annotated[StrictStr, AfterValidator(_absolute_uri)]
EvaluatorKey = ID
PositiveInt = Annotated[StrictInt, Field(ge=1, le=JSON_SAFE_INTEGER)]
NonNegativeInt = Annotated[StrictInt, Field(ge=0, le=JSON_SAFE_INTEGER)]
Bool = StrictBool


class StrictModel(BaseModel):
    """Closed immutable contract value."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
    )


class RecordBase(StrictModel):
    """Envelope for FoundationTask and reusable policy definitions."""

    schema_version: Literal["0.1.0"]
    object_type: ObjectType
    id: ID
    revision: PositiveInt
    created_at: Timestamp


class TaskOwnedRecord(RecordBase):
    """Envelope for records owned by one FoundationTask."""

    task_id: ID

"""Lineage Logger for tracking the source and target of data values."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class LineageRecord(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_anchor: str
    target_value: str
    source_file: str
    source_anchor: str
    confidence: float = 1.0


class LineageLogger:
    def __init__(self, log_dir: str = ".lineage_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"lineage_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        # Configure logging to console as well
        self.logger = logging.getLogger("LineageLogger")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def log_mapping(self, target_anchor: str, target_value: Any, source_file: str, source_anchor: str, confidence: float = 1.0) -> LineageRecord:
        record = LineageRecord(
            target_anchor=target_anchor,
            target_value=str(target_value),
            source_file=source_file,
            source_anchor=source_anchor,
            confidence=confidence
        )

        # Log to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        # Log to console
        self.logger.info(f"VALUE_PATCHED | Target: {target_anchor} | Value: {target_value} | Source: {source_file} @ {source_anchor}")

        return record


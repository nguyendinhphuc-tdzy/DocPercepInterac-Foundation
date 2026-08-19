"""Lineage Logger for tracking the source, target, and cryptographic fingerprints of data mutations."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field


class LineageRecord(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_anchor: str
    target_value_hash: str
    target_value: Optional[str] = None
    source_file: str
    source_anchor: str
    confidence: float = 1.0


class LineageLogger:
    """Logs data lineage records with cryptographic value fingerprints to prevent sensitive leaks in operational logs."""

    def __init__(self, log_dir: str = ".lineage_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"lineage_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        
        # Configure logging to console
        self.logger = logging.getLogger("LineageLogger")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def log_mapping(
        self,
        target_anchor: str,
        target_value: Any,
        source_file: str,
        source_anchor: str,
        confidence: float = 1.0,
        retain_full_value: bool = False,
    ) -> LineageRecord:
        val_str = str(target_value) if target_value is not None else ""
        val_hash = hashlib.sha256(val_str.encode("utf-8")).hexdigest()

        record = LineageRecord(
            target_anchor=target_anchor,
            target_value_hash=val_hash,
            target_value=val_str if retain_full_value else None,
            source_file=source_file,
            source_anchor=source_anchor,
            confidence=confidence,
        )

        # Log structured audit record to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        # Operational log NEVER prints plaintext sensitive document content to console
        self.logger.info(
            f"VALUE_PATCHED | Target: {target_anchor} | ValueHash: {val_hash[:16]} | Source: {source_file} @ {source_anchor}"
        )

        return record

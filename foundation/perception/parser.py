"""Parse capability: Docling singleton converts source files into DoclingDocument JSON.

This is the raw Substrate — element_classifier.py turns it into typed
FoundationElement/FoundationDocument objects.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)

# Pre-downloaded model artifacts (see foundation/models/README.md). If this
# directory exists, Docling loads models from here instead of Hugging Face
# Hub, so a clone + extract is enough to run fully offline.
LOCAL_ARTIFACTS_PATH = Path(__file__).resolve().parent.parent / "models"


@lru_cache(maxsize=1)
def get_converter() -> DocumentConverter:
    """Singleton DocumentConverter — loading Docling's models is expensive,
    so this must only happen once per process.

    OCR is disabled: fixture PDFs are born-digital (real text layer), not
    scanned images, and RapidOCR's torch backend roughly doubles peak memory
    on constrained dev machines for no benefit on this input type.
    """
    logger.info("Initializing Docling DocumentConverter (loading models)...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    # This dev machine has very little free RAM; keep peak memory low by
    # rendering pages at lower resolution, not retaining page images, and
    # processing one page at a time instead of batching.
    pipeline_options.images_scale = 1.0
    pipeline_options.generate_page_images = False
    pipeline_options.layout_batch_size = 1
    pipeline_options.table_batch_size = 1
    if LOCAL_ARTIFACTS_PATH.is_dir():
        pipeline_options.artifacts_path = LOCAL_ARTIFACTS_PATH
        logger.info("Using local model artifacts at %s", LOCAL_ARTIFACTS_PATH)
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    logger.info("Docling DocumentConverter ready.")
    return converter


def parse_document(path: str) -> dict:
    """Parse a source file into raw DoclingDocument JSON (the Substrate)."""
    converter = get_converter()
    result = converter.convert(path)
    return result.document.export_to_dict()

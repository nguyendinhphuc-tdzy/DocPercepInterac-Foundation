"""POST /api/agent/chat — AI Agent endpoint that proxies user requests
to the KPMG Workbench, enriched with Foundation document context.

Architecture note: this route calls applications/gpts/workbench_client.py
(application layer). It does NOT import from perception/, output/, or eval/.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.gpts.workbench_client import (  # noqa: E402
    WorkbenchApiError,
    WorkbenchConfigError,
    chat_completion,
)

agent_bp = Blueprint("agent", __name__)


def _build_system_prompt(context: dict) -> str:
    """Construct a system prompt that gives the model Foundation context."""
    parts = [
        "You are the Foundation Document Intelligence Agent.",
        "You help users analyze, compare, update, and extract information from enterprise documents.",
        "You have access to the following document context:",
    ]

    file_names = context.get("file_names", [])
    if file_names:
        parts.append(f"\nDocuments loaded: {', '.join(file_names)}")

    element_count = context.get("element_count", 0)
    if element_count > 0:
        parts.append(f"Total extracted elements: {element_count}")

    mapped_count = context.get("mapped_count", 0)
    if mapped_count > 0:
        parts.append(f"Mapped values: {mapped_count}")
        mapped_summary = context.get("mapped_summary", [])
        if mapped_summary:
            summary_lines = []
            for m in mapped_summary[:10]:
                summary_lines.append(
                    f"  - {m['target_anchor']}: {m['target_value']} "
                    f"(confidence: {m['confidence']:.0%})"
                )
            parts.append("Sample mapped values:\n" + "\n".join(summary_lines))

    parts.extend([
        "\nBe helpful, precise, and reference specific document elements when possible.",
        "If the user asks to modify document content, explain what changes would be needed.",
        "Always acknowledge which documents and elements are relevant to the user's question.",
    ])

    return "\n".join(parts)


@agent_bp.post("/api/agent/chat")
def agent_chat():
    body = request.get_json(silent=True) or {}
    message = body.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    context = body.get("context", {})
    process_id = body.get("process_id")

    system_prompt = _build_system_prompt(context)

    try:
        result = chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
        )
    except WorkbenchConfigError as exc:
        return jsonify({
            "error": str(exc),
            "status": "error",
            "response": f"Agent is not configured: {exc}",
            "run_id": None,
            "steps": [],
        }), 503
    except WorkbenchApiError as exc:
        return jsonify({
            "error": str(exc),
            "status": "error",
            "response": f"Workbench API error: {exc}",
            "run_id": None,
            "steps": [],
        }), 502
    except Exception as exc:
        return jsonify({
            "error": f"Unexpected error: {exc}",
            "status": "error",
            "response": f"An unexpected error occurred: {exc}",
            "run_id": None,
            "steps": [],
        }), 500

    run_id = str(uuid.uuid4())

    # Build step summary
    steps = [
        {"label": "Received request", "status": "done"},
    ]
    if context.get("file_names"):
        steps.append({
            "label": f"Read {len(context['file_names'])} documents",
            "status": "done",
        })
    if context.get("element_count", 0) > 0:
        steps.append({
            "label": f"Analyzed {context['element_count']} elements",
            "status": "done",
        })
    if context.get("mapped_count", 0) > 0:
        steps.append({
            "label": f"Referenced {context['mapped_count']} mapped values",
            "status": "done",
        })
    steps.append({"label": "Generated response", "status": "done"})

    return jsonify({
        "response": result.content,
        "status": "success",
        "run_id": run_id,
        "steps": steps,
    })

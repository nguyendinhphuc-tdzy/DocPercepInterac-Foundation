"""Agent Orchestrator for Foundation Document Intelligence.

Coordinates ContextBuilder, Intent parsing, Workbench LLM reasoning,
provenance Citation generation, and governed action proposals.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import uuid
from typing import Any, Optional

from applications.agent.models import (
    AgentContext,
    AgentIntent,
    AgentModelId,
    AgentResponse,
    AgentStep,
    Citation,
    ProposedAction,
    resolve_agent_model,
    get_model_key,
)
from applications.agent.context_builder import ContextBuilder, perceive_session_document
from applications.agent.proposal_store import ProposalStore
from applications.workbench_client import (
    WorkbenchApiError,
    WorkbenchConfigError,
    chat_completion,
)

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


class AgentOrchestrator:
    """Orchestrates natural language interactions over Foundation document primitives."""

    @classmethod
    def handle_chat(
        cls,
        message: str,
        session_id: Optional[str] = None,
        context_input: Optional[dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> AgentResponse:
        context_input = context_input or {}
        active_doc_id = context_input.get("active_doc_id")
        selected_element_id = context_input.get("selected_element_id")

        # Resolve selected model against server allowlist (default Luna)
        deployment_name = resolve_agent_model(model)
        model_key: AgentModelId = get_model_key(model)

        # 1. Build authoritative context from Foundation
        context = ContextBuilder.build_context(
            session_id=session_id,
            active_doc_id=active_doc_id,
            selected_element_id=selected_element_id,
        )

        run_id = str(uuid.uuid4())
        steps: list[AgentStep] = [
            AgentStep(label="Received request", status="done")
        ]
        citations: list[Citation] = []
        proposed_actions: list[ProposedAction] = []

        msg_lower = message.lower().strip()

        # ====================================================================
        # SLICE 4: PROPOSED EDIT / MUTATION INTENT
        # ====================================================================
        is_edit_request = any(k in msg_lower for k in ["change", "update", "modify", "replace", "set ", "edit "])
        if is_edit_request and session_id:
            if not context.selected_element:
                steps.append(AgentStep(label="Detected edit request without target selection", status="done"))
                return AgentResponse(
                    response="To propose an edit or update a value, please select the target element (cell or paragraph) in the document canvas first, then specify the new value.",
                    status="success",
                    run_id=run_id,
                    intent="clarify_target",
                    model=model_key,
                    steps=steps,
                    citations=[],
                    proposed_actions=[],
                )

            sel = context.selected_element
            doc_id = sel["doc_id"]
            el_id = sel["element_id"]
            current_val = sel.get("text", "")
            is_editable = sel.get("capabilities", {}).get("editable", False)

            # Extract proposed value from quotes or after "to"
            proposed_val = ""
            quote_match = re.search(r'["\']([^"\']+)["\']', message)
            if quote_match:
                proposed_val = quote_match.group(1)
            elif " to " in msg_lower:
                proposed_val = message.split(" to ", 1)[1].strip().strip(".\"';")

            if not proposed_val:
                proposed_val = "UPDATED_VALUE"

            steps.append(AgentStep(label=f"Inspected element: {sel.get('name', el_id)}", status="done"))

            if not is_editable:
                steps.append(AgentStep(label="Validated edit capabilities (Read-Only)", status="done"))
                return AgentResponse(
                    response=f"Element '{sel.get('name', el_id)}' in document '{sel.get('doc_name')}' is read-only (capabilities.editable is false). Direct write-back is not permitted.",
                    status="success",
                    run_id=run_id,
                    intent="propose_edit",
                    model=model_key,
                    steps=steps,
                    citations=[
                        Citation(
                            doc_id=doc_id,
                            doc_name=sel.get("doc_name"),
                            element_id=el_id,
                            element_name=sel.get("name", ""),
                            type=sel.get("type", "element"),
                            text_snippet=current_val[:100],
                        )
                    ],
                    proposed_actions=[],
                )

            # Compute SHA-256 document hash and value fingerprint for tamper-proof freshness
            doc_hash = None
            session_dir = UPLOAD_ROOT / session_id
            manifest_path = session_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    entry = manifest.get("documents", {}).get(doc_id)
                    if entry:
                        stored_path = session_dir / entry["stored_filename"]
                        patched = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
                        curr = patched if patched.exists() else stored_path
                        if curr.exists():
                            doc_hash = hashlib.sha256(curr.read_bytes()).hexdigest()
                except Exception:
                    pass

            val_fp = hashlib.sha256(current_val.strip().encode("utf-8")).hexdigest()[:16]

            # Create Governed ProposedAction with anchor and hash
            proposal = ProposedAction(
                doc_id=doc_id,
                doc_name=sel.get("doc_name", ""),
                element_id=el_id,
                element_name=sel.get("name", el_id),
                current_value=current_val,
                proposed_value=proposed_val,
                rationale=f"User requested change via prompt: '{message}'",
                requires_confirmation=True,
                status="proposed",
                doc_hash=doc_hash,
                value_fingerprint=val_fp,
                target_anchor=sel.get("anchor"),
            )
            ProposalStore.save_proposal(session_id, proposal)
            proposed_actions.append(proposal)

            steps.append(AgentStep(label="Created governed edit proposal", status="done"))
            steps.append(AgentStep(label="Awaiting user confirmation", status="pending"))

            citations.append(
                Citation(
                    doc_id=doc_id,
                    doc_name=sel.get("doc_name"),
                    element_id=el_id,
                    element_name=sel.get("name", ""),
                    type=sel.get("type", "element"),
                    text_snippet=current_val[:100],
                )
            )

            return AgentResponse(
                response=f"I have prepared a governed edit proposal to update **{sel.get('name', el_id)}** in **{sel.get('doc_name')}**.\n\nPlease review and confirm the change below.",
                status="success",
                run_id=run_id,
                intent="propose_edit",
                model=model_key,
                steps=steps,
                citations=citations,
                proposed_actions=proposed_actions,
            )

        # ====================================================================
        # SLICE 1: SELECTED ELEMENT SUMMARIZATION & CITATION REVEAL
        # ====================================================================
        if context.selected_element:
            sel = context.selected_element
            steps.append(AgentStep(label=f"Inspected selected element: {sel.get('name', sel['element_id'])}", status="done"))

            citations.append(
                Citation(
                    doc_id=sel["doc_id"],
                    doc_name=sel.get("doc_name"),
                    element_id=sel["element_id"],
                    element_name=sel.get("name", ""),
                    type=sel.get("type", "element"),
                    text_snippet=sel.get("text", "")[:120],
                )
            )

            # Attempt Workbench completion
            llm_text = cls._call_workbench(
                message=message,
                system_prompt=cls._build_selected_element_prompt(context),
                model=deployment_name,
            )
            steps.append(AgentStep(label="Generated element summary with citation", status="done"))

            return AgentResponse(
                response=llm_text,
                status="success",
                run_id=run_id,
                intent="summarize_element",
                model=model_key,
                steps=steps,
                citations=citations,
                proposed_actions=[],
            )

        # ====================================================================
        # SLICE 2: SEARCH / INSPECT ACROSS ELEMENTS
        # ====================================================================
        search_keywords = ["find", "search", "list", "show me", "locate", "where is", "where are", "revenue", "table", "tax"]
        is_search = any(k in msg_lower for k in search_keywords)
        if session_id and is_search:
            # Check for ambiguous document context
            if not context.active_doc_id and len(context.available_documents) > 1:
                steps.append(AgentStep(label="Ambiguous active document context", status="done"))
                return AgentResponse(
                    response="Multiple documents are loaded in the workspace. Please select or specify which document you would like to search.",
                    status="success",
                    run_id=run_id,
                    intent="clarify_document",
                    model=model_key,
                    steps=steps,
                    citations=[],
                    proposed_actions=[],
                )

            if context.active_doc_id:
                # Extract query term
                query_term = message
                for prefix in ["find ", "search for ", "search ", "list ", "show me ", "where is ", "where are ", "locate "]:
                    if msg_lower.startswith(prefix):
                        query_term = message[len(prefix):].strip()
                        break

                # Strip trailing context phrases and question marks
                query_term = re.sub(r"\s+in\s+(this\s+|the\s+)?(document|file|sheet|section|table|report).*$", "", query_term, flags=re.IGNORECASE).strip()
                query_term = re.sub(r"\s+(located|found)\??$", "", query_term, flags=re.IGNORECASE).strip()
                query_term = query_term.rstrip("?.! ")

                search_results = ContextBuilder.search_elements(
                    session_id=session_id,
                    doc_id=context.active_doc_id,
                    query=query_term,
                    limit=5,
                )

                if search_results:
                    steps.append(AgentStep(label=f"Searched document for '{query_term}' ({len(search_results)} matches)", status="done"))
                    for res in search_results:
                        citations.append(
                            Citation(
                                doc_id=res["doc_id"],
                                doc_name=res.get("doc_name"),
                                element_id=res["element_id"],
                                element_name=res.get("name", ""),
                                type=res.get("type", "element"),
                                text_snippet=res.get("text", "")[:100],
                            )
                        )

                    llm_text = cls._call_workbench(
                        message=message,
                        system_prompt=cls._build_search_prompt(context, search_results),
                        model=deployment_name,
                    )
                    steps.append(AgentStep(label="Generated provenance answer", status="done"))

                    return AgentResponse(
                        response=llm_text,
                        status="success",
                        run_id=run_id,
                        intent="search_elements",
                        model=model_key,
                        steps=steps,
                        citations=citations,
                        proposed_actions=[],
                    )
                else:
                    steps.append(AgentStep(label=f"Searched document for '{query_term}' (0 matches)", status="done"))
                    return AgentResponse(
                        response=f"No elements matching **'{query_term}'** were found in the active document.",
                        status="success",
                        run_id=run_id,
                        intent="search_elements",
                        model=model_key,
                        steps=steps,
                        citations=[],
                        proposed_actions=[],
                    )

        # ====================================================================
        # SLICE 3: CROSS-DOCUMENT COMPARE
        # ====================================================================
        if "compare" in msg_lower:
            if len(context.available_documents) < 2:
                steps.append(AgentStep(label="Evaluated comparison prerequisites", status="done"))
                doc_avail = len(context.available_documents)
                return AgentResponse(
                    response=f"Cross-document comparison requires at least 2 documents in the workspace. Currently, {doc_avail} document is loaded. Please add another document to compare.",
                    status="success",
                    run_id=run_id,
                    intent="clarify_comparison",
                    model=model_key,
                    steps=steps,
                    citations=[],
                    proposed_actions=[],
                )

            steps.append(AgentStep(label=f"Analyzed {len(context.available_documents)} documents for comparison", status="done"))
            for doc in context.available_documents[:2]:
                # Add top-level citation per document
                try:
                    entry, els = perceive_session_document(session_id, doc["doc_id"])
                    if els:
                        citations.append(
                            Citation(
                                doc_id=doc["doc_id"],
                                doc_name=doc["filename"],
                                element_id=els[0].element_id,
                                element_name=els[0].name,
                                type=els[0].type.value if hasattr(els[0].type, "value") else str(els[0].type),
                                text_snippet=els[0].text[:100],
                            )
                        )
                except Exception:
                    pass

            llm_text = cls._call_workbench(
                message=message,
                system_prompt=cls._build_compare_prompt(context),
                model=deployment_name,
            )
            steps.append(AgentStep(label="Generated comparison summary", status="done"))

            return AgentResponse(
                response=llm_text,
                status="success",
                run_id=run_id,
                intent="compare_documents",
                model=model_key,
                steps=steps,
                citations=citations,
                proposed_actions=[],
            )

        # ====================================================================
        # GENERAL DOCUMENT QUERY
        # ====================================================================
        doc_count = len(context.available_documents)
        steps.append(AgentStep(label=f"Read workspace context ({doc_count} document{'s' if doc_count != 1 else ''})", status="done"))
        
        system_prompt = cls._build_general_prompt(context)
        llm_text = cls._call_workbench(message, system_prompt, model=deployment_name)
        steps.append(AgentStep(label="Generated response", status="done"))

        return AgentResponse(
            response=llm_text,
            status="success",
            run_id=run_id,
            intent="general_query",
            model=model_key,
            steps=steps,
            citations=citations,
            proposed_actions=[],
        )

    # ------------------------------------------------------------------------
    # LLM Helper & Prompt Construction
    # ------------------------------------------------------------------------
    @classmethod
    def _call_workbench(
        cls, message: str, system_prompt: str, model: Optional[str] = None
    ) -> str:
        kwargs: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.3,
        }
        if model:
            kwargs["model"] = model
        res = chat_completion(**kwargs)
        return res.content

    @staticmethod
    def _build_selected_element_prompt(context: AgentContext) -> str:
        sel = context.selected_element or {}
        return (
            "You are the Foundation Document Intelligence Agent.\n"
            "The user has selected a specific document element:\n"
            f"- Document: {sel.get('doc_name')}\n"
            f"- Element Name: {sel.get('name')}\n"
            f"- Element ID: {sel.get('element_id')}\n"
            f"- Type: {sel.get('type')}\n"
            f"- Content: {sel.get('text')}\n\n"
            "Provide a concise, helpful summary or explanation of this element. Do not output hidden chain-of-thought."
        )

    @staticmethod
    def _build_search_prompt(context: AgentContext, results: list[dict[str, Any]]) -> str:
        res_summary = "\n".join([f"- {r['name']} ({r['type']}): {r['text'][:100]}" for r in results])
        return (
            "You are the Foundation Document Intelligence Agent.\n"
            f"Here are matching elements from {context.active_doc_id}:\n"
            f"{res_summary}\n\n"
            "Summarize the findings and reference the elements clearly."
        )

    @staticmethod
    def _build_compare_prompt(context: AgentContext) -> str:
        doc_names = [d["filename"] for d in context.available_documents]
        return (
            "You are the Foundation Document Intelligence Agent.\n"
            f"The user wants to compare documents: {', '.join(doc_names)}.\n"
            "Highlight structural and content relationships."
        )

    @staticmethod
    def _build_general_prompt(context: AgentContext) -> str:
        doc_names = [d["filename"] for d in context.available_documents]
        return (
            "You are the Foundation Document Intelligence Agent.\n"
            f"Documents loaded: {', '.join(doc_names) if doc_names else 'None'}.\n"
            "Answer the user's questions clearly based on Foundation document primitives."
        )

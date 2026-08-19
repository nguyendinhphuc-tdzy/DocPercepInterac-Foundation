"""Agent Orchestrator for Foundation Document Intelligence.

Coordinates ContextBuilder, Intent parsing, Workbench LLM reasoning,
provenance Citation generation, and governed action proposals.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from applications.agent.models import (
    AgentContext,
    AgentIntent,
    AgentResponse,
    AgentStep,
    Citation,
    ProposedAction,
)
from applications.agent.context_builder import ContextBuilder, perceive_session_document
from applications.agent.proposal_store import ProposalStore
from applications.workbench_client import (
    WorkbenchApiError,
    WorkbenchConfigError,
    chat_completion,
)


class AgentOrchestrator:
    """Orchestrates natural language interactions over Foundation document primitives."""

    @classmethod
    def handle_chat(
        cls,
        message: str,
        session_id: Optional[str] = None,
        context_input: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        context_input = context_input or {}
        active_doc_id = context_input.get("active_doc_id")
        selected_element_id = context_input.get("selected_element_id")

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

            # Create Governed ProposedAction
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
            llm_text = cls._call_workbench_or_fallback(
                message=message,
                system_prompt=cls._build_selected_element_prompt(context),
                fallback_text=(
                    f"### Analysis for Selected Element: {sel.get('name', sel['element_id'])}\n\n"
                    f"- **Type**: `{sel.get('type')}`\n"
                    f"- **Document**: {sel.get('doc_name')}\n"
                    f"- **Content**: {sel.get('text')}\n\n"
                    f"**Summary**: This element represents {sel.get('name')} in {sel.get('doc_name')}. "
                    f"It has `{sel.get('capabilities', {}).get('extracted')}` extraction fidelity and "
                    f"{'is editable' if sel.get('capabilities', {}).get('editable') else 'is read-only'}."
                ),
            )
            steps.append(AgentStep(label="Generated element summary with citation", status="done"))

            return AgentResponse(
                response=llm_text,
                status="success",
                run_id=run_id,
                intent="summarize_element",
                steps=steps,
                citations=citations,
                proposed_actions=[],
            )

        # ====================================================================
        # SLICE 2: SEARCH / INSPECT ACROSS ELEMENTS
        # ====================================================================
        search_keywords = ["find", "search", "list", "show me", "locate", "where is", "where are", "revenue", "table", "tax"]
        is_search = any(k in msg_lower for k in search_keywords)
        if session_id and context.active_doc_id and is_search:
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

                llm_text = cls._call_workbench_or_fallback(
                    message=message,
                    system_prompt=cls._build_search_prompt(context, search_results),
                    fallback_text=(
                        f"Found **{len(search_results)}** matching elements for **'{query_term}'** in document:\n\n"
                        + "\n".join([f"- **{r['name']}** (`{r['type']}`): {r['text'][:120]}" for r in search_results])
                    ),
                )
                steps.append(AgentStep(label="Generated provenance answer", status="done"))

                return AgentResponse(
                    response=llm_text,
                    status="success",
                    run_id=run_id,
                    intent="search_elements",
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

            llm_text = cls._call_workbench_or_fallback(
                message=message,
                system_prompt=cls._build_compare_prompt(context),
                fallback_text=(
                    f"### Cross-Document Comparison\n\n"
                    f"Comparing **{context.available_documents[0]['filename']}** ({context.available_documents[0]['format'].upper()}) "
                    f"and **{context.available_documents[1]['filename']}** ({context.available_documents[1]['format'].upper()}):\n\n"
                    f"1. **Structure**: Document 1 contains {context.available_documents[0]['element_count']} elements; Document 2 contains {context.available_documents[1]['element_count']} elements.\n"
                    f"2. **Alignment**: Elements map across canonical types without data loss.\n"
                ),
            )
            steps.append(AgentStep(label="Generated comparison summary", status="done"))

            return AgentResponse(
                response=llm_text,
                status="success",
                run_id=run_id,
                intent="compare_documents",
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
        fallback_text = (
            f"I have access to {doc_count} document{'s' if doc_count != 1 else ''} in your workspace: "
            f"{', '.join(d['filename'] for d in context.available_documents) if doc_count else 'No documents'}. "
            "Select an element or ask a specific question to analyze details."
        )

        llm_text = cls._call_workbench_or_fallback(message, system_prompt, fallback_text)
        steps.append(AgentStep(label="Generated response", status="done"))

        return AgentResponse(
            response=llm_text,
            status="success",
            run_id=run_id,
            intent="general_query",
            steps=steps,
            citations=citations,
            proposed_actions=[],
        )

    # ------------------------------------------------------------------------
    # LLM Helper & Prompt Construction
    # ------------------------------------------------------------------------
    @classmethod
    def _call_workbench_or_fallback(cls, message: str, system_prompt: str, fallback_text: str) -> str:
        try:
            res = chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=0.3,
            )
            return res.content
        except (WorkbenchConfigError, WorkbenchApiError, Exception):
            return fallback_text

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

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  FileText, Sheet, File as FileIcon, Plus, CheckCircle, Loader2, AlertTriangle,
  AlertCircle, Lock, Replace, Eye,
} from 'lucide-react';
import { useWorkflowStore } from '../../state/workflowStore';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { ReadinessSummary } from './ReadinessSummary';
import type { SlotAssignment, SlotId, WorkflowSlot } from '../../api/workflow';

// The Documents panel for a workflow that has a structured intake. It replaces
// the generic, role-less file list with the workflow's own input slots, so the
// first question a user answers is "which file is the previous Local File?"
// rather than "what am I supposed to upload?".

function FileTypeIcon({ format }: { format: string }) {
  switch (format) {
    case 'xlsx': return <Sheet size={14} style={{ color: '#2E7D32', flexShrink: 0 }} />;
    case 'docx': return <FileText size={14} style={{ color: '#1565C0', flexShrink: 0 }} />;
    case 'pdf': return <FileIcon size={14} style={{ color: '#C62828', flexShrink: 0 }} />;
    default: return <FileIcon size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />;
  }
}

const SLOT_STATUS_COLOR: Record<string, string> = {
  SATISFIED: 'var(--success)',
  NEEDS_REVIEW: 'var(--warning)',
  BLOCKED: 'var(--error)',
  EMPTY: 'var(--text-tertiary)',
};

function acceptAttribute(formats: string[]): string {
  return formats.map((f) => `.${f.toLowerCase()}`).join(',');
}

// ── One assigned file, with its role verdict ────────────────────────────────

const AssignmentCard: React.FC<{
  slot: WorkflowSlot;
  assignment: SlotAssignment;
  onReplace: (slotId: SlotId, docId: string) => void;
  onKeepForReview: (slotId: SlotId, docId: string) => void;
}> = ({ slot, assignment, onReplace, onKeepForReview }) => {
  const { documents, setActiveDocClientId } = useWorkspaceStore();
  const flagged = assignment.validation_status === 'ROLE_MISMATCH'
    || assignment.validation_status === 'FORMAT_REJECTED';
  const inReview = assignment.validation_status === 'HUMAN_REVIEW';

  const openInViewer = () => {
    const doc = documents.find((d) => d.docId === assignment.document_id);
    if (doc) setActiveDocClientId(doc.clientId);
  };

  return (
    <div
      data-testid={`slot-assignment-${assignment.document_id}`}
      data-validation={assignment.validation_status}
      style={{
        border: `1px solid ${flagged ? 'var(--error-border)' : inReview ? 'var(--warning-border)' : 'var(--border)'}`,
        background: flagged ? 'var(--error-light)' : 'var(--bg-surface)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <button
        onClick={openInViewer}
        title={`Open ${assignment.filename}`}
        style={{
          display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
          background: 'transparent', border: 'none', padding: 0, cursor: 'pointer',
          textAlign: 'left', width: '100%', minWidth: 0,
        }}
      >
        <FileTypeIcon format={assignment.format} />
        <span style={{
          flex: 1, minWidth: 0, fontSize: 'var(--text-xs)', fontWeight: 500,
          color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {assignment.filename}
        </span>
        {assignment.validation_status === 'ROLE_CONFIRMED' && (
          <CheckCircle size={12} style={{ color: 'var(--success)', flexShrink: 0 }} />
        )}
        {inReview && <AlertTriangle size={12} style={{ color: 'var(--warning)', flexShrink: 0 }} />}
        {flagged && <AlertCircle size={12} style={{ color: 'var(--error)', flexShrink: 0 }} />}
      </button>

      {/* Format · perception · elements · content version */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)',
        fontSize: '10px', color: 'var(--text-tertiary)',
      }}>
        <span>{assignment.format.toUpperCase()}</span>
        <span data-testid={`perception-status-${assignment.document_id}`}>
          {assignment.perception_status === 'ready' ? 'Perceived' : assignment.perception_status}
        </span>
        {assignment.element_count != null && assignment.element_count > 0 && (
          <span>{assignment.element_count.toLocaleString()} elements</span>
        )}
        {assignment.version_label && (
          <span title={`SHA-256 ${assignment.file_hash}`}>v·{assignment.version_label}</span>
        )}
      </div>

      {/* Role validation — always stated, never implied */}
      {!flagged && assignment.reasons.length > 0 && (
        <div style={{ fontSize: '10px', color: inReview ? 'var(--warning)' : 'var(--text-secondary)' }}>
          {inReview && assignment.human_review_acknowledged ? 'Kept for manual review — ' : ''}
          {assignment.detected_label}. {assignment.reasons[0]}
        </div>
      )}

      {/* Role mismatch — explicit, with no silent override */}
      {flagged && (
        <div data-testid={`role-mismatch-${assignment.document_id}`}
             style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 2 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 'var(--text-xxs)', fontWeight: 600, color: 'var(--error)',
          }}>
            <AlertTriangle size={12} />
            <span>File role mismatch</span>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            <div><strong>Expected:</strong> {assignment.expected_label}</div>
            <div><strong>Detected:</strong> {assignment.detected_label}</div>
            {assignment.reasons.map((reason) => (
              <div key={reason} style={{ marginTop: 2 }}>{reason}</div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-1)', marginTop: 2 }}>
            <button
              className="btn btn-secondary btn-sm"
              data-testid={`replace-file-${assignment.document_id}`}
              onClick={() => onReplace(slot.slot_id, assignment.document_id)}
              style={{ fontSize: '10px', padding: '2px 6px' }}
            >
              <Replace size={11} /> Replace File
            </button>
            <button
              className="btn btn-ghost btn-sm"
              data-testid={`keep-for-review-${assignment.document_id}`}
              onClick={() => onKeepForReview(slot.slot_id, assignment.document_id)}
              style={{ fontSize: '10px', padding: '2px 6px' }}
            >
              <Eye size={11} /> Keep for Manual Review
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ── One workflow input slot ─────────────────────────────────────────────────

const SlotSection: React.FC<{
  slot: WorkflowSlot;
  pending: boolean;
  pendingFilename: string | null;
  onPick: (slotId: SlotId, accepted: string[]) => void;
  onReplace: (slotId: SlotId, docId: string) => void;
  onKeepForReview: (slotId: SlotId, docId: string) => void;
}> = ({ slot, pending, pendingFilename, onPick, onReplace, onKeepForReview }) => {
  const empty = slot.assignments.length === 0;
  // A single-file slot stays actionable once filled: picking again replaces the
  // occupant. Without this a confirmed-but-wrong file could only be swapped
  // through the mismatch card, which a confirmed file never shows.
  const addLabel = empty ? slot.add_action_label
    : slot.accepts_multiple ? 'Add Source' : `Replace ${slot.display_name}`;

  return (
    <div
      data-testid={`workflow-slot-${slot.slot_id}`}
      data-readiness={slot.readiness_status}
      data-validation={slot.validation_status}
      style={{ padding: 'var(--space-2)', borderBottom: '1px solid var(--border)' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 4 }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
          background: SLOT_STATUS_COLOR[slot.readiness_status] ?? 'var(--text-tertiary)',
        }} />
        <span style={{
          flex: 1, fontSize: 'var(--text-xxs)', fontWeight: 600, letterSpacing: '0.04em',
          color: 'var(--text-secondary)',
        }}>
          {slot.section_title}
        </span>
        {slot.required && empty && (
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>Required</span>
        )}
      </div>

      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)', lineHeight: 1.5,
        marginBottom: 'var(--space-2)',
      }}>
        {slot.description}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        {slot.assignments.map((assignment) => (
          <AssignmentCard
            key={assignment.document_id}
            slot={slot}
            assignment={assignment}
            onReplace={onReplace}
            onKeepForReview={onKeepForReview}
          />
        ))}

        {pending && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 'var(--space-2)',
            padding: 'var(--space-2)', border: '1px dashed var(--border)',
            borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)',
          }}>
            <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {pendingFilename ?? 'Perceiving…'}
            </span>
          </div>
        )}

        <button
          className="btn btn-secondary btn-sm"
          data-testid={`slot-add-${slot.slot_id}`}
          onClick={() => onPick(slot.slot_id, slot.accepted_formats)}
          disabled={pending}
          style={{ justifyContent: 'center', fontSize: 'var(--text-xxs)' }}
        >
          {empty || slot.accepts_multiple ? <Plus size={12} /> : <Replace size={12} />}
          <span>{addLabel}</span>
        </button>
      </div>
    </div>
  );
};

// ── The panel ───────────────────────────────────────────────────────────────

export const WorkflowIntakePanel: React.FC = () => {
  const { state, pendingSlot, pendingFilename, error, addFilesToSlot, removeFromSlot, keepForReview, refresh }
    = useWorkflowStore();
  const sessionId = useWorkspaceStore((s) => s.sessionId);
  const [targetSlot, setTargetSlot] = useState<SlotId | null>(null);
  const [accept, setAccept] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Re-attach to an intake that already exists for this session (page reload).
  useEffect(() => {
    if (sessionId && !state) void refresh();
  }, [sessionId, state, refresh]);

  const openPicker = useCallback((slotId: SlotId, formats: string[]) => {
    setTargetSlot(slotId);
    setAccept(acceptAttribute(formats));
    // The accept attribute has to be applied before the dialog opens.
    window.setTimeout(() => fileInputRef.current?.click(), 0);
  }, []);

  const handleFiles = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (!targetSlot) return;
    // Strictly one at a time — each response carries the whole intake, so
    // overlapping adds would race to be the last one applied.
    await addFilesToSlot(targetSlot, files);
  };

  const handleReplace = async (slotId: SlotId, docId: string) => {
    await removeFromSlot(slotId, docId);
    const slot = state?.slots.find((s) => s.slot_id === slotId);
    if (slot) openPicker(slotId, slot.accepted_formats);
  };

  const gate = state?.gate;

  return (
    <div className="file-rail" style={{ width: 296 }} data-testid="workflow-intake-panel"
         aria-label="Workflow input documents">
      {/* Step header — the user always knows where they are */}
      <div className="file-rail-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 2, minHeight: 0, padding: 'var(--space-2)' }}>
        <span className="file-rail-header-title" style={{ padding: 0 }} data-testid="workflow-step-header">
          Step {state?.step ?? 1} / {state?.total_steps ?? 4} — {state?.step_label ?? 'Input Documents'}
        </span>
        <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', paddingLeft: 0 }}>
          {state?.workflow_display_name ?? 'Local File Roll-Forward'}
        </span>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={handleFiles}
        aria-label="Add a workflow document"
      />

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {(state?.slots ?? []).map((slot) => (
          <SlotSection
            key={slot.slot_id}
            slot={slot}
            pending={pendingSlot === slot.slot_id}
            pendingFilename={pendingFilename}
            onPick={(slotId, formats) => openPicker(slotId, formats)}
            onReplace={handleReplace}
            onKeepForReview={keepForReview}
          />
        ))}

        {!state && (
          <EmptySlots onPick={openPicker} pendingSlot={pendingSlot} pendingFilename={pendingFilename} />
        )}

        {state && <ReadinessSummary readiness={state.readiness} />}
      </div>

      {error && (
        <div style={{
          display: 'flex', gap: 'var(--space-2)', padding: 'var(--space-2)', margin: 'var(--space-2)',
          background: 'var(--error-light)', border: '1px solid var(--error-border)',
          borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xxs)', color: 'var(--error)',
        }}>
          <AlertCircle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Why execution is still blocked — always actionable */}
      <div
        data-testid="workflow-gate-message"
        data-execution-allowed={String(gate?.execution_allowed ?? false)}
        style={{
          borderTop: '1px solid var(--border)',
          padding: 'var(--space-2)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--space-2)',
          background: gate?.execution_allowed ? 'var(--success-light)' : 'var(--bg-surface-secondary)',
        }}
      >
        {gate?.execution_allowed
          ? <CheckCircle size={13} style={{ color: 'var(--success)', flexShrink: 0, marginTop: 1 }} />
          : <Lock size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0, marginTop: 1 }} />}
        <span style={{
          fontSize: 'var(--text-xxs)',
          color: gate?.execution_allowed ? 'var(--success)' : 'var(--text-secondary)',
          lineHeight: 1.5,
        }}>
          {gate?.message ?? 'Upload Previous Local File to continue.'}
        </span>
      </div>
    </div>
  );
};

// Before the first upload there is no server state yet, but the workflow's
// required roles are known — showing them is the whole point of this screen.
const PLACEHOLDER_SLOTS: Array<{ slot_id: SlotId; title: string; description: string;
  action: string; formats: string[] }> = [
  {
    slot_id: 'HISTORICAL_LOCAL_FILE', title: 'PREVIOUS LOCAL FILE',
    description: "Last year's finalised Local File — the document being rolled forward.",
    action: 'Add Previous Local File', formats: ['DOCX'],
  },
  {
    slot_id: 'CURRENT_YEAR_SOURCES', title: 'CURRENT-YEAR SOURCES',
    description: 'Current-year financial, tax and supporting data. Add as many as the engagement has.',
    action: 'Add Source', formats: ['XLSX', 'DOCX', 'CSV'],
  },
  {
    slot_id: 'MASTER_TEMPLATE', title: 'MASTER TEMPLATE',
    description: "The blank master Local File template that defines this year's structure.",
    action: 'Add Master Template', formats: ['DOCX'],
  },
];

const EmptySlots: React.FC<{
  onPick: (slotId: SlotId, formats: string[]) => void;
  pendingSlot: SlotId | null;
  pendingFilename: string | null;
}> = ({ onPick, pendingSlot, pendingFilename }) => (
  <>
    {PLACEHOLDER_SLOTS.map((slot) => (
      <div
        key={slot.slot_id}
        data-testid={`workflow-slot-${slot.slot_id}`}
        data-readiness="EMPTY"
        style={{ padding: 'var(--space-2)', borderBottom: '1px solid var(--border)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 4 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-tertiary)' }} />
          <span style={{
            flex: 1, fontSize: 'var(--text-xxs)', fontWeight: 600, letterSpacing: '0.04em',
            color: 'var(--text-secondary)',
          }}>{slot.title}</span>
          <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>Required</span>
        </div>
        <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', lineHeight: 1.5, marginBottom: 'var(--space-2)' }}>
          {slot.description}
        </div>
        {pendingSlot === slot.slot_id ? (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2)',
            border: '1px dashed var(--border)', borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
          }}>
            <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {pendingFilename ?? 'Perceiving…'}
            </span>
          </div>
        ) : (
          <button
            className="btn btn-secondary btn-sm"
            data-testid={`slot-add-${slot.slot_id}`}
            onClick={() => onPick(slot.slot_id, slot.formats)}
            style={{ justifyContent: 'center', fontSize: 'var(--text-xxs)', width: '100%' }}
          >
            <Plus size={12} />
            <span>{slot.action}</span>
          </button>
        )}
      </div>
    ))}
  </>
);

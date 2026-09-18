/**
 * GtpsRealDocDemo — GTPS Local File Real-Document Interactive Demo.
 * ==================================================================
 * Location: frontend/src/components/gtps/GtpsRealDocDemo.tsx
 *
 * Preserves the exact v5-lite visual design system while replacing all
 * mocked data with real uploaded document bytes and real backend mapping.
 *
 * Architecture constraints (AGENTS.md):
 * - Preview is a visual review PROJECTION, not a mutated document.
 * - No WritebackEngine, no ApprovedChangeSet, no Replay.
 * - docx-preview renders real template bytes; proposals are overlaid.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useGtpsDemoStore, type StatusFilter } from '../../state/gtpsDemoStore';
import type { DemoProposal } from '../../api/demo';
import { DocxRenderer } from '../document/rendering/DocxRenderer';
import { XlsxRenderer } from '../document/rendering/XlsxRenderer';
import type { DocumentRendererProps } from '../document/rendering/types';
import './GtpsRealDocDemo.css';

// ── Helpers ──

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function statusPillClass(status: string): string {
  switch (status) {
    case 'MAPPED': return 'good';
    case 'NEEDS_CONFIRMATION': return 'warn';
    case 'MISSING_SOURCE': return 'bad';
    case 'UNSUPPORTED': return '';
    default: return '';
  }
}

function fileIconClass(format: string): string {
  return format === 'xlsx' || format === 'xlsm' ? 'xlsx' : '';
}

const ROLE_LABELS: Record<string, string> = {
  TARGET_TEMPLATE: 'Mẫu mục tiêu',
  HISTORICAL_REFERENCE: 'LF năm trước',
  CURRENT_SOURCE: 'Nguồn dữ liệu hiện tại',
};

const FILTER_LABELS: { key: StatusFilter; label: string }[] = [
  { key: 'ALL', label: 'Tất cả' },
  { key: 'MAPPED', label: 'Đã ánh xạ' },
  { key: 'NEEDS_CONFIRMATION', label: 'Cần xác nhận' },
  { key: 'MISSING_SOURCE', label: 'Thiếu dữ liệu' },
  { key: 'UNSUPPORTED', label: 'Chưa hỗ trợ' },
];

const EMPTY_ELEMENTS: any[] = [];

// ── Intake Stage ──

const IntakeStage: React.FC = () => {
  const {
    documents, readiness, analyzeError, analyzeProgress,
    loadLocalDemo, uploadFiles, assignRole, removeDocument, runAnalysis,
  } = useGtpsDemoStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ['docx', 'xlsx', 'xlsm', 'pdf'].includes(ext ?? '');
    });
    if (files.length) uploadFiles(files);
  }, [uploadFiles]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    if (files.length) uploadFiles(files);
    e.target.value = '';
  }, [uploadFiles]);

  return (
    <div className="intake-wrap">
      <h1>GTPS Local File · Real-Document Demo</h1>
      <p>
        Nạp tệp thực (.docx, .xlsx, .pdf) để chạy ánh xạ roll-forward thực trên hệ thống Foundation.
        Không sử dụng dữ liệu mẫu cứng — mọi kết quả đến từ <code>RollForwardPlanner.plan()</code> thực tế.
      </p>

      {analyzeError && <div className="error-banner">{analyzeError}</div>}
      {analyzeProgress && (
        <div className="notice gov">{analyzeProgress}</div>
      )}

      {/* Local demo set loader */}
      <button className="demo-load-btn" onClick={() => loadLocalDemo()}>
        <div>
          <strong>📁 Nạp tệp mẫu thực tế (Local Demo Set)</strong>
          <small>Template DOCX + Prior LF DOCX + FA&RPT XLSX — tải ngay từ thư mục demo trên máy chủ</small>
        </div>
      </button>

      {/* Drop zone */}
      <div
        className={`drop-zone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <strong>Kéo thả tệp vào đây hoặc nhấn để chọn</strong>
        <span>.docx · .xlsx · .xlsm · .pdf</span>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".docx,.xlsx,.xlsm,.pdf"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {/* Document list with role assignment */}
      {documents.length > 0 && (
        <>
          <div className="railtitle">Tệp đã nạp ({documents.length})</div>
          <div className="intake-doc-list">
            {documents.map((doc) => (
              <div key={doc.doc_id} className="intake-doc-row">
                <div className={`file-icon ${fileIconClass(doc.format)}`}>
                  {doc.format.toUpperCase().slice(0, 4)}
                </div>
                <div>
                  <strong>{doc.filename}</strong>
                  <small>{formatBytes(doc.size_bytes)} · {doc.format.toUpperCase()}</small>
                </div>
                <select
                  className="role-select"
                  value={doc.assigned_role ?? ''}
                  onChange={(e) => assignRole(doc.doc_id, e.target.value || null)}
                >
                  <option value="">— Chọn vai trò —</option>
                  <option value="TARGET_TEMPLATE">Mẫu mục tiêu (Template)</option>
                  <option value="HISTORICAL_REFERENCE">LF năm trước (Historical)</option>
                  <option value="CURRENT_SOURCE">Nguồn dữ liệu (Source)</option>
                </select>
                <button className="remove-btn" onClick={() => removeDocument(doc.doc_id)} title="Xóa tệp">✕</button>
              </div>
            ))}
          </div>

          {/* Readiness indicators */}
          <div className="readiness-bar">
            <div className="readiness-item">
              <span className={`dot ${readiness.template_ready ? 'ready' : ''}`} />
              Template {readiness.template_ready ? '✓' : '—'}
            </div>
            <div className="readiness-item">
              <span className={`dot ${readiness.historical_ready ? 'ready' : ''}`} />
              Historical {readiness.historical_ready ? '✓' : '—'}
            </div>
            <div className="readiness-item">
              <span className={`dot ${readiness.current_source_ready ? 'ready' : ''}`} />
              Source {readiness.current_source_ready ? '✓' : '—'}
            </div>
          </div>

          <div className="notice gov">
            ⚠️ Bản xem trước thay đổi đề xuất — <strong>Chưa ghi vào tệp DOCX</strong>.
            Không có ApprovedChangeSet, không có Replay, không có mutation.
          </div>

          <button
            className="btn primary"
            disabled={!readiness.all_ready}
            onClick={() => runAnalysis()}
            style={{ width: '100%', padding: '12px', fontSize: '12px' }}
          >
            Chuẩn bị bản thảo đầu tiên
          </button>
        </>
      )}
    </div>
  );
};

// ── DocxPreviewPane: renders real DOCX bytes via DocxRenderer ──

const DocxPreviewPane: React.FC<{
  docId: string;
  label: string;
  selectedTableIndex?: number | null;
}> = ({ docId, label, selectedTableIndex }) => {
  const { fetchDocBytes, fetchDocElements } = useGtpsDemoStore();
  const [bytes, setBytes] = useState<ArrayBuffer | null>(null);
  const [elements, setElements] = useState<any[]>(EMPTY_ELEMENTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const [buf, els] = await Promise.all([
          fetchDocBytes(docId),
          fetchDocElements(docId).catch(() => []),
        ]);
        if (!cancelled) {
          setBytes(buf);
          setElements(els);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load document.');
          setLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [docId, fetchDocBytes, fetchDocElements]);

  const selectedElementId = React.useMemo(() => {
    if (selectedTableIndex == null) return null;
    const tableElements = elements.filter((el) => el.element_type === 'table' || el.type === 'table');
    return tableElements[selectedTableIndex]?.element_id ?? null;
  }, [elements, selectedTableIndex]);

  if (loading) {
    return (
      <div className="analyze-overlay">
        <div className="spinner" />
        <span style={{ fontSize: '10px', color: '#718095' }}>Đang tải {label}…</span>
      </div>
    );
  }

  if (error || !bytes) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#ad4747', fontSize: '10px' }}>
        {error ?? 'Không thể tải tài liệu.'}
      </div>
    );
  }

  const rendererProps: DocumentRendererProps = {
    source: bytes,
    sessionId: '',
    docId: docId,
    elements: elements,
    selectedElementId: selectedElementId,
    hoveredElementId: null,
    onSelectElement: () => {},
    onHoverElement: () => {},
    onEditElement: () => {},
    editable: false,
  };

  return (
    <div className="doc-render-wrap">
      <div className="doc-render-paper">
        <DocxRenderer {...rendererProps} />
      </div>
    </div>
  );
};

// ── XlsxPreviewPane: renders real XLSX bytes via XlsxRenderer ──

const XlsxPreviewPane: React.FC<{
  docId: string;
  label: string;
  highlightSheet?: string | null;
  highlightCell?: string | null;
}> = ({ docId, label }) => {
  const { fetchDocElements } = useGtpsDemoStore();
  const [elements, setElements] = useState<any[]>(EMPTY_ELEMENTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const els = await fetchDocElements(docId);
        if (!cancelled) { setElements(els); setLoading(false); }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load elements.');
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [docId, fetchDocElements]);

  if (loading) {
    return (
      <div className="analyze-overlay">
        <div className="spinner" />
        <span style={{ fontSize: '10px', color: '#718095' }}>Đang tải {label}…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#ad4747', fontSize: '10px' }}>
        {error}
      </div>
    );
  }

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <XlsxRenderer
        source={new ArrayBuffer(0)}
        sessionId=""
        docId={docId}
        elements={elements}
        selectedElementId={null}
        hoveredElementId={null}
        onSelectElement={() => {}}
        onHoverElement={() => {}}
        onEditElement={() => {}}
        editable={false}
      />
    </div>
  );
};

// ── Evidence Detail Panel ──

const EvidencePanel: React.FC<{
  proposal: DemoProposal;
  onViewSource: () => void;
}> = ({ proposal, onViewSource }) => {
  const { recordDecision, reviewProjection } = useGtpsDemoStore();
  const sessionId = reviewProjection?.session_id;

  return (
    <div className="evidence-panel">
      <h3>{proposal.business_target}</h3>
      <div className="ev-grid">
        <span className="ev-label">Vùng mục tiêu</span>
        <span className="ev-value">{proposal.target_region}</span>

        <span className="ev-label">Trạng thái</span>
        <span className="ev-value">
          <span className={`pill ${statusPillClass(proposal.status)}`}>{proposal.status_label_vi}</span>
        </span>

        {proposal.source_evidence && (
          <>
            <span className="ev-label">Nguồn dữ liệu</span>
            <span className="ev-value">
              {proposal.source_evidence.source_doc_name}
              {proposal.source_evidence.sheet_name && ` · ${proposal.source_evidence.sheet_name}`}
              {proposal.source_evidence.cell_range && ` · ${proposal.source_evidence.cell_range}`}
            </span>
            {proposal.source_evidence.record_count != null && (
              <>
                <span className="ev-label">Số dòng</span>
                <span className="ev-value">{proposal.source_evidence.record_count}</span>
              </>
            )}
          </>
        )}

        {proposal.historical_reference && (
          <>
            <span className="ev-label">Tham chiếu lịch sử</span>
            <span className="ev-value">
              {proposal.historical_reference.doc_name}
              {proposal.historical_reference.table_index != null && ` · Table ${proposal.historical_reference.table_index + 1}`}
              {proposal.historical_reference.correspondence != null && ` · ${(proposal.historical_reference.correspondence * 100).toFixed(0)}%`}
            </span>
          </>
        )}

        <span className="ev-label">Đề xuất</span>
        <span className="ev-value">{proposal.proposed_content}</span>

        <span className="ev-label">Lý do</span>
        <span className="ev-value">{proposal.rationale}</span>

        {proposal.binding_verdict && (
          <>
            <span className="ev-label">Binding verdict</span>
            <span className="ev-value">{proposal.binding_verdict}</span>
          </>
        )}
      </div>

      <div className="ev-actions">
        {proposal.source_evidence && (
          <button className="btn sm" onClick={onViewSource}>
            📄 Xem tệp nguồn FA&RPT
          </button>
        )}
        <button
          className={`btn sm ${proposal.decision === 'APPROVED' ? 'success' : ''}`}
          onClick={() => sessionId && recordDecision(proposal.id, 'APPROVED')}
        >
          ✓ Chấp nhận
        </button>
        <button
          className="btn sm"
          onClick={() => sessionId && recordDecision(proposal.id, 'EDITED')}
        >
          ✎ Chỉnh sửa
        </button>
        <button
          className="btn sm"
          onClick={() => sessionId && recordDecision(proposal.id, 'SKIPPED')}
        >
          ↷ Bỏ qua
        </button>
        <button
          className="btn sm"
          onClick={() => sessionId && recordDecision(proposal.id, 'REJECTED')}
        >
          ✕ Yêu cầu bổ sung
        </button>
      </div>

      <div className="notice gov" style={{ marginTop: '10px' }}>
        ⚠️ Bản xem trước thay đổi đề xuất — Chưa ghi vào tệp DOCX.
        Quyết định review được ghi nhận nhưng không thực hiện mutation.
      </div>
    </div>
  );
};

// ── Left Rail (Review stage) ──

const ReviewRail: React.FC = () => {
  const {
    documents, reviewProjection, selectedProposalId, statusFilter,
    setSelectedProposal, setHoveredProposal, setStatusFilter, previewDocument,
  } = useGtpsDemoStore();

  if (!reviewProjection) return null;
  const { summary, proposals } = reviewProjection;

  const filtered = statusFilter === 'ALL'
    ? proposals
    : proposals.filter(p => p.status === statusFilter);

  return (
    <>
      <div className="railhead">
        <div className="eyebrow">GTPS LOCAL FILE DEMO</div>
        <h2>Đối chiếu ánh xạ</h2>
      </div>
      <div className="railbody">
        {/* Input documents */}
        <div className="railtitle">Tệp đầu vào</div>
        {documents.map(doc => (
          <div
            key={doc.doc_id}
            className="doc-card"
            onClick={() => previewDocument(doc.doc_id)}
          >
            <div className="doc-card-row">
              <div className={`file-icon ${fileIconClass(doc.format)}`}>
                {doc.format.toUpperCase().slice(0, 4)}
              </div>
              <div>
                <strong>{doc.filename.length > 40 ? doc.filename.slice(0, 37) + '…' : doc.filename}</strong>
                <small>{formatBytes(doc.size_bytes)}</small>
                {doc.assigned_role && <div className="role-badge">{ROLE_LABELS[doc.assigned_role] ?? doc.assigned_role}</div>}
              </div>
            </div>
          </div>
        ))}

        {/* Summary */}
        <div className="railtitle">Tổng quan ánh xạ</div>
        <div className="summary-grid">
          <div>
            <span>Tổng</span>
            <strong>{summary.total}</strong>
          </div>
          <div>
            <span style={{ color: '#24745d' }}>Đã ánh xạ</span>
            <strong style={{ color: '#24745d' }}>{summary.mapped}</strong>
          </div>
          <div>
            <span style={{ color: '#94651c' }}>Cần xác nhận</span>
            <strong style={{ color: '#94651c' }}>{summary.needs_confirmation}</strong>
          </div>
          <div>
            <span style={{ color: '#ad4747' }}>Thiếu / Chưa hỗ trợ</span>
            <strong style={{ color: '#ad4747' }}>{summary.missing_source + summary.unsupported}</strong>
          </div>
        </div>

        {/* Filter buttons */}
        <div className="filter-bar">
          {FILTER_LABELS.map(({ key, label }) => (
            <button
              key={key}
              className={`filter-btn ${statusFilter === key ? 'active' : ''}`}
              onClick={() => setStatusFilter(key)}
            >
              {label}
              {key !== 'ALL' && ` (${
                key === 'MAPPED' ? summary.mapped :
                key === 'NEEDS_CONFIRMATION' ? summary.needs_confirmation :
                key === 'MISSING_SOURCE' ? summary.missing_source :
                summary.unsupported
              })`}
            </button>
          ))}
        </div>

        {/* Proposal list */}
        <div className="railtitle">Đề xuất thay đổi ({filtered.length})</div>
        {filtered.map(p => (
          <button
            key={p.id}
            className={`proposal-card ${selectedProposalId === p.id ? 'active' : ''}`}
            onClick={() => setSelectedProposal(p.id)}
            onMouseEnter={() => setHoveredProposal(p.id)}
            onMouseLeave={() => setHoveredProposal(null)}
          >
            <div className="prop-title">{p.business_target}</div>
            <div className="prop-region">{p.target_region}</div>
            <div className="prop-meta">
              <span className={`pill ${statusPillClass(p.status)}`}>{p.status_label_vi}</span>
              {p.decision !== 'PENDING' && (
                <span className="pill blue">{p.decision}</span>
              )}
            </div>
          </button>
        ))}
      </div>
    </>
  );
};

// ── Main Review Workspace (3-pane) ──

const ReviewWorkspace: React.FC = () => {
  const {
    reviewProjection, viewMode, selectedProposalId, previewDocId, documents,
    returnToComparison, previewDocument,
  } = useGtpsDemoStore();

  if (!reviewProjection) return null;

  const selectedProposal = reviewProjection.proposals.find(p => p.id === selectedProposalId) ?? null;
  const templateDocId = reviewProjection.template_doc_id;

  // Find first source that's an xlsx for "view source" action
  const firstXlsxSourceId = reviewProjection.current_source_doc_ids.find(id => {
    const doc = documents.find(d => d.doc_id === id);
    return doc && (doc.format === 'xlsx' || doc.format === 'xlsm');
  });

  const handleViewSource = useCallback(() => {
    if (firstXlsxSourceId) previewDocument(firstXlsxSourceId);
  }, [firstXlsxSourceId, previewDocument]);

  // Single-document preview mode
  if (viewMode !== 'dual-comparison' && previewDocId) {
    const previewDoc = documents.find(d => d.doc_id === previewDocId);
    const isXlsx = previewDoc && (previewDoc.format === 'xlsx' || previewDoc.format === 'xlsm');

    return (
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        <div className="pane-header">
          <button className="btn sm back-btn" onClick={returnToComparison}>
            ← Quay lại đối chiếu
          </button>
          <strong>{previewDoc?.filename ?? previewDocId}</strong>
          <span className="sub">{previewDoc?.assigned_role ? ROLE_LABELS[previewDoc.assigned_role] : ''}</span>
        </div>
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {isXlsx ? (
            <XlsxPreviewPane docId={previewDocId} label={previewDoc?.filename ?? ''} />
          ) : (
            <DocxPreviewPane docId={previewDocId} label={previewDoc?.filename ?? ''} />
          )}
        </div>
      </div>
    );
  }

  // Dual comparison mode
  return (
    <>
      {/* Center Pane: Proposed changes preview */}
      <div className="center-pane">
        <div className="pane-header">
          <strong>Bản xem trước thay đổi đề xuất</strong>
          <span className="sub">Chưa ghi vào tệp DOCX</span>
        </div>
        <div className="preview-banner">
          <span>📋</span>
          <span>
            <strong>{reviewProjection.template_filename}</strong> ·
            Kỳ hiện tại: {reviewProjection.current_period} ·
            {reviewProjection.summary.total} vùng được phân tích
          </span>
        </div>
        <div className="pane-body">
          <DocxPreviewPane
            docId={templateDocId}
            label="Template — Đề xuất"
            selectedTableIndex={selectedProposal?.target_table_index}
          />
        </div>
        {selectedProposal && (
          <EvidencePanel proposal={selectedProposal} onViewSource={handleViewSource} />
        )}
      </div>

      {/* Right Pane: Original template */}
      <div className="right-pane">
        <div className="pane-header">
          <strong>Mẫu gốc</strong>
          <span className="sub">(không thay đổi)</span>
        </div>
        <div className="pane-body">
          <DocxPreviewPane
            docId={templateDocId}
            label="Template — Gốc"
          />
        </div>
      </div>
    </>
  );
};

// ── Main Component ──

export const GtpsRealDocDemo: React.FC = () => {
  const { stage, reset } = useGtpsDemoStore();

  // Analyzing overlay
  if (stage === 'analyzing') {
    return (
      <div className="gtps-demo">
        <DemoTopbar onReset={reset} />
        <div className="analyze-overlay" style={{ flex: 1 }}>
          <div className="spinner" />
          <strong style={{ fontSize: '13px' }}>Đang phân tích ánh xạ roll-forward…</strong>
          <span style={{ fontSize: '10px', color: '#718095' }}>
            RollForwardPlanner.plan() đang xử lý tệp thực tế
          </span>
        </div>
      </div>
    );
  }

  // Intake stage
  if (stage === 'intake') {
    return (
      <div className="gtps-demo">
        <DemoTopbar onReset={reset} />
        <div style={{ flex: 1, overflow: 'auto' }}>
          <IntakeStage />
        </div>
      </div>
    );
  }

  // Review stage: 3-pane layout
  return (
    <div className="gtps-demo">
      <DemoTopbar onReset={reset} />
      <div className="demo-shell">
        <aside className="demo-rail">
          <ReviewRail />
        </aside>
        <ReviewWorkspace />
      </div>
    </div>
  );
};

// ── Demo Topbar ──

const DemoTopbar: React.FC<{ onReset: () => void }> = ({ onReset }) => {
  const { reviewProjection } = useGtpsDemoStore();
  return (
    <div className="demo-topbar">
      <div className="brand-mark">F</div>
      <span className="title">Foundation · Document Processing</span>
      <div className="spacer" />
      <span className="demo-badge">INTERACTIVE DEMO</span>
      {reviewProjection && (
        <span className="governance-badge">
          🔒 {reviewProjection.governance.statement}
        </span>
      )}
      <button className="btn sm ghost" onClick={onReset} title="Đặt lại demo">
        ↺ Reset
      </button>
    </div>
  );
};

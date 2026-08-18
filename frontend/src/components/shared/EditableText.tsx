import React, { useState, useEffect } from 'react';

interface EditableTextProps {
  value: string;
  onSave: (newValue: string) => void;
  className?: string;
  multiline?: boolean;
  disabled?: boolean;
  title?: string;
}

// Click-to-edit text used by DocumentPane/ElementsPane for live edits that
// write directly into the document (PATCH /api/documents/<session_id>/elements/<doc_id>,
// see state/workspaceStore.ts::editElement).
export const EditableText: React.FC<EditableTextProps> = ({
  value,
  onSave,
  className,
  multiline,
  disabled,
  title,
}) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  const commit = () => {
    setEditing(false);
    if (draft !== value) onSave(draft);
  };

  const cancel = () => {
    setDraft(value);
    setEditing(false);
  };

  if (disabled) {
    return <span className={className}>{value}</span>;
  }

  if (editing) {
    const editClassName = `${className ?? ''} bg-blue-50 outline outline-1 outline-blue-400 rounded px-1 w-full`;
    if (multiline) {
      return (
        <textarea
          autoFocus
          rows={3}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              commit();
            }
            if (e.key === 'Escape') {
              e.preventDefault();
              cancel();
            }
          }}
          className={editClassName}
        />
      );
    }
    return (
      <input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            commit();
          }
          if (e.key === 'Escape') {
            e.preventDefault();
            cancel();
          }
        }}
        className={editClassName}
      />
    );
  }

  return (
    <span
      className={`${className ?? ''} cursor-text hover:bg-blue-50 rounded px-0.5 -mx-0.5`}
      onClick={() => setEditing(true)}
      title={title ?? 'Click to edit'}
    >
      {value ? value : <span className="text-gray-300 italic">(empty — click to fill in)</span>}
    </span>
  );
};

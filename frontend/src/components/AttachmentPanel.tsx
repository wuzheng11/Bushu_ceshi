import { useRef, useState } from "react";
import { Download, FileText, Trash2, UploadCloud } from "lucide-react";
import { formatBytes, formatDateTime } from "../lib/api";
import type { Attachment } from "../types";

interface Props {
  attachments: Attachment[];
  selectedIds: number[];
  disabled?: boolean;
  onToggle: (id: number) => void;
  onUpload: (file: File) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

const statusLabels: Record<string, string> = {
  pending: "待解析",
  parsed: "已解析",
  stored: "已存储",
  failed: "失败",
};

export default function AttachmentPanel({
  attachments,
  selectedIds,
  disabled,
  onToggle,
  onUpload,
  onDelete,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  async function acceptFiles(files: FileList | null) {
    if (!files?.length || disabled) return;
    for (const file of Array.from(files)) {
      await onUpload(file);
    }
  }

  return (
    <section className="panel-section attachment-panel">
      <div className="section-heading">
        <div>
          <span>附件</span>
          <strong>{attachments.length}</strong>
        </div>
        <button
          className="text-icon-button"
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud size={16} />
          上传
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(event) => {
            void acceptFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </div>
      <div
        className={`attachment-dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void acceptFiles(event.dataTransfer.files);
        }}
      >
        {attachments.map((attachment) => (
          <div className="attachment-row" key={attachment.attachment_id}>
            <label className="attachment-check">
              <input
                type="checkbox"
                checked={selectedIds.includes(attachment.attachment_id)}
                onChange={() => onToggle(attachment.attachment_id)}
              />
            </label>
            <span className="file-icon">
              <FileText size={17} />
            </span>
            <div className="attachment-copy">
              <strong title={attachment.file_name}>{attachment.file_name}</strong>
              <span>
                {formatBytes(attachment.file_size)} · {statusLabels[attachment.parse_status] || attachment.parse_status}
              </span>
              <small>{formatDateTime(attachment.created_at)}</small>
            </div>
            <div className="attachment-actions">
              <a
                href={`/api/attachment/get?attachment_id=${attachment.attachment_id}`}
                title="下载附件"
              >
                <Download size={15} />
              </a>
              <button
                type="button"
                title="删除附件"
                disabled={disabled}
                onClick={() => void onDelete(attachment.attachment_id)}
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        ))}
        {!attachments.length && (
          <button
            type="button"
            className="dropzone-empty"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
          >
            <UploadCloud size={19} />
            <span>上传 CSV、JSON、TXT 或业务文档</span>
          </button>
        )}
      </div>
    </section>
  );
}

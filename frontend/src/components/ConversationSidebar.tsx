import { useState } from "react";
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { formatDateTime } from "../lib/api";
import type { Conversation } from "../types";

interface Props {
  conversations: Conversation[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onRename: (id: number, title: string) => Promise<void>;
}

export default function ConversationSidebar({
  conversations,
  currentId,
  onSelect,
  onCreate,
  onDelete,
  onRename,
}: Props) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  function startRename(item: Conversation) {
    setEditingId(item.conversation_id);
    setEditingTitle(item.title);
  }

  async function commitRename(id: number) {
    const title = editingTitle.trim();
    if (title) {
      await onRename(id, title);
    }
    setEditingId(null);
  }

  return (
    <aside className="conversation-sidebar">
      <div className="sidebar-heading">
        <div>
          <span>分析会话</span>
          <strong>{conversations.length}</strong>
        </div>
        <button className="primary-icon-button" type="button" onClick={() => void onCreate()} title="新建会话">
          <Plus size={18} />
        </button>
      </div>
      <div className="conversation-list">
        {conversations.map((item) => (
          <div
            key={item.conversation_id}
            className={`conversation-item ${currentId === item.conversation_id ? "active" : ""}`}
            onClick={() => onSelect(item.conversation_id)}
          >
            <div className="conversation-copy">
              {editingId === item.conversation_id ? (
                <input
                  className="inline-title-input"
                  value={editingTitle}
                  autoFocus
                  onChange={(event) => setEditingTitle(event.target.value)}
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void commitRename(item.conversation_id);
                    if (event.key === "Escape") setEditingId(null);
                  }}
                />
              ) : (
                <strong>{item.title}</strong>
              )}
              <span>{formatDateTime(item.last_message_at || item.updated_at)}</span>
            </div>
            <div className="conversation-actions">
              {editingId === item.conversation_id ? (
                <>
                  <button
                    type="button"
                    title="保存标题"
                    onClick={(event) => {
                      event.stopPropagation();
                      void commitRename(item.conversation_id);
                    }}
                  >
                    <Check size={15} />
                  </button>
                  <button
                    type="button"
                    title="取消"
                    onClick={(event) => {
                      event.stopPropagation();
                      setEditingId(null);
                    }}
                  >
                    <X size={15} />
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    title="重命名"
                    onClick={(event) => {
                      event.stopPropagation();
                      startRename(item);
                    }}
                  >
                    <Pencil size={15} />
                  </button>
                  <button
                    type="button"
                    title="删除会话"
                    onClick={(event) => {
                      event.stopPropagation();
                      void onDelete(item.conversation_id);
                    }}
                  >
                    <Trash2 size={15} />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
        {!conversations.length && (
          <div className="sidebar-empty">
            <span>暂无会话</span>
            <button type="button" onClick={() => void onCreate()}>
              新建分析
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

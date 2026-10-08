import { useEffect, useRef, useState } from "react";
import { apiFetch } from "../lib/api";
import type {
  AnalysisResult,
  AnalysisTask,
  Attachment,
  Conversation,
  Message,
  SocketEvent,
  ToolStep,
} from "../types";
import AppHeader from "../components/AppHeader";
import ConversationSidebar from "../components/ConversationSidebar";
import ChatPanel from "../components/ChatPanel";
import AttachmentPanel from "../components/AttachmentPanel";
import TaskPanel from "../components/TaskPanel";
import ResultPanel from "../components/ResultPanel";

export default function WorkbenchPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [selectedAttachmentIds, setSelectedAttachmentIds] = useState<number[]>([]);
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [toolSteps, setToolSteps] = useState<ToolStep[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [socketConnected, setSocketConnected] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [loadingConversation, setLoadingConversation] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const activeTaskRef = useRef<number | null>(null);

  const activeTask = tasks.find((task) => task.task_id === activeTaskId) || null;
  const running = activeTask?.task_status === "queued" || activeTask?.task_status === "running";

  async function loadConversations() {
    const items = await apiFetch<Conversation[]>("/api/chat/ls");
    setConversations(items);
    if (items.length > 0) {
      setCurrentId((current) => current ?? items[0].conversation_id);
    } else {
      const created = await apiFetch<Conversation>("/api/chat/create", {
        method: "POST",
        body: JSON.stringify({ title: "新会话" }),
      });
      setConversations([created]);
      setCurrentId(created.conversation_id);
    }
  }

  async function loadMessages(conversationId: number) {
    const items = await apiFetch<Message[]>(`/api/chat/ls/${conversationId}`);
    setMessages(items);
  }

  async function loadAttachments(conversationId: number) {
    const items = await apiFetch<Attachment[]>(
      `/api/attachment/ls?conversation_id=${conversationId}`,
    );
    setAttachments(items);
    setSelectedAttachmentIds((selected) =>
      selected.filter((id) => items.some((item) => item.attachment_id === id)),
    );
  }

  async function loadTasks(conversationId: number) {
    const items = await apiFetch<AnalysisTask[]>(
      `/api/tasks?conversation_id=${conversationId}`,
    );
    setTasks(items);
    const latest = items[0];
    if (latest) {
      setActiveTaskId(latest.task_id);
      activeTaskRef.current = latest.task_id;
      if (latest.task_status === "success") {
        await loadResult(latest.task_id);
      } else {
        setResult(null);
      }
    } else {
      setActiveTaskId(null);
      activeTaskRef.current = null;
      setResult(null);
    }
  }

  async function loadResult(taskId: number) {
    try {
      const item = await apiFetch<AnalysisResult>(`/api/results/${taskId}`);
      setResult(item);
      return item;
    } catch {
      setResult(null);
      return null;
    }
  }

  function closeSocket() {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setSocketConnected(false);
  }

  async function connectSocket(conversationId: number) {
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    setSocketConnected(false);
    const tokenPayload = await apiFetch<{ websocket_token: string; expires_in: number }>(
      `/api/chat/ws-token?conversation_id=${conversationId}`,
      { method: "POST" },
    );
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/api/chat/ws/chat?websocket_token=${encodeURIComponent(
      tokenPayload.websocket_token,
    )}&conversation_id=${conversationId}`;
    const socket = new WebSocket(url);
    socketRef.current = socket;
    socket.onopen = () => setSocketConnected(true);
    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      setSocketConnected(false);
    };
    socket.onerror = () => setSocketConnected(false);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as SocketEvent;
      if (payload.conversation_id && payload.conversation_id !== conversationId) return;
      void handleSocketEvent(payload, conversationId);
    };
  }

  async function handleSocketEvent(payload: SocketEvent, conversationId: number) {
    if (payload.task_id) {
      if (!activeTaskRef.current || payload.task_id >= activeTaskRef.current) {
        activeTaskRef.current = payload.task_id;
        setActiveTaskId(payload.task_id);
      }
    }
    switch (payload.event) {
      case "message_start":
        setStreamingContent("");
        break;
      case "message_delta":
        setStreamingContent((current) => current + (payload.delta_text || ""));
        break;
      case "tool_start":
        setToolSteps((current) => [
          ...current,
          {
            tool_name: payload.tool_name || "unknown_tool",
            status: "running",
            task_id: payload.task_id,
          },
        ]);
        break;
      case "tool_finish":
        setToolSteps((current) => {
          const next = [...current];
          for (let index = next.length - 1; index >= 0; index -= 1) {
            if (
              next[index].tool_name === payload.tool_name &&
              next[index].task_id === payload.task_id &&
              next[index].status === "running"
            ) {
              next[index] = {
                ...next[index],
                status: payload.tool_status === "failed" ? "failed" : "success",
                summary: payload.tool_result_summary,
              };
              return next;
            }
          }
          return [
            ...next,
            {
              tool_name: payload.tool_name || "unknown_tool",
              status: payload.tool_status === "failed" ? "failed" : "success",
              summary: payload.tool_result_summary,
              task_id: payload.task_id,
            },
          ];
        });
        break;
      case "task_status":
        if (payload.task_id && payload.task_status) {
          setTasks((current) => {
            const existing = current.find((task) => task.task_id === payload.task_id);
            if (existing) {
              return current.map((task) =>
                task.task_id === payload.task_id
                  ? {
                      ...task,
                      task_status: payload.task_status!,
                      current_step: payload.current_step || task.current_step,
                      finished_at:
                        payload.task_status === "success" || payload.task_status === "failed"
                          ? payload.finished_at || new Date().toISOString()
                          : task.finished_at,
                    }
                  : task,
              );
            }
            return [
              {
                task_id: payload.task_id!,
                conversation_id: conversationId,
                task_status: payload.task_status!,
                current_step: payload.current_step || null,
                started_at: null,
                finished_at: payload.finished_at || null,
                error_message: null,
              },
              ...current,
            ];
          });
        }
        break;
      case "result_ready":
        if (payload.task_id) {
          await loadResult(payload.task_id);
          await loadMessages(conversationId);
        }
        break;
      case "error":
        setErrorMessage(payload.error_message || "分析任务失败");
        break;
      case "done":
        setStreamingContent("");
        await Promise.all([
          loadMessages(conversationId),
          loadTasks(conversationId),
          loadAttachments(conversationId),
          loadConversations(),
        ]);
        break;
    }
  }

  useEffect(() => {
    void loadConversations();
    return () => closeSocket();
  }, []);

  useEffect(() => {
    if (!currentId) return;
    let active = true;
    closeSocket();
    setLoadingConversation(true);
    setMessages([]);
    setToolSteps([]);
    setStreamingContent("");
    setErrorMessage("");
    Promise.all([
      loadMessages(currentId),
      loadAttachments(currentId),
      loadTasks(currentId),
    ])
      .then(() => {
        if (active) return connectSocket(currentId);
      })
      .finally(() => {
        if (active) setLoadingConversation(false);
      });
    return () => {
      active = false;
      closeSocket();
    };
  }, [currentId]);

  async function createConversation() {
    const conversation = await apiFetch<Conversation>("/api/chat/create", {
      method: "POST",
      body: JSON.stringify({ title: "新会话" }),
    });
    setConversations((current) => [conversation, ...current]);
    setCurrentId(conversation.conversation_id);
  }

  async function deleteConversation(conversationId: number) {
    if (!window.confirm("删除会话会同时清理消息、附件、任务和结果，是否继续？")) return;
    await apiFetch("/api/chat/delete", {
      method: "POST",
      body: JSON.stringify({ conversation_ids: [conversationId] }),
    });
    const remaining = conversations.filter((item) => item.conversation_id !== conversationId);
    setConversations(remaining);
    if (currentId === conversationId) {
      setCurrentId(remaining[0]?.conversation_id || null);
    }
    if (!remaining.length) {
      await createConversation();
    }
  }

  async function renameConversation(conversationId: number, title: string) {
    const updated = await apiFetch<Conversation>("/api/chat/update", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, title }),
    });
    setConversations((current) =>
      current.map((item) => (item.conversation_id === conversationId ? updated : item)),
    );
  }

  async function sendMessage(content: string) {
    if (!currentId) return;
    setErrorMessage("");
    await connectSocket(currentId);
    const task = await apiFetch<{
      message_id: number;
      task_id: number;
      conversation_id: number;
      task_status: AnalysisTask["task_status"];
      current_step: string;
    }>("/api/chat/send", {
      method: "POST",
      body: JSON.stringify({
        conversation_id: currentId,
        content,
        attachment_ids: selectedAttachmentIds,
        scenario: "auto",
      }),
    });
    activeTaskRef.current = task.task_id;
    setActiveTaskId(task.task_id);
    setResult(null);
    setToolSteps([]);
    setStreamingContent("");
    setSelectedAttachmentIds([]);
    setTasks((current) => [
      {
        task_id: task.task_id,
        conversation_id: currentId,
        task_status: task.task_status,
        current_step: task.current_step,
        started_at: null,
        finished_at: null,
        error_message: null,
      },
      ...current,
    ]);
    await Promise.all([loadMessages(currentId), loadAttachments(currentId), loadConversations()]);
  }

  async function uploadAttachment(file: File) {
    if (!currentId) return;
    const formData = new FormData();
    formData.append("conversation_id", String(currentId));
    formData.append("file", file);
    await apiFetch<Attachment>("/api/attachment/upload", {
      method: "POST",
      body: formData,
    });
    await loadAttachments(currentId);
  }

  async function deleteAttachment(attachmentId: number) {
    const formData = new FormData();
    formData.append("attachment_id", String(attachmentId));
    await apiFetch("/api/attachment/delete", {
      method: "POST",
      body: formData,
    });
    if (currentId) await loadAttachments(currentId);
  }

  async function saveResult() {
    if (!result) return;
    const saved = await apiFetch<{ file_path: string }>(`/api/results/${result.task_id}/save`, {
      method: "POST",
    });
    setResult({ ...result, result_file_path: saved.file_path });
  }

  return (
    <div className="app-shell">
      <AppHeader />
      <main className="workbench">
        <ConversationSidebar
          conversations={conversations}
          currentId={currentId}
          onSelect={setCurrentId}
          onCreate={createConversation}
          onDelete={deleteConversation}
          onRename={renameConversation}
        />
        <div className="chat-area">
          {loadingConversation ? (
            <div className="page-loader">正在加载会话...</div>
          ) : (
            <ChatPanel
              messages={messages}
              streamingContent={streamingContent}
              disabled={running}
              onSend={sendMessage}
            />
          )}
        </div>
        <aside className="insight-sidebar">
          <TaskPanel
            task={activeTask}
            toolSteps={toolSteps.filter(
              (step) => !activeTaskId || step.task_id === activeTaskId,
            )}
            socketConnected={socketConnected}
            errorMessage={errorMessage}
          />
          <AttachmentPanel
            attachments={attachments}
            selectedIds={selectedAttachmentIds}
            disabled={running}
            onToggle={(id) =>
              setSelectedAttachmentIds((current) =>
                current.includes(id)
                  ? current.filter((item) => item !== id)
                  : [...current, id],
              )
            }
            onUpload={uploadAttachment}
            onDelete={deleteAttachment}
          />
          <ResultPanel
            result={result}
            onSave={saveResult}
            onExport={() => {
              if (result) {
                window.open(`/api/results/${result.task_id}/download`, "_blank", "noopener");
              }
            }}
          />
        </aside>
      </main>
    </div>
  );
}

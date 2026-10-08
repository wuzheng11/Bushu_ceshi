import { useEffect, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import AppHeader from "../components/AppHeader";
import { apiFetch, formatDateTime } from "../lib/api";
import type { LogItem } from "../types";

export default function AdminLogsPage() {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [taskId, setTaskId] = useState("");
  const [level, setLevel] = useState("");

  async function loadLogs() {
    const query = new URLSearchParams({ limit: "300" });
    if (taskId.trim()) query.set("task_id", taskId.trim());
    if (level) query.set("log_level", level);
    setLogs(await apiFetch<LogItem[]>(`/api/admin/logs?${query.toString()}`));
  }

  useEffect(() => {
    void loadLogs();
  }, []);

  return (
    <div className="app-shell">
      <AppHeader />
      <main className="admin-page">
        <header className="admin-titlebar">
          <div>
            <span>系统管理</span>
            <h1>运行日志</h1>
          </div>
          <button className="command-button" type="button" onClick={() => void loadLogs()}>
            <RefreshCw size={17} />
            刷新日志
          </button>
        </header>
        <div className="log-filters">
          <label>
            <Search size={16} />
            <input
              value={taskId}
              placeholder="任务 ID"
              inputMode="numeric"
              onChange={(event) => setTaskId(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void loadLogs();
              }}
            />
          </label>
          <select value={level} onChange={(event) => setLevel(event.target.value)}>
            <option value="">全部级别</option>
            <option value="INFO">INFO</option>
            <option value="ERROR">ERROR</option>
          </select>
          <button type="button" onClick={() => void loadLogs()}>
            查询
          </button>
        </div>
        <section className="log-list">
          {logs.map((item) => (
            <details className="log-entry" key={item.id}>
              <summary>
                <span className={`log-level ${item.log_level.toLowerCase()}`}>{item.log_level}</span>
                <strong>{item.log_type}</strong>
                <span>任务 #{item.task_id}</span>
                <time>{formatDateTime(item.created_at)}</time>
              </summary>
              <pre>{formatLogContent(item.log_content)}</pre>
            </details>
          ))}
          {!logs.length && <div className="muted-empty">没有匹配的运行日志</div>}
        </section>
      </main>
    </div>
  );
}

function formatLogContent(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}

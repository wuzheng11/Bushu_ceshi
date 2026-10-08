import {
  AlertCircle,
  CheckCircle2,
  CircleDashed,
  Loader2,
  Radio,
  Wrench,
} from "lucide-react";
import { formatDateTime } from "../lib/api";
import type { AnalysisTask, ToolStep } from "../types";

interface Props {
  task: AnalysisTask | null;
  toolSteps: ToolStep[];
  socketConnected: boolean;
  errorMessage: string;
}

const statusLabels: Record<string, string> = {
  queued: "排队中",
  running: "运行中",
  success: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

function StatusIcon({ status }: { status: string }) {
  if (status === "running" || status === "queued") {
    return <Loader2 size={16} className="spin" />;
  }
  if (status === "success") return <CheckCircle2 size={16} />;
  if (status === "failed") return <AlertCircle size={16} />;
  return <CircleDashed size={16} />;
}

export default function TaskPanel({ task, toolSteps, socketConnected, errorMessage }: Props) {
  return (
    <section className="panel-section task-panel">
      <div className="section-heading">
        <div>
          <span>实时任务</span>
          <strong>{task ? `#${task.task_id}` : "-"}</strong>
        </div>
        <span className={`socket-state ${socketConnected ? "online" : ""}`}>
          <Radio size={14} />
          {socketConnected ? "已连接" : "未连接"}
        </span>
      </div>
      <div className={`task-summary status-${task?.task_status || "idle"}`}>
        <div className="task-status-icon">
          <StatusIcon status={task?.task_status || "idle"} />
        </div>
        <div>
          <strong>{statusLabels[task?.task_status || ""] || "等待任务"}</strong>
          <span>{task?.current_step || "尚未开始分析"}</span>
        </div>
      </div>
      <div className="task-times">
        <span>开始 {formatDateTime(task?.started_at)}</span>
        <span>结束 {formatDateTime(task?.finished_at)}</span>
      </div>
      {errorMessage && (
        <div className="inline-error">
          <AlertCircle size={15} />
          <span>{errorMessage}</span>
        </div>
      )}
      <div className="tool-stream">
        <div className="subsection-title">
          <Wrench size={15} />
          工具执行
        </div>
        {toolSteps.map((step, index) => (
          <div className="tool-step" key={`${step.task_id}-${step.tool_name}-${index}`}>
            <span className={`tool-dot ${step.status}`} />
            <div>
              <strong>{step.tool_name}</strong>
              <span>{step.summary || (step.status === "running" ? "执行中..." : "已执行")}</span>
            </div>
          </div>
        ))}
        {!toolSteps.length && <div className="muted-empty">暂无工具调用</div>}
      </div>
    </section>
  );
}

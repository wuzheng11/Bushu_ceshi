import { useState } from "react";
import {
  Check,
  Clipboard,
  Download,
  FileCheck2,
  Lightbulb,
  ListChecks,
  Save,
  SearchCheck,
  Target,
  TriangleAlert,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { AnalysisResult } from "../types";

interface Props {
  result: AnalysisResult | null;
  onSave: () => Promise<void>;
  onExport: () => void;
}

export default function ResultPanel({ result, onSave, onExport }: Props) {
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(result.result_markdown);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  async function saveResult() {
    await onSave();
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  }

  if (!result) {
    return (
      <section className="panel-section result-panel empty">
        <div className="result-empty">
          <SearchCheck size={24} />
          <strong>等待分析结果</strong>
          <span>任务完成后，六部分结构化结果会显示在这里。</span>
        </div>
      </section>
    );
  }

  return (
    <section className="panel-section result-panel">
      <div className="section-heading result-heading">
        <div>
          <span>分析结果</span>
          <strong>#{result.task_id}</strong>
        </div>
        <div className="result-actions">
          <button type="button" title="复制结果" onClick={() => void copyResult()}>
            {copied ? <Check size={16} /> : <Clipboard size={16} />}
          </button>
          <button type="button" title="保存结果" onClick={() => void saveResult()}>
            {saved ? <Check size={16} /> : <Save size={16} />}
          </button>
          <button type="button" title="导出结果" onClick={onExport}>
            <Download size={16} />
          </button>
        </div>
      </div>
      <div className="result-scroll">
        <ResultBlock icon={<Target size={16} />} title="问题定义">
          <p>{result.problem_definition}</p>
        </ResultBlock>
        <ResultBlock icon={<ListChecks size={16} />} title="关键指标">
          <div className="metric-grid">
            {result.key_metrics.map((metric) => (
              <div className="metric-card" key={`${metric.metric_name}-${metric.metric_period}`}>
                <span>{metric.metric_name}</span>
                <strong>
                  {metric.metric_value}
                  <small>{metric.metric_unit}</small>
                </strong>
                <em>{metric.metric_period}</em>
              </div>
            ))}
          </div>
        </ResultBlock>
        <ResultBlock icon={<SearchCheck size={16} />} title="证据列表">
          <div className="evidence-list">
            {result.evidence_list.map((evidence, index) => (
              <div className="evidence-item" key={`${evidence.source_name}-${index}`}>
                <div>
                  <span>{evidence.source_type}</span>
                  <strong>{evidence.source_name}</strong>
                  <em>{Math.round(evidence.confidence * 100)}%</em>
                </div>
                <p>{evidence.evidence_text}</p>
                <small>{evidence.related_metric}</small>
              </div>
            ))}
          </div>
        </ResultBlock>
        <ResultBlock icon={<FileCheck2 size={16} />} title="归因结论">
          <p>{result.conclusion_text}</p>
        </ResultBlock>
        <ResultBlock icon={<TriangleAlert size={16} />} title="待补充数据">
          <p>{result.missing_data_text}</p>
        </ResultBlock>
        <ResultBlock icon={<Lightbulb size={16} />} title="下一步建议">
          <div className="action-text">{result.next_action_text}</div>
        </ResultBlock>
        <details className="markdown-details">
          <summary>查看完整报告 Markdown</summary>
          <ReactMarkdown>{result.result_markdown}</ReactMarkdown>
        </details>
      </div>
    </section>
  );
}

function ResultBlock({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="result-block">
      <h3>
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

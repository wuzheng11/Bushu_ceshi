import { useEffect, useRef, useState } from "react";
import { SendHorizonal } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { formatDateTime } from "../lib/api";
import type { Message } from "../types";

interface Props {
  messages: Message[];
  streamingContent: string;
  disabled: boolean;
  onSend: (content: string) => Promise<void>;
}

const prompts = [
  "请分析最近 30 天商品目录优化问题。重点检查高曝光低点击类目、类目属性完整度与转化变化，并给出下一步动作。",
  "请分析最近 30 天客户行为漏斗，定位访问到加购、加购到下单的主要流失环节和用户分群差异。",
];

export default function ChatPanel({ messages, streamingContent, disabled, onSend }: Props) {
  const [content, setContent] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  async function submit() {
    const value = content.trim();
    if (!value || disabled) return;
    setContent("");
    await onSend(value);
  }

  return (
    <section className="chat-panel">
      <div className="chat-scroll">
        {!messages.length && !streamingContent && (
          <div className="empty-chat">
            <div className="empty-chat-mark">01</div>
            <h2>从一个经营问题开始</h2>
            <p>选择示例问题，或直接描述需要归因的业务现象。</p>
            <div className="prompt-list">
              {prompts.map((prompt) => (
                <button key={prompt} type="button" onClick={() => void onSend(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message) => (
          <article key={message.message_id} className={`message-row ${message.role}`}>
            <div className="message-avatar">{message.role === "user" ? "你" : "析"}</div>
            <div className="message-body">
              <div className="message-meta">
                <strong>{message.role === "user" ? "分析用户" : "归因分析助手"}</strong>
                <span>{formatDateTime(message.created_at)}</span>
              </div>
              <div className={`message-content ${message.message_type === "result" ? "markdown" : ""}`}>
                {message.message_type === "result" ? (
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                ) : (
                  message.content
                )}
              </div>
              {message.attachments.length > 0 && (
                <div className="message-attachments">
                  {message.attachments.map((attachment) => (
                    <span key={attachment.attachment_id}>{attachment.file_name}</span>
                  ))}
                </div>
              )}
            </div>
          </article>
        ))}
        {streamingContent && (
          <article className="message-row assistant">
            <div className="message-avatar">析</div>
            <div className="message-body">
              <div className="message-meta">
                <strong>归因分析助手</strong>
                <span>生成中</span>
              </div>
              <div className="message-content markdown">
                <ReactMarkdown>{streamingContent}</ReactMarkdown>
              </div>
            </div>
          </article>
        )}
        <div ref={endRef} />
      </div>
      <div className="composer">
        <textarea
          value={content}
          disabled={disabled}
          placeholder="描述业务问题，支持连续追问..."
          onChange={(event) => setContent(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />
        <button type="button" className="send-button" disabled={disabled || !content.trim()} onClick={() => void submit()}>
          <SendHorizonal size={19} />
          <span>{disabled ? "分析中" : "发送"}</span>
        </button>
      </div>
    </section>
  );
}

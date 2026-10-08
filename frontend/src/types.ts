export interface User {
  id: number;
  external_user_id: string;
  username: string;
  display_name: string;
  role: "analysis_user" | "admin";
  status: string;
  created_at: string;
}

export interface Conversation {
  conversation_id: number;
  title: string;
  status: "active" | "archived" | "deleted";
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageAttachment {
  attachment_id: number;
  file_name: string;
  file_type: string;
  file_size: number;
}

export interface Message {
  message_id: number;
  role: "user" | "assistant" | "system";
  message_type: string;
  content: string;
  tool_name?: string | null;
  tool_status?: string | null;
  seq_no: number;
  attachments: MessageAttachment[];
  created_at: string;
}

export interface Attachment {
  attachment_id: number;
  conversation_id: number;
  message_id: number | null;
  file_name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  parse_status: string;
  created_at: string;
}

export interface AnalysisTask {
  task_id: number;
  conversation_id: number;
  task_status: "queued" | "running" | "success" | "failed" | "cancelled";
  current_step: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface MetricItem {
  metric_name: string;
  metric_value: number | string;
  metric_unit: string;
  metric_period: string;
}

export interface EvidenceItem {
  source_type: string;
  source_name: string;
  evidence_text: string;
  related_metric: string;
  confidence: number;
}

export interface AnalysisResult {
  result_id: number;
  task_id: number;
  problem_definition: string;
  key_metrics: MetricItem[];
  evidence_list: EvidenceItem[];
  conclusion_text: string;
  missing_data_text: string;
  next_action_text: string;
  result_markdown: string;
  result_file_path: string | null;
  created_at: string;
}

export interface SocketEvent {
  event: string;
  task_id?: number;
  conversation_id?: number;
  timestamp?: string;
  message_id?: number;
  delta_text?: string;
  tool_name?: string;
  tool_result_summary?: string;
  tool_status?: string;
  task_status?: AnalysisTask["task_status"];
  current_step?: string;
  result_id?: number;
  error_message?: string;
  finished_at?: string;
}

export interface ToolStep {
  tool_name: string;
  status: "running" | "success" | "failed";
  summary?: string;
  task_id?: number;
}

export interface ConfigItem {
  config_key: string;
  config_value: string;
  config_group: string;
  updated_at: string;
}

export interface LogItem {
  id: number;
  task_id: number;
  conversation_id: number;
  log_level: string;
  log_type: string;
  log_content: string;
  created_at: string;
}

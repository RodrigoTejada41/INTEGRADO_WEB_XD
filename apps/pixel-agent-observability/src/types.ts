export type AgentStatus = "running" | "idle" | "error" | "done" | "unknown";
export type EventSource = "log" | "file" | "websocket" | "command" | "control";

export interface AgentEvent {
  agent_id: string;
  status: AgentStatus;
  task: string;
  log: string;
  timestamp: string;
  source: EventSource;
}

export interface AgentSummary {
  agent_id: string;
  status: AgentStatus;
  task: string;
  last_update: string;
  last_source: EventSource;
}

export interface DashboardSnapshot {
  agents: AgentSummary[];
  logs: AgentEvent[];
  timeline: AgentEvent[];
}

export interface AdapterHealth {
  fileWatcher: boolean;
  websocket: boolean;
  commandScan: boolean;
}


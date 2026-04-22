import { AgentEvent, AgentStatus, EventSource } from "./types";

const STATUS_MAP: Record<string, AgentStatus> = {
  running: "running",
  started: "running",
  start: "running",
  idle: "idle",
  waiting: "idle",
  done: "done",
  success: "done",
  completed: "done",
  complete: "done",
  failed: "error",
  error: "error"
};

function normalizeStatus(value?: string): AgentStatus {
  if (!value) {
    return "unknown";
  }
  const normalized = value.trim().toLowerCase();
  return STATUS_MAP[normalized] ?? "unknown";
}

function findByRegex(line: string, patterns: RegExp[]): string | undefined {
  for (const pattern of patterns) {
    const match = line.match(pattern);
    if (match?.[1]) {
      return match[1].trim();
    }
  }
  return undefined;
}

function parseMaybeJson(raw: string): Partial<AgentEvent> {
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const agentId = String(parsed.agent_id ?? parsed.agentId ?? parsed.agent ?? "").trim();
    const task = String(parsed.task ?? parsed.action ?? parsed.job ?? "").trim();
    const status = normalizeStatus(String(parsed.status ?? ""));
    const timestamp = String(parsed.timestamp ?? parsed.ts ?? parsed.time ?? "").trim();
    const log = String(parsed.log ?? parsed.message ?? raw).trim();

    return {
      agent_id: agentId || undefined,
      task: task || undefined,
      status,
      timestamp: timestamp || undefined,
      log
    };
  } catch {
    return {};
  }
}

export class LogParser {
  parseLine(rawLine: string, source: EventSource = "log"): AgentEvent | null {
    const line = rawLine.trim();
    if (!line) {
      return null;
    }

    const fromJson = parseMaybeJson(line);
    const agent_id =
      fromJson.agent_id ??
      findByRegex(line, [/agent[_-]?id[:=]\s*([a-zA-Z0-9._-]+)/i, /\[agent[:=]\s*([a-zA-Z0-9._-]+)\]/i]) ??
      "pixel-agent-unknown";
    const task =
      fromJson.task ??
      findByRegex(line, [/task[:=]\s*"?([a-zA-Z0-9._:/-]+)"?/i, /job[:=]\s*"?([a-zA-Z0-9._:/-]+)"?/i]) ??
      "unknown-task";
    const status =
      fromJson.status && fromJson.status !== "unknown"
        ? fromJson.status
        : normalizeStatus(findByRegex(line, [/status[:=]\s*"?([a-zA-Z_]+)"?/i]));
    const timestamp =
      fromJson.timestamp ??
      findByRegex(line, [/timestamp[:=]\s*([0-9T:.+\-Z]+)/i, /^\[([0-9T:.+\-Z]+)\]/]) ??
      new Date().toISOString();
    const log = fromJson.log ?? line;

    return {
      agent_id,
      task,
      status,
      timestamp,
      log,
      source
    };
  }
}

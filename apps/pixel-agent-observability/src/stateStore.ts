import { EventEmitter } from "node:events";
import { AgentEvent, AgentSummary, DashboardSnapshot } from "./types";

export class StateStore extends EventEmitter {
  private readonly agents = new Map<string, AgentSummary>();
  private readonly logs: AgentEvent[] = [];
  private readonly timeline: AgentEvent[] = [];
  private readonly maxEvents: number;

  constructor(maxEvents = 2000) {
    super();
    this.maxEvents = maxEvents;
  }

  upsertEvent(event: AgentEvent): void {
    const previous = this.agents.get(event.agent_id);
    this.agents.set(event.agent_id, {
      agent_id: event.agent_id,
      status: event.status,
      task: event.task,
      last_update: event.timestamp,
      last_source: event.source
    });

    this.logs.push(event);
    this.timeline.push(event);

    if (this.logs.length > this.maxEvents) {
      this.logs.splice(0, this.logs.length - this.maxEvents);
    }
    if (this.timeline.length > this.maxEvents) {
      this.timeline.splice(0, this.timeline.length - this.maxEvents);
    }

    if (!previous || previous.status !== event.status || previous.task !== event.task) {
      this.emit("agent-change", event.agent_id);
    }
    this.emit("event", event);
  }

  snapshot(): DashboardSnapshot {
    const agents = Array.from(this.agents.values()).sort((a, b) => {
      return new Date(b.last_update).getTime() - new Date(a.last_update).getTime();
    });
    return {
      agents,
      logs: [...this.logs],
      timeline: [...this.timeline]
    };
  }
}


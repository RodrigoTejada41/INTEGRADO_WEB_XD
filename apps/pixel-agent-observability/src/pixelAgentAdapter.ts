import * as fsp from "node:fs/promises";
import * as path from "node:path";
import * as vscode from "vscode";
import { LogParser } from "./logParser";
import { FileWatcher } from "./fileWatcher";
import { detectPixelProcesses } from "./processProbe";
import { StateStore } from "./stateStore";
import { AdapterHealth, AgentEvent } from "./types";
import { PixelWebSocketClient } from "./websocketClient";

const DEFAULT_WATCH_TARGETS = [".pixel-agent", "agents", "logs"];

export class PixelAgentAdapter {
  private readonly parser = new LogParser();
  private readonly store = new StateStore();
  private readonly health: AdapterHealth = {
    fileWatcher: false,
    websocket: false,
    commandScan: false
  };
  private fileWatcher: FileWatcher | null = null;
  private webSocketClient: PixelWebSocketClient | null = null;
  private commandPollTimer: NodeJS.Timeout | null = null;
  private logDiscoveryTimer: NodeJS.Timeout | null = null;
  private processProbeTimer: NodeJS.Timeout | null = null;
  private readonly knownPixelCommands = new Set<string>();

  constructor(private readonly context: vscode.ExtensionContext) {}

  async start(): Promise<void> {
    this.store.upsertEvent(
      this.toEvent({
        agent_id: "pixel-observability",
        status: "idle",
        task: "bootstrap",
        log: "Observability adapter initialized",
        source: "control"
      })
    );
    this.discoverInstalledPixelExtensions();
    this.startFileWatcher();
    this.startWebSocket();
    await this.scanCommands();
    await this.discoverExistingLogs();
    await this.probeProcesses();
    this.commandPollTimer = setInterval(() => {
      this.scanCommands().catch(() => undefined);
    }, 5000);
    this.logDiscoveryTimer = setInterval(() => {
      this.discoverExistingLogs().catch(() => undefined);
    }, 15000);
    this.processProbeTimer = setInterval(() => {
      this.probeProcesses().catch(() => undefined);
    }, 8000);
  }

  async stop(): Promise<void> {
    if (this.commandPollTimer) {
      clearInterval(this.commandPollTimer);
      this.commandPollTimer = null;
    }
    if (this.logDiscoveryTimer) {
      clearInterval(this.logDiscoveryTimer);
      this.logDiscoveryTimer = null;
    }
    if (this.processProbeTimer) {
      clearInterval(this.processProbeTimer);
      this.processProbeTimer = null;
    }
    if (this.fileWatcher) {
      await this.fileWatcher.stop();
      this.fileWatcher = null;
    }
    this.webSocketClient?.stop();
    this.webSocketClient = null;
  }

  getStore(): StateStore {
    return this.store;
  }

  getHealth(): AdapterHealth {
    return { ...this.health };
  }

  async refresh(): Promise<void> {
    await this.scanCommands();
    this.store.upsertEvent(
      this.toEvent({
        agent_id: "pixel-observability",
        status: "idle",
        task: "refresh",
        log: "Sources refreshed"
      })
    );
  }

  async safeStart(): Promise<void> {
    const command = this.findLikelyPixelCommand(["start", "run", "execute"]);
    if (command) {
      await vscode.commands.executeCommand(command);
      this.store.upsertEvent(
        this.toEvent({
          agent_id: "pixel-control",
          status: "running",
          task: "safe_start_command",
          log: `Executed command ${command}`,
          source: "control"
        })
      );
      return;
    }
    await this.writeControlFlag("start.flag");
  }

  async safeStop(): Promise<void> {
    const command = this.findLikelyPixelCommand(["stop", "cancel", "abort"]);
    if (command) {
      await vscode.commands.executeCommand(command);
      this.store.upsertEvent(
        this.toEvent({
          agent_id: "pixel-control",
          status: "idle",
          task: "safe_stop_command",
          log: `Executed command ${command}`,
          source: "control"
        })
      );
      return;
    }
    await this.writeControlFlag("stop.flag");
  }

  private startFileWatcher(): void {
    const rootPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!rootPath) {
      return;
    }
    const watchTargets = DEFAULT_WATCH_TARGETS.map((entry) => path.join(rootPath, entry));
    this.fileWatcher = new FileWatcher(rootPath, watchTargets, (event) => this.store.upsertEvent(this.toEvent(event)));
    this.fileWatcher
      .start()
      .then(() => {
        this.health.fileWatcher = true;
      })
      .catch(() => {
        this.health.fileWatcher = false;
      });
  }

  private startWebSocket(): void {
    this.webSocketClient = new PixelWebSocketClient(
      (event) => this.store.upsertEvent(this.toEvent(event)),
      (connected) => {
        this.health.websocket = connected;
        this.store.upsertEvent(
          this.toEvent({
            agent_id: "pixel-websocket",
            status: connected ? "running" : "idle",
            task: "connection",
            log: connected ? "WebSocket connected" : "WebSocket disconnected",
            source: "websocket"
          })
        );
      }
    );
    this.webSocketClient.start();
  }

  private async scanCommands(): Promise<void> {
    const allCommands = await vscode.commands.getCommands(true);
    const pixelCommands = allCommands.filter((command) => command.toLowerCase().includes("pixel"));
    this.health.commandScan = true;

    for (const command of pixelCommands) {
      if (this.knownPixelCommands.has(command)) {
        continue;
      }
      this.knownPixelCommands.add(command);
      const namespace = command.includes(".") ? command.split(".")[0] : "pixel-command-registry";
      this.store.upsertEvent(
        this.toEvent({
          agent_id: `command:${namespace}`,
          status: "running",
          task: "command_discovered",
          log: `Discovered command ${command}`,
          source: "command"
        })
      );
    }
  }

  private discoverInstalledPixelExtensions(): void {
    const pixelExtensions = vscode.extensions.all.filter((ext) => {
      const haystack = `${ext.id} ${ext.packageJSON?.displayName ?? ""} ${ext.packageJSON?.name ?? ""}`.toLowerCase();
      return haystack.includes("pixel") || haystack.includes("agent");
    });

    if (pixelExtensions.length === 0) {
      this.store.upsertEvent(
        this.toEvent({
          agent_id: "pixel-extension-discovery",
          status: "idle",
          task: "scan_extensions",
          log: "No Pixel-like extension detected yet",
          source: "command"
        })
      );
      return;
    }

    for (const ext of pixelExtensions.slice(0, 20)) {
      this.store.upsertEvent(
        this.toEvent({
          agent_id: `extension:${ext.id}`,
          status: ext.isActive ? "running" : "idle",
          task: "extension_discovered",
          log: `${ext.id} (${ext.packageJSON?.displayName ?? ext.packageJSON?.name ?? "unknown"})`,
          source: "command"
        })
      );
    }
  }

  private async discoverExistingLogs(): Promise<void> {
    if (!vscode.workspace.workspaceFolders?.length) {
      return;
    }

    const files = await vscode.workspace.findFiles("**/*.{log,json,txt}", "**/node_modules/**", 300);
    const candidates = files
      .map((item) => item.fsPath)
      .filter((filePath) => {
        const lower = filePath.toLowerCase();
        return lower.includes("pixel") || lower.includes("agent") || lower.includes(`${path.sep}logs${path.sep}`);
      })
      .slice(0, 80);

    for (const filePath of candidates) {
      const tail = await this.readTail(filePath, 10);
      for (const line of tail) {
        const parsed = this.parser.parseLine(line, "log");
        if (parsed) {
          this.store.upsertEvent(parsed);
        }
      }
    }
  }

  private async readTail(filePath: string, maxLines: number): Promise<string[]> {
    try {
      const content = await fsp.readFile(filePath, "utf-8");
      const lines = content.split(/\r?\n/).filter(Boolean);
      return lines.slice(-maxLines);
    } catch {
      return [];
    }
  }

  private async probeProcesses(): Promise<void> {
    const processNames = await detectPixelProcesses();
    if (processNames.length === 0) {
      return;
    }
    for (const name of processNames.slice(0, 10)) {
      this.store.upsertEvent(
        this.toEvent({
          agent_id: `process:${name}`,
          status: "running",
          task: "process_probe",
          log: `Detected running process ${name}`,
          source: "command"
        })
      );
    }
  }

  private findLikelyPixelCommand(keywords: string[]): string | undefined {
    const commandList = Array.from(this.knownPixelCommands);
    return commandList.find((command) => {
      const commandLower = command.toLowerCase();
      return keywords.some((keyword) => commandLower.includes(keyword));
    });
  }

  private async writeControlFlag(fileName: string): Promise<void> {
    const rootPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!rootPath) {
      return;
    }
    const controlDir = path.join(rootPath, ".pixel-agent", "control");
    await fsp.mkdir(controlDir, { recursive: true });
    const flagPath = path.join(controlDir, fileName);
    await fsp.writeFile(flagPath, new Date().toISOString(), "utf-8");
    this.store.upsertEvent(
      this.toEvent({
        agent_id: "pixel-control",
        status: "idle",
        task: "flag_written",
        log: `Wrote control flag ${flagPath}`,
        source: "control"
      })
    );
  }

  private toEvent(partial: Partial<AgentEvent>): AgentEvent {
    const line = JSON.stringify(partial);
    return (
      this.parser.parseLine(line, partial.source ?? "log") ?? {
        agent_id: "pixel-agent-unknown",
        status: "unknown",
        task: "unknown-task",
        log: line,
        timestamp: new Date().toISOString(),
        source: partial.source ?? "log"
      }
    );
  }
}

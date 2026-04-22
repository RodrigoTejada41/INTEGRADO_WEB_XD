import * as fsp from "node:fs/promises";
import * as path from "node:path";
import chokidar, { FSWatcher } from "chokidar";
import { AgentEvent } from "./types";
import { LogParser } from "./logParser";

type EventHandler = (event: AgentEvent) => void;

function normalizeToAbsolute(cwd: string, target: string): string {
  return path.isAbsolute(target) ? target : path.resolve(cwd, target);
}

export class FileWatcher {
  private watcher: FSWatcher | null = null;
  private readonly parser = new LogParser();
  private readonly offsets = new Map<string, number>();

  constructor(
    private readonly workspacePath: string,
    private readonly watchPaths: string[],
    private readonly onEvent: EventHandler
  ) {}

  async start(): Promise<void> {
    const normalizedPaths = this.watchPaths.map((watchPath) => normalizeToAbsolute(this.workspacePath, watchPath));

    this.watcher = chokidar.watch(normalizedPaths, {
      ignoreInitial: false,
      persistent: true,
      awaitWriteFinish: {
        stabilityThreshold: 200,
        pollInterval: 100
      }
    });

    this.watcher.on("add", (filePath) => {
      this.processFile(filePath).catch(() => undefined);
    });
    this.watcher.on("change", (filePath) => {
      this.processFile(filePath).catch(() => undefined);
    });
  }

  async stop(): Promise<void> {
    if (this.watcher) {
      await this.watcher.close();
      this.watcher = null;
    }
  }

  private async processFile(filePath: string): Promise<void> {
    try {
      const stat = await fsp.stat(filePath);
      if (!stat.isFile()) {
        return;
      }
      if (!this.isLogLike(filePath)) {
        return;
      }

      const previousOffset = this.offsets.get(filePath) ?? 0;
      const nextOffset = stat.size;
      const start = Math.min(previousOffset, stat.size);
      const readLength = nextOffset - start;
      if (readLength <= 0) {
        return;
      }

      const handle = await fsp.open(filePath, "r");
      const buffer = Buffer.alloc(readLength);
      await handle.read(buffer, 0, readLength, start);
      await handle.close();

      this.offsets.set(filePath, nextOffset);
      const chunk = buffer.toString("utf-8");
      const lines = chunk.split(/\r?\n/);
      for (const line of lines) {
        const event = this.parser.parseLine(line, "file");
        if (event) {
          this.onEvent(event);
        }
      }
    } catch (error) {
      const fallback = this.parser.parseLine(
        `agent_id=pixel-agent-filewatch status=error task=file_watcher message=${String(error)}`,
        "file"
      );
      if (fallback) {
        this.onEvent(fallback);
      }
    }
  }

  private isLogLike(filePath: string): boolean {
    const extension = path.extname(filePath).toLowerCase();
    return extension === ".log" || extension === ".json" || extension === ".txt" || extension === "";
  }
}

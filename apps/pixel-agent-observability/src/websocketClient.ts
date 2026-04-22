import WebSocket, { RawData } from "ws";
import { AgentEvent } from "./types";
import { LogParser } from "./logParser";

type EventHandler = (event: AgentEvent) => void;
type StatusHandler = (connected: boolean) => void;

const DEFAULT_PORTS = [7777, 8080, 3001, 4000, 5050, 8765, 9000, 9229];

export class PixelWebSocketClient {
  private socket: WebSocket | null = null;
  private stopped = false;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private readonly parser = new LogParser();

  constructor(
    private readonly onEvent: EventHandler,
    private readonly onStatus: StatusHandler,
    private readonly ports = DEFAULT_PORTS
  ) {}

  start(): void {
    this.stopped = false;
    this.tryConnectSequence(0);
  }

  stop(): void {
    this.stopped = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
    this.onStatus(false);
  }

  private tryConnectSequence(startPortIndex: number): void {
    if (this.stopped) {
      return;
    }

    let index = startPortIndex;
    const tryNext = () => {
      if (this.stopped) {
        return;
      }
      if (index >= this.ports.length) {
        this.onStatus(false);
        this.scheduleReconnect(3_000);
        return;
      }
      const port = this.ports[index];
      const endpoint = `ws://127.0.0.1:${port}`;
      const socket = new WebSocket(endpoint);
      let settled = false;

      const fail = () => {
        if (settled) {
          return;
        }
        settled = true;
        socket.removeAllListeners();
        socket.close();
        index += 1;
        tryNext();
      };

      socket.once("open", () => {
        if (settled || this.stopped) {
          socket.close();
          return;
        }
        settled = true;
        this.socket = socket;
        this.onStatus(true);
        socket.send(JSON.stringify({ type: "subscribe", topics: ["agent.*", "pixel-agent.*", "logs"] }));
        socket.on("message", (data: RawData) => this.handleMessage(data.toString("utf-8")));
        socket.on("close", () => {
          this.onStatus(false);
          this.scheduleReconnect(2_000);
        });
        socket.on("error", () => {
          this.onStatus(false);
        });
      });

      socket.once("error", fail);
      setTimeout(fail, 800);
    };

    tryNext();
  }

  private handleMessage(payload: string): void {
    const event = this.parser.parseLine(payload, "websocket");
    if (event) {
      this.onEvent(event);
    }
  }

  private scheduleReconnect(ms: number): void {
    if (this.stopped) {
      return;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.reconnectTimer = setTimeout(() => this.tryConnectSequence(0), ms);
  }
}

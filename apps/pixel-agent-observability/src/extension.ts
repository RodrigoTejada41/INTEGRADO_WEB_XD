import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { PixelAgentAdapter } from "./pixelAgentAdapter";

class DashboardPanel {
  private panel: vscode.WebviewPanel | null = null;
  private pendingUpdate = false;

  constructor(private readonly context: vscode.ExtensionContext, private readonly adapter: PixelAgentAdapter) {}

  show(): void {
    if (this.panel) {
      this.panel.reveal(vscode.ViewColumn.One);
      return;
    }

    this.panel = vscode.window.createWebviewPanel(
      "pixelObservabilityDashboard",
      "Pixel Agent Observability",
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.file(path.join(this.context.extensionPath, "webview"))]
      }
    );

    this.panel.webview.html = this.getHtml(this.panel.webview);
    this.panel.onDidDispose(() => {
      this.panel = null;
    });

    const store = this.adapter.getStore();
    store.on("event", () => this.queueUpdate());
    this.queueUpdate();
  }

  dispose(): void {
    this.panel?.dispose();
  }

  private queueUpdate(): void {
    if (!this.panel) {
      return;
    }
    if (this.pendingUpdate) {
      return;
    }
    this.pendingUpdate = true;
    setTimeout(() => {
      this.pendingUpdate = false;
      if (!this.panel) {
        return;
      }
      this.panel.webview.postMessage({
        type: "snapshot",
        payload: this.adapter.getStore().snapshot(),
        health: this.adapter.getHealth()
      });
    }, 150);
  }

  private getHtml(webview: vscode.Webview): string {
    const htmlPath = path.join(this.context.extensionPath, "webview", "dashboard.html");
    const rawHtml = fs.readFileSync(htmlPath, "utf-8");
    const scriptUri = webview.asWebviewUri(vscode.Uri.file(path.join(this.context.extensionPath, "webview", "app.js")));
    const styleUri = webview.asWebviewUri(vscode.Uri.file(path.join(this.context.extensionPath, "webview", "styles.css")));
    const nonce = getNonce();

    return rawHtml
      .replaceAll("{{STYLE_URI}}", styleUri.toString())
      .replaceAll("{{SCRIPT_URI}}", scriptUri.toString())
      .replaceAll("{{NONCE}}", nonce);
  }
}

function getNonce(): string {
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let value = "";
  for (let i = 0; i < 32; i += 1) {
    value += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return value;
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const adapter = new PixelAgentAdapter(context);
  await adapter.start();
  const dashboard = new DashboardPanel(context, adapter);

  context.subscriptions.push(
    vscode.commands.registerCommand("pixelObservability.openDashboard", () => dashboard.show()),
    vscode.commands.registerCommand("pixelObservability.refresh", () => adapter.refresh()),
    vscode.commands.registerCommand("pixelObservability.safeStart", () => adapter.safeStart()),
    vscode.commands.registerCommand("pixelObservability.safeStop", () => adapter.safeStop()),
    {
      dispose: () => {
        dashboard.dispose();
        void adapter.stop();
      }
    }
  );
}

export function deactivate(): void {
  // Managed through extension subscriptions.
}

# Pixel Agent Observability (VS Code Extension)

Production-oriented observability and safe control layer for Pixel Agent integration as a black box.

## What It Monitors

- Log interception from workspace directories
- File watching on:
  - `.pixel-agent/`
  - `agents/`
  - `logs/`
- Command registry scanning (`vscode.commands.getCommands`)
- WebSocket auto-discovery on localhost common ports with reconnect

## Unified Event Format

All sources are normalized in `pixelAgentAdapter` as:

```json
{
  "agent_id": "string",
  "status": "running | idle | error | done | unknown",
  "task": "string",
  "log": "string",
  "timestamp": "ISO-8601"
}
```

## Dashboard

- Agents Panel: discovered agents and current status
- Logs Panel: real-time stream, error highlighting
- Details Panel: selected agent metadata + execution trace timeline

## Safe Control Layer

If no direct Pixel Agent control command exists:

- Writes fallback control flags:
  - `.pixel-agent/control/start.flag`
  - `.pixel-agent/control/stop.flag`

If command hooks are discovered, triggers the best matching Pixel command.

## Commands

- `Pixel Observability: Open Dashboard`
- `Pixel Observability: Refresh Sources`
- `Pixel Observability: Safe Start Agent`
- `Pixel Observability: Safe Stop Agent`

## Development

```powershell
cd apps/pixel-agent-observability
npm install
npm run build
npm run test
```


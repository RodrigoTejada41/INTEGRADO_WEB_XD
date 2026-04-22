import test from "node:test";
import assert from "node:assert/strict";
import { LogParser } from "../logParser";

test("parses key-value log lines", () => {
  const parser = new LogParser();
  const event = parser.parseLine("agent_id=ag-1 task=sync_customers status=running timestamp=2026-04-19T13:00:00Z");

  assert.ok(event);
  assert.equal(event.agent_id, "ag-1");
  assert.equal(event.task, "sync_customers");
  assert.equal(event.status, "running");
});

test("parses json logs with status mapping", () => {
  const parser = new LogParser();
  const event = parser.parseLine(
    JSON.stringify({
      agent_id: "ag-2",
      task: "import_orders",
      status: "completed",
      timestamp: "2026-04-19T13:10:00Z",
      message: "Done"
    })
  );

  assert.ok(event);
  assert.equal(event.agent_id, "ag-2");
  assert.equal(event.status, "done");
  assert.equal(event.task, "import_orders");
});

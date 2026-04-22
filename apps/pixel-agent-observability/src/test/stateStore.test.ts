import test from "node:test";
import assert from "node:assert/strict";
import { StateStore } from "../stateStore";

test("keeps latest state by agent and bounded log history", () => {
  const store = new StateStore(2);
  store.upsertEvent({
    agent_id: "ag-1",
    status: "running",
    task: "t1",
    log: "start",
    source: "log",
    timestamp: "2026-04-19T14:00:00Z"
  });
  store.upsertEvent({
    agent_id: "ag-1",
    status: "done",
    task: "t1",
    log: "done",
    source: "log",
    timestamp: "2026-04-19T14:01:00Z"
  });
  store.upsertEvent({
    agent_id: "ag-2",
    status: "idle",
    task: "t2",
    log: "wait",
    source: "log",
    timestamp: "2026-04-19T14:01:30Z"
  });

  const snapshot = store.snapshot();
  assert.equal(snapshot.agents.length, 2);
  assert.equal(snapshot.logs.length, 2);
  const ag1 = snapshot.agents.find((a) => a.agent_id === "ag-1");
  assert.ok(ag1);
  assert.equal(ag1.status, "done");
});


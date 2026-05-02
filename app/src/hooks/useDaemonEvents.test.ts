import { describe, expect, it } from "vitest";
import { parseSSEFrame } from "./useDaemonEvents";

describe("parseSSEFrame", () => {
  it("parses a daemon.ready frame", () => {
    const frame =
      'event: daemon.ready\ndata: {"network":"testnet","readonly":false,"ipc_version":1}';
    const event = parseSSEFrame(frame);
    expect(event).not.toBeNull();
    expect(event?.type).toBe("daemon.ready");
    expect(event?.data).toEqual({
      network: "testnet",
      readonly: false,
      ipc_version: 1,
    });
  });

  it("parses anchor.batch_complete with explorer URL", () => {
    const frame =
      'event: anchor.batch_complete\ndata: {"game_id":"s42","txid":"ABC","rounds":["1","2"],"explorer_url":"https://x"}';
    const event = parseSSEFrame(frame);
    expect(event?.type).toBe("anchor.batch_complete");
    expect((event?.data as { game_id: string }).game_id).toBe("s42");
  });

  it("parses game.state_changed event", () => {
    const event = parseSSEFrame('event: game.state_changed\ndata: {"game_id":"s42"}');
    expect(event?.type).toBe("game.state_changed");
  });

  it("parses error event", () => {
    const event = parseSSEFrame(
      'event: error\ndata: {"level":"warn","code":"ANCHOR_PENDING","message":"x"}',
    );
    expect(event?.type).toBe("error");
  });

  it("returns null on missing event line", () => {
    const event = parseSSEFrame('data: {"foo":"bar"}');
    expect(event).toBeNull();
  });

  it("returns null on malformed JSON", () => {
    const event = parseSSEFrame("event: daemon.ready\ndata: not-json");
    expect(event).toBeNull();
  });

  it("supports multi-line data", () => {
    const event = parseSSEFrame('event: daemon.ready\ndata: {"a":1,\ndata: "b":2}');
    expect(event).not.toBeNull();
    expect(event?.data).toEqual({ a: 1, b: 2 });
  });

  it("treats empty data as empty object", () => {
    const event = parseSSEFrame("event: daemon.shutdown\ndata: ");
    expect(event?.type).toBe("daemon.shutdown");
    expect(event?.data).toEqual({});
  });
});

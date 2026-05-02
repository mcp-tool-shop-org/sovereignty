import { useState } from "react";
import { Link } from "react-router-dom";
import { useDaemon } from "../hooks/useDaemon";

export default function Settings() {
  const { status, config, error, stopDaemon, startDaemon } = useDaemon();
  const [busy, setBusy] = useState(false);

  async function restart() {
    setBusy(true);
    try {
      if (status === "running") await stopDaemon();
      await startDaemon(config?.readonly ?? true, config?.network);
    } catch {
      // surfaced via context error state
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <nav>
        <Link to="/">Home</Link>
      </nav>
      <h1>Settings</h1>
      <p>
        Daemon: <strong>{status}</strong>
      </p>
      {config ? (
        <dl style={{ marginTop: "1rem" }}>
          <dt>URL</dt>
          <dd>http://127.0.0.1:{config.port}</dd>
          <dt>Port</dt>
          <dd>{config.port}</dd>
          <dt>Network</dt>
          <dd>{config.network}</dd>
          <dt>Mode</dt>
          <dd>{config.readonly ? "readonly" : "full"}</dd>
          <dt>Started</dt>
          <dd>{config.started_iso}</dd>
          <dt>IPC version</dt>
          <dd>{config.ipc_version}</dd>
        </dl>
      ) : (
        <p>(no daemon config available)</p>
      )}
      {error ? <p style={{ color: "#ff8c8c" }}>Error: {error}</p> : null}
      <button
        type="button"
        onClick={restart}
        disabled={busy || status === "loading"}
        style={{ marginTop: "1.5rem" }}
      >
        {busy ? "Restarting..." : "Restart Daemon"}
      </button>
    </main>
  );
}

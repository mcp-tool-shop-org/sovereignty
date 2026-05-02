import { Link } from "react-router-dom";
import { useDaemon } from "../hooks/useDaemon";

export default function Index() {
  const { status, config, error } = useDaemon();

  return (
    <main>
      <h1>Sovereignty</h1>
      <p>
        Status: <DaemonStatusPill />
        {config ? ` (port ${config.port}, ${config.network})` : null}
      </p>
      {error ? <p style={{ color: "#ff8c8c" }}>Error: {error}</p> : null}
      {status === "loading" ? <p>Connecting to daemon...</p> : null}
      <nav style={{ marginTop: "1.5rem" }}>
        <Link to="/audit">Audit</Link>
        <Link to="/game">Game</Link>
        <Link to="/settings">Settings</Link>
      </nav>
    </main>
  );
}

function DaemonStatusPill() {
  const { status } = useDaemon();
  const label =
    status === "loading"
      ? "loading"
      : status === "running"
        ? "running"
        : status === "stale"
          ? "stale"
          : status === "error"
            ? "error"
            : "stopped";
  const cls =
    status === "running"
      ? "status-pill running"
      : status === "error"
        ? "status-pill error"
        : "status-pill";
  return <span className={cls}>{label}</span>;
}

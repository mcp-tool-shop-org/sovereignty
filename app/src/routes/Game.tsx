import { Link } from "react-router-dom";
import { useDaemon } from "../hooks/useDaemon";

export default function Game() {
  const { status, error } = useDaemon();

  return (
    <main>
      <nav>
        <Link to="/">Home</Link>
      </nav>
      <h1>Game shell</h1>
      <p>Coming in Wave 5.</p>
      <p>
        Daemon: <strong>{status}</strong>
      </p>
      {error ? <p style={{ color: "#ff8c8c" }}>Error: {error}</p> : null}
    </main>
  );
}

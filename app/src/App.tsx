import { Route, Routes } from "react-router-dom";
import { DaemonDisconnectedBanner } from "./components/DaemonDisconnectedBanner";
import { DaemonProvider } from "./hooks/useDaemon";
import Audit from "./routes/Audit";
import Game from "./routes/Game";
import Index from "./routes/Index";
import Settings from "./routes/Settings";

export default function App() {
  return (
    <DaemonProvider>
      <DaemonDisconnectedBanner />
      <Routes>
        <Route path="/" element={<Index />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/game" element={<Game />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </DaemonProvider>
  );
}

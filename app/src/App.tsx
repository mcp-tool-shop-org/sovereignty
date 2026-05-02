import { Route, Routes } from "react-router-dom";
import { DaemonDisconnectedBanner } from "./components/DaemonDisconnectedBanner";
import { PanicModal } from "./components/PanicModal";
import { DaemonProvider } from "./hooks/useDaemon";
import Audit from "./routes/Audit";
import Game from "./routes/Game";
import Index from "./routes/Index";
import Settings from "./routes/Settings";

// Stage 9-D Theme 1 (WEB-UI-D-012): PanicModal mount point is OUTSIDE
// <DaemonProvider> on Mike's lock. A shell panic that prevents the
// DaemonProvider from initializing must still surface the modal — that's
// the whole point of the surface. Mounting inside the provider would couple
// panic visibility to daemon state. PanicModal listens to the Tauri
// `shell-panic` event independently of any daemon connection.
export default function App() {
  return (
    <>
      <PanicModal />
      <DaemonProvider>
        <DaemonDisconnectedBanner />
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/game" element={<Game />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </DaemonProvider>
    </>
  );
}

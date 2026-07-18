import { Routes, Route } from "react-router-dom";
import AppShell from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import Architecture from "./pages/Architecture";
import X402Lab from "./pages/X402Lab";
import SignalDetail from "./pages/SignalDetail";
import Pitch from "./pages/Pitch";
import WalletSetup from "./pages/WalletSetup";
import JudgeDemo from "./pages/JudgeDemo";
import PitchDeck from "./pages/PitchDeck";
import Economics from "./pages/Economics";
import Methodology from "./pages/Methodology";

export default function App() {
  return (
    <Routes>
      <Route path="pitch-deck" element={<PitchDeck />} />
      <Route path="demo/embed" element={<JudgeDemo embed />} />
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="economics" element={<Economics />} />
        <Route path="methodology" element={<Methodology />} />
        <Route path="demo" element={<JudgeDemo />} />
        <Route path="strategy" element={<Pitch />} />
        <Route path="architecture" element={<Architecture />} />
        <Route path="wallet" element={<WalletSetup />} />
        <Route path="x402-lab" element={<X402Lab />} />
        <Route path="signals/:id" element={<SignalDetail />} />
      </Route>
    </Routes>
  );
}

import { ShieldCheck } from "lucide-react";
import { NavLink, Route, Routes } from "react-router-dom";
import { ChatPage } from "./routes/ChatPage";
import { UploadPage } from "./routes/UploadPage";
import { EvalDashboardPage } from "./routes/EvalDashboardPage";

const NAV_LINKS = [
  { to: "/", label: "Chat", end: true },
  { to: "/upload", label: "Documents", end: false },
  { to: "/eval", label: "Evaluation", end: false },
];

function App() {
  return (
    <div className="min-h-screen bg-paper dark:bg-paper-dark">
      <header className="bg-brand-700 dark:bg-brand-900">
        <nav className="mx-auto flex h-16 max-w-3xl items-center gap-2 px-4">
          <div className="flex items-center gap-2 pr-6">
            <ShieldCheck className="h-6 w-6 text-accent-400" strokeWidth={2.25} />
            <span className="font-display text-lg font-medium tracking-tight text-white">
              Veritas
            </span>
          </div>
          <div className="flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-white/10 text-white"
                      : "text-brand-200 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/eval" element={<EvalDashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;

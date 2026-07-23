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
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <header className="h-14 border-b border-slate-200 dark:border-slate-800">
        <nav className="mx-auto flex h-full max-w-3xl items-center gap-6 px-4">
          <span className="font-semibold text-slate-900 dark:text-slate-100">Veritas</span>
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `text-sm font-medium ${
                  isActive
                    ? "text-slate-900 dark:text-slate-100"
                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
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

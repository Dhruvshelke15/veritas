import { Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { Toaster } from "sonner";
import clsx from "clsx";
import { useChatStream } from "./hooks/useChatStream";
import { StartPage } from "./routes/StartPage";
import { ChatPage } from "./routes/ChatPage";
import { UploadPage } from "./routes/UploadPage";
import { EvalDashboardPage } from "./routes/EvalDashboardPage";

const NAV_LINKS = [
  { to: "/ask", label: "Ask" },
  { to: "/upload", label: "Sources" },
  { to: "/eval", label: "Answer quality" },
];

function App() {
  const chat = useChatStream();
  const navigate = useNavigate();

  // Questions picked on the start screen open the question log and start streaming at once.
  const askFromStart = (query: string) => {
    navigate("/ask");
    chat.ask(query);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Toaster position="bottom-right" closeButton />
      <header className="border-b border-rule bg-paper dark:border-rule-dark dark:bg-paper-dark">
        <nav className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="text-lg font-extrabold tracking-tight">
            Veritas
          </Link>
          <div className="flex h-full items-stretch gap-1 overflow-x-auto sm:gap-4">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center whitespace-nowrap border-b-2 px-2 text-sm font-medium transition-colors",
                    isActive
                      ? "border-form text-ink dark:border-form-dark dark:text-ink-dark"
                      : "border-transparent text-muted hover:text-ink dark:text-muted-dark dark:hover:text-ink-dark",
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<StartPage onAsk={askFromStart} />} />
          <Route path="/ask" element={<ChatPage turns={chat.turns} ask={chat.ask} />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/eval" element={<EvalDashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;

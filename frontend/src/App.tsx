import { ShieldCheck } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { useChatStream } from "./hooks/useChatStream";
import { ChatPage } from "./routes/ChatPage";
import { UploadPage } from "./routes/UploadPage";
import { EvalDashboardPage } from "./routes/EvalDashboardPage";

const NAV_LINKS = [
  { to: "/", label: "Chat", end: true },
  { to: "/upload", label: "Documents", end: false },
  { to: "/eval", label: "Evaluation", end: false },
];

function isLinkActive(pathname: string, link: (typeof NAV_LINKS)[number]) {
  return link.end ? pathname === link.to : pathname.startsWith(link.to);
}

function PageTransition({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

function App() {
  const location = useLocation();
  const chat = useChatStream();

  return (
    <div className="min-h-screen bg-paper dark:bg-paper-dark">
      <Toaster position="bottom-right" richColors closeButton />
      <header className="bg-brand-700 dark:bg-brand-900">
        <nav className="mx-auto flex h-16 max-w-3xl items-center gap-2 px-4">
          <div className="flex items-center gap-2 pr-6">
            <ShieldCheck className="h-6 w-6 text-accent-400" strokeWidth={2.25} />
            <span className="font-display text-lg font-medium tracking-tight text-white">
              Veritas
            </span>
          </div>
          <div className="flex items-center gap-1">
            {NAV_LINKS.map((link) => {
              const active = isLinkActive(location.pathname, link);
              return (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  className="relative rounded-full px-3.5 py-1.5 text-sm font-medium"
                >
                  {active && (
                    <motion.div
                      layoutId="nav-active-pill"
                      className="absolute inset-0 rounded-full bg-white/10"
                      transition={{ type: "spring", bounce: 0.25, duration: 0.5 }}
                    />
                  )}
                  <span
                    className={`relative z-10 transition-colors ${
                      active ? "text-white" : "text-brand-200 hover:text-white"
                    }`}
                  >
                    {link.label}
                  </span>
                </NavLink>
              );
            })}
          </div>
        </nav>
      </header>
      <main>
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<PageTransition><ChatPage turns={chat.turns} ask={chat.ask} /></PageTransition>} />
            <Route path="/upload" element={<PageTransition><UploadPage /></PageTransition>} />
            <Route path="/eval" element={<PageTransition><EvalDashboardPage /></PageTransition>} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;

import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import clsx from "clsx";

// The F-1 work path really is a sequence, so the start screen is built around it.
const STAGES = [
  {
    name: "Finishing your program",
    when: "Up to 90 days before your program end date",
    questions: [
      "How early can I apply for post-completion OPT?",
      "What is the 60-day grace period after my program ends?",
    ],
  },
  {
    name: "On OPT",
    when: "Up to 12 months",
    questions: [
      "How many days of unemployment are allowed on OPT?",
      "Does my OPT job have to be related to my degree?",
    ],
  },
  {
    name: "On STEM OPT",
    when: "A 24-month extension",
    questions: [
      "Who qualifies for the STEM OPT extension?",
      "What does Form I-983 require from my employer?",
    ],
  },
  {
    name: "Cap-gap",
    when: "Between your OPT end date and October 1",
    questions: [
      "What is the cap-gap extension?",
      "Does cap-gap cover me if my OPT ends before October 1?",
    ],
  },
  {
    name: "Starting H-1B",
    when: "Usually October 1",
    questions: [
      "What happens to my F-1 status when my H-1B starts?",
      "Can I keep working if my H-1B petition is still pending?",
    ],
  },
];

export function StartPage({ onAsk }: { onAsk: (query: string) => void }) {
  const [selected, setSelected] = useState(1);
  const reduceMotion = useReducedMotion();
  const stage = STAGES[selected];

  return (
    <div className="mx-auto max-w-5xl px-4 pb-16 pt-12 sm:px-6 sm:pt-20">
      <section className="max-w-2xl">
        <h1 className="text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl">
          Your F-1 work rules, answered from the source.
        </h1>
        <p className="mt-5 font-serif text-lg leading-relaxed text-muted dark:text-muted-dark">
          Veritas answers questions about OPT, STEM OPT, the cap-gap extension, and the move to H-1B
          using USCIS and ICE documents. Every answer shows the passage it came from. If the documents
          don't cover your question, it tells you instead of guessing.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link
            to="/ask"
            className="rounded-md bg-form px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-ink dark:bg-form-dark dark:text-paper-dark dark:hover:bg-ink-dark"
          >
            Ask a question
          </Link>
          <Link
            to="/upload"
            className="text-sm font-semibold text-form underline-offset-4 hover:underline dark:text-form-dark"
          >
            See the source documents
          </Link>
        </div>
      </section>

      <section className="mt-16 sm:mt-24" aria-labelledby="stage-heading">
        <h2 id="stage-heading" className="text-xl font-bold">
          Where are you right now?
        </h2>
        <p className="mt-1 text-sm text-muted dark:text-muted-dark">
          Pick a stage to see questions people ask at that point.
        </p>

        <ol className="relative mt-8 grid gap-6 sm:grid-cols-5 sm:gap-3">
          {/* The track runs from the first stop to the last: one grid column (minus half a dot) short of the edge.
              Drawn once on load; the page's one piece of ambient motion. */}
          <motion.span
            aria-hidden
            className="absolute left-[7px] top-2 h-[calc(100%-1rem)] w-0.5 origin-top bg-rule sm:left-2 sm:right-[calc((100%-3rem)/5-0.5rem)] sm:top-[7px] sm:h-0.5 sm:w-auto sm:origin-left dark:bg-rule-dark"
            initial={reduceMotion ? false : { scaleX: 0, scaleY: 0 }}
            animate={{ scaleX: 1, scaleY: 1 }}
            transition={{ duration: 0.9, ease: "easeInOut" }}
          >
            {/* Desktop only: the stretch you've already covered, in ink-blue. Stops are evenly spaced there. */}
            <motion.span
              className="absolute inset-y-0 left-0 hidden bg-form sm:block dark:bg-form-dark"
              initial={false}
              animate={{ width: `${(selected / (STAGES.length - 1)) * 100}%` }}
              transition={reduceMotion ? { duration: 0 } : { duration: 0.35, ease: "easeOut" }}
            />
          </motion.span>
          {STAGES.map((s, i) => {
            const active = i === selected;
            const passed = i < selected;
            return (
              <motion.li
                key={s.name}
                className="relative"
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.15 + i * 0.15, duration: 0.3 }}
              >
                <button
                  type="button"
                  onClick={() => setSelected(i)}
                  aria-pressed={active}
                  className="group flex w-full gap-4 text-left sm:flex-col sm:gap-3"
                >
                  <span
                    aria-hidden
                    className={clsx(
                      "relative z-10 mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 transition-colors",
                      active
                        ? "border-form bg-form dark:border-form-dark dark:bg-form-dark"
                        : passed
                          ? "border-form bg-paper dark:border-form-dark dark:bg-paper-dark"
                          : "border-muted bg-paper group-hover:border-form dark:border-muted-dark dark:bg-paper-dark dark:group-hover:border-form-dark",
                    )}
                  />
                  <span>
                    <span
                      className={clsx(
                        "block font-semibold",
                        active ? "text-form dark:text-form-dark" : "group-hover:text-form dark:group-hover:text-form-dark",
                      )}
                    >
                      {s.name}
                    </span>
                    <span className="mt-0.5 block text-sm text-muted dark:text-muted-dark">{s.when}</span>
                  </span>
                </button>
              </motion.li>
            );
          })}
        </ol>

        <div className="mt-10 max-w-2xl border-t border-rule dark:border-rule-dark" aria-live="polite">
          {stage.questions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onAsk(q)}
              className="group flex w-full items-baseline justify-between gap-6 border-b border-rule py-4 text-left dark:border-rule-dark"
            >
              <span className="font-serif text-lg group-hover:text-form dark:group-hover:text-form-dark">{q}</span>
              <span className="shrink-0 text-sm font-semibold text-form dark:text-form-dark">Ask</span>
            </button>
          ))}
        </div>
      </section>

      <p className="mt-20 max-w-2xl text-sm text-muted dark:text-muted-dark">
        Veritas is an independent study tool. It is not a government website and not legal advice.
        Before you act on an answer, confirm it with your school's DSO or an immigration attorney.
      </p>
    </div>
  );
}

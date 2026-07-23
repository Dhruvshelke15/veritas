# Testing Veritas

This is the step-by-step guide to verifying the system actually works, not just that it imports cleanly. Follow it top to bottom for a full check, or jump to the section you need.

## Prerequisites

### Backend: Python 3.12, not the system Python

The classifier depends on TensorFlow, which has **no wheel for Python 3.14** (this project's earlier default) and **no `tensorflow-cpu` wheel for macOS at all** — only plain `tensorflow`. If you're on a newer system Python, set up a dedicated 3.12 environment once:

```bash
brew install python@3.12
cd backend
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `backend/.venv/bin/python` for everything below. If your system Python is already 3.9–3.12, you may not need this — but if `import tensorflow` fails, this is why.

### API key

Generation, dataset expansion, and the eval faithfulness judge all call Claude. Put your key in `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

It's loaded automatically at process start (`app/config.py` calls `load_dotenv()`) — no need to `export` it manually. Everything that doesn't touch Claude (retrieval, chunking, the classifier itself) works fine without a key.

### Frontend

```bash
cd frontend
npm install
```

---

## 1. Backend lint + tests

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
```

Both should be clean. No API key or ingested corpus required for tests — external calls are faked via `FakeGenerator`/`FakeClassifier`/`FakeRetriever` doubles.

## 2. Frontend build + lint

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

All three should be clean with no errors.

## 3. Retrieval sanity check (no API key needed)

Ingest the corpus and confirm search returns relevant chunks:

```bash
cd backend
for f in ../data/corpus/*.md; do
  .venv/bin/python scripts/ingest_cli.py ingest "$f"
done
.venv/bin/python scripts/ingest_cli.py search "How many days of unemployment are allowed during OPT?"
```

You should see chunks from `uscis_stem_opt_extension.md` / `uscis_policy_manual_vol2_f_ch5.md` mentioning the 90-day limit.

## 4. Classifier routing — live check (needs API key)

Confirms all three routing paths behave correctly against the trained model in `data/classifier/model.keras`:

```bash
cd backend
.venv/bin/python -c "
from app.classifier.predictor import get_classifier
from app.rag.generator import get_generator
from app.rag.pipeline import ask_routed

classifier = get_classifier()
generator = get_generator()

for query in [
    'How many days of unemployment are allowed during initial post-completion OPT?',  # expect: standard
    'I already used 80 days, should I risk a short unpaid gig?',                        # expect: advise
    'Can I get an O-1 visa for athletic achievements?',                                 # expect: reject
]:
    c = classifier.classify(query)
    r = ask_routed(query, generator=generator, classification=c)
    print(f'{r.routing_action:10s} (classifier: {c.label} {c.confidence:.2f})  {query}')
"
```

Note: the classifier fails open by design — a misclassification never produces a wrong *answer*, because citation validation at the generation layer is the actual backstop. Expect the classifier's per-category accuracy to be well below its training-set accuracy on naturally-phrased questions (see `data/eval/eval_results.db` after step 5) — this is a known, documented gap, not a bug.

## 5. Full evaluation harness (needs API key)

Runs all 30 golden questions through retrieval, generation, and LLM-judged faithfulness scoring, plus classifier accuracy:

```bash
cd backend
.venv/bin/python scripts/run_eval.py
```

Reference numbers from the last full run: retrieval hit rate 100%, mean faithfulness 4.64/5. Results persist to `data/eval/eval_results.db` — inspect any run's per-question detail:

```bash
.venv/bin/python -c "
from app.eval import storage
from app.config import settings
conn = storage.connect(settings.eval_db_path)
run_id = storage.list_runs(conn)[0]['run_id']
for q in storage.get_run_detail(conn, run_id)['questions']:
    print(q['classifier_correct'], q['category'], '->', q['classifier_predicted'], '|', q['query'][:70])
"
```

## 6. Full stack, manually, in a browser

```bash
# terminal 1
cd backend && ./run.sh   # wraps `.venv/bin/python -m uvicorn app.main:app --port 8000`

# terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173 and check:

- **Chat** (`/`) — ask "How many days of unemployment are allowed during initial post-completion OPT?" and confirm the answer streams in, cites `uscis_stem_opt_extension.md`, and shows a freshness date. Ask "What is the capital of France?" and confirm it refuses.
- **Documents** (`/upload`) — the 5 ingested corpus docs are listed with source URLs and chunk counts. Try dropping a `.md`/`.txt`/`.pdf` file and confirm it appears after upload.
- **Evaluation** (`/eval`) — after running step 5 at least once, confirm the stat tiles, category-accuracy bar chart, and runs table populate with real numbers.

## Known gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'tensorflow'` | Running on the system Python instead of `backend/.venv` (`python3 -m uvicorn ...` resolves to the global Python) | Use `.venv/bin/python`, not `python3` — or just run `./run.sh` to start the server, which always uses the venv |
| `ERROR: Could not find a version that satisfies the requirement tensorflow==2.21.0` during `pip install` | Same root cause as above, but at install time: bare `pip install -r requirements.txt` resolved to the global Python (macOS `sys_platform == "darwin"` picks the plain `tensorflow` line, which has no wheel outside a narrow set of Python versions) | Use `.venv/bin/pip install -r requirements.txt`, not bare `pip`/`pip3` |
| `Could not resolve authentication method` | `ANTHROPIC_API_KEY` not in `backend/.env`, or `.env` sitting in the wrong directory | Key must be in `backend/.env` specifically (not repo root) |
| `/ask/stream` hangs or errors in the browser but `curl` to `/health` works | A stale `uvicorn` process from an earlier run is still holding port 8000, possibly started under the wrong Python | `lsof -ti:8000 -sTCP:LISTEN \| xargs kill -9`, then restart |
| Classifier confidently mislabels an obviously in-scope or out-of-scope question | Known distribution-shift gap between Claude-generated training phrasing and natural human phrasing (see `data/eval/eval_results.db`) | Not a bug to "fix" blindly — the RAG-layer refusal backstop is the actual safety net; verify the *answer* is still correct via step 4/5 rather than the classifier label alone |

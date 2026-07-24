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

### API keys

Generation, dataset expansion, and the eval faithfulness judge all call Claude. Retrieval (search, `/ask`, `/ask/stream`, the retrieval-hit-rate gate) calls HuggingFace's hosted Inference API for embeddings — see `app/ingestion/indexer.py`. Put both in `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
HUGGINGFACE_API_KEY=hf_...
```

Get an HF token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) — the free tier's default "read" scope is enough, no paid account needed. Both are loaded automatically at process start (`app/config.py` calls `load_dotenv()`) — no need to `export` them manually. Unit tests never need a real value for either (Claude calls are faked; `tests/conftest.py` sets a placeholder `HUGGINGFACE_API_KEY` and embedding HTTP calls are mocked) — only live/manual runs (this document's steps 3 onward) need real keys.

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

## 3. Retrieval sanity check (needs `HUGGINGFACE_API_KEY`, not `ANTHROPIC_API_KEY`)

Ingest the corpus and confirm search returns relevant chunks:

```bash
cd backend
for f in ../data/corpus/*.md; do
  .venv/bin/python scripts/ingest_cli.py ingest "$f"
done
.venv/bin/python scripts/ingest_cli.py search "How many days of unemployment are allowed during OPT?"
```

You should see chunks from `uscis_stem_opt_extension.md` / `uscis_policy_manual_vol2_f_ch5.md` mentioning the 90-day limit.

## 4. Classifier routing — live check (needs both API keys)

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

## 5. Full evaluation harness (needs both API keys)

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

## 7. USCIS watch job (no API key needed)

Unit tests (`tests/test_watch.py`) run entirely against local HTML fixtures — no network access required — and are covered by step 1. To test it against the live USCIS site instead:

```bash
cd backend
.venv/bin/python scripts/watch_uscis.py --since-days 180
```

`--since-days 180` matters on a first run: `data/watch/seen.json` starts empty, so without it every relevant item ever posted would be reported as "new." Add `--json` for machine-readable output, or `--no-save-state` to do a dry run without updating `data/watch/seen.json`.

USCIS blocks requests that don't look like a browser. This should work from a normal residential connection; if it comes back empty or errors, the request may have been blocked rather than there being nothing posted — see the "silence is treated as failure" note in the README. It has **not** been verified against the live page from this environment (network access here is itself often blocked by the same bot detection), so treat the parser as tested-against-realistic-fixtures rather than confirmed-against-production markup until you've run it once yourself.

The scheduled job (`.github/workflows/uscis-watch.yml`, weekly) runs this same script, commits the updated `data/watch/seen.json` back to `main`, and opens a GitHub issue listing anything new — it does not auto-ingest. GitHub Actions runners are datacenter IPs, which is exactly the kind of traffic USCIS's bot detection targets, so there's a real chance the scheduled run gets blocked even though it works locally. Trigger it once manually (`workflow_dispatch`, or `gh workflow run uscis-watch.yml`) after pushing to see which way it goes.

## Known gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'tensorflow'` | Running on the system Python instead of `backend/.venv` (`python3 -m uvicorn ...` resolves to the global Python) | Use `.venv/bin/python`, not `python3` — or just run `./run.sh` to start the server, which always uses the venv |
| `ERROR: Could not find a version that satisfies the requirement tensorflow==2.21.0` during `pip install` | Same root cause as above, but at install time: bare `pip install -r requirements.txt` resolved to the global Python (macOS `sys_platform == "darwin"` picks the plain `tensorflow` line, which has no wheel outside a narrow set of Python versions) | Use `.venv/bin/pip install -r requirements.txt`, not bare `pip`/`pip3` |
| `Could not resolve authentication method` | `ANTHROPIC_API_KEY` not in `backend/.env`, or `.env` sitting in the wrong directory | Key must be in `backend/.env` specifically (not repo root) |
| `/ask/stream` hangs or errors in the browser but `curl` to `/health` works | A stale `uvicorn` process from an earlier run is still holding port 8000, possibly started under the wrong Python | `lsof -ti:8000 -sTCP:LISTEN \| xargs kill -9`, then restart |
| Classifier confidently mislabels an obviously in-scope or out-of-scope question | Known distribution-shift gap between Claude-generated training phrasing and natural human phrasing (see `data/eval/eval_results.db`) | Not a bug to "fix" blindly — the RAG-layer refusal backstop is the actual safety net; verify the *answer* is still correct via step 4/5 rather than the classifier label alone |
| `ValueError: The HUGGINGFACE_API_KEY environment variable is not set` | Missing from `backend/.env` (see API keys above) | Add it and restart — note `./run.sh` doesn't pick up a `.env` edit made while it's already running |
| `ValueError: An embedding function already exists in the collection configuration... new: huggingface vs persisted: sentence_transformer` | `data/chroma/` has a stale index built with the old local embedding function, from before embeddings moved to the hosted API | Safe to delete and let it re-seed: `find data/chroma -mindepth 1 -not -name .gitkeep -delete` (it's gitignored/ephemeral by design — see DEPLOYMENT.md) |

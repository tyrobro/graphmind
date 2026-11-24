# GraphMind — Product Requirements Document

Knowledge Graph Memory Management System for AI Agents

## 1. Executive Summary

GraphMind is an open-source, graph-theory-native memory management layer for AI agents. It replaces naive context-window stuffing with a typed knowledge graph that grows alongside a conversation or agentic session — and intelligently prunes itself when memory pressure rises, using a novel combination of **degree centrality** (how connected a node is) and **flow-inhibition scoring** (how much a node blocks information flow across the graph).

The opportunity is large. Context graphs have been called a trillion-dollar infrastructure layer for enterprise AI in 2026, and the dominant production pain point remains the same: AI agents forget, hallucinate from stale facts, and burn tokens re-stating context every turn. GraphMind targets this gap with a software-only, zero-cost stack that any developer can run locally or deploy on free-tier cloud infrastructure.

**Project type:** Open-source research + developer tool **License:** Apache 2.0 **Target users:** AI engineers, researchers, and hobbyists building long-running agents **Deployment:** Local-first, GitHub-hosted, free-tier cloud-ready

## 2. Problem Statement

Large language models process information through a fixed-size context window. Once that window fills, one of three things happens — all bad:

1. **Truncation** — early context is silently dropped. The model loses the beginning of a conversation and forgets established facts.
2. **Sliding-window summarization** — coarse summaries replace raw turns, losing entity relationships and precise facts.
3. **RAG retrieval** — relevant chunks are fetched by vector similarity, but similarity does not equal importance; a highly-connected fact buried in an old turn is invisible to cosine distance.

Existing frameworks (Mem0, Zep, Letta, Cognee) are significant steps forward, but they all share a limitation: their pruning and eviction strategies are **heuristic and flat** — based on recency, retrieval frequency, or LLM-scored importance — rather than structural. They treat the graph as a retrieval index rather than a true relational memory substrate.

The specific unmet need identified in 2026 research (arXiv 2608.25489, SEMANTiCS'26) is a **query-conditioned, structure-aware composition mechanism** — one that knows which nodes are load-bearing in the graph, not just which ones were recently accessed. GraphMind's pruning algorithm directly addresses this gap.

## 3. Proposed Solution

GraphMind models an AI agent's working memory as a **directed, weighted knowledge graph** where nodes are entities or concepts extracted from the conversation, and edges are relationships between them.

When context pressure hits a configurable threshold, GraphMind runs its pruning pass. Rather than removing the most-recently-added or least-recently-accessed nodes (which discards temporally-recent but structurally-peripheral information), GraphMind applies two structural signals in combination:

**Signal 1 — Degree Centrality:** Nodes with the fewest edges (in-degree + out-degree) are the least connected and most redundant. Peripheral nodes whose removal does not disconnect any subgraph are safe candidates.

**Signal 2 — Flow-Inhibition Score:** GraphMind models information flow across the graph using a betweenness-centrality variant. A node that lies on few shortest paths between other nodes is a flow inhibitor — removing it does not degrade the graph's ability to propagate context between high-value nodes.

**Composite Pruning Score:** `prune_score = α × (1 / degree) + β × (1 / betweenness)` where α and β are tunable weights (default 0.5 / 0.5). Nodes exceeding a score threshold and flagged as non-critical are removed, their edges are re-wired to preserve graph connectivity, and the freed token budget is logged.

This is **not RAG** — retrieval at query time fetches relevant subgraphs from what remains. The pruning pass runs asynchronously, between turns, and is designed to be fully reversible via a soft-delete + tombstone pattern.

## 4. System Architecture

GraphMind is organized as a monorepo with four layers:

**Ingestion Layer** receives text from any source (API call, file upload, or webhook), runs entity + relation extraction using a local LLM, and writes nodes/edges to the graph database.

**Graph Engine** manages the live knowledge graph in Neo4j (free Community Edition). It exposes a typed schema: `Entity` nodes, `Relationship` edges with weight + timestamp, and `Session` nodes linking memories to specific agent contexts.

**Pruning Service** runs on a background scheduler (APScheduler). It queries graph metrics, computes prune scores, and executes soft-deletions. A pruning event log is written to SQLite for audit and replay.

**API Layer** is a FastAPI backend serving REST and WebSocket endpoints. It is consumed by the MCP server, the CLI, and a standalone graph visualizer (`visualizer/graph.html`, a D3.js force-directed graph in a single HTML file).

```
User / Agent (any MCP client)
     │
     ▼
 MCP server / CLI ──► FastAPI (REST + WebSocket)
                           │
                           ├── Ingestion → Ollama (entity extraction)
                           ├── Graph Engine → Neo4j Community
                           ├── Pruning Service (APScheduler)
                           └── Retrieval → GraphRAG subgraph serializer
                           │
                           ▼
              visualizer/graph.html (D3, dark UI, live via WebSocket)
```

## 5. Tech Stack (100% Free & Open Source)

Every component in GraphMind is free and open-source. No paid API keys required.

**Backend**

| Layer | Tool | Notes |
| --- | --- | --- |
| API framework | FastAPI (Python) | REST + WebSocket, async |
| Task queue / scheduler | APScheduler | In-process, no Redis needed for MVP |
| Graph database | Neo4j Community Edition | Free, local, Cypher query language |
| Relational / audit log | SQLite (via SQLModel) | Zero-config, file-based |
| LLM inference (local) | Ollama | Runs Llama 3.2 / Mistral / Qwen locally |
| Entity extraction | spaCy + custom prompts via Ollama | Free, offline |
| Graph metrics | NetworkX | Python-native, no extra infra |
| Embeddings (optional) | nomic-embed-text via Ollama | Local, free |

**Graph Visualizer (single file, no framework)**

| Layer | Tool | Notes |
| --- | --- | --- |
| Graph rendering | D3.js v7 (CDN) | Force-directed, no install |
| Styling | Inline CSS + CSS variables | Dark theme, zero deps |
| Realtime | Native WebSocket API | Built into every browser |
| No framework, no npm, no build step | — | Single HTML file |

**Infrastructure & DevOps**

| Layer | Tool | Notes |
| --- | --- | --- |
| Version control | GitHub (free tier) | Public repo, pushed after each sprint gate |
| Quality gate | Makefile + git pre-push hook | Runs locally; no hosted CI |
| Container | Docker + Docker Compose | Local dev |
| Linting / types | Ruff, mypy | Python only; no Node toolchain anywhere |
| Testing | pytest, pytest-cov, hypothesis, Playwright for Python (pytest-playwright) | Free; the test browser is downloaded once with `playwright install chromium` |

**Benchmarking**

| Layer | Tool | Notes |
| --- | --- | --- |
| Memory eval harness | LoCoMo dataset (public) | Long-context memory benchmark |
| LLM judge | Ollama (local LLM) | No OpenAI key needed |
| Metrics computation | Python + pandas | Free |
| Visualization | matplotlib / seaborn | Free |

## 6. Core Features

**F1 — Memory Ingestion** Accept raw text, uploaded files (PDF, TXT, MD, JSON), or a URL to fetch. Run entity and relation extraction via a local Ollama LLM. Deduplicate against existing nodes using entity resolution (name normalization + embedding similarity). Write nodes and edges to Neo4j with metadata: `source`, `timestamp`, `session_id`, `confidence`.

**F2 — Graph Construction** Maintain a typed schema: `Entity` (person, place, concept, event, with `other` as a fallback), `Relationship` (directional, weighted, carrying a canonical `type` from a fixed core set plus the raw `label` the extractor produced), and `Session`. Edge weights come from co-occurrence frequency and extraction confidence. Support manual annotation and correction via MCP tools and the REST API. Section 13 defines the relationship taxonomy and the confidence score.

**F3 — Structural Pruning** On-demand or scheduled pruning pass. Compute degree centrality and betweenness centrality for all nodes via NetworkX. Apply composite prune score. Soft-delete low-score nodes (tombstoned, not hard-deleted). Log every pruning event with before/after graph stats. Provide undo within a configurable window (default: 24 hours).

**F4 — Subgraph Retrieval (GraphRAG)** At query time, serialize a relevant k-hop subgraph around the query's entities as structured text. Inject it into the LLM's context window instead of raw transcript. Support both Cypher-native retrieval and embedding-based nearest-neighbor node lookup (optional, when embeddings are enabled).

**F5 — REST API** Endpoints: `POST /ingest`, `GET /graph`, `POST /prune`, `POST /prune/undo`, `GET /prune/history`, `GET /retrieve?query=...`, `PATCH /nodes/{id}`, `GET /sessions`, `DELETE /sessions/{id}`, `GET /metrics`, `GET /health`, `WebSocket /graph/live` (streams graph updates to the visualizer). Every endpoint accepts an optional `session` parameter.

**F6 — Agent Integration (MCP-compatible)** Export a Model Context Protocol (MCP) server wrapper so GraphMind can be plugged directly into Claude, Continue, or any MCP-compatible agent with zero glue code.

## 7. Frontend — Standalone Graph Visualizer

Since GraphMind is an MCP server, all agent interaction (ingestion, retrieval, pruning triggers) happens through the host model's UI. A full web app would be scope creep.

The one thing that genuinely can't be done through text is **seeing the graph** — which nodes are load-bearing, how clusters formed, what the pruning pass removed. That stays.

Everything else goes CLI-first:

- Ingestion → `graphmind ingest <file|url>` or direct MCP tool call
- Benchmarking → `python bench/run.py` → JSON/CSV output
- Metrics → `graphmind status` + structured log output

**The entire frontend is a single file: `visualizer/graph.html`** — D3.js loaded from CDN, no npm, no build step, no framework. Open it while the backend is running and it just works.

**`visualizer/graph.html` — Live Knowledge Graph Viewer**

Full-viewport D3.js force-directed graph of the current memory state. Dark background (`#0a0a0a`), nodes color-coded by entity type, edge thickness encoding relationship weight.

- Opens a WebSocket to `ws://localhost:8000/graph/live` on load
- Streams real-time mutations — new nodes glow on entry, pruned nodes fade and collapse
- Hover a node → metadata tooltip (entity type, timestamp, session, prune score)
- Right-click a node → context menu: mark as critical, soft-delete, inspect neighbors
- Sidebar: live stats (node count, edge count, memory pressure gauge, last pruning event)
- `?server=` query param to point at a non-default host

To use: `open visualizer/graph.html` while the backend is running. No install required.

**Page 2 — `/ingest` — Upload & Fetch Console** Drag-and-drop file upload (PDF, TXT, MD, JSON). URL fetch field with a one-click scrape. Raw text paste area. Extraction preview — before committing, the user sees the extracted entities and relations highlighted. Batch ingest from a folder. Session selector (memories can be scoped to a named agent session).

## 8. Graph Pruning Algorithm (Novel)

The pruning algorithm is GraphMind's core research contribution. It runs as a background service between agent turns.

**Step 1 — Pressure Check** Estimate the token cost of serializing the session's whole graph. Pressure is that cost divided by `GRAPH_CAPACITY_TOKENS`. If pressure is below `MEMORY_PRESSURE_THRESHOLD` (default 0.80), skip. Otherwise run a pruning pass that aims to bring the graph down to `PRUNE_TARGET_RATIO` (default 0.60) of capacity, so the next ingest does not immediately trigger another pass.

**Step 2 — Graph Snapshot** Extract the live subgraph for the current session into a NetworkX DiGraph. Compute:

- `degree[v]` = in-degree + out-degree for every node v
- `betweenness[v]` = normalized betweenness centrality (NetworkX's `betweenness_centrality()`)

**Step 3 — Composite Score**

```python
for node in graph.nodes:
    d = degree[node] or 0.001  # avoid div/0
    b = betweenness[node] or 0.001
    prune_score[node] = ALPHA * (1/d) + BETA * (1/b)
```

Default: `ALPHA = 0.5`, `BETA = 0.5`. Both are runtime-configurable.

**Step 4 — Safety Filters** Exclude from pruning:

- Nodes marked `critical=True` by the user
- Nodes with `age_seconds < MIN_AGE` (default: 300s) — protect fresh context
- Articulation points (nodes whose removal would disconnect the graph) — computed via NetworkX's `articulation_points()`

**Step 5 — Removal** Sort candidates by prune\_score descending. Remove the top-N nodes needed to bring the graph down to the prune target. For each removed node:

1. Soft-delete: set `deleted=True`, `deleted_at=now()` in Neo4j (not hard-deleted)
2. Re-wire: for each pair (predecessor, successor) of the removed node, create a new edge with weight = min(predecessor\_edge\_weight, successor\_edge\_weight) × 0.7 (decay factor)
3. Log the pruning event to the audit SQLite table

**Step 6 — Rehydration (optional)** If a future query's retrieved subgraph has a low-coverage score (entity miss rate > threshold), a rehydration pass can restore recently soft-deleted nodes within the configurable undo window.

**Tuning parameters (all in `.env`):**

```
GRAPH_CAPACITY_TOKENS=20000
RETRIEVAL_BUDGET_TOKENS=2000
MEMORY_PRESSURE_THRESHOLD=0.80
PRUNE_TARGET_RATIO=0.60
ALPHA=0.5
BETA=0.5
MIN_NODE_AGE_SECONDS=300
PRUNE_UNDO_WINDOW_HOURS=24
EDGE_DECAY_FACTOR=0.7
CONFIDENCE_THRESHOLD=0.5
OLLAMA_MODEL=llama3.2:3b
GRAPHMIND_SESSION=default
```

## 9. Benchmarking Suite

GraphMind ships a self-contained benchmark runner that requires no external API keys.

**Datasets (downloaded at run time, never bundled; licenses differ):**

| Dataset | What it tests | Source | License |
| --- | --- | --- | --- |
| LoCoMo | Very long-term conversational memory: question answering over long multi-session dialogues | Maharana et al., ACL 2024 (arXiv 2402.17753) | CC BY-NC 4.0 (non-commercial, attribution), per third-party reports; confirm in the repo |
| LongMemEval | Long-term memory in chat assistants: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention | Wu et al., ICLR 2025 (arXiv 2410.10813) | MIT per the dataset README; confirm by downloading |
| Custom JSONL | User-supplied QA pairs against a seeded knowledge base, plus the hand-annotated gold graphs | Local | Yours |

**Using these datasets responsibly:**

- LoCoMo is non-commercial. Use it for research evaluation only, never bundle or redistribute it, and keep attribution. GraphMind's Apache 2.0 code license is unaffected because no dataset is shipped. This is not legal advice; read the license in the dataset's own repo before publishing results.
- A third-party audit reports that 99 of 1,540 LoCoMo questions (6.4%) have wrong golden answers, which caps the achievable score at about 93.6%. Report LoCoMo scores with that caveat.
- Scores from a local judge model are not comparable to published leaderboard numbers. Report them only as relative comparisons between the systems run here, under identical settings.

**Metrics computed:**

- **QA Accuracy** (primary) — F1 and local-LLM-judge correctness on each dataset's own questions
- **Evidence Retention** — % of a question's gold evidence turns (from the dataset's own evidence labels; field names confirmed when the loaders are written) whose entities are still in the graph after pruning
- **Entity Recall and Relation Accuracy** — computed only on the hand-annotated custom set, because the public datasets have no gold graphs; relations are scored on edge existence first and canonical type second
- **Token Savings** — (baseline context tokens − GraphMind context tokens) / baseline
- **Retrieval Latency** — ms per query, p50 and p95
- **Pruning Fidelity** — % of pruned nodes that were genuinely low-importance (human-eval sample or LLM judge)
- **Memory Pressure Reduction** — % reduction in graph size after a pruning pass

**Baselines compared:**

1. **No memory** — fresh context window per turn (worst-case baseline)
2. **Sliding window summarization** — last N turns summarized, representative of naive approaches
3. **Mem0** — vector + graph hybrid, the current SOTA open-source framework
4. **GraphMind (no pruning)** — ablation: full graph, no pruning
5. **GraphMind (degree-only pruning)** — ablation: only degree centrality
6. **GraphMind (full)** — degree + flow-inhibition composite

**Benchmark runner CLI:**

```bash
python bench/run.py \
  --dataset locomo \
  --model ollama/llama3.2 \
  --baseline sliding_window mem0 \
  --output results/run_001.json
```

Results are written to `results/*.json` and `results/*.csv`, and a Markdown summary table is generated for the README.

## 10. GitHub Repository Structure

```
graphmind/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # pruning engine, graph engine
│   │   ├── ingestion/    # entity extraction, dedup
│   │   ├── retrieval/    # subgraph serializer, GraphRAG
│   │   ├── models/       # SQLModel schemas
│   │   └── mcp/          # MCP server wrapper
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── visualizer/
│   └── graph.html        # standalone D3 viewer, no build step
├── bench/
│   ├── datasets/     # LoCoMo, LongMemEval loaders
│   ├── baselines/    # sliding_window.py, mem0_wrapper.py
│   └── run.py
├── docker-compose.yml
├── .env.example
├── Makefile              # up, down, test, lint, gate, gate-live, doctor
├── SPRINT                # current sprint number, read by the pre-push hook
├── .githooks/            # pre-push: runs the sprint gate
├── CONTRIBUTING.md
└── README.md
```

**Local quality gates and git workflow (no hosted CI):**

- `make gate N=<sprint>` runs lint, type checks, coverage and every test for sprints 0 to N, on your machine
- A `pre-push` hook in `.githooks/` (enabled with `git config core.hooksPath .githooks`) re-runs the gate for the sprint named in the `SPRINT` file and refuses the push if it fails
- During a sprint, work on a `sprint-N` branch and commit as often as you like
- At sprint end, once the gate is green: merge to `main`, tag `sprint-N-complete`, and push `main` and the tag to GitHub
- Hosted CI (GitHub Actions) can be added later if you want it; nothing in this plan depends on it

**License:** Apache 2.0 (permissive, allows commercial use, compatible with all dependencies)

**Contribution guide:** Issues labeled `good-first-issue` for new contributors. PRs require one approving review. All benchmark results reproducible via `docker-compose up`.

## 11. Milestones & Roadmap

The build is split into ten sprints, ordered strictly bottom-up: each sprint builds only on layers that already exist and are already tested, and nothing above a layer is started until that layer's gate is green. Durations assume one developer and are estimates; the gate, not the calendar, decides when you move on.

### Gate protocol (applies to every sprint)

- **Tests ship with the code.** A sprint is not complete until the tests listed for it exist and pass.
- **The gate is five checks, all required:** (1) this sprint's tests pass; (2) the full suite from all earlier sprints still passes (regression); (3) `ruff` and `mypy` are clean; (4) coverage on this sprint's modules is at least 85%; (5) the sprint's docs section is updated.
- **Everything runs on your machine.** Tests carry pytest markers `sprint0` to `sprint9`. `make gate N=3` runs sprints 0 to 3 plus lint, types and coverage. It needs Docker running (for Neo4j) and nothing else. There is no hosted CI.
- **Push once per sprint, after the gate passes.** Work on a `sprint-N` branch. When `make gate N=N` is green, merge to `main`, tag it `sprint-N-complete`, and push `main` and the tag to GitHub. A `pre-push` git hook re-runs the gate and refuses the push if it fails. A hook can be bypassed with `--no-verify`, so it is a safety net against accidents, not enforcement; the discipline is yours.
- **If the gate fails, nothing new starts.** Fix forward or revert.
- **If a lower layer turns out to have a bug later,** write a failing regression test in that layer first, fix it there, and re-run every gate above it before continuing.
- **Two tiers of test.** `make gate` runs the fast deterministic tests (fixtures, stub LLM, recorded HTTP). `make gate-live N=...` adds the slower tests that need a real Ollama model. Sprints marked 'live gate' (2, 6 and 9) cannot be closed until the live tier passes and its output is saved in the sprint checklist.
- **Thresholds are starting points.** Numbers such as 85% coverage or 90% schema-valid output are proposals; adjust them after the first measurements, but change them in a separate commit with the reason in the message, never on the fly to get a gate through.

### Sprint overview

| Sprint | Layer | Builds on | Est. | Gate headline |
| --- | --- | --- | --- | --- |
| 0 | Environment and foundations | none | 1 wk | Clean clone reaches green with `make up && make gate N=0` |
| 1 | Data layer (Neo4j store, audit log) | 0 | 2 wks | Repository invariants hold under property tests |
| 2 | Ingestion pipeline | 0-1 | 2 wks | Text in gives a correct, deduplicated, idempotent graph |
| 3 | Pruning engine | 0-1 | 3 wks | Pruning is safe, reversible and deterministic |
| 4 | Retrieval | 0-3 | 2 wks | Subgraph retrieval never exceeds the token budget |
| 5 | API service and scheduler | 0-4 | 2 wks | Every endpoint and WebSocket event is contract-tested |
| 6 | MCP server and CLI | 0-5 | 2 wks | A real MCP client completes an ingest, prune, retrieve session |
| 7 | Graph visualizer | 5 | 2 wks | Browser tests pass against mocked and real backends |
| 8 | Benchmark harness | 0-6 | 2 wks | Metrics match hand-computed values; runs are reproducible |
| 9 | Benchmark runs, tuning and release | 0-8 | 3 wks | Reproducible, honestly reported results; v1.0 tagged |

### Sprint 0: Environment and foundations (Layer 0)

**Goal:** anyone can clone the repo and get a working, tested, gate-checked development environment.

**Build:**

- GitHub repo with Apache-2.0 `LICENSE`, README stub, `CONTRIBUTING.md`, and the monorepo skeleton from Section 10
- Python 3.11+ project (`pyproject.toml`) with ruff, mypy, pytest, pytest-cov and hypothesis configured
- `docker-compose.yml` running Neo4j Community and Ollama with health checks; `.env.example` and a typed settings loader (pydantic-settings), including `OLLAMA_MODEL` so you can pick a model your machine can run
- SQLite initialization, structured logging, and a `Makefile` (`up`, `down`, `test`, `lint`, `gate`, `gate-live`, `doctor`)
- The gate machinery: pytest sprint markers, a `SPRINT` file holding the current sprint number, and a `.githooks/pre-push` hook (enabled with `git config core.hooksPath .githooks`)
- Git workflow: `main` plus one `sprint-N` branch per sprint; first push of the skeleton to GitHub

**Tests (gate):**

- Settings: defaults load; invalid values are rejected with a clear error
- Neo4j: connects over Bolt and runs `RETURN 1` against the docker compose service
- SQLite: the database file is created and a trivial write and read work
- Ollama (`live`): the health endpoint responds and the configured model is present
- `make doctor` reports pass or fail for every dependency
- Gate machinery: a deliberately failing test makes `make gate N=0` exit non-zero and makes the `pre-push` hook block a push (check once, then remove the failing test)

**Done when:** a fresh clone reaches green by following only the README.

### Sprint 1: Data layer (Layer 1)

**Goal:** a trustworthy store that every later layer reads and writes through.

**Build:**

- Domain models (`Entity`, `Relationship`, `Session`) as Pydantic types, and the Neo4j schema with constraints and indexes
- Graph repository: idempotent upsert of nodes and edges, neighbor and k-hop queries, soft-delete and restore (tombstones), the `critical` flag, per-session scoping (sessions are named by the caller and created lazily on first write), node and edge counts
- SQLite audit log (SQLModel) with `IngestEvent` and `PruneEvent` tables and versioned migrations
- Token-cost estimator for a subgraph (pluggable; a simple heuristic by default)

**Tests (gate):**

- Integration tests against real Neo4j: create, read, update, soft-delete and restore for nodes and edges
- Upserting the same entity twice gives one node with merged weight, never a duplicate
- Soft-deleted nodes are invisible to normal reads and fully restorable
- Sessions are isolated: one session's graph never appears in another's
- Constraint violations raise typed errors
- Property tests (hypothesis): random sequences of operations never leave dangling edges or inconsistent counts
- Audit log round-trips; migrations apply cleanly from an empty database and are idempotent
- Token estimator is monotonic in graph size and stable across runs
- Architecture test: no Cypher strings exist outside the repository module

**Done when:** the full suite for sprints 0 and 1 is green.

### Sprint 2: Ingestion pipeline (Layer 2), live gate

**Goal:** raw text goes in, a clean deduplicated graph comes out.

**Build:**

- `Extractor` interface with two implementations: a spaCy baseline that needs no LLM, and an Ollama extractor that requests schema-constrained JSON
- Validation and bounded retry for malformed model output; confidence-threshold filter
- Entity resolution: name normalization plus fuzzy matching, with optional embedding similarity (`nomic-embed-text` via Ollama)
- Edge-weight assignment from co-occurrence and extraction confidence
- Readers for TXT, MD, JSON, PDF and URLs (fetch plus main-text extraction)
- Ingest pipeline that writes through the Sprint 1 repository in one transaction per document

**Tests (gate):**

- Golden tests: a fake extractor with recorded outputs turns fixture documents into the expected entities and relations
- Malformed model output triggers retries, then fails cleanly with no partial writes
- Entity resolution on a small labeled set of alias pairs (for example 'Alice' and 'my coworker Alice'): precision and recall at or above 0.9 (proposed)
- Confidence: the grounding factor is 1.0, 0.5 or 0 for a verbatim, fuzzy or missing source span; repeated mentions combine by noisy-OR and stay within 0 to 1; spaCy items use the configured fixed value
- Relationship canonicalization: free-form labels map to the expected canonical type on a fixture list; unknown labels fall back to `related_to` and keep the raw label
- Two phrasings of the same fact produce one edge (dedup keys on head, canonical type and tail)
- The confidence filter drops low-confidence items and keeps the rest
- Re-ingesting the same document leaves the graph unchanged apart from weight and count updates
- Reader tests for each format, including empty, malformed and oversized files
- URL fetching uses recorded HTTP responses; the deterministic tier makes no live network calls
- Live gate (local, Ollama): five sample paragraphs produce schema-valid output at least 90% of the time (proposed), with results logged

**Done when:** the deterministic gate is green and the live result is recorded.

### Sprint 3: Pruning engine (Layer 3)

**Goal:** the core contribution, built and proven safe before anything depends on it.

**Build:**

- Snapshot a session's graph into NetworkX and compute degree and betweenness centrality (exact, with an approximate k-sample mode above a node-count threshold)
- Composite prune score and the safety filters from Section 8: `critical` nodes, minimum node age, and articulation points (computed on the undirected view)
- Removal planner that picks candidates until the token estimate reaches the prune target (PRUNE\_TARGET\_RATIO of GRAPH\_CAPACITY\_TOKENS), or reports that it cannot reduce further
- Execution: soft-delete, edge re-wiring with decay, and an audit entry with before and after stats
- Undo and rehydration within the configured window, and a `dry_run` mode that returns the plan without touching the graph

**Tests (gate):**

- Hand-built graphs with known structure (star, path, barbell, two clusters joined by a bridge): the prune order matches hand-computed expectations
- Articulation points, `critical` nodes and fresh nodes are never pruned
- `dry_run` changes nothing in Neo4j or the audit log
- Prune then undo restores the identical node set, edge set and weights
- Re-wiring: the new edge weight equals the smaller of the two original weights times the decay factor
- Determinism: the same graph and seed always give the same plan, including in approximate mode
- Budget: after a pass the estimate is within target, or the result states why not
- Property tests on random graphs: the number of connected components never increases, and no edges dangle
- Performance: a 10,000-node synthetic graph is planned within a time budget set from the first measurement; later runs fail if more than 2x slower
- Every pass writes exactly one audit record

**Done when:** the suite for sprints 0 to 3 is green and the performance baseline file is committed.

### Sprint 4: Retrieval (Layer 4)

**Goal:** turn the surviving graph into context an LLM can use, within a fixed token budget.

**Build:**

- Query entity linking: exact and fuzzy name matching, with optional embedding lookup
- k-hop subgraph extraction ranked by edge weight
- Serializer to compact structured text (triples) under RETRIEVAL\_BUDGET\_TOKENS; the lowest-weight edges are dropped first when over budget
- Tombstoned nodes excluded; a coverage signal (share of query entities not found) that can trigger the Sprint 3 rehydration

**Tests (gate):**

- Serializer golden-output tests
- Fuzzed graphs: output never exceeds the token budget
- k-hop results match a NetworkX reference implementation
- Tombstoned nodes never appear in results
- Low coverage triggers rehydration, and the restored nodes appear in the next retrieval
- Integration scenario: ingest a fixture, prune, retrieve, and confirm a seeded important fact is still present
- Latency smoke test on a 5,000-node graph (threshold set from the first measurement)

**Done when:** the suite for sprints 0 to 4 is green.

### Sprint 5: API service and scheduler (Layer 5)

**Goal:** one stable HTTP and WebSocket surface that the MCP server, CLI and visualizer all share.

**Build:**

- FastAPI app: `POST /ingest`, `GET /graph`, `POST /prune` (with `dry_run`), `POST /prune/undo`, `GET /prune/history`, `GET /retrieve`, `PATCH /nodes/{id}` (critical flag), `GET /metrics`, `GET /health`
- `WebSocket /graph/live` driven by an internal event bus (`node_added`, `edge_added`, `node_pruned`, `prune_completed`)
- APScheduler job that checks memory pressure and triggers pruning; operations serialized per session so ingest and prune cannot collide
- Optional bearer-token auth and configurable CORS (the visualizer opens from a local file, so its origin must be allowed explicitly)
- `GET /sessions` and `DELETE /sessions/{id}`; every other endpoint accepts an optional `session` parameter (default `default`)
- Auto-generated OpenAPI schema

**Tests (gate):**

- Contract tests for every endpoint: success, validation error and not-found
- OpenAPI snapshot test so breaking changes are deliberate
- WebSocket: connect, ingest, receive the expected events in order; `node_pruned` events match the audit log
- Scheduler with a fake clock: prunes above the pressure threshold and does nothing below it
- Concurrency: simultaneous ingest and prune leave the graph consistent
- Auth on and off, and CORS behaviour

**Done when:** the suite for sprints 0 to 5 is green.

### Sprint 6: MCP server and CLI (Layer 6), live gate

**Goal:** the product's real interface, usable from any MCP client.

**Build:**

- MCP server using the official Python MCP SDK as a thin shim over the REST API (per risk R5): tools for ingest, retrieve, prune (with dry run), undo, mark critical, status and list sessions (each tool takes an optional session argument, defaulting to the GRAPHMIND\_SESSION setting); stdio transport, HTTP optional
- CLI (Typer): `graphmind ingest | retrieve | prune | status | bench`, with `--json` output
- Setup docs with config snippets for MCP clients (Claude Desktop, Claude Code, Continue)

**Tests (gate):**

- Using the SDK client over stdio, `list_tools` matches a committed schema snapshot
- Each tool round-trips against a test API instance
- API 4xx and 5xx errors surface as readable MCP errors
- CLI tests (CliRunner): exit codes, human output and `--json` output
- Scripted end-to-end agent session: ingest 50 messages, trigger a prune, retrieve, and assert on the facts returned
- Live gate (manual): connect a real MCP client, run a three-step session, and record the transcript in the sprint checklist

**Done when:** the deterministic suite is green and the live transcript is recorded.

### Sprint 7: Graph visualizer (Layer 7)

**Goal:** see what the memory looks like and what pruning did to it.

**Build:** `visualizer/graph.html` as specified in Section 7:

- D3 force-directed graph with dark theme, WebSocket live updates, hover tooltips, context menu (mark critical, soft-delete, undo) and a stats sidebar
- `?server=` parameter, automatic reconnect with backoff, and a clear error state when the backend is unreachable
- Canvas rendering so it stays interactive on large graphs (target: smooth at 2,000 nodes)
- A small `window.__graphmind` hook exposing current node and edge state for tests

**Tests (gate, Playwright for Python):**

- Initial load renders the nodes and edges returned by `GET /graph`
- `node_added` adds a node; `node_pruned` removes it
- Context menu 'mark critical' sends the correct PATCH request
- Reconnects after the server drops and resyncs state
- `?server=` is honored; an unreachable backend shows the error banner
- No console errors during any of the above
- Screenshot regression of the dark theme against committed baselines
- Load test: 2,000 nodes render within a time budget set from the first measurement
- Most tests run against a mock server replaying event streams; at least one runs against the real backend via docker compose; the D3 CDN request is served from a pinned local copy so tests run offline

**Done when:** the suite for sprints 0 to 7 is green.

### Sprint 8: Benchmark harness (Layer 8)

**Goal:** a trustworthy measuring instrument, verified before it measures anything real.

**Build:**

- Dataset loaders for LoCoMo, LongMemEval and custom JSONL. Datasets are downloaded at run time into a gitignored folder; check each dataset's license before deciding whether anything can be vendored
- A `MemorySystem` interface (`ingest`, `answer`) with implementations: no memory, sliding-window summary, Mem0 (open-source, local), GraphMind full, and the ablations (no pruning, degree-only, betweenness-only)
- Metrics: QA accuracy (F1 and a local LLM judge), evidence retention, token savings, p50 and p95 latency, pruning fidelity, memory-pressure reduction, plus entity recall and relation accuracy (scored only on a small hand-annotated gold set that you create, because the public datasets have no gold graphs)
- Runner with fixed seeds, resumable, writing JSON and CSV that record config, git SHA and model digest; Markdown summary generator

**Tests (gate):**

- Each metric is verified against hand-computed values on tiny fixtures
- Loader tests use small hand-written files in each dataset's format; the test suite never downloads real datasets
- A shared conformance suite that every `MemorySystem` must pass on a five-turn toy conversation
- Runner end-to-end on a 10-question toy dataset with a stub LLM; output matches a golden file
- Resume after a simulated crash produces the same final results
- Two runs with the same seed and a stub LLM are byte-identical
- Output files validate against a committed JSON schema
- Judge-output parsing is robust to malformed replies

**Done when:** the suite for sprints 0 to 8 is green.

### Sprint 9: Benchmark runs, tuning and release (Layer 9), live gate

**Goal:** produce the real results and ship v1.0.

**Build:**

- Full runs of LoCoMo and LongMemEval for every baseline and ablation using local Ollama models
- An alpha/beta sweep on a dev split, with final numbers reported on a held-out split so tuning does not leak into results
- Pressure sweeps (prune at 80%, 60% and 40% of budget) to produce quality-versus-tokens curves
- At least 3 seeds per configuration, reported with confidence intervals
- Results tables in the README, a quick smoke benchmark (make bench-smoke) on a small subset, profiling of betweenness at scale, docs, demo and the v1.0 tag

**Tests (gate):**

- `make bench-repro` on a pinned small subset reproduces the recorded numbers within tolerance from a fresh clone
- `bench/thresholds.json` holds score floors for that subset; the gate fails if GraphMind falls below them
- A script verifies every number quoted in the README against the committed result files
- All earlier gates are still green
- Live gate: the full run completes and its metadata (model, seed, commit) is committed alongside the results

**Important:** this gate checks that results are reproducible and honestly reported, not that GraphMind beats the baselines. The pruning hypothesis may not hold; a documented negative result is a valid outcome and becomes the main finding.

**Done when:** all gates are green and v1.0 is tagged.

## 12. Open Questions & Risks

**R1 — Betweenness centrality at scale**

- *Risk:* NetworkX betweenness centrality is O(VE) — expensive on large graphs (10k+ nodes)
- *Mitigation:* Use approximate betweenness (k-sample algorithm in NetworkX) for graphs above a node threshold. Long-term: migrate to graph-native Cypher approximations in Neo4j.

**R2 — Ollama entity extraction quality**

- *Risk:* Small local models (for example Llama 3.2 3B or Mistral 7B) may produce noisy entity extractions, polluting the graph
- *Mitigation:* Add a confidence threshold filter. Ship a curated spaCy NER fallback for named entity detection. Allow manual correction via MCP tools and the REST API.

**R3 — Neo4j Community Edition limits**

- *Risk:* Neo4j Community has no clustering, no RBAC, no online backup
- *Mitigation:* This is acceptable for a research/local tool. For production scale, document the migration path to Neo4j AuraDB free tier (1GB free) or Apache AGE (PostgreSQL extension, fully free).

**R4 — Pruning fidelity validation**

- *Risk:* The composite pruning score may remove semantically important nodes that happen to be structurally peripheral
- *Mitigation:* The `critical` flag lets users manually protect nodes. The soft-delete + undo window catches over-pruning. The benchmarking suite's Pruning Fidelity metric will surface this quantitatively.

**R5 — MCP compatibility drift**

- *Risk:* MCP spec is evolving fast; the GraphMind MCP wrapper may lag
- *Mitigation:* Keep the MCP layer thin (a shim over the REST API). Version it separately so the core is not coupled to spec changes.

**Open Research Questions:**

- What is the optimal ALPHA/BETA ratio for different agent task types (conversational vs. code-assistant vs. research)?
- Can the pruning score be learned end-to-end from user feedback (reinforcement from implicit signals like node re-access after pruning)?
- Is there a graph topology (scale-free vs. random vs. small-world) that emerges naturally from LLM-extracted knowledge, and does it affect pruning strategy?

## 13. Design Decisions & Defaults

These decisions close gaps found in review. Every default is a proposal: change it in this PRD before the sprint that depends on it starts.

| Topic | Decision | Used in |
| --- | --- | --- |
| Toolchain | No Node or npm anywhere. Browser tests use Playwright for Python (pytest-playwright), so everything installs with pip. ESLint is dropped: the inline script is covered by the browser tests, including a no-console-errors check. During tests the D3 CDN request is served from a pinned local copy, so they run offline. | Sprints 0, 7 |
| Relationship taxonomy | Hybrid. The extractor may emit any label; it is stored as `label`. Each relationship is also mapped to a canonical `type` from the core set below, falling back to `related_to`. Deduplication keys on head, canonical type and tail. | Sprints 2, 8 |
| Confidence | A float from 0 to 1. LLM extractor: self-reported score times a grounding factor (1.0 if the source span appears verbatim in the chunk, 0.5 if only a fuzzy match, 0 if not found). spaCy extractor: a fixed configurable value (default 0.7), because spaCy gives no per-entity score. Repeated mentions combine by noisy-OR: `1 - (1 - old) * (1 - new)`. Items below `CONFIDENCE_THRESHOLD` (default 0.5) are dropped. Self-reported scores from small models are poorly calibrated, so treat the threshold as something to tune. | Sprint 2 |
| Default model | `OLLAMA_MODEL` defaults to `llama3.2:3b`. The Llama 3.2 text models are 1B and 3B; there is no 7B. Use Mistral 7B or a similar 7B model when your hardware allows. | Sprints 0, 2 |
| Budgets | Two separate budgets, neither tied to a host model's window (GraphMind does not know which model is calling it). `GRAPH_CAPACITY_TOKENS` (default 20,000) is how large the stored graph may grow; pruning triggers at 0.80 of it and prunes down to 0.60 (`PRUNE_TARGET_RATIO`). `RETRIEVAL_BUDGET_TOKENS` (default 2,000) is the most injected per query. In benchmarks, capacity is set as a fraction (100%, 80%, 60%, 40%) of each conversation's unpruned graph, and the retrieval budget is identical for every system compared. | Sprints 3, 4, 9 |
| Session lifecycle | A session is a named memory namespace chosen by the caller, not generated by the server, and created lazily on first write. MCP tools take an optional `session` argument whose default comes from `GRAPHMIND_SESSION`, so each project's MCP config can name its own memory; without it, `default` is used. The REST API takes the same `session` parameter and adds `GET /sessions` and `DELETE /sessions/{id}`. Pruning and entity resolution never cross sessions. | Sprints 1, 5, 6 |
| Dataset access | LongMemEval appears MIT-licensed and ungated; LoCoMo is CC BY-NC 4.0. Both are downloaded at run time, never bundled. Sprint 8 begins by actually downloading both; if either needs an account or key, the 'no API keys' claim is revisited before the sprint is scoped. See Section 9. | Sprint 8 |

**Core relationship types:** `works_with`, `member_of`, `located_in`, `part_of`, `owns`, `created`, `causes`, `precedes`, `knows`, and the fallback `related_to`. The set is deliberately small so the extractor can be prompted with it and the Sprint 8 gold set can be annotated against it; extend it only when a benchmark shows a real gap.

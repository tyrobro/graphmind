# GraphMind

Graph-theory-native memory management for AI agents. See `GraphMind — Product Requirements Document.md` for full design.

## Quickstart
1. `cp .env.example .env`
2. `make up` — starts Neo4j
3. Install [Ollama](https://ollama.com) and pull the model named in `.env` (`OLLAMA_MODEL`)
4. `cd backend && uv sync`
5. `make gate N=0`

## Development
- `make gate N=<sprint>` — fast deterministic gate for sprints 0..N
- `make gate-live N=<sprint>` — adds slower tests requiring a real Ollama model
- `make doctor` — checks Neo4j and Ollama connectivity
- Git workflow: branch `sprint-N`, merge to `main` and tag `sprint-N-complete` once the gate is green
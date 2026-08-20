# Annual Report Asset Extractor — agent router

Multi-strategy Annual Report PDF extraction and benchmarking app with a Python API and browser UI.

Stack: Python 3.11+, Flask, Pydantic, PDF parsers, React 19, TypeScript, Vite

## Routing table — read ONLY what the task needs

| If the task concerns... | read |
|---|---|
| build / install / run / env | `agent/setup.md` |
| architecture / how it fits together | `agent/architecture.md` |
| endpoint / provider / connector | `agent/api.md` |
| UI component / Python module | `agent/components.md` |
| schemas / run storage / state | `agent/data.md` |
| file placement / naming / style | `agent/conventions.md` |
| tests | `agent/tests.md` |
| bug / gotcha / known issue | `agent/errors.md` |
| secrets / env keys | `agent/secrets.md` |
| architectural decisions | `agent/decisions.md` |
| current state / recent work | `agent/state.md` |
| change impact | `agent/graph/graph.md` |

After changes, update `agent/state.md`, append architectural decisions to
`agent/decisions.md`, and refresh `agent/graph/` when structure changes.

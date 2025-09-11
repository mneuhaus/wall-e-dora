# Repository Guidelines

## Project Structure & Module Organization
- Core graph: `dataflow.yml` wires Dora nodes and topics.
- Nodes live under `nodes/<node>/<package>/main.py` (e.g., `nodes/web/web/main.py`).
- Preferred node layout (aspirational): `entrypoint.py` (Dora), `main.py` (orchestration only), domain modules in `domain/`, event handlers in `inputs/` and `outputs/`, shared `utils/`.
- Tests: `nodes/<node>/tests/test_*.py` (pytest). Assets: `nodes/audio/sounds/*.mp3`, eye GIFs under `nodes/eyes`.
- Web UI: `nodes/web/resources` (Webpack Encore), served by web node over HTTPS `:8443`.
- Firmware: `nodes/tracks/firmware` (CMake); service scripts: `service_runner.sh`. Docs in `docs/`.

## Build, Test & Development
- Environment (Python 3.12+): `python -m venv .venv && source .venv/bin/activate && uv pip install -e .`
- Run system: `make run` or `dora run dataflow.yml --name wall-e-dora`.
- Web assets: `make web/build` or `make web/build-watch` (use `pnpm` in `nodes/web/resources` if adding packages).
- Tracks firmware: `make tracks/build`, `make tracks/flash`, `make tracks/update`.
- Create node: `dora new --kind node <name> --lang python`. Tests: `pytest -q` or `pytest nodes/<node>/tests -q`.

## Coding Style & Conventions
- Python: 4-space indent, type hints, imports ordered stdlib → third‑party → local. Prefer `pathlib`, `dataclasses`, Google‑style docstrings.
- Separation of concerns: `main.py` orchestrates only; put logic in domain/handlers; favor dependency injection via a context dict.
- Lint/format with Ruff: `ruff check .` (use `--fix`), `ruff format .`.
- Naming: modules/funcs `snake_case`, classes `CamelCase`, constants `UPPER_SNAKE`. Logging via `logging` (INFO/DEBUG), avoid `print` beyond bootstrap.

## Web ↔ Dora Data Format
- Nodes exchange Apache Arrow arrays. Web emits via JS and web node wraps with `pa.array(...)`.
- Send structured data as arrays of objects (not JSON strings):
```js
// correct
node.emit('move_servo', [{ id: 5, position: 700 }]);
// wrong
node.emit('move_servo', [JSON.stringify({ id: 5, position: 700 })]);
```
- When adding events: add to sender `outputs`, to receiver `inputs` as `sender/event`, and update both READMEs.

## Testing Guidelines
- Use pytest; mock hardware/IO. For isolated node mains, assert the Dora runtime raises (pattern used in existing tests).
- Cover parsing, config, and routing. Run `pytest -q` before PRs.

## Commit & Pull Request Guidelines
- Commits: imperative; Conventional Commits (`feat:`, `fix:`, etc.) welcome.
- PRs: clear description, linked issues, screenshots for web changes, relevant logs for node behavior.
- Documentation: keep node README.md in sync (purpose, IO, diagrams), update `dataflow.yml` and Mermaid flows when interfaces change.
- CI checklist: `ruff check`, `ruff format`, `pytest`. Include Make targets for new firmware/services.

## Frontend Notes & Ops
- Frontend: React 18 with Hooks, BeerCSS amber theme, Context for state, clean up effects, robust WebSocket error handling; add JSDoc to components.
- Web node TLS is self‑signed on `:8443`—do not commit private keys. Manage service with `make service/install` and `make service/uninstall`. Avoid committing `nodes/web/resources/build/` and local caches.

See `README.md` (architecture) and `CLAUDE.md` (expanded practices) before major changes.

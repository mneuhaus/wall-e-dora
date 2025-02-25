# Commands and Guidelines for WALL-E-DORA Project

## Build/Run Commands
- Run all nodes: `make run` or `dora run dataflow.yml --name wall-e-dora`
- Build web resources: `make web/build`
- Build tracks firmware: `make tracks/build`
- Flash firmware: `make tracks/flash`
- Create new node: `dora new --kind node [node_name] --lang python`

## Test Commands
- Run all tests: `pytest`
- Run specific node tests: `cd nodes/[node_name] && pytest`
- Run single test: `pytest nodes/[node_name]/tests/test_[node_name].py::test_function_name`

## Linting/Formatting
- Format code: `ruff format`
- Lint code: `ruff check`

## Dora-Specific Patterns
- For new dataflow events:
  1. Add event to outputs in sending node
  2. Add event to inputs in receiving node as `sender_node/event_name`
- Use Apache Arrow arrays for data passing between nodes
- Node event loop: `for event in node: if event["type"] == "INPUT" and event["id"] == "[expected_id]": ...`

## Coding Guidelines
- Python: 3.12+ with type annotations
- Imports order: standard library → third-party → local modules
- Node structure: `__init__.py`, `__main__.py`, and `main.py` per node
- Error handling: Use try/except with detailed messages and graceful fallbacks
- Use pa.array() for sending outputs through Dora nodes
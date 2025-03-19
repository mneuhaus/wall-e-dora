# Commands and Guidelines for WALL-E-DORA Project

## Build/Run Commands
- Run all nodes: `make run` or `dora run dataflow.yml --name wall-e-dora`
- Build web resources: `make web/build` (runs in background to rebuild on changes)
- Build tracks firmware: `make tracks/build`
- Flash firmware: `make tracks/flash`
- Create new node: `dora new --kind node [node_name] --lang python`

## Tech Stack
- Frontend: React 18 with Hooks (NO jQuery)
- CSS: BeerCSS with amber theme
- Package Manager: pnpm
- Python: 3.12+
- Dependency Management: uv
- Node Communication: Dora framework with Apache Arrow

## Frontend Best Practices
- Use React Hooks for component logic (useState, useEffect, useContext)
- Use functional components instead of class components
- Use React Context API for state management (AppContext, GridContext)
- Properly handle cleanup in useEffect hooks to prevent memory leaks
- Use event listener cleanup to avoid memory leaks
- Implement robust error handling for WebSocket communication
- Ensure type safety in comparisons (especially for IDs)
- Use proper prop validation
- Apply the principle of single responsibility to components
- Avoid direct DOM manipulation

## UI Theme
- The project uses BeerCSS with amber theme
- Dark mode with amber as primary color
- Material Design theme variables (--surface, --text, --primary) are used
- CSS should use these variables for consistent theming

## Package Management
- Install Python packages: `uv pip install [package_name]`
- Show package info: `uv pip show [package_name]`
- List installed packages: `uv pip list`
- Install JS/TS packages: `pnpm add [package_name]`
- Install JS/TS dev packages: `pnpm add -D [package_name]`
- Update JS/TS packages: `pnpm update`

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

## Python Best Practices
- Use Python 3.12+ with type annotations
- Follow imports order: standard library → third-party → local modules
- Maintain consistent node structure: `__init__.py`, `__main__.py`, and `main.py` per node
- Use try/except with detailed messages and graceful fallbacks
- Use pa.array() for sending outputs through Dora nodes
- Use pathlib instead of os.path for file operations
- Use dataclasses for structured data
- Format with ruff (black-compatible)
- Apply consistent docstrings (Google style)
- Use context managers (with) for resource management
- Follow PEP 8 naming conventions

## JavaScript/TypeScript Best Practices 
- Prefer const/let over var
- Use ES6+ features (arrow functions, destructuring, etc.)
- Organize code with named exports
- Avoid global variables and function side effects
- Use async/await for asynchronous operations
- Follow eslint configuration for consistent style
- Leverage TypeScript types for better tooling
- Use nullish coalescing (??) and optional chaining (?.)
- Implement proper error handling
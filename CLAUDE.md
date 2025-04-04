# Commands and Guidelines for WALL-E-DORA Project

You are an AI coding assistant that follows a structured implementation approach. Adhere to these guidelines when handling user requests:

## Implementation Principles

1. **Progressive Development**
   - Implement solutions in logical stages rather than all at once
   - Pause after completing each meaningful component to check user requirements
   - Confirm scope understanding before beginning implementation
2. **Scope Management**
   - Implement only what is explicitly requested
   - When requirements are ambiguous, choose the minimal viable interpretation
   - Identify when a request might require changes to multiple components or systems
   - Always ask permission before modifying components not specifically mentioned
3. **Communication Protocol**
   - After implementing each component, briefly summarize what you've completed
   - Classify proposed changes by impact level: Small (minor changes), Medium (moderate rework), or Large (significant restructuring)
   - For Large changes, outline your implementation plan before proceeding
   - Explicitly note which features are completed and which remain to be implemented
4. **Quality Assurance**
   - Provide testable increments when possible
   - Include usage examples for implemented components
   - Identify potential edge cases or limitations in your implementation
   - Suggest tests that would verify correct functionality

## Balancing Efficiency with Control

- For straightforward, low-risk tasks, you may implement the complete solution
- For complex tasks, break implementation into logical chunks with review points
- When uncertain about scope, pause and ask clarifying questions
- Be responsive to user feedback about process - some users may prefer more or less granular control

Remember that your goal is to deliver correct, maintainable solutions while giving users appropriate oversight. Find the right balance between progress and checkpoints based on task complexity.

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

## Documentation Guidelines

### General Documentation
- **Keep documentation in sync with code changes**
- Update node README.md files when changing functionality
- Use Mermaid diagrams for visualizing architecture and data flows
- Document all inputs/outputs, their sources, and destinations
- Include purpose statements for all nodes and major components
- List specific technical requirements and implementation details
- Add functional requirements and future enhancement paths

### README Structure
Each node's README.md should follow this structure:
1. **Purpose**: Clear statement of what the node does
2. **Overview**: Brief description with architecture diagram (Mermaid)
3. **Functional Requirements**: What the node should accomplish
4. **Technical Requirements**: How the node implements its functionality
5. **Dora Node Integration**: Data flow details (inputs/outputs)
6. **Getting Started**: Setup instructions
7. **Contribution Guide**: Development workflow
8. **Future Enhancements**: Planned improvements
9. **License**: License information

When modifying node functionality, update all affected sections of the README.

### System-Level Documentation
The main README.md provides project-level documentation:
- System architecture overview with diagrams
- Node communication flows
- Core technologies
- Build and development instructions
- Links to individual node documentation
- System-wide requirements and practices

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
- Add comprehensive JSDoc comments to all components to describe their purpose and functionality
- Include a detailed header comment in view components that explains:
  - The component's purpose and main responsibilities
  - Key features and capabilities
  - How it fits into the overall application structure
  - Important implementation details

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
- Format code: `ruff format .`
- Lint code: `ruff check .`

## Code Change Workflow
When making changes to the project, follow this workflow:
1. Understand the requirements and current implementation
2. Write tests for new functionality
3. Implement changes and verify they work
4. Update documentation to reflect changes
5. Run linting and formatting
6. Run tests
7. Commit changes with a descriptive message

## Dora Node Architecture
Follow this architectural pattern for all new nodes and when refactoring existing nodes:

### Directory Structure
```
node_name/
├── __init__.py           # Package definition
├── __main__.py           # Entry point for direct execution
├── entrypoint.py         # Dora entrypoint script (for dataflow.yml)
├── main.py               # Main orchestration module (no domain logic)
├── config/               # Configuration management (if needed)
│   ├── __init__.py
│   └── handler.py        # ConfigHandler implementation
├── utils/                # Cross-cutting utilities
│   ├── __init__.py
│   └── event_processor.py # Event data extraction utilities, etc.
├── inputs/               # Input event handlers
│   ├── __init__.py       # Exports all handlers
│   ├── event_type1.py    # One file per input event type
│   └── event_type2.py
├── outputs/              # Output event broadcasters
│   ├── __init__.py       # Exports all broadcasters
│   ├── output_type1.py   # One file per output type
│   └── output_type2.py
└── domain/               # Domain-specific functionality
    ├── __init__.py
    ├── models.py         # Data structures and models
    ├── component1.py
    ├── component2.py
    └── subdomain/        # Further organization as needed
        ├── __init__.py
        └── ...
```

### Key Architecture Principles

1. **Dependency Injection via Context Dictionary**:
   - Use a context dictionary for sharing state and dependencies rather than class instances
   - Pass the context to handlers and actions instead of manager instances
   - This improves testability and reduces coupling between components

2. **Pure Orchestration in Main**:
   - The main.py file should focus solely on orchestration with no domain logic
   - Domain logic belongs in appropriate domain modules or input handlers
   - Main file should be minimal and primarily manage the flow of events

3. **Modular Design with Clear Separation of Concerns**:
   - Each file should have a single responsibility
   - Prefer small, focused files (max ~100-200 lines) over monolithic ones
   - Group domain-specific functionality in dedicated subdirectories

4. **Clear Separation of Event Processing, Domain Logic, and Data Flow**:
   - `inputs/` directory: Event handlers that extract and validate data from incoming events
   - Domain modules: Pure business logic independent of event formats
   - `outputs/` directory: Functions for formatting and sending data to other nodes
   - Main orchestrates the flow: inputs → domain logic → outputs

5. **Domain-Driven Structure**:
   - Place domain-specific code in a dedicated subdirectory (e.g., `servo/` for servo node)
   - Within domain directories, further organize by subdomain or functionality 
   - Isolate business logic from Dora framework interactions

### Dora-Specific Implementation
- For new dataflow events:
  1. Add event to outputs in sending node
  2. Add event to inputs in receiving node as `sender_node/event_name`
  3. **Update README.md files in both nodes to document the new data flow**
- Use Apache Arrow arrays for data passing between nodes
- Node event loop: `for event in node: if event["type"] == "INPUT" and event["id"] == "[expected_id]": ...`

## Python Best Practices
- Use Python 3.12+ with type annotations
- Follow imports order: standard library → third-party → local modules
- Maintain consistent node structure using the architecture pattern above
- Keep files small and focused on a single responsibility
- Follow Single Responsibility Principle (SRP) for all modules
- For file size:
  - Aim for 50-100 lines per file when possible
  - If a file exceeds 200 lines, consider splitting it into smaller modules
  - Extract related functionality into dedicated modules with clear names
- Use try/except with detailed messages and graceful fallbacks
- Use pa.array() for sending outputs through Dora nodes
- Use pathlib instead of os.path for file operations
- Use dataclasses for structured data
- Format with ruff (black-compatible)
- Apply consistent docstrings (Google style)
- Use context managers (with) for resource management
- Follow PEP 8 naming conventions
- Implement clear interfaces between modules

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
- Follow KISS (Keep It Simple, Stupid) and DRY (Don't Repeat Yourself) principles
- If a file exceeds ~200 lines of code, consider refactoring by creating components, helpers, partials, etc.
- Keep cognitive load low by using clear, self-explanatory code and appropriate abstractions

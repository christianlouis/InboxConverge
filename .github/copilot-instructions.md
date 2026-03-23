# Copilot Instructions

## Linting Requirements

Before committing any changes, always run the relevant linters and fix all errors:

### Backend (Python)

```bash
# Check code formatting
black --check backend/

# Lint with ruff
ruff check backend/

# Type check with mypy
mypy backend/app --ignore-missing-imports
```

### Frontend (TypeScript/React)

```bash
cd frontend
npm run lint
```

## Documentation Requirements

When making changes, always update the following files:

- **`docs/TODO.md`**: Update task checkboxes, progress percentages, and status indicators to reflect completed work and any new items discovered.
- **`CHANGELOG.md`**: Add entries under the `[Unreleased]` section using the appropriate category (`Added`, `Changed`, `Fixed`, `Security`, `Removed`, `Deprecated`).

## Conventions

- **Python**: Follow PEP 8. Use `black` for formatting. All ruff and mypy errors must be resolved before committing.
- **TypeScript**: Follow the ESLint configuration. Avoid `any` types — use `unknown` with type narrowing instead. Remove unused variables and imports.
- **SQLAlchemy**: Use `# type: ignore[assignment]` for Column attribute assignments and `# noqa: E712` for `== True` comparisons in SQLAlchemy queries (these are valid ORM patterns).

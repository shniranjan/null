# Contributing

Null is open source and welcomes contributions!

## Development Setup

```bash
git clone https://github.com/yourusername/xcpng-manager.git
cd xcpng-manager
make setup
```

## Running Locally

Two terminals:

```bash
# Terminal 1: Backend
make dev-backend
# → http://localhost:8000/docs

# Terminal 2: Frontend
make dev-frontend
# → http://localhost:3000
```

## Project Conventions

### Backend (Python)

- **Style:** PEP 8, 88-char line limit
- **Imports:** stdlib → third-party → local, alphabetized
- **Docstrings:** Google-style for public functions
- **Types:** Pydantic models for request/response, type hints elsewhere
- **Database:** Use `get_db()` from `database.py`, close connections after use
- **XAPI calls:** Go through `xapi/client.py` `PoolConnection.call()` method
- **Auth:** Use `get_current_user()` dependency for protected endpoints

### Frontend (JavaScript/React)

- **Components:** Functional components, hooks
- **State:** React Context for global state (auth), local state for forms
- **API calls:** Use `api.get/post/put/delete` from `api/client.js`
- **CSS:** Custom properties (variables) in `:root`, no inline styles
- **Naming:** PascalCase for components, camelCase for functions/variables
- **Files:** One component per file, co-locate related files in feature folders

### Commits

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Keep commits focused — one logical change per commit

## Adding New Features

### Adding a new API endpoint

1. Create a route file in `backend/app/routes/` (e.g., `vms.py`)
2. Define Pydantic models for request/response
3. Use `get_current_user()` dependency for auth
4. Get pool connection via `pool_registry.get(pool_id)`
5. Call XAPI via `pool.call("VM.some_method", *args)`
6. Register the router in `backend/app/main.py`

### Adding a new frontend page

1. Create a page component in `frontend/src/pages/`
2. Add an entry in `frontend/src/components/Sidebar/Sidebar.jsx` `NAV_ITEMS`
3. Add a case in `frontend/src/App.jsx` `renderPage()`
4. Import and use `api.get/post/put/delete` from `api/client.js`

### Adding a plugin

1. Create `backend/app/plugins/your_plugin.py`
2. Extend `BasePlugin` and implement `register(app)`
3. Add routes, middleware, or event handlers
4. Import in `main.py` and call `plugin.register(app)`

## Testing

```bash
# Backend tests (coming soon)
cd backend && source .venv/bin/activate && pytest

# Frontend tests (coming soon)
cd frontend && npm test
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `feat/my-feature` or `fix/bug-description`
3. Make your changes with clear commit messages
4. Update documentation if needed (README, docs/, inline docstrings)
5. Test manually with a real or mock XCP-ng pool
6. Open a PR against `main` with a description of changes

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Help others learn

## License

By contributing, you agree that your contributions will be licensed under
the GNU Affero General Public License v3.0 (AGPL v3).

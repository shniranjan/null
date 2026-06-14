.PHONY: dev dev-backend dev-frontend build clean db-reset

# ── Development ────────────────────────────────────────────────────

# Run backend in development mode (with auto-reload)
dev-backend:
	cd backend/app && source ../.venv/bin/activate && \
		XCPNG_MANAGER_SECRET=*** \
		uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run frontend in development mode (with HMR)
dev-frontend:
	cd frontend && npm run dev

# Run both (requires two terminals, or use Docker)
dev:
	@echo "Start in two terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

# ── Build ──────────────────────────────────────────────────────────

# Build Docker images
build:
	docker compose build

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# ── Setup ──────────────────────────────────────────────────────────

# Install backend Python dependencies
setup-backend:
	cd backend && uv venv && source .venv/bin/activate && \
		uv pip install -r requirements.txt

# Install frontend Node dependencies
setup-frontend:
	cd frontend && npm install

# Full first-time setup
setup: setup-backend setup-frontend
	@echo "Setup complete. Run 'make dev-backend' and 'make dev-frontend' in separate terminals."
	@echo "Default login: admin / admin"

# ── Maintenance ────────────────────────────────────────────────────

# Reset the database (⚠️ destructive)
db-reset:
	rm -f data/xcpng-gui.db
	@echo "Database reset. Restart backend to recreate."

# Clean build artifacts
clean:
	rm -rf backend/.venv frontend/node_modules frontend/dist
	@echo "Cleaned."

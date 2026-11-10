.PHONY: up down logs backend-test frontend-build smoke
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

backend-test:
	cd backend && pytest -q

frontend-build:
	cd frontend && npm install && npm run build

smoke:
	python scripts/smoke_test.py

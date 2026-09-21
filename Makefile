.PHONY: install db migrate seed backend frontend api-types

install:
	cd backend && python -m venv venv
	cd backend && ./venv/bin/pip install -r requirements.txt
	cd frontend && npm install

db:
	docker compose up -d db

migrate:
	cd backend && ./venv/bin/alembic upgrade head

seed:
	cd backend && ./venv/bin/python scripts/seed.py

backend:
	cd backend && ./venv/bin/uvicorn app.main:app --reload

frontend:
	cd frontend && npm start

api-types:
	cd frontend && npx openapi-typescript@7.13.0 \
		http://localhost:8000/openapi.json \
		-o src/app/core/api/generated/models.ts

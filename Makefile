.PHONY: install db migrate seed seed-movements materialize-features train-demand train-ranker backend frontend api-types ml-pipeline

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

seed-movements:
	cd backend && ./venv/bin/python scripts/generate_synthetic_movements.py

materialize-features:
	cd backend && DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smart_luben ./venv/bin/python scripts/materialize_ml_features.py

train-demand:
	cd backend && DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smart_luben ./venv/bin/python ml/train_demand.py

train-ranker:
	cd backend && DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smart_luben ./venv/bin/python ml/train_ranker.py

backend:
	cd backend && ./venv/bin/uvicorn app.main:app --reload

frontend:
	cd frontend && npm start

api-types:
	cd frontend && npx openapi-typescript@7.13.0 \
		http://localhost:8000/openapi.json \
		-o src/app/core/api/generated/models.ts

ml-pipeline: seed-movements materialize-features train-demand train-ranker

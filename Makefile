include .env
export

DATABASE_URL := postgresql://$(DB_USER):$(DB_PASS)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)

# Yoyo migrations
migrate-new:
	@read -p "Migration name: " name; \
	uv run yoyo new -m "$$name"

migrate-apply:
	uv run yoyo apply -d "$(DATABASE_URL)"

migrate-rollback:
	uv run yoyo rollback -d "$(DATABASE_URL)"

migrate-list:
	uv run yoyo list -d "$(DATABASE_URL)"

# Development
dev:
	uv run main.py

# Docker
docker-build:
	docker build -t email-service .

docker-run:
	docker run -p 3031:3031 --env-file .env email-service

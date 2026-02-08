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

# Docker - Build individual images
docker-build-api:
	docker build --build-arg SERVICE_TYPE=api -t email-service-api .

docker-build-email-sender:
	docker build --build-arg SERVICE_TYPE=email-sender -t email-service-email-sender .

docker-build-imap-receiver:
	docker build --build-arg SERVICE_TYPE=imap-receiver -t email-service-imap-receiver .

docker-build-webhook-delivery:
	docker build --build-arg SERVICE_TYPE=webhook-delivery -t email-service-webhook-delivery .

docker-build-migrate:
	docker build --build-arg SERVICE_TYPE=migrate -t email-service-migrate .

# Docker - Build all images
docker-build-all: docker-build-api docker-build-email-sender docker-build-imap-receiver docker-build-webhook-delivery docker-build-migrate
	@echo "All images built successfully"

# Docker Compose - Development
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-migrate:
	docker compose run --rm migrate

docker-scale:
	@read -p "Service (email-sender/imap-receiver/webhook-delivery): " svc; \
	read -p "Replicas: " count; \
	docker compose up -d --scale $$svc=$$count

# Docker Compose - Production
docker-prod-up:
	docker compose -f docker-compose.production.yml up -d

docker-prod-down:
	docker compose -f docker-compose.production.yml down

docker-prod-logs:
	docker compose -f docker-compose.production.yml logs -f

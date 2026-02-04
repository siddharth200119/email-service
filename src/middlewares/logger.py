import uuid
import time
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils import Logger, logger


MAX_BODY_LENGTH = 10_000  # chars (safety limit)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tracker_id = request.headers.get("x-tracker-id") or str(uuid.uuid4())
        Logger.set_tracker_id(tracker_id)

        start_time = time.perf_counter()

        # ---------- REQUEST METADATA ----------
        client_ip = request.client.host if request.client else None
        headers = dict(request.headers)
        query_params = dict(request.query_params)

        body = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_str = body_bytes.decode("utf-8", errors="ignore")

                # try JSON first
                try:
                    body = json.loads(body_str)
                except json.JSONDecodeError:
                    body = body_str

                # truncate very large bodies
                if isinstance(body, str) and len(body) > MAX_BODY_LENGTH:
                    body = body[:MAX_BODY_LENGTH] + "...(truncated)"
        except Exception as e:
            body = f"<failed to read body: {e}>"

        # ---------- BEFORE REQUEST LOG ----------
        logger.info(
            json.dumps(
                {
                    "event": "incoming_request",
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "headers": headers,
                    "query_params": query_params,
                    "body": body,
                }
            )
        )
        try:
            response = await call_next(request)

            duration_ms = (time.perf_counter() - start_time) * 1000

            # ---------- AFTER REQUEST LOG ----------
            logger.info(
                f"request completed {request.method} "
                f"{request.url.path} "
                f"{response.status_code} "
                f"({duration_ms:.2f} ms)"
            )
        except Exception as exc:
            logger.error(
                f"request failed {request.method} {request.url.path} error={exc}"
            )
            raise

        return response

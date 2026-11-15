from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import sessionmaker

from app.api.routes import router
from app.blockchain.client import ChainClient
from app.blockchain.token import TokenGateway
from app.core.config import Settings, get_settings
from app.core.db import make_engine
from app.core.errors import register_error_handlers
from app.core.security import ensure_fernet_key
from app.core.logging import configure_logging, get_logger
from app.services.wallet_service import WalletService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    ensure_fernet_key(settings)
    log = get_logger("app")

    engine = make_engine(settings.database_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    gateway = TokenGateway(ChainClient(settings))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            with session_factory() as s:
                WalletService(s, gateway, settings).ensure_treasury()
        except Exception as exc:  # DB not migrated yet / RPC down: API still starts, errors surface per request
            log.warning("treasury_bootstrap_skipped", error=str(exc))
        yield

    app = FastAPI(title="AssetChain API", version="1.0.0", lifespan=lifespan,
                  description="Educational RWA tokenization platform. Fictional assets, local test chain.")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.gateway = gateway
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    register_error_handlers(app)

    if settings.api_key:
        import hmac

        from fastapi import Request

        @app.middleware("http")
        async def _require_api_key(request: Request, call_next):
            path = request.url.path
            if path.startswith("/api") and path != "/api/health" and request.method != "OPTIONS":
                supplied = request.headers.get("x-api-key", "")
                if not hmac.compare_digest(supplied, settings.api_key):
                    return JSONResponse(status_code=401, content={"error": {
                        "code": "UNAUTHORIZED", "message": "Missing or invalid X-API-Key"}})
            return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def _validation(_, exc: RequestValidationError):
        details = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR",
                                                                 "message": "Invalid input", "details": details}})

    app.include_router(router)

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

"""Container entrypoint helper: wait for DB + RPC, then run Alembic migrations."""
import sys
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.blockchain.client import ChainClient
from app.core.config import get_settings
from app.core.db import make_engine
from app.core.logging import configure_logging, get_logger

log = get_logger("bootstrap")


def wait_for(name: str, probe, attempts: int = 60, delay: float = 2.0) -> None:
    for i in range(1, attempts + 1):
        try:
            if probe():
                log.info("dependency_ready", name=name)
                return
        except Exception as exc:
            log.info("waiting_dependency", name=name, attempt=i, error=str(exc)[:80])
        time.sleep(delay)
    log.error("dependency_timeout", name=name)
    sys.exit(1)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings.database_url)

    def db_ok() -> bool:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True

    wait_for("postgres", db_ok)
    wait_for("blockchain-rpc", ChainClient(settings).is_connected)
    command.upgrade(Config("alembic.ini"), "head")
    log.info("migrations_applied")

    from sqlalchemy.orm import sessionmaker

    from app.blockchain.token import TokenGateway
    from app.services.health import reconcile_chain_reset

    with sessionmaker(bind=engine)() as session:
        reconcile_chain_reset(session, TokenGateway(ChainClient(settings)), settings.auto_reset_on_chain_mismatch)


if __name__ == "__main__":
    main()

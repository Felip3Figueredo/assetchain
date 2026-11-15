from cryptography.fernet import Fernet

from app.core.db import Base
from app.main import create_app
from app.models import Asset, AssetStatus, Wallet
from app.seed import run_seed


def test_seed_is_idempotent_and_demo_flow_tokenizes(settings):
    settings.fernet_key = Fernet.generate_key().decode()
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as s:
        run_seed(s, app.state.gateway, settings)
        run_seed(s, app.state.gateway, settings)
        assert s.query(Asset).count() == 2
        assert s.query(Wallet).count() == 3
        assert all(a.status == AssetStatus.DRAFT for a in s.query(Asset))
        assert all(w.encrypted_key and "0x" not in w.encrypted_key[:2] for w in s.query(Wallet))
        run_seed(s, app.state.gateway, settings, demo=True)
        alpha = s.query(Asset).filter_by(asset_code="ASSET-001").one()
        assert alpha.status == AssetStatus.TOKENIZED
        run_seed(s, app.state.gateway, settings, demo=True)  # still idempotent

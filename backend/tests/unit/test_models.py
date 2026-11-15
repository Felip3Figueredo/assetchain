from sqlalchemy.orm import sessionmaker

from app.core.db import Base, make_engine
from app.models import Asset, AssetStatus, ChainTransaction, TxStatus


def test_wei_amounts_roundtrip_exactly():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    a = Asset(asset_code="A-1", name="x", category="c", estimated_value_brl=1, token_supply=1, token_price_brl=1)
    s.add(a)
    s.flush()
    big = 10_000_000 * 10**18 + 1
    s.add(ChainTransaction(asset_id=a.id, from_address="0x1", to_address="0x2", amount=big))
    s.commit()
    tx = s.query(ChainTransaction).one()
    assert tx.amount == big
    assert tx.status == TxStatus.PENDING
    assert a.status == AssetStatus.DRAFT

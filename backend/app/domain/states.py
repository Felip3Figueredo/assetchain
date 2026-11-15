from app.core.errors import AppError
from app.models import AssetStatus

_ALLOWED = {
    AssetStatus.DRAFT: {AssetStatus.APPROVED},
    AssetStatus.APPROVED: {AssetStatus.TOKENIZED},
    AssetStatus.TOKENIZED: set(),
}


def ensure_transition(current: AssetStatus, target: AssetStatus) -> None:
    if target not in _ALLOWED[current]:
        raise AppError(409, "INVALID_STATE", f"Cannot move asset from {current.value} to {target.value}")

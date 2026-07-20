"""Production readiness validator endpoint.

GET /api/admin/production-readiness — super_admin only. Returns the result of
`prod_validator.evaluate_env()` so ops can see what's missing/unsafe BEFORE
flipping APP_ENV to production.

C1 FIX: replaced broken _require_admin() (checked non-existent roles "admin"/"owner")
with the platform-standard require_super_admin dependency.
"""
from fastapi import APIRouter, Depends
from services.permissions import require_super_admin
from services.prod_validator import evaluate_env

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/production-readiness", dependencies=[Depends(require_super_admin)])
async def production_readiness():
    return evaluate_env()

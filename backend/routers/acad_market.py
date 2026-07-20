"""Academic Services Ecosystem & Marketplace — /api/acad-market"""
from fastapi import APIRouter, Depends, Query
from worker import enqueue_job
from worker.models import Job
from pydantic import BaseModel, Field
from typing import Optional
from auth_utils import get_current_user
from db import get_db

from services.acad_market import (
    provider_engine,
    service_engine,
    order_engine,
    contract_engine,
    payment_engine,
    rating_engine,
    dispute_engine,
    analytics_engine,
    recommendation_engine,
)
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

router = APIRouter(prefix="/api/acad-market", tags=["academic-marketplace"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class ProviderProfileIn(BaseModel):
    display_name: Optional[str] = ""
    headline: Optional[str] = ""
    bio: Optional[str] = ""
    categories: Optional[list] = []
    expertise_tags: Optional[list] = []
    languages: Optional[list] = ["English"]
    institution: Optional[str] = ""
    country: Optional[str] = ""
    availability: Optional[str] = "available"
    response_time_hours: Optional[int] = 24
    hourly_rate: Optional[float] = 0
    currency: Optional[str] = "USD"
    certifications: Optional[list] = []


class ServiceIn(BaseModel):
    title: str
    description: Optional[str] = ""
    category: Optional[str] = "custom_service"
    tags: Optional[list] = []
    methodology: Optional[str] = ""
    deliverables: Optional[list] = []
    languages: Optional[list] = ["English"]
    packages: Optional[list] = []
    faqs: Optional[list] = []
    sample_output: Optional[str] = ""
    requirements_from_client: Optional[str] = ""


class OrderIn(BaseModel):
    service_id: str
    package_tier: Optional[str] = "basic"
    requirements: Optional[str] = ""
    milestones: Optional[list] = []
    custom_price: Optional[float] = None
    custom_delivery_days: Optional[int] = None
    currency: Optional[str] = "USD"


class TransitionIn(BaseModel):
    status: str
    note: Optional[str] = ""


class DeliverableIn(BaseModel):
    title: Optional[str] = "Deliverable"
    description: Optional[str] = ""
    file_url: Optional[str] = ""


class RevisionNoteIn(BaseModel):
    note: str


class RatingIn(BaseModel):
    order_id: str
    communication: Optional[int] = 3
    quality: Optional[int] = 3
    expertise: Optional[int] = 3
    timeliness: Optional[int] = 3
    value: Optional[int] = 3
    review_text: Optional[str] = ""
    would_recommend: Optional[bool] = True


class RatingResponseIn(BaseModel):
    response: str


class DisputeIn(BaseModel):
    order_id: str
    reason: Optional[str] = "other"
    description: Optional[str] = ""
    desired_resolution: Optional[str] = ""


class EvidenceIn(BaseModel):
    type: Optional[str] = "statement"
    title: Optional[str] = ""
    content: Optional[str] = ""
    file_url: Optional[str] = ""


class MessageIn(BaseModel):
    text: str


class ResolveDisputeIn(BaseModel):
    resolution: str
    note: Optional[str] = ""


class PortfolioItemIn(BaseModel):
    title: Optional[str] = ""
    description: Optional[str] = ""
    category: Optional[str] = ""
    type: Optional[str] = "case_study"
    link: Optional[str] = ""
    tags: Optional[list] = []


class ContractAcceptIn(BaseModel):
    order_id: str


class CreditsIn(BaseModel):
    credits: int
    reason: Optional[str] = ""


# ── Provider endpoints ────────────────────────────────────────────────────────

@router.post("/providers/me")
async def create_my_provider_profile(data: ProviderProfileIn,
                                      user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await provider_engine.create_provider_profile(str(user["_id"]), data.model_dump(), db)


@router.get("/providers/me")
async def get_my_provider_profile(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    p = await provider_engine.get_provider_by_user(str(user["_id"]), db)
    if not p:
        return {"error": "No provider profile found"}
    return p


@router.put("/providers/me")
async def update_my_provider_profile(data: ProviderProfileIn,
                                      user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await provider_engine.update_provider_profile(str(user["_id"]), data.model_dump(), db)


@router.get("/providers/search")
async def search_providers(q: Optional[str] = None, category: Optional[str] = None,
                            language: Optional[str] = None, country: Optional[str] = None,
                            availability: Optional[str] = None,
                            min_rating: Optional[float] = None,
                            min_trust_score: Optional[float] = None,
                            sort: Optional[str] = "average_rating",
                            page: int = 1, limit: int = 20,
                            user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    filters = {k: v for k, v in {
        "q": q, "category": category, "language": language, "country": country,
        "availability": availability, "min_rating": min_rating, "min_trust_score": min_trust_score,
        "sort": sort,
    }.items() if v is not None}
    return await provider_engine.search_providers(db, filters, page, limit)


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    p = await provider_engine.get_provider(provider_id, db)
    return p or {"error": "Provider not found"}


@router.get("/providers/{provider_id}/portfolio")
async def get_provider_portfolio(provider_id: str,
                                  user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    p = await provider_engine.get_provider(provider_id, db)
    if not p:
        return {"error": "Provider not found"}
    return await provider_engine.get_portfolio(p["user_id"], db)


@router.get("/providers/me/portfolio")
async def get_my_portfolio(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await provider_engine.get_portfolio(str(user["_id"]), db)


@router.post("/providers/me/portfolio")
async def add_portfolio_item(data: PortfolioItemIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await provider_engine.add_portfolio_item(str(user["_id"]), data.model_dump(), db)


@router.delete("/providers/me/portfolio/{item_id}")
async def delete_portfolio_item(item_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await provider_engine.delete_portfolio_item(item_id, str(user["_id"]), db)
    return {"deleted": ok}


# ── Service endpoints ─────────────────────────────────────────────────────────

@router.post("/services")
async def create_service(data: ServiceIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await service_engine.create_service(str(user["_id"]), data.model_dump(), db)


@router.get("/services")
async def list_services(q: Optional[str] = None, category: Optional[str] = None,
                         language: Optional[str] = None, max_price: Optional[float] = None,
                         sort: Optional[str] = "rating",
                         page: int = 1, limit: int = 20,
                         user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    filters = {k: v for k, v in {
        "q": q, "category": category, "language": language, "max_price": max_price, "sort": sort
    }.items() if v is not None}
    return await service_engine.list_services(db, filters, page, limit)


@router.get("/services/categories")
async def get_categories(user=Depends(get_current_user)):
    return {"categories": provider_engine.SERVICE_CATEGORIES}


@router.get("/services/my")
async def get_my_services(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await service_engine.get_my_services(str(user["_id"]), db)


@router.get("/services/{service_id}")
async def get_service(service_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    s = await service_engine.get_service(service_id, db)
    return s or {"error": "Service not found"}


@router.put("/services/{service_id}")
async def update_service(service_id: str, data: ServiceIn,
                          user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    s = await service_engine.update_service(service_id, str(user["_id"]), data.model_dump(), db)
    return s or {"error": "Service not found or not authorized"}


@router.delete("/services/{service_id}")
async def delete_service(service_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await service_engine.delete_service(service_id, str(user["_id"]), db)
    return {"deleted": ok}


@router.get("/services/{service_id}/quality")
async def estimate_quality(service_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    svc = await service_engine.get_service(service_id, db)
    if not svc:
        return {"error": "Service not found"}
    prov = await provider_engine.get_provider_by_user(svc.get("provider_user_id", ""), db) or {}
    return service_engine.estimate_service_quality(svc, prov)


# ── Order endpoints ───────────────────────────────────────────────────────────

@router.post("/orders")
async def create_order(data: OrderIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    order = await order_engine.create_order(str(user["_id"]), data.model_dump(), db)
    if "error" not in order:
        await enqueue_job(
            Job(job_type="marketplace.process",
                payload={"order_id": order["id"], "action": "generate_contract"},
                user_id=str(user["_id"])),
            db,
        )
    return order


@router.get("/orders")
async def list_my_orders(role: str = "buyer", status: Optional[str] = None,
                          page: int = 1, limit: int = 20,
                          user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await order_engine.list_orders(str(user["_id"]), db, role, status, page, limit)


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    o = await order_engine.get_order(order_id, db)
    if not o:
        return {"error": "Order not found"}
    uid = str(user["_id"])
    if o.get("buyer_user_id") != uid and o.get("provider_user_id") != uid:
        return {"error": "Not authorized"}
    return o


@router.post("/orders/{order_id}/transition")
async def transition_order(order_id: str, data: TransitionIn,
                            user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await order_engine.transition_order(order_id, str(user["_id"]),
                                                data.status, data.note or "", db)


@router.post("/orders/{order_id}/deliverables")
async def submit_deliverable(order_id: str, data: DeliverableIn,
                               user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await order_engine.submit_deliverable(order_id, str(user["_id"]), data.model_dump(), db)


@router.post("/orders/{order_id}/revision-notes")
async def add_revision_note(order_id: str, data: RevisionNoteIn,
                              user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await order_engine.add_revision_note(order_id, str(user["_id"]), data.note, db)


# ── Contract endpoints ────────────────────────────────────────────────────────

@router.get("/contracts")
async def list_my_contracts(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await contract_engine.list_my_contracts(str(user["_id"]), db)


@router.get("/contracts/{order_id}")
async def get_contract(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    c = await contract_engine.get_contract(order_id, str(user["_id"]), db)
    return c or {"error": "Contract not found"}


@router.post("/contracts/{order_id}/accept")
async def provider_accept_contract(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await contract_engine.provider_accept_contract(order_id, str(user["_id"]), db)


# ── Payment / Wallet endpoints ────────────────────────────────────────────────

@router.get("/wallet")
async def get_wallet(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await payment_engine.get_wallet(str(user["_id"]), db)


@router.post("/wallet/credits")
async def add_credits(data: CreditsIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await payment_engine.add_credits(str(user["_id"]), data.credits, data.reason, db)


@router.get("/wallet/transactions")
async def get_transactions(page: int = 1, limit: int = 30,
                            user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await payment_engine.get_transactions(str(user["_id"]), db, page, limit)


@router.get("/invoices/{order_id}")
async def get_invoice(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await payment_engine.get_invoice(order_id, str(user["_id"]), db)


@router.post("/escrow/{order_id}/hold")
async def hold_escrow(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    o = await order_engine.get_order(order_id, db)
    if not o or o.get("buyer_user_id") != str(user["_id"]):
        return {"error": "Not authorized"}
    return await payment_engine.hold_in_escrow(order_id, str(user["_id"]),
                                                o.get("price", 0), o.get("currency", "USD"), db)


@router.post("/escrow/{order_id}/release")
async def release_escrow(order_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    o = await order_engine.get_order(order_id, db)
    if not o or o.get("buyer_user_id") != str(user["_id"]):
        return {"error": "Not authorized"}
    if o.get("status") != "completed":
        return {"error": "Order must be completed first"}
    return await payment_engine.release_escrow_to_provider(order_id, o["provider_user_id"], db)


# ── Rating endpoints ──────────────────────────────────────────────────────────

@router.post("/ratings")
async def submit_rating(data: RatingIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await rating_engine.submit_rating(str(user["_id"]), data.model_dump(), db)


@router.get("/ratings/providers/{provider_user_id}")
async def get_provider_ratings(provider_user_id: str, page: int = 1, limit: int = 10,
                                 user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await rating_engine.get_ratings_for_provider(provider_user_id, db, page, limit)


@router.get("/ratings/providers/{provider_user_id}/summary")
async def get_rating_summary(provider_user_id: str,
                               user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await rating_engine.get_rating_summary(provider_user_id, db)


@router.get("/ratings/services/{service_id}")
async def get_service_ratings(service_id: str, page: int = 1, limit: int = 10,
                                user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await rating_engine.get_ratings_for_service(service_id, db, page, limit)


@router.post("/ratings/{rating_id}/respond")
async def provider_respond_rating(rating_id: str, data: RatingResponseIn,
                                   user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await rating_engine.provider_respond_to_rating(rating_id, str(user["_id"]),
                                                           data.response, db)


@router.post("/ratings/{rating_id}/helpful")
async def mark_helpful(rating_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await rating_engine.mark_helpful(rating_id, db)


# ── Dispute endpoints ─────────────────────────────────────────────────────────

@router.post("/disputes")
async def open_dispute(data: DisputeIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await dispute_engine.open_dispute(str(user["_id"]), data.model_dump(), db)


@router.get("/disputes")
async def list_my_disputes(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await dispute_engine.list_my_disputes(str(user["_id"]), db)


@router.get("/disputes/{dispute_id}")
async def get_dispute(dispute_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    d = await dispute_engine.get_dispute(dispute_id, str(user["_id"]), db)
    return d or {"error": "Dispute not found or not authorized"}


@router.post("/disputes/{dispute_id}/evidence")
async def add_evidence(dispute_id: str, data: EvidenceIn,
                        user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await dispute_engine.add_evidence(dispute_id, str(user["_id"]), data.model_dump(), db)


@router.post("/disputes/{dispute_id}/messages")
async def add_message(dispute_id: str, data: MessageIn,
                       user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await dispute_engine.add_message(dispute_id, str(user["_id"]), data.text, db)


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(dispute_id: str, data: ResolveDisputeIn,
                           user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    role = user.get("role", "")
    if role not in ("admin", "super_admin", "moderator"):
        return {"error": "Only platform moderators can resolve disputes"}
    return await dispute_engine.resolve_dispute(dispute_id, str(user["_id"]),
                                                 data.resolution, data.note or "", db)


# ── Analytics endpoints ───────────────────────────────────────────────────────

@router.get("/analytics/provider")
async def provider_dashboard(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await analytics_engine.get_provider_dashboard(str(user["_id"]), db)


@router.get("/analytics/buyer")
async def buyer_dashboard(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await analytics_engine.get_buyer_dashboard(str(user["_id"]), db)


@router.get("/analytics/services/{service_id}")
async def service_analytics(service_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await analytics_engine.get_service_analytics(service_id, str(user["_id"]), db)


# ── Recommendation endpoints ──────────────────────────────────────────────────

@router.get("/recommendations")
async def get_recommendations(category: Optional[str] = None,
                                user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await recommendation_engine.get_recommendations(str(user["_id"]), db, category)


@router.post("/recommendations/refresh")
async def refresh_recommendations(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    recs = await recommendation_engine.generate_recommendations(str(user["_id"]), db)
    return {"generated": len(recs), "recommendations": recs}


@router.delete("/recommendations/{service_id}")
async def dismiss_recommendation(service_id: str,
                                  user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    ok = await recommendation_engine.dismiss_recommendation(str(user["_id"]), service_id, db)
    return {"dismissed": ok}


@router.get("/trending")
async def get_trending(limit: int = 10, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await recommendation_engine.get_trending_services(db, limit)


@router.get("/featured-providers")
async def get_featured_providers(limit: int = 8, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await recommendation_engine.get_featured_providers(db, limit)


# ── Admin endpoints ───────────────────────────────────────────────────────────

admin_router = APIRouter(prefix="/api/admin/acad-market", tags=["admin-marketplace"])


@admin_router.get("/stats")
async def admin_stats(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    return await analytics_engine.get_platform_stats(db)


@admin_router.get("/disputes")
async def admin_disputes(status: Optional[str] = None, page: int = 1, limit: int = 20,
                          user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    return await dispute_engine.get_admin_disputes(db, status, page, limit)


@admin_router.post("/disputes/{dispute_id}/resolve")
async def admin_resolve_dispute(dispute_id: str, data: ResolveDisputeIn,
                                 user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    return await dispute_engine.resolve_dispute(dispute_id, str(user["_id"]),
                                                 data.resolution, data.note or "", db)

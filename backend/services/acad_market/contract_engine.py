"""Auto-generated project agreements for Academic Services Marketplace."""
from datetime import datetime, timezone, timedelta
from bson import ObjectId


def _now():
    return datetime.now(timezone.utc).isoformat()


def _s(doc):
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc


def _generate_contract_text(order: dict, service: dict, buyer_name: str,
                             provider_name: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    deadline = (datetime.now(timezone.utc) + timedelta(days=order.get("delivery_days", 7))).strftime("%Y-%m-%d")
    deliverables = "\n".join(f"  • {d}" for d in service.get("deliverables", ["As agreed"]))
    package = order.get("package", {})
    revisions = order.get("revisions_allowed", 1)

    return f"""ACADEMIC SERVICES AGREEMENT

Date: {today}
Order ID: {order.get("id", "")}
Platform: Synaptiq Academic Services Marketplace

PARTIES
Buyer: {buyer_name}
Provider: {provider_name}

SERVICE
Title: {order.get("service_title", "")}
Category: {order.get("category", "").replace("_", " ").title()}
Package: {order.get("package_tier", "").title()}
Description: {service.get("description", "")[:300]}

DELIVERABLES
{deliverables or "  • To be defined upon acceptance"}

TIMELINE
Deadline: {deadline} ({order.get("delivery_days", 7)} calendar days from order acceptance)

PRICING
Total: {order.get("currency", "USD")} {order.get("price", 0):.2f}
Platform Fee: {order.get("currency", "USD")} {order.get("platform_fee", 0):.2f} (held by platform)
Provider Payout: {order.get("currency", "USD")} {order.get("provider_payout", 0):.2f}

REVISIONS
{revisions} revision(s) included. Additional revisions may be requested at agreed rates.

METHODOLOGY
{service.get("methodology", "As described in the service listing.")}

INTELLECTUAL PROPERTY
All deliverables produced under this agreement are the sole property of the Buyer upon full payment. The Provider retains the right to describe the general nature of the work in their portfolio without disclosing confidential information.

CONFIDENTIALITY
Both parties agree to maintain strict confidentiality regarding all project materials, data, and information shared during this engagement.

ACCEPTANCE CRITERIA
The Buyer will confirm completion by approving delivered work within the platform. Approval constitutes acceptance of all deliverables.

DISPUTE RESOLUTION
Any disputes shall be resolved through the Synaptiq Dispute Center. Both parties agree to engage in good-faith mediation before escalation.

LIMITATION OF LIABILITY
The Provider's liability is limited to the amount paid for the specific service.

GOVERNING PLATFORM
This agreement is governed by the Synaptiq Terms of Service and Academic Integrity Standards.

ELECTRONIC ACCEPTANCE
By proceeding with this order on the Synaptiq platform, both parties electronically accept the terms of this agreement.
"""


async def generate_contract(order_id: str, db) -> dict:
    try:
        order = await db["mkt_orders"].find_one({"_id": ObjectId(order_id)})
    except Exception:
        return {"error": "Invalid order"}
    if not order:
        return {"error": "Order not found"}

    existing = await db["mkt_contracts"].find_one({"order_id": order_id})
    if existing:
        return _s(existing)

    try:
        service = await db["mkt_services"].find_one({"_id": ObjectId(order.get("service_id", ""))})
    except Exception:
        service = {}
    service = service or {}

    try:
        buyer = await db["users"].find_one(
            {"_id": ObjectId(order["buyer_user_id"])}, {"name": 1}
        )
        provider = await db["users"].find_one(
            {"_id": ObjectId(order["provider_user_id"])}, {"name": 1}
        )
    except Exception:
        buyer = provider = {}

    buyer_name = (buyer or {}).get("name", "Buyer")
    provider_name = (provider or {}).get("name", "Provider")

    order["id"] = order_id
    contract_text = _generate_contract_text(order, service, buyer_name, provider_name)

    contract = {
        "order_id": order_id,
        "buyer_user_id": order["buyer_user_id"],
        "provider_user_id": order["provider_user_id"],
        "service_id": order.get("service_id", ""),
        "contract_text": contract_text,
        "status": "active",
        "buyer_accepted": True,
        "provider_accepted": False,
        "buyer_accepted_at": _now(),
        "provider_accepted_at": None,
        "created_at": _now(),
    }
    r = await db["mkt_contracts"].insert_one(contract)
    contract["id"] = str(r.inserted_id)
    contract.pop("_id", None)
    return contract


async def provider_accept_contract(order_id: str, provider_user_id: str, db) -> dict:
    contract = await db["mkt_contracts"].find_one({"order_id": order_id})
    if not contract:
        return {"error": "Contract not found"}
    if contract.get("provider_user_id") != provider_user_id:
        return {"error": "Not authorized"}
    await db["mkt_contracts"].update_one(
        {"order_id": order_id},
        {"$set": {"provider_accepted": True, "provider_accepted_at": _now()}}
    )
    contract = await db["mkt_contracts"].find_one({"order_id": order_id})
    return _s(contract)


async def get_contract(order_id: str, user_id: str, db) -> dict | None:
    doc = await db["mkt_contracts"].find_one({
        "order_id": order_id,
        "$or": [{"buyer_user_id": user_id}, {"provider_user_id": user_id}]
    })
    return _s(doc)


async def list_my_contracts(user_id: str, db) -> list:
    cursor = db["mkt_contracts"].find(
        {"$or": [{"buyer_user_id": user_id}, {"provider_user_id": user_id}]}
    ).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(50)
    return [_s(d) for d in docs]

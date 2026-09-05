"""Mock suppliers — one app, two verticals, data-driven handlers.

These stand in for real inventory and verification APIs. Domain detail belongs
here, not in `app/` — they are external services in everything but hosting.

**Two tiers per provider, and the split is the whole x402 argument:**

  GET /<path>          free   — indicative catalogue: price, capacity, features.
                               Enough to *compare* plans, like a rate card.
  GET /<path>/verify   PAID   — live availability, confirmed right now, with a
                               hold reference. This is what is actually worth
                               paying for, and what expires while you deliberate.

Plan comparison runs on the free tier. Only the selected plan's providers get
paid verification, which is exactly how a real operator would spend.

Run: uvicorn vendors.main:app --port 8011          (free tier only)
     X402=1 uvicorn vendors.main:app --port 8011   (verify endpoints gated)
"""
import os
import pathlib
import random

from fastapi import FastAPI

app = FastAPI(title="alternate.ai / ContingencyOS mock suppliers")

# --- event-contingency vertical (S$, business layer) ------------------------
EVENT: dict[str, list[dict]] = {
    "/venue/marina-hall": [
        {"id": "marina", "supplier": "Marina Hall", "label": "Original venue",
         "price": "0", "reliability": 0.0,
         "attributes": {"capacity": 1200, "public_transport": False,
                        "av_support": True, "available": False,
                        "status": "flooded — unusable"}},
    ],
    "/venue/suntec-backup": [
        {"id": "suntec", "supplier": "Suntec Backup Hall", "label": "Hall 402, full day",
         "price": "42000", "reliability": 0.95,
         "attributes": {"capacity": 1200, "public_transport": True,
                        "av_support": True, "available": True,
                        "setup_hours": 6}},
    ],
    "/venue/expo-c": [
        {"id": "expo_c", "supplier": "Expo Venue C", "label": "Hall C, full day",
         "price": "35000", "reliability": 0.90,
         "attributes": {"capacity": 1500, "public_transport": False,
                        "av_support": True, "available": True,
                        "note": "MRT line suspended — road access only"}},
    ],
    "/venue/city-ballroom": [
        {"id": "city_ballroom", "supplier": "City Ballroom", "label": "Grand ballroom",
         "price": "28000", "reliability": 0.92,
         "attributes": {"capacity": 900, "public_transport": True,
                        "av_support": True, "available": True}},
    ],
    "/av/supplier-a": [
        {"id": "av_a", "supplier": "AV Supplier A", "label": "Full stage AV + crew",
         "price": "13000", "reliability": 0.94,
         "attributes": {"available": True, "crew": 8, "setup_hours": 5}},
    ],
    "/av/supplier-b": [
        {"id": "av_b", "supplier": "AV Supplier B", "label": "Full stage AV",
         "price": "8000", "reliability": 0.55,
         "attributes": {"available": False, "note": "crew committed elsewhere"}},
    ],
    "/catering/supplier-a": [
        {"id": "cat_a", "supplier": "Catering Supplier A", "label": "1,000 pax, full day",
         "price": "11000", "reliability": 0.93,
         "attributes": {"available": True, "covers": 1000}},
    ],
    "/transport/supplier-a": [
        {"id": "tr_a", "supplier": "Transport Supplier A", "label": "Shuttle fleet",
         "price": "9000", "reliability": 0.60,
         "attributes": {"available": False, "note": "road closures around Marina"}},
    ],
}

# --- flight-disruption vertical (kept: evidence a vertical is just data) ----
FLIGHT: dict[str, list[dict]] = {
    "/transport/skyline": [
        {"id": "sky-0844", "supplier": "Skyline Air", "label": "SQ0844 06:40",
         "price": "4.60", "reliability": 0.94,
         "attributes": {"departure_time": "2026-09-06T06:40:00+08:00",
                        "arrival_time": "2026-09-06T07:35:00+07:00",
                        "departs_next_day": True}},
    ],
    "/lodging/transit-inn": [
        {"id": "ti-std", "supplier": "Transit Inn", "label": "Standard, 1 night",
         "price": "1.95", "reliability": 0.91,
         "attributes": {"distance_km": 3, "checkin": "2026-09-05T23:00:00+08:00"}},
    ],
}

INVENTORY = {**EVENT, **FLIGHT}

# Providers that fail verification even though the catalogue looked fine.
# This is the supplier-failure path, and it must be discovered by *paying* —
# which is the honest version of the problem, not a free lookup.
FAILS_VERIFICATION = {"/av/supplier-b", "/transport/supplier-a"}


def _catalogue(path: str):
    async def handler():
        return {"endpoint": path, "tier": "indicative", "options": INVENTORY[path]}
    return handler


def _verify(path: str):
    async def handler():
        opts = INVENTORY[path]
        if path in FAILS_VERIFICATION or os.getenv("FORCE_FAIL") == path:
            return {"endpoint": path, "tier": "live", "verified": False,
                    "reason": opts[0]["attributes"].get("note", "unavailable at this date"),
                    "options": []}
        return {"endpoint": path, "tier": "live", "verified": True,
                "hold_reference": f"HOLD-{random.randint(100000, 999999)}",
                "hold_expires_minutes": 20, "options": opts}
    return handler


for _p in INVENTORY:
    app.get(_p)(_catalogue(_p))
    app.get(_p + "/verify")(_verify(_p))


# --- x402 gating on the PAID tier only -------------------------------------
if os.getenv("X402") == "1":
    import json as _json

    from x402_xrpl.server import RequireX402Options, require_x402

    WALLETS = _json.loads((pathlib.Path(__file__).resolve().parent.parent
                           / "wallets.json").read_text())
    ROLES = ["flights_skyline", "flights_aeroconnect", "hotels_aurora",
             "hotels_transit_inn", "hotels_meridian", "ground_swiftcar",
             "ground_metrolink", "data_status"]
    PRICE_DROPS = os.getenv("X402_PRICE_DROPS", "20000")     # 0.02 XRP
    FACILITATOR = os.getenv("XRPL_FACILITATOR_URL",
                            "https://xrpl-facilitator-testnet.t54.ai")

    for _i, _p in enumerate(INVENTORY):
        app.middleware("http")(require_x402(RequireX402Options(
            pay_to=WALLETS[ROLES[_i % len(ROLES)]]["address"],
            amount=PRICE_DROPS,
            asset="XRP",
            network="xrpl:1",
            path=_p + "/verify",
            source_tag=4021,
            facilitator_url=FACILITATOR,
            description=f"ContingencyOS live verification {_p}",
        )))


@app.get("/")
async def index():
    return {"providers": len(INVENTORY),
            "free_tier": sorted(INVENTORY),
            "paid_tier": [p + "/verify" for p in sorted(INVENTORY)]}

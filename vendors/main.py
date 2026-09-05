"""Mock suppliers — one app, eight endpoints, data-driven handlers.

These stand in for real inventory APIs (NDC/GDS/direct). Domain detail belongs
here, not in `app/` — these are external services in everything but hosting.

Amounts are 1/40 scale (D-009). Inventory is engineered so the run has real
trade-offs rather than one obvious winner:

  - AeroConnect is cheaper than Skyline but is a red-eye the profile avoids
  - Aurora Grand meets every criterion except the lodging cap  -> rejected
  - MetroLink is cheapest but low reliability and on the profile's avoid list
    -> this is the provider the agent declines to even query

Run: uvicorn vendors.main:app --port 8011
"""
from fastapi import FastAPI

app = FastAPI(title="alternate.ai mock suppliers")

INVENTORY: dict[str, list[dict]] = {
    "/status/feed": [
        {"id": "wv-1", "supplier": "Status Feed", "label": "Carrier waiver active",
         "price": "0.00", "reliability": 0.99,
         "attributes": {"waiver": True, "rebooking_window_minutes": 15,
                        "seats_remaining_estimate": 34}},
    ],
    "/transport/skyline": [
        {"id": "sky-0844", "supplier": "Skyline Air", "label": "SQ0844 06:40 → 07:35",
         "price": "4.60", "reliability": 0.94,
         "attributes": {"departure_time": "2026-09-06T06:40:00+08:00",
                        "arrival_time": "2026-09-06T07:35:00+07:00",
                        "departs_next_day": True, "red_eye": False, "seats": 6}},
        {"id": "sky-0902", "supplier": "Skyline Air", "label": "SQ0902 11:20 → 12:15",
         "price": "3.10", "reliability": 0.94,
         "attributes": {"departure_time": "2026-09-06T11:20:00+08:00",
                        "arrival_time": "2026-09-06T12:15:00+07:00",
                        "departs_next_day": True, "red_eye": False, "seats": 22}},
    ],
    "/transport/aeroconnect": [
        {"id": "aero-1204", "supplier": "AeroConnect", "label": "AC1204 01:15 → 02:10",
         "price": "3.90", "reliability": 0.88,
         "attributes": {"departure_time": "2026-09-06T01:15:00+08:00",
                        "arrival_time": "2026-09-06T02:10:00+07:00",
                        "departs_next_day": True, "red_eye": True, "seats": 3}},
    ],
    "/lodging/aurora": [
        {"id": "aur-king", "supplier": "Aurora Grand", "label": "Deluxe, 1 night",
         "price": "7.75", "reliability": 0.96,
         "attributes": {"distance_km": 2, "checkin": "2026-09-05T23:00:00+08:00",
                        "rooms_remaining": 8}},
    ],
    "/lodging/transit-inn": [
        {"id": "ti-std", "supplier": "Transit Inn", "label": "Standard, 1 night",
         "price": "1.95", "reliability": 0.91,
         "attributes": {"distance_km": 3, "checkin": "2026-09-05T23:00:00+08:00",
                        "rooms_remaining": 2}},
    ],
    "/lodging/meridian": [
        {"id": "mer-std", "supplier": "Meridian", "label": "Standard, 1 night",
         "price": "2.40", "reliability": 0.89,
         "attributes": {"distance_km": 12, "checkin": "2026-09-05T23:30:00+08:00",
                        "rooms_remaining": 9}},
    ],
    "/ground/swiftcar": [
        {"id": "sc-xfer", "supplier": "SwiftCar", "label": "Airport transfer 05:40",
         "price": "0.49", "reliability": 0.93,
         "attributes": {"pickup": "2026-09-06T05:40:00+08:00", "eta_minutes": 18}},
    ],
    "/ground/metrolink": [
        {"id": "ml-xfer", "supplier": "MetroLink", "label": "Shared shuttle 05:20",
         "price": "0.35", "reliability": 0.72,
         "attributes": {"pickup": "2026-09-06T05:20:00+08:00", "eta_minutes": 41}},
    ],
}


def _make(path: str):
    async def handler():
        return {"endpoint": path, "options": INVENTORY[path]}
    return handler


for _path in INVENTORY:
    app.get(_path)(_make(_path))


@app.get("/")
async def index():
    return {"suppliers": len(INVENTORY), "endpoints": sorted(INVENTORY)}

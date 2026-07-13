import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import SoilDetails
from app.core.db_models import SoilInfo, User

PROPERTIES_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
CLASSIFICATION_URL = "https://rest.isric.org/soilgrids/v2.0/classification/query"

# SoilGrids property name -> SoilDetails field
_PROPERTY_FIELDS = {
    "sand": "sand_percent",
    "silt": "silt_percent",
    "clay": "clay_percent",
    "phh2o": "ph",
    "soc": "organic_carbon",
    "nitrogen": "nitrogen",
    "cec": "cation_exchange_capacity",
    "bdod": "bulk_density",
}

# Aggregate the top 30cm, weighting each layer by its thickness in cm
_DEPTH_WEIGHTS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}


async def fetch_soil_details(latitude: float, longitude: float) -> SoilDetails:
    params = {"lat": latitude, "lon": longitude}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            props_resp = await client.get(
                PROPERTIES_URL,
                params={
                    **params,
                    "property": list(_PROPERTY_FIELDS),
                    "depth": list(_DEPTH_WEIGHTS),
                    "value": "mean",
                },
            )
            props_resp.raise_for_status()
            class_resp = await client.get(
                CLASSIFICATION_URL, params={**params, "number_classes": 1}
            )
            class_resp.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Soil data service is unavailable")

    fields: dict[str, float | None] = {}
    for layer in props_resp.json()["properties"]["layers"]:
        field = _PROPERTY_FIELDS.get(layer["name"])
        if field is None:
            continue
        # d_factor converts SoilGrids' integer mapped units to target units
        d_factor = layer["unit_measure"]["d_factor"]
        total = 0.0
        weight = 0
        for depth in layer["depths"]:
            w = _DEPTH_WEIGHTS.get(depth["label"])
            mean = depth["values"].get("mean")
            if w is None or mean is None:
                continue
            total += mean * w
            weight += w
        fields[field] = round(total / weight / d_factor, 2) if weight else None

    soil_type = class_resp.json().get("wrb_class_name")

    if soil_type is None and all(v is None for v in fields.values()):
        raise HTTPException(
            status_code=404, detail="No soil data available for this location"
        )

    return SoilDetails(
        latitude=latitude, longitude=longitude, soil_type=soil_type, **fields
    )


def save_soil_details(db: Session, email: str, details: SoilDetails) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")

    soil = db.scalar(select(SoilInfo).where(SoilInfo.user_id == user.id))
    if soil is None:
        soil = SoilInfo(user_id=user.id)
        db.add(soil)
    for field, value in details.model_dump().items():
        setattr(soil, field, value)
    db.commit()

    return {"message": f"Soil details saved for {user.email}"}

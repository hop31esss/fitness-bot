"""Canonical storage unit is kilograms."""

LB_TO_KG = 0.45359237
LB_UNITS = {"lb", "lbs", "pound", "pounds"}


def to_kg(weight: float | None, units: str | None = "kg") -> float:
    value = max(0.0, float(weight or 0))
    if (units or "kg").strip().lower() in LB_UNITS:
        return value * LB_TO_KG
    return value

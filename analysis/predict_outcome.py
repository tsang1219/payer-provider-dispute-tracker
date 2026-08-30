#!/usr/bin/env python3
"""
Dispute Outcome Predictor
Simple rule-based predictor based on empirical patterns from dispute data
"""

import sys

def predict_outcome(
    insurer: str,
    provider_type: str = "standard",  # "academic", "large_system", "regional", "small_rural", "specialty"
    lawsuit_filed: bool = False,
    state: str = None,
    age_months: int = 0,
    has_public_pressure: bool = False
) -> dict:
    """
    Predict dispute outcome based on empirical patterns.

    Returns dict with:
        - prediction: "Resolved" or "OON-Ongoing"
        - confidence: 0-100%
        - factors: list of contributing factors
    """

    # Start with base probability
    base_prob = 0.36  # Overall resolution rate from data

    factors = []
    adjustments = []

    # ===== INSURER FACTOR (strongest predictor) =====
    insurer_lower = insurer.lower()

    if "humana" in insurer_lower:
        adjustment = -0.35  # 0% resolution in our data!
        adjustments.append(adjustment)
        factors.append(f"Humana: Very low resolution rate (-35%)")
    elif "bcbs" in insurer_lower or "blue cross" in insurer_lower or "blue shield" in insurer_lower:
        adjustment = 0.20
        adjustments.append(adjustment)
        factors.append(f"BCBS: Higher resolution rate (+20%)")
    elif "anthem" in insurer_lower or "elevance" in insurer_lower:
        adjustment = 0.15
        adjustments.append(adjustment)
        factors.append(f"Anthem/Elevance: Above average resolution (+15%)")
    elif "united" in insurer_lower or "uhc" in insurer_lower:
        adjustment = 0.05
        adjustments.append(adjustment)
        factors.append(f"UnitedHealthcare: Near average resolution (+5%)")
    elif "aetna" in insurer_lower or "cvs" in insurer_lower:
        adjustment = -0.15
        adjustments.append(adjustment)
        factors.append(f"Aetna/CVS: Below average resolution (-15%)")
    elif "cigna" in insurer_lower:
        adjustment = -0.10
        adjustments.append(adjustment)
        factors.append(f"Cigna: Below average resolution (-10%)")

    # ===== PROVIDER TYPE FACTOR =====
    if provider_type == "academic":
        adjustment = 0.35
        adjustments.append(adjustment)
        factors.append(f"Academic medical center: Very high leverage (+35%)")
    elif provider_type == "specialty":
        adjustment = 0.30
        adjustments.append(adjustment)
        factors.append(f"Specialty provider (oncology/pediatric): High leverage (+30%)")
    elif provider_type == "large_system":
        adjustment = 0.20
        adjustments.append(adjustment)
        factors.append(f"Large health system: Good leverage (+20%)")
    elif provider_type == "regional":
        adjustment = 0.05
        adjustments.append(adjustment)
        factors.append(f"Regional provider: Moderate leverage (+5%)")
    elif provider_type == "small_rural":
        adjustment = -0.15
        adjustments.append(adjustment)
        factors.append(f"Small/rural provider: Limited leverage (-15%)")

    # ===== LAWSUIT FACTOR =====
    if lawsuit_filed:
        adjustment = 0.25
        adjustments.append(adjustment)
        factors.append(f"Lawsuit filed: Strong pressure to resolve (+25%)")

    # ===== PUBLIC PRESSURE FACTOR =====
    if has_public_pressure:
        adjustment = 0.15
        adjustments.append(adjustment)
        factors.append(f"Media/AG attention: Accelerates resolution (+15%)")

    # ===== STATE FACTOR =====
    high_resolution_states = ["ny", "ct", "fl", "ca"]
    low_resolution_states = ["mi", "or", "pa", "nc"]

    if state:
        state_lower = state.lower()
        if state_lower in high_resolution_states:
            adjustment = 0.10
            adjustments.append(adjustment)
            factors.append(f"State {state.upper()}: Above average resolution (+10%)")
        elif state_lower in low_resolution_states:
            adjustment = -0.10
            adjustments.append(adjustment)
            factors.append(f"State {state.upper()}: Below average resolution (-10%)")

    # ===== RECENCY FACTOR =====
    if age_months < 6:
        adjustment = -0.15
        adjustments.append(adjustment)
        factors.append(f"Recent dispute (<6 months): Still developing (-15%)")
    elif age_months > 12:
        adjustment = 0.10
        adjustments.append(adjustment)
        factors.append(f"Mature dispute (>12 months): Pressure to resolve (+10%)")

    # Calculate final probability
    final_prob = base_prob + sum(adjustments)
    final_prob = max(0.05, min(0.95, final_prob))  # Clamp to 5-95%

    # Determine prediction
    if final_prob >= 0.50:
        prediction = "Resolved"
        confidence = final_prob * 100
    else:
        prediction = "OON-Ongoing"
        confidence = (1 - final_prob) * 100

    return {
        "prediction": prediction,
        "confidence": round(confidence, 1),
        "resolution_probability": round(final_prob * 100, 1),
        "factors": factors,
        "base_rate": "36%"
    }


def interactive_predict():
    """Interactive prediction mode"""
    print("\n" + "=" * 60)
    print("DISPUTE OUTCOME PREDICTOR")
    print("=" * 60)

    print("\nEnter dispute characteristics (press Enter for defaults):\n")

    # Get insurer
    insurer = input("Insurer name (e.g., UnitedHealthcare, Humana, BCBS): ").strip()
    if not insurer:
        insurer = "Unknown"

    # Get provider type
    print("\nProvider types: academic, large_system, regional, small_rural, specialty")
    provider_type = input("Provider type [standard]: ").strip().lower()
    if provider_type not in ["academic", "large_system", "regional", "small_rural", "specialty"]:
        provider_type = "standard"

    # Get lawsuit status
    lawsuit = input("Lawsuit filed? (y/n) [n]: ").strip().lower()
    lawsuit_filed = lawsuit == 'y'

    # Get state
    state = input("State (2-letter code, optional): ").strip().upper()
    if len(state) != 2:
        state = None

    # Get age
    age_str = input("Dispute age in months [0]: ").strip()
    try:
        age_months = int(age_str) if age_str else 0
    except:
        age_months = 0

    # Get public pressure
    pressure = input("Media/AG attention? (y/n) [n]: ").strip().lower()
    has_public_pressure = pressure == 'y'

    # Run prediction
    result = predict_outcome(
        insurer=insurer,
        provider_type=provider_type,
        lawsuit_filed=lawsuit_filed,
        state=state,
        age_months=age_months,
        has_public_pressure=has_public_pressure
    )

    # Display results
    print("\n" + "=" * 60)
    print("PREDICTION RESULTS")
    print("=" * 60)

    print(f"\n🎯 PREDICTED OUTCOME: {result['prediction']}")
    print(f"   Confidence: {result['confidence']}%")
    print(f"   Resolution probability: {result['resolution_probability']}%")

    print("\n📊 CONTRIBUTING FACTORS:")
    for factor in result['factors']:
        print(f"   • {factor}")

    print(f"\n   Base rate (historical): {result['base_rate']}")
    print("=" * 60)


# Example predictions
def show_examples():
    print("\n" + "=" * 60)
    print("EXAMPLE PREDICTIONS")
    print("=" * 60)

    examples = [
        {
            "name": "Academic center vs UnitedHealthcare",
            "params": {"insurer": "UnitedHealthcare", "provider_type": "academic", "state": "NY"}
        },
        {
            "name": "Small rural hospital vs Humana",
            "params": {"insurer": "Humana", "provider_type": "small_rural", "state": "MN"}
        },
        {
            "name": "Regional system vs BCBS with lawsuit",
            "params": {"insurer": "Blue Cross Blue Shield", "provider_type": "regional", "lawsuit_filed": True}
        },
        {
            "name": "Specialty center vs Aetna",
            "params": {"insurer": "Aetna", "provider_type": "specialty", "has_public_pressure": True}
        },
        {
            "name": "Large system vs Cigna (recent)",
            "params": {"insurer": "Cigna", "provider_type": "large_system", "age_months": 2}
        },
    ]

    for ex in examples:
        result = predict_outcome(**ex["params"])
        print(f"\n📋 {ex['name']}")
        print(f"   Prediction: {result['prediction']} ({result['confidence']}% confidence)")
        print(f"   Resolution probability: {result['resolution_probability']}%")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_examples()
    else:
        show_examples()
        print("\n" + "-" * 60)
        interactive_predict()

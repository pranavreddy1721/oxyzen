"""OxyZen explainable environmental health-risk engine.

Rule-based, transparent scoring. Structured so a future ML model can replace
`assess()` while keeping the same input/output contract.

Input:  aqi + 6 pollutant concentrations
Output: riskLevel, riskScore (0-100), mainContributors, explanation,
        healthImpacts, precautions, activityGuidance
"""
from aqi_data import POLLUTANT_META

# Per-pollutant concentration considered "high" (upper bound used to normalize 0..1).
# Roughly 2-3x the health reference / guideline value.
HIGH_LEVEL = {
    "pm25": 120.0,
    "pm10": 200.0,
    "o3": 200.0,
    "no2": 120.0,
    "so2": 150.0,
    "co": 12.0,
}

# Weights reflect relative health significance of each pollutant.
WEIGHTS = {
    "pm25": 0.34,
    "aqi": 0.24,
    "pm10": 0.14,
    "o3": 0.12,
    "no2": 0.08,
    "so2": 0.05,
    "co": 0.03,
}

RISK_BANDS = [
    (0, 20,  "LOW",       "low"),
    (21, 40, "MODERATE",  "moderate"),
    (41, 60, "ELEVATED",  "elevated"),
    (61, 80, "HIGH",      "high"),
    (81, 100, "SEVERE",   "severe"),
]

RISK_COLORS = {
    "low": "#10B981",
    "moderate": "#F59E0B",
    "elevated": "#F97316",
    "high": "#EF4444",
    "severe": "#9F1239",
}


def _band(score: int):
    for lo, hi, label, key in RISK_BANDS:
        if lo <= score <= hi:
            return label, key
    return "SEVERE", "severe"


def _norm(value: float, high: float) -> float:
    return max(0.0, min(1.0, value / high))


def assess(aqi: int, pollutants: dict) -> dict:
    # normalized sub-scores (0..1)
    subs = {k: _norm(pollutants[k], HIGH_LEVEL[k]) for k in HIGH_LEVEL}
    aqi_norm = max(0.0, min(1.0, aqi / 300.0))

    weighted = aqi_norm * WEIGHTS["aqi"]
    for k in HIGH_LEVEL:
        weighted += subs[k] * WEIGHTS[k]
    score = int(round(weighted * 100))
    score = max(0, min(100, score))
    label, key = _band(score)

    # main contributors (share of total weighted score)
    contrib_raw = {"AQI": aqi_norm * WEIGHTS["aqi"]}
    for k in HIGH_LEVEL:
        contrib_raw[POLLUTANT_META[k]["name"]] = subs[k] * WEIGHTS[k]
    total = sum(contrib_raw.values()) or 1.0
    contributors = [
        {"name": n, "share": round(v / total, 3), "intensity": round(min(1.0, v / (total or 1) * 3), 2)}
        for n, v in sorted(contrib_raw.items(), key=lambda x: x[1], reverse=True)
    ]
    # normalize intensity so top contributor fills the bar
    top = contributors[0]["share"] if contributors else 1.0
    for c in contributors:
        c["intensity"] = round(min(1.0, c["share"] / top), 2) if top else 0.0

    top_names = [c["name"] for c in contributors[:2] if c["share"] > 0.05]
    explanation = _explanation(key, top_names)
    return {
        "aqi": aqi,
        "riskScore": score,
        "riskLevel": label,
        "riskLevelKey": key,
        "riskColor": RISK_COLORS[key],
        "mainContributors": contributors,
        "explanation": explanation,
        "healthImpacts": _impacts(key),
        "precautions": _precautions(key),
        "activityGuidance": _activities(aqi),
        "scoreBands": [
            {"range": "0–20", "label": "Low"},
            {"range": "21–40", "label": "Moderate"},
            {"range": "41–60", "label": "Elevated"},
            {"range": "61–80", "label": "High"},
            {"range": "81–100", "label": "Severe"},
        ],
        "disclaimer": "Environmental Health Risk Score — an awareness indicator based on air-quality conditions. Not a medical diagnosis or clinical assessment.",
    }


def _explanation(key: str, top_names) -> str:
    if not top_names:
        top_names = ["overall air quality"]
    factors = " and ".join(top_names)
    base = {
        "low": f"Air quality is favorable. The current environmental health risk is low, driven mainly by {factors}. Outdoor activity is generally appropriate for most people.",
        "moderate": f"Air quality is acceptable but slightly elevated, primarily due to {factors}. Unusually sensitive individuals may wish to limit prolonged outdoor exertion.",
        "elevated": f"Pollution is elevated, with {factors} the leading contributors. Sensitive groups may begin to experience effects and should moderate outdoor exposure.",
        "high": f"The current risk is high and primarily associated with elevated {factors}. Reducing prolonged outdoor exertion is advisable, especially for sensitive individuals.",
        "severe": f"Air quality poses a severe environmental health risk, driven strongly by {factors}. Minimizing outdoor exposure and keeping indoor air clean is strongly advised.",
    }
    return base[key]


def _impacts(key: str):
    if key in ("low",):
        return [
            {"system": "Respiratory", "text": "Little to no respiratory impact expected under current conditions."},
            {"system": "Cardiovascular", "text": "No meaningful additional cardiovascular stress from air quality."},
            {"system": "General", "text": "Conditions are comfortable for outdoor activity for the general population."},
        ]
    if key in ("moderate",):
        return [
            {"system": "Respiratory", "text": "Very sensitive individuals may notice mild airway irritation with prolonged exposure."},
            {"system": "Cardiovascular", "text": "Minimal additional cardiovascular stress for the general population."},
            {"system": "General", "text": "Most people can continue normal activities without discomfort."},
        ]
    if key in ("elevated",):
        return [
            {"system": "Respiratory", "text": "Potential airway irritation and mild breathing discomfort, especially for those with asthma."},
            {"system": "Cardiovascular", "text": "Some added environmental stress possible with prolonged outdoor exposure."},
            {"system": "General", "text": "Sensitive groups (children, elderly, pregnant, respiratory/heart conditions) should take care."},
        ]
    if key in ("high",):
        return [
            {"system": "Respiratory", "text": "Increased likelihood of coughing, throat irritation and breathing discomfort with exposure."},
            {"system": "Cardiovascular", "text": "Prolonged exposure is associated with increased cardiovascular strain in vulnerable people."},
            {"system": "General", "text": "Fatigue, headache or irritation may occur; sensitive individuals are more affected."},
        ]
    return [
        {"system": "Respiratory", "text": "High pollution may significantly aggravate respiratory conditions and irritate healthy airways."},
        {"system": "Cardiovascular", "text": "Prolonged exposure may increase cardiovascular stress, particularly for at-risk individuals."},
        {"system": "General", "text": "Everyone may experience discomfort; outdoor exposure should be minimized."},
    ]


def _precautions(key: str):
    return {
        "low": [
            "Normal outdoor activity is generally appropriate.",
            "A good time for outdoor exercise and ventilation.",
        ],
        "moderate": [
            "Most people can maintain normal activity.",
            "Unusually sensitive individuals may consider reducing prolonged outdoor exertion.",
        ],
        "elevated": [
            "Sensitive groups should limit prolonged or heavy outdoor exertion.",
            "Consider shifting intense activity to times with cleaner air.",
            "Keep windows closed during pollution peaks.",
        ],
        "high": [
            "Reduce prolonged outdoor exposure.",
            "Avoid intense outdoor exercise.",
            "Keep indoor air as clean as practical (filtration, closed windows).",
            "Sensitive individuals should stay indoors when possible.",
        ],
        "severe": [
            "Minimize outdoor exposure; stay indoors where possible.",
            "Avoid all outdoor exercise.",
            "Keep indoor air clean and follow local public-health guidance.",
            "Sensitive individuals should take particular care.",
        ],
    }[key]


def _activities(aqi: int):
    """Activity safety indicator per outdoor activity."""
    acts = [
        {"key": "walking", "name": "Walking", "icon": "footprints", "threshold": 200},
        {"key": "running", "name": "Running", "icon": "activity", "threshold": 150},
        {"key": "cycling", "name": "Cycling", "icon": "bike", "threshold": 150},
        {"key": "sports", "name": "Outdoor Sports", "icon": "dumbbell", "threshold": 130},
    ]
    out = []
    for a in acts:
        t = a["threshold"]
        if aqi <= t * 0.5:
            status, key = "Recommended", "good"
        elif aqi <= t * 0.8:
            status, key = "Use Caution", "caution"
        elif aqi <= t:
            status, key = "Limit Activity", "limit"
        else:
            status, key = "Not Recommended", "avoid"
        out.append({"key": a["key"], "name": a["name"], "icon": a["icon"], "status": status, "statusKey": key})
    return out


def exposure_guidance(aqi: int, environment: str, activity: str, duration: str) -> dict:
    """Lightweight exposure-context guidance (NOT a mask recommendation)."""
    load = {"resting": 1.0, "walking": 1.4, "exercise": 2.2}.get(activity, 1.0)
    dur = {"<1h": 0.6, "1-3h": 1.0, "3h+": 1.6}.get(duration, 1.0)
    env = {"indoor": 0.45, "outdoor": 1.0}.get(environment, 1.0)
    effective = aqi * load * dur * env

    if effective < 60:
        level, text = "Low exposure concern", "Your current context suggests a low pollution exposure. General activity is fine."
    elif effective < 130:
        level, text = "Moderate exposure", "Your context suggests moderate exposure. Consider shorter sessions or lighter intensity if you are sensitive."
    elif effective < 250:
        level, text = "Elevated exposure", "This combination leads to elevated exposure. Reduce intensity and duration outdoors, and prefer cleaner indoor air."
    else:
        level, text = "High exposure", "This combination results in high pollution exposure. Strongly consider staying indoors, reducing exertion, and improving indoor air quality."

    tips = []
    if environment == "outdoor":
        tips.append("Prefer times of day when pollution is lower (often late night / early morning).")
    if activity == "exercise":
        tips.append("Heavy breathing increases the volume of air inhaled — lower the intensity when air is poor.")
    if environment == "indoor":
        tips.append("Good filtration and closed windows during peaks help keep indoor air cleaner.")
    tips.append("General guidance only — not a personalized medical or mask recommendation.")
    return {"level": level, "text": text, "tips": tips, "effectiveExposure": int(effective)}

// AQI + risk color helpers shared across the app (must match backend hex codes).

export const AQI_COLORS = {
  good: "#10B981",
  moderate: "#F59E0B",
  sensitive: "#F97316",
  unhealthy: "#EF4444",
  veryUnhealthy: "#9333EA",
  hazardous: "#9F1239",
};

export const RISK_COLORS = {
  low: "#10B981",
  moderate: "#F59E0B",
  elevated: "#F97316",
  high: "#EF4444",
  severe: "#9F1239",
};

export function aqiCategory(aqi) {
  if (aqi <= 50) return { key: "good", label: "Good", color: AQI_COLORS.good };
  if (aqi <= 100) return { key: "moderate", label: "Moderate", color: AQI_COLORS.moderate };
  if (aqi <= 150) return { key: "sensitive", label: "Unhealthy for Sensitive Groups", color: AQI_COLORS.sensitive };
  if (aqi <= 200) return { key: "unhealthy", label: "Unhealthy", color: AQI_COLORS.unhealthy };
  if (aqi <= 300) return { key: "veryUnhealthy", label: "Very Unhealthy", color: AQI_COLORS.veryUnhealthy };
  return { key: "hazardous", label: "Hazardous", color: AQI_COLORS.hazardous };
}

// Yellow/moderate needs dark text for contrast
export function textOn(color) {
  return ["#F59E0B", "#10B981"].includes(color) ? "#0b0b0b" : "#ffffff";
}

export const ACTIVITY_STATUS_COLORS = {
  good: "#10B981",
  caution: "#F59E0B",
  limit: "#F97316",
  avoid: "#EF4444",
};

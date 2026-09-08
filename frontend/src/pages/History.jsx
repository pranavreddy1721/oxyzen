import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { useLocation } from "@/context/LocationContext";
import { aqiCategory } from "@/lib/aqiColors";
import LocationSearch from "@/components/LocationSearch";
import AQIChart from "@/components/AQIChart";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoader, ErrorState } from "@/components/states";

const RANGES = [{ v: "24h", label: "24 Hours" }, { v: "7d", label: "7 Days" }, { v: "30d", label: "30 Days" }];
const POLLUTANTS = [
  { v: "aqi", label: "AQI", unit: "" },
  { v: "pm25", label: "PM2.5", unit: " µg/m³" },
  { v: "pm10", label: "PM10", unit: " µg/m³" },
  { v: "o3", label: "O₃", unit: " µg/m³" },
  { v: "no2", label: "NO₂", unit: " µg/m³" },
  { v: "so2", label: "SO₂", unit: " µg/m³" },
  { v: "co", label: "CO", unit: " mg/m³" },
];

export default function History() {
  const { location, setLocation } = useLocation();
  const [range, setRange] = useState("7d");
  const [pollutant, setPollutant] = useState("aqi");
  const [points, setPoints] = useState(null);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setError(false); setPoints(null);
    try {
      const { data } = await api.get("/aqi/history", { params: { locationId: location.id, lat: location.lat, lon: location.lon, locationName: location.name, locationCountry: location.country, range } });
      setPoints(data.points);
    } catch { setError(true); }
  }, [location, range]);

  useEffect(() => { load(); }, [load]);

  const trend = points && points.length > 1
    ? points[points.length - 1][pollutant] - points[0][pollutant]
    : 0;
  const trendLabel = trend > 3 ? "Worsening" : trend < -3 ? "Improving" : "Stable";
  const meta = POLLUTANTS.find((p) => p.v === pollutant);
  const avg = points?.length ? Math.round(points.reduce((s, p) => s + p[pollutant], 0) / points.length) : 0;
  const color = pollutant === "aqi" && points?.length ? aqiCategory(avg).color : "#10B981";

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="font-heading text-3xl font-black tracking-tight sm:text-4xl">Historical Analysis</h1>
        <p className="mt-1 text-muted-foreground">Understand whether pollution in <span className="font-semibold text-foreground">{location.name}</span> is improving, worsening or stable.</p>
      </div>

      <div className="mb-6 max-w-3xl"><LocationSearch onSelect={setLocation} /></div>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={range} onValueChange={setRange}>
          <TabsList data-testid="history-range-tabs">
            {RANGES.map((r) => <TabsTrigger key={r.v} value={r.v} data-testid={`range-${r.v}`}>{r.label}</TabsTrigger>)}
          </TabsList>
        </Tabs>
        <div className="flex flex-wrap gap-2" data-testid="history-pollutant-select">
          {POLLUTANTS.map((p) => (
            <button
              key={p.v}
              onClick={() => setPollutant(p.v)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${pollutant === p.v ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <ErrorState onRetry={load} />
      ) : !points ? (
        <PageLoader />
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Average", value: avg + meta.unit },
              { label: "Peak", value: Math.max(...points.map((p) => p[pollutant])) + meta.unit },
              { label: "Lowest", value: Math.min(...points.map((p) => p[pollutant])) + meta.unit },
              { label: "Trend", value: trendLabel },
            ].map((s) => (
              <div key={s.label} className="rounded-xl border border-border bg-card p-4">
                <p className="text-xs uppercase tracking-widest text-muted-foreground">{s.label}</p>
                <p className="mt-1 font-data text-xl font-bold">{s.value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-widest text-muted-foreground">{meta.label} · {RANGES.find((r) => r.v === range).label}</h3>
            <AQIChart data={points} dataKey={pollutant} color={color} height={340} unit={meta.unit} />
          </div>
        </>
      )}
    </div>
  );
}

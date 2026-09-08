const SEGMENTS = [
  { label: "Good", range: "0–50", color: "#10B981", max: 50 },
  { label: "Moderate", range: "51–100", color: "#F59E0B", max: 100 },
  { label: "Sensitive", range: "101–150", color: "#F97316", max: 150 },
  { label: "Unhealthy", range: "151–200", color: "#EF4444", max: 200 },
  { label: "Very Unhealthy", range: "201–300", color: "#9333EA", max: 300 },
  { label: "Hazardous", range: "301+", color: "#9F1239", max: 500 },
];

export default function AQIScale({ aqi }) {
  const pos = Math.min(100, (Math.min(aqi, 500) / 500) * 100);
  return (
    <div className="rounded-xl border border-border bg-card p-6" data-testid="aqi-scale">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">AQI Scale</h3>
        {aqi != null && <span className="font-data text-xs text-muted-foreground">Current: {aqi}</span>}
      </div>
      <div className="relative">
        <div className="flex h-3 overflow-hidden rounded-full">
          {SEGMENTS.map((s) => (
            <div key={s.label} className="flex-1" style={{ background: s.color }} />
          ))}
        </div>
        {aqi != null && (
          <div className="absolute -top-1 h-5 w-1 -translate-x-1/2 rounded-full bg-foreground ring-2 ring-background" style={{ left: `${pos}%` }} data-testid="aqi-scale-marker" />
        )}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3 lg:grid-cols-6">
        {SEGMENTS.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: s.color }} />
            <div className="min-w-0">
              <p className="truncate text-xs font-medium">{s.label}</p>
              <p className="font-data text-[10px] text-muted-foreground">{s.range}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

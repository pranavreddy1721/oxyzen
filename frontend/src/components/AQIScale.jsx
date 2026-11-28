const SEGMENTS = [
  { label: "Good", range: "0–50", color: "#10B981" },
  { label: "Moderate", range: "51–100", color: "#F59E0B" },
  { label: "Sensitive", range: "101–150", color: "#F97316" },
  { label: "Unhealthy", range: "151–200", color: "#EF4444" },
  { label: "Very Unhealthy", range: "201–300", color: "#9333EA" },
  { label: "Hazardous", range: "301+", color: "#9F1239" },
];

export default function AQIScale({ aqi, aqiScale }) {
  const cpcb = aqiScale === "india_cpcb";
  const segments = cpcb ? [
    { label: "Good", range: "0–50", color: "#10B981" },
    { label: "Satisfactory", range: "51–100", color: "#84CC16" },
    { label: "Moderate", range: "101–200", color: "#F59E0B" },
    { label: "Poor", range: "201–300", color: "#F97316" },
    { label: "Very Poor", range: "301–400", color: "#EF4444" },
    { label: "Severe", range: "401–500", color: "#7F1D1D" },
  ] : SEGMENTS;
  const pos = Math.min(100, (Math.min(aqi, 500) / 500) * 100);
  return (
    <div className="rounded-2xl border border-emerald-400/40 bg-[#071b17] p-5" data-testid="aqi-scale">
      <div className="mb-5 flex items-center justify-between"><h3 className="text-sm font-bold uppercase tracking-widest text-slate-300">{cpcb ? "CPCB National AQI Scale" : "US AQI Scale"}</h3>{aqi != null && <span className="font-data text-xs text-slate-300">Current: {aqi}</span>}</div>
      <div className="relative"><div className="flex h-3 overflow-hidden rounded-full">{segments.map((s) => <div key={s.label} className="flex-1" style={{background:s.color}}/>)}</div>{aqi != null && <div className="absolute -top-1 h-5 w-1 -translate-x-1/2 rounded-full bg-white ring-2 ring-[#071b17]" style={{left:pos+"%"}} data-testid="aqi-scale-marker"/>}</div>
      <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-3 sm:grid-cols-3 xl:grid-cols-6">{segments.map((s) => <div key={s.label} className="flex items-center gap-2"><span className="h-3 w-3 shrink-0 rounded-full" style={{background:s.color}}/><div className="min-w-0"><p className="truncate text-xs font-semibold text-white">{s.label}</p><p className="font-data text-[10px] text-slate-400">{s.range}</p></div></div>)}</div>
    </div>
  );
}

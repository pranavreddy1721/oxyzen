import { aqiCategory, textOn } from "@/lib/aqiColors";

export default function AQICard({ aqi, category, color, dominantPollutant, updatedAt, locationName, source, aqiScale }) {
  const hasAqi = aqi != null && Number.isFinite(Number(aqi));
  const cat = category ? { label: category, color } : hasAqi ? aqiCategory(aqi) : { label: "Unavailable", color: "#64748B" };
  const c = color || cat.color;
  const pct = hasAqi ? Math.min(100, (Number(aqi) / 500) * 100) : 0;
  const circumference = 2 * Math.PI * 88;
  const dash = (pct / 100) * circumference;
  const isNearby = source?.matchType === "nearby";
  const station = source?.station || "WAQI station";
  const distance = Number.isFinite(source?.distanceKm) ? source.distanceKm + " km away" : null;
  const agency = source?.origin || "Source agency not specified";
  const dataType = source?.dataType || "Live monitoring-station data";
  return (
    <div className="relative flex h-full min-h-[650px] flex-col justify-between overflow-hidden rounded-2xl border border-emerald-400/40 bg-[#071b17] p-5 shadow-[0_0_35px_rgba(16,185,129,0.08)]" data-testid="aqi-card">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_52%,rgba(16,185,129,0.16),transparent_58%),linear-gradient(180deg,rgba(4,18,15,0.96)_0%,rgba(4,18,15,0.60)_48%,rgba(4,18,15,0.98)_100%)]" />
      <div className="relative z-10 flex items-start justify-between">
        <div><p className="text-sm font-semibold uppercase tracking-widest text-slate-300">Air Quality Index</p>{locationName && <p className="mt-2 font-heading text-3xl font-bold text-white">{locationName}</p>}</div>
        <span className="rounded-full px-4 py-2 text-sm font-bold" style={{background:c,color:textOn(c)}} data-testid="aqi-category-badge">{cat.label}</span>
      </div>
      <div className="relative z-10 my-8 flex items-center justify-center">
        <div className="relative h-64 w-64 max-w-full">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 200 200"><circle cx="100" cy="100" r="88" fill="none" stroke="rgba(148,163,184,.22)" strokeWidth="12"/><circle cx="100" cy="100" r="88" fill="none" stroke={c} strokeWidth="12" strokeLinecap="round" strokeDasharray={dash + " " + circumference} style={{transition:"stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)"}}/></svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center"><span className="font-data text-7xl font-bold leading-none" style={{color:c}} data-testid="aqi-value">{hasAqi ? aqi : "—"}</span><span className="mt-2 text-base font-semibold uppercase tracking-widest text-white">{aqiScale === "india_cpcb" ? "India CPCB AQI" : "US AQI"}</span></div>
        </div>
      </div>
      <div className="relative z-10 border-t border-emerald-200/20 pt-5 text-sm text-slate-300">
        <div className="flex items-center justify-between gap-2"><span>Dominant: <span className="font-data font-semibold text-white">{(dominantPollutant || "—").toUpperCase()}</span></span>{updatedAt && <span className="font-data text-xs">Updated {new Date(updatedAt).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</span>}</div>
        <div className="mt-4 rounded-xl border border-emerald-300/30 bg-black/30 p-4 backdrop-blur-sm" data-testid="data-source-card">
          <p className="text-xs font-bold uppercase tracking-widest text-emerald-300">● Live Data Source</p>
          <div className="mt-3 space-y-2 text-xs leading-relaxed text-slate-200">
            <p><strong className="text-white">Selected location:</strong> {locationName || "—"}</p>
            <p><strong className="text-white">Monitoring station:</strong> {station}</p>
            <p><strong className="text-white">Source agency:</strong> {agency}</p>
            <p><strong className="text-white">Provider:</strong> {source?.provider || "World Air Quality Index (WAQI)"}</p>
            <p><strong className="text-white">Data type:</strong> {dataType}{distance ? " · " + distance : ""}</p>
            {isNearby && <p className="pt-1 font-semibold text-emerald-200">This AQI is from a nearby monitoring station, not an exact city measurement.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

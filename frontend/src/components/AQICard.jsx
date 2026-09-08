import { aqiCategory, textOn } from "@/lib/aqiColors";

export default function AQICard({ aqi, category, color, dominantPollutant, updatedAt, locationName, source }) {
  const cat = category ? { label: category, color } : aqiCategory(aqi);
  const c = color || cat.color;
  const pct = Math.min(100, (aqi / 500) * 100);
  const circumference = 2 * Math.PI * 88;
  const dash = (pct / 100) * circumference;
  return <div className="relative flex h-full flex-col justify-between overflow-hidden rounded-xl border border-border bg-card p-8" data-testid="aqi-card">
    <div className="flex items-start justify-between"><div><p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Air Quality Index</p>{locationName&&<p className="mt-1 font-heading text-lg font-bold">{locationName}</p>}</div><span className="rounded-full px-3 py-1 text-xs font-bold" style={{background:c,color:textOn(c)}} data-testid="aqi-category-badge">{cat.label}</span></div>
    <div className="my-6 flex items-center justify-center"><div className="relative h-52 w-52"><svg className="h-full w-full -rotate-90" viewBox="0 0 200 200"><circle cx="100" cy="100" r="88" fill="none" stroke="hsl(var(--muted))" strokeWidth="12"/><circle cx="100" cy="100" r="88" fill="none" stroke={c} strokeWidth="12" strokeLinecap="round" strokeDasharray={`${dash} ${circumference}`} style={{transition:"stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)"}}/></svg><div className="absolute inset-0 flex flex-col items-center justify-center"><span className="font-data text-6xl font-bold leading-none" style={{color:c}} data-testid="aqi-value">{aqi}</span><span className="mt-1 text-xs uppercase tracking-widest text-muted-foreground">US AQI</span></div></div></div>
    <div className="border-t border-border pt-4 text-xs text-muted-foreground"><div className="flex items-center justify-between"><span>Dominant: <span className="font-data font-semibold text-foreground">{(dominantPollutant||"—").toUpperCase()}</span></span>{updatedAt&&<span className="font-data">Updated {new Date(updatedAt).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</span>}</div><p className="mt-2 text-[11px]">Source: {source?.provider||"World Air Quality Index (WAQI)"}</p></div>
  </div>;
}

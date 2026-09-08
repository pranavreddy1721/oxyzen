import { useState } from "react";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import api from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Spinner } from "@/components/states";

const SEV = { Good: "#10B981", Moderate: "#F59E0B", High: "#F97316", "Very High": "#EF4444" };
function severity(value) { if (value <= 50) return "Good"; if (value <= 100) return "Moderate"; if (value <= 150) return "High"; return "Very High"; }

export default function PollutantGrid({ pollutants, meta, location }) {
  const [active, setActive] = useState(null); const [detail, setDetail] = useState(null); const [loading, setLoading] = useState(false);
  const openDetail = async (key) => { setActive(key); setDetail(null); setLoading(true); try { const { data } = await api.get(`/aqi/pollutant/${key}`, { params: { locationId: location?.id, lat: location?.lat, lon: location?.lon, locationName: location?.name, locationCountry: location?.country } }); setDetail(data); } catch { setDetail(null); } finally { setLoading(false); } };
  const keys = ["pm25", "pm10", "o3", "no2", "so2", "co"];
  return <>
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3" data-testid="pollutant-grid">
      {keys.map((k) => { const m = meta[k]; const value = pollutants[k]; const sev = severity(value); const color = SEV[sev]; return <button key={k} onClick={() => openDetail(k)} data-testid={`pollutant-card-${k}`} className="group flex flex-col items-start rounded-xl border border-border bg-card p-5 text-left transition-transform hover:-translate-y-1 hover:border-primary">
        <div className="flex w-full items-center justify-between"><span className="font-heading text-lg font-bold">{m.name}</span><span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} /></div>
        <div className="mt-3 flex items-baseline gap-1"><span className="font-data text-2xl font-bold" style={{ color }}>{value}</span><span className="text-xs text-muted-foreground">AQI sub-index</span></div>
        <span className="mt-1 text-xs font-semibold" style={{ color }}>{sev}</span><p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{m.short}</p>
      </button>; })}
    </div>
    <Dialog open={!!active} onOpenChange={(o) => !o && setActive(null)}><DialogContent className="max-w-lg" data-testid="pollutant-modal">{active && <><DialogHeader><DialogTitle className="font-heading text-2xl">{meta[active].name} · <span className="text-base font-normal text-muted-foreground">{meta[active].full_name}</span></DialogTitle></DialogHeader>}{loading && <div className="flex justify-center py-10"><Spinner /></div>}{detail && <div className="space-y-5 pt-1">
      <div className="flex items-center gap-6 rounded-xl border border-border bg-accent/40 p-4"><div><p className="text-xs uppercase tracking-widest text-muted-foreground">Current</p><p className="font-data text-3xl font-bold" style={{ color: SEV[detail.severity] }}>{detail.current}</p><p className="text-xs text-muted-foreground">AQI sub-index</p></div><div><p className="text-xs uppercase tracking-widest text-muted-foreground">Reference</p><p className="font-data text-3xl font-bold text-foreground">{detail.reference}</p><p className="text-xs text-muted-foreground">AQI sub-index</p></div><div><p className="text-xs uppercase tracking-widest text-muted-foreground">Severity</p><p className="text-lg font-bold" style={{ color: SEV[detail.severity] }}>{detail.severity}</p></div></div>
      <p className="text-sm text-muted-foreground">{meta[active].what}</p>{detail.trend && <div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">24-hour trend</p><div className="h-28 w-full"><ResponsiveContainer width="100%" height="100%"><AreaChart data={detail.trend}><defs><linearGradient id="polgrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={SEV[detail.severity]} stopOpacity={0.4}/><stop offset="100%" stopColor={SEV[detail.severity]} stopOpacity={0}/></linearGradient></defs><XAxis dataKey="label" hide/><Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 12, fontSize: 12 }}/><Area type="monotone" dataKey="value" stroke={SEV[detail.severity]} strokeWidth={2} fill="url(#polgrad)"/></AreaChart></ResponsiveContainer></div></div>}
      <div className="grid grid-cols-2 gap-4"><div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Main sources</p><ul className="space-y-1 text-sm text-muted-foreground">{meta[active].sources.map((s) => <li key={s}>· {s}</li>)}</ul></div><div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Health effects</p><ul className="space-y-1 text-sm text-muted-foreground">{meta[active].effects.map((s) => <li key={s}>· {s}</li>)}</ul></div></div><div><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">General precautions</p><ul className="space-y-1 text-sm text-muted-foreground">{meta[active].precautions.map((s) => <li key={s}>· {s}</li>)}</ul></div>
    </div>}</>}</DialogContent></Dialog>
  </>;
}

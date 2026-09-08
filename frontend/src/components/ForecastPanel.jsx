import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { textOn } from "@/lib/aqiColors";
const TREND_ICON={worsening:TrendingUp,improving:TrendingDown,stable:Minus};
export default function ForecastPanel({forecast}){
 if(!forecast?.length)return null;
 return <div className="rounded-xl border border-border bg-card p-6" data-testid="forecast-panel"><h3 className="mb-1 text-sm font-semibold uppercase tracking-widest text-muted-foreground">Air Quality Forecast</h3><p className="mb-4 text-xs text-muted-foreground">Derived from available WAQI pollutant forecast sub-indices.</p><div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{forecast.map(f=>{const Trend=TREND_ICON[f.trend]||Minus;return <div key={f.t} className="rounded-xl border border-border p-4" data-testid={`forecast-day-${f.label}`}><p className="text-xs font-medium text-muted-foreground">{f.label}</p><p className="mt-2 font-data text-3xl font-bold" style={{color:f.color}}>{f.aqi}</p><span className="mt-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{background:f.color,color:textOn(f.color)}}>{f.category}</span><div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground"><Trend className="h-3.5 w-3.5" strokeWidth={1.5}/> {f.trend}</div></div>})}</div></div>;
}

import { HeartPulse, Wind, Activity, ShieldCheck, Info, Layers3 } from "lucide-react";

const SYS_ICON = { Respiratory: Wind, Cardiovascular: HeartPulse, General: Activity };

export default function HealthRiskCard({ risk }) {
  if (!risk) return null;
  if (risk.scoreMode === "insufficient" || risk.riskScore == null) {
    return <div className="rounded-2xl border border-emerald-400/35 bg-[#071b17] p-6" data-testid="health-risk-card">
      <p className="text-xs font-semibold uppercase tracking-widest text-emerald-300">OxyZen Health Impact Indicator</p>
      <h2 className="mt-2 text-2xl font-bold text-white">Insufficient data</h2>
      <p className="mt-2 text-sm text-slate-300">{risk.explanation}</p>
      <p className="mt-3 text-xs text-slate-400">Pollutant indices: {risk.dataCompleteness?.available ?? 0}/{risk.dataCompleteness?.total ?? 6} available ({risk.dataCompleteness?.percentage ?? 0}%).</p>
      <p className="mt-1 text-xs text-slate-400">Ground-station measurements: {risk.dataCompleteness?.stationMeasurements ?? 0}/{risk.dataCompleteness?.total ?? 6} · Modelled estimates: {risk.dataCompleteness?.modelledEstimates ?? 0}/{risk.dataCompleteness?.total ?? 6}</p>
      <p className="mt-4 text-xs text-slate-400">{risk.disclaimer}</p>
    </div>;
  }
  const c = risk.riskColor || "#F59E0B";
  const sourceValues = Object.values(risk.pollutantSources || {});
  const hasWaqi = sourceValues.some((value) => String(value).includes("WAQI"));
  const hasModel = sourceValues.some((value) => String(value).includes("Open-Meteo"));
  const hasCpcb = sourceValues.some((value) => String(value).includes("CPCB"));
  const sourceLabel = hasCpcb && hasWaqi ? "CPCB + WAQI station measurements" : hasCpcb && hasModel ? "CPCB station + Open-Meteo model" : hasCpcb ? "CPCB station measurements" : hasWaqi && hasModel ? "WAQI station + Open-Meteo model" : hasWaqi ? "WAQI station measurements" : hasModel ? "Open-Meteo model estimates" : "AQI-based estimate";
  const completeness = risk.dataCompleteness || {};
  return (
    <div className="space-y-4" data-testid="health-risk-card">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="flex min-h-[170px] items-center gap-6 rounded-2xl border border-emerald-400/45 bg-[radial-gradient(ellipse_at_30%_50%,rgba(16,185,129,0.16),transparent_70%),#071b17] p-5">
          <div className="relative h-32 w-32 shrink-0">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" fill="none" stroke="rgba(148,163,184,.25)" strokeWidth="9"/><circle cx="60" cy="60" r="52" fill="none" stroke={c} strokeWidth="9" strokeLinecap="round" strokeDasharray={(risk.riskScore / 100) * 2 * Math.PI * 52 + " " + 2 * Math.PI * 52} style={{transition:"stroke-dasharray .8s ease"}}/></svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center"><span className="font-data text-4xl font-bold" style={{color:c}} data-testid="risk-score">{risk.riskScore}</span><span className="text-xs text-white">/ 100</span></div>
          </div>
          <div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-widest text-slate-300">OxyZen Health Impact Indicator</p><p className="mt-2 font-heading text-3xl font-black leading-tight" style={{color:c}} data-testid="risk-level">{risk.riskLevel}</p><p className="mt-1 text-sm text-slate-300">{risk.scoreModeLabel || "Pollutant-weighted indicator"}</p></div>
        </div>
        <div className="rounded-2xl border border-emerald-400/45 bg-[#071b17] p-5">
          <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-slate-300">Main contributing factors</p>
          <div className="space-y-3" data-testid="risk-contributors">
            {(risk.mainContributors || []).slice(0,4).map((ct) => <div key={ct.name} className="flex items-center gap-3"><span className="w-14 shrink-0 font-data text-xs text-slate-300">{ct.name}</span><div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-700/70"><div className="h-full rounded-full" style={{width:(ct.intensity*100)+"%",background:c}}/></div><span className="w-10 text-right font-data text-xs text-slate-300">{Math.round(ct.share*100)}%</span></div>)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.55fr_0.95fr]">
        <div className="rounded-2xl border border-emerald-400/40 bg-[#071b17] p-5">
          <div className="flex items-start gap-4"><Info className="mt-1 h-7 w-7 shrink-0 rounded-full bg-emerald-500 p-1 text-[#052019]"/><div className="min-w-0"><p className="text-sm leading-relaxed text-white" data-testid="risk-explanation">{risk.explanation}</p><div className="mt-4 border-t border-emerald-200/20 pt-3 text-xs text-slate-300" data-testid="risk-data-quality">Pollutant indices: {completeness.available ?? 0}/{completeness.total ?? 6} available ({completeness.percentage ?? 0}%) <span className="mx-2 text-emerald-300">|</span> Sources: {sourceLabel}</div></div></div>
        </div>
        <div className="rounded-2xl border border-emerald-400/40 bg-[#071b17] p-5 text-xs text-slate-300" data-testid="risk-source-completeness">
          <div className="mb-2 flex items-center gap-3"><Layers3 className="h-8 w-8 text-emerald-400"/><div className="space-y-1"><p>Ground-station measurements: <strong className="text-white">{completeness.stationMeasurements ?? 0}/{completeness.total ?? 6}</strong></p><p>Modelled estimates: <strong className="text-white">{completeness.modelledEstimates ?? 0}/{completeness.total ?? 6}</strong></p></div></div>
          {hasModel && <p className="leading-relaxed">Modelled estimates are not ground-station measurements.</p>}
          {(completeness.unclassified ?? 0) > 0 && <p className="mt-1">Unverified source: <strong className="text-white">{completeness.unclassified}/{completeness.total ?? 6}</strong></p>}
          {risk.scoreMode === "aqi_only" && <p className="mt-2 text-amber-300">This score is mapped from the available overall AQI only; missing pollutants are not counted as zero.</p>}
          {risk.scoreMode === "pollutant_weighted" && <p className="mt-2 text-emerald-300">{hasCpcb ? "CPCB = ground-station measurement (via mirror)" : hasWaqi ? "WAQI = station measurement" : ""}{hasModel && (hasCpcb || hasWaqi) ? " · " : ""}{hasModel ? "Open-Meteo = model estimate" : ""}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {(risk.healthImpacts || []).map((h) => { const Icon = SYS_ICON[h.system] || Activity; return <div key={h.system} className="rounded-xl border border-emerald-400/35 bg-[#071b17] p-4"><div className="mb-2 flex items-center gap-3"><Icon className="h-6 w-6 text-emerald-400" strokeWidth={1.7}/><span className="text-base font-bold text-white">{h.system}</span></div><p className="text-sm leading-relaxed text-slate-300">{h.text}</p></div>; })}
      </div>

      <div className="rounded-2xl border border-emerald-400/35 bg-[#071b17] p-5">
        <div className="mb-4 flex items-center gap-3"><ShieldCheck className="h-7 w-7 text-emerald-400"/><span className="text-lg font-bold text-white">Recommended Precautions</span></div>
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">{(risk.precautions || []).map((p) => <li key={p} className="flex items-start gap-3 text-sm text-slate-200"><span className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full" style={{background:c}}/>{p}</li>)}</ul>
        <p className="mt-5 border-t border-emerald-200/20 pt-4 text-xs leading-relaxed text-slate-300">{risk.disclaimer}</p>
      </div>
    </div>
  );
}

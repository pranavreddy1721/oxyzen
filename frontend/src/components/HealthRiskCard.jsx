import { HeartPulse, Wind, Activity, ShieldCheck } from "lucide-react";

const SYS_ICON = { Respiratory: Wind, Cardiovascular: HeartPulse, General: Activity };

export default function HealthRiskCard({ risk }) {
  if (!risk) return null;
  const c = risk.riskColor;

  return (
    <div className="rounded-xl border border-border bg-card p-8" data-testid="health-risk-card">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        {/* Score dial + level */}
        <div className="flex shrink-0 items-center gap-6">
          <div className="relative h-32 w-32">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="hsl(var(--muted))" strokeWidth="9" />
              <circle
                cx="60" cy="60" r="52" fill="none" stroke={c} strokeWidth="9" strokeLinecap="round"
                strokeDasharray={`${(risk.riskScore / 100) * 2 * Math.PI * 52} ${2 * Math.PI * 52}`}
                style={{ transition: "stroke-dasharray 0.8s ease" }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-data text-3xl font-bold" style={{ color: c }} data-testid="risk-score">{risk.riskScore}</span>
              <span className="text-[10px] uppercase tracking-widest text-muted-foreground">/ 100</span>
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Health Risk</p>
            <p className="mt-1 font-heading text-3xl font-black tracking-tight" style={{ color: c }} data-testid="risk-level">{risk.riskLevel}</p>
            <p className="mt-1 text-xs text-muted-foreground">Environmental Health Risk Score</p>
          </div>
        </div>

        <div className="flex-1 space-y-5">
          {/* Contributors */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Main contributing factors</p>
            <div className="space-y-2.5" data-testid="risk-contributors">
              {risk.mainContributors.slice(0, 4).map((ct) => (
                <div key={ct.name} className="flex items-center gap-3">
                  <span className="w-14 font-data text-xs font-medium text-muted-foreground">{ct.name}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full" style={{ width: `${ct.intensity * 100}%`, background: c, transition: "width 0.8s ease" }} />
                  </div>
                  <span className="w-10 text-right font-data text-xs text-muted-foreground">{Math.round(ct.share * 100)}%</span>
                </div>
              ))}
            </div>
          </div>

          <p className="rounded-xl border border-border bg-accent/40 p-4 text-sm leading-relaxed" data-testid="risk-explanation">
            {risk.explanation}
          </p>
        </div>
      </div>

      {/* Health impacts */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {risk.healthImpacts.map((h) => {
          const Icon = SYS_ICON[h.system] || Activity;
          return (
            <div key={h.system} className="rounded-xl border border-border p-4">
              <div className="mb-2 flex items-center gap-2">
                <Icon className="h-4 w-4 text-primary" strokeWidth={1.5} />
                <span className="text-sm font-semibold">{h.system}</span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{h.text}</p>
            </div>
          );
        })}
      </div>

      {/* Precautions */}
      <div className="mt-6 rounded-xl border border-border p-5">
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" strokeWidth={1.5} />
          <span className="text-sm font-semibold">Recommended precautions</span>
        </div>
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2" data-testid="risk-precautions">
          {risk.precautions.map((p) => (
            <li key={p} className="flex items-start gap-2 text-sm text-muted-foreground">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: c }} />
              {p}
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-4 text-xs text-muted-foreground">{risk.disclaimer}</p>
    </div>
  );
}

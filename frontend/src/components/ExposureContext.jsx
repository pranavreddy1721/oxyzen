import { useState } from "react";
import { Home, Trees, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";

const OPT = {
  environment: [
    { v: "indoor", label: "Indoor" },
    { v: "outdoor", label: "Outdoor" },
  ],
  activity: [
    { v: "resting", label: "Resting" },
    { v: "walking", label: "Walking" },
    { v: "exercise", label: "Exercise" },
  ],
  duration: [
    { v: "<1h", label: "< 1 hour" },
    { v: "1-3h", label: "1–3 hours" },
    { v: "3h+", label: "3+ hours" },
  ],
};

function Segmented({ label, options, value, onChange, testId }) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2" data-testid={testId}>
        {options.map((o) => (
          <button
            key={o.v}
            onClick={() => onChange(o.v)}
            className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              value === o.v ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ExposureContext({ aqi }) {
  const [environment, setEnvironment] = useState("outdoor");
  const [activity, setActivity] = useState("walking");
  const [duration, setDuration] = useState("1-3h");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const compute = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/exposure", { aqi, environment, activity, duration });
      setResult(data);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-6" data-testid="exposure-context">
      <div className="mb-1 flex items-center gap-2">
        {environment === "indoor" ? <Home className="h-4 w-4 text-primary" strokeWidth={1.5} /> : <Trees className="h-4 w-4 text-primary" strokeWidth={1.5} />}
        <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Personal Exposure Context</h3>
      </div>
      <p className="mb-5 text-xs text-muted-foreground">General exposure guidance based on your context. Not a mask or medical recommendation.</p>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <Segmented label="Where are you?" options={OPT.environment} value={environment} onChange={setEnvironment} testId="exposure-env" />
        <Segmented label="Activity" options={OPT.activity} value={activity} onChange={setActivity} testId="exposure-activity" />
        <Segmented label="Exposure" options={OPT.duration} value={duration} onChange={setDuration} testId="exposure-duration" />
      </div>

      <Button className="mt-5" onClick={compute} disabled={loading} data-testid="exposure-submit-btn">
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={1.5} />}
        Get exposure guidance
      </Button>

      {result && (
        <div className="mt-5 rounded-xl border border-border bg-accent/40 p-5 animate-fade-up" data-testid="exposure-result">
          <p className="font-heading text-lg font-bold text-primary">{result.level}</p>
          <p className="mt-1 text-sm text-muted-foreground">{result.text}</p>
          <ul className="mt-3 space-y-1.5">
            {result.tips.map((t) => (
              <li key={t} className="flex items-start gap-2 text-xs text-muted-foreground">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {t}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

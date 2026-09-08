import { Wind, Sun, Cloud, Factory, Car, Thermometer } from "lucide-react";

const CATS = [
  { range: "0–50", label: "Good", color: "#10B981", text: "Air quality is satisfactory; air pollution poses little or no risk." },
  { range: "51–100", label: "Moderate", color: "#F59E0B", text: "Acceptable; unusually sensitive people may experience minor effects." },
  { range: "101–150", label: "Unhealthy for Sensitive Groups", color: "#F97316", text: "Sensitive groups may experience health effects; general public less likely." },
  { range: "151–200", label: "Unhealthy", color: "#EF4444", text: "Some of the general public may experience effects; sensitive groups more serious." },
  { range: "201–300", label: "Very Unhealthy", color: "#9333EA", text: "Health alert: risk of effects is increased for everyone." },
  { range: "301+", label: "Hazardous", color: "#9F1239", text: "Emergency conditions: everyone is more likely to be affected." },
];

const POLL = [
  { name: "PM2.5", desc: "Fine particles that penetrate deep into lungs and bloodstream.", icon: Cloud },
  { name: "PM10", desc: "Coarse inhalable particles from dust and combustion.", icon: Wind },
  { name: "O₃", desc: "Ground-level ozone formed by sunlight acting on pollutants.", icon: Sun },
  { name: "NO₂", desc: "Traffic-related gas that irritates airways.", icon: Car },
  { name: "SO₂", desc: "Gas from fossil-fuel burning; irritates the respiratory tract.", icon: Factory },
  { name: "CO", desc: "Colorless gas that reduces oxygen delivery in the body.", icon: Thermometer },
];

const FACTORS = [
  { title: "Weather & temperature", text: "Hot, sunny, stagnant days boost ozone; temperature inversions trap pollutants near the ground." },
  { title: "Wind & rain", text: "Wind disperses pollutants and rain washes particles out of the air, improving AQI." },
  { title: "Local sources", text: "Traffic density, industry, construction and biomass burning drive local pollution levels." },
  { title: "Time of day", text: "Rush-hour traffic causes morning and evening pollution peaks in many cities." },
];

export default function AQIInfo() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="font-heading text-4xl font-black tracking-tight">What is AQI?</h1>
      <p className="mt-3 max-w-2xl text-muted-foreground">
        The Air Quality Index (AQI) converts complex pollutant measurements into a single, understandable number from 0 to 500. The higher the number, the greater the level of air pollution and the associated health concern.
      </p>

      <section className="mt-12">
        <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">How AQI is calculated</h2>
        <div className="rounded-xl border border-border bg-card p-6 text-sm leading-relaxed text-muted-foreground">
          Each pollutant is measured and compared against health-based reference concentrations. The measured value is converted to a sub-index using standardized breakpoints, and the <span className="font-semibold text-foreground">highest sub-index becomes the overall AQI</span>. That pollutant is called the "dominant pollutant." OxyZen uses a PM2.5-anchored US EPA-style scale.
        </div>
      </section>

      <section className="mt-12">
        <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">AQI categories</h2>
        <div className="space-y-3">
          {CATS.map((c) => (
            <div key={c.label} className="flex items-center gap-4 rounded-xl border border-border bg-card p-4">
              <span className="flex h-12 w-20 shrink-0 items-center justify-center rounded-lg font-data text-sm font-bold text-white" style={{ background: c.color }}>{c.range}</span>
              <div>
                <p className="font-semibold">{c.label}</p>
                <p className="text-sm text-muted-foreground">{c.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">The six key pollutants</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {POLL.map((p) => (
            <div key={p.name} className="rounded-xl border border-border bg-card p-5">
              <p.icon className="mb-3 h-6 w-6 text-primary" strokeWidth={1.5} />
              <p className="font-heading text-lg font-bold">{p.name}</p>
              <p className="mt-1 text-sm text-muted-foreground">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">Why AQI varies by location & weather</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {FACTORS.map((f) => (
            <div key={f.title} className="rounded-xl border border-border bg-card p-5">
              <p className="font-semibold">{f.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{f.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

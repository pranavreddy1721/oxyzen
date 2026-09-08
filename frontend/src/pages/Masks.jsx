import { Info } from "lucide-react";

const TYPES = [
  { name: "Cloth masks", filt: "Low", text: "Basic cloth face coverings offer minimal filtration of fine particles. Useful for coarse dust but limited against PM2.5." },
  { name: "Surgical masks", filt: "Low–Moderate", text: "Designed as fluid barriers. They fit loosely, so unfiltered air leaks around the edges." },
  { name: "N95 / FFP2", filt: "High", text: "Filter at least 94–95% of airborne particles when well-fitted and sealed. Widely used for fine-particle protection." },
  { name: "N99 / FFP3", filt: "Very High", text: "Filter ~99% of particles with a tight seal. Higher breathing resistance and cost." },
];

const CONCEPTS = [
  { title: "Filtration efficiency", text: "The percentage of particles a mask material captures. Higher ratings capture more fine particulate matter." },
  { title: "Fit & seal", text: "A mask only protects if air passes through it, not around it. Gaps dramatically reduce real-world protection." },
  { title: "Breathability", text: "Denser filters protect more but are harder to breathe through, affecting comfort during activity." },
  { title: "Reuse & hygiene", text: "Filtering masks degrade with moisture and wear. Follow product guidance on reuse and replacement." },
];

const LIMITS = [
  "Masks reduce but do not eliminate exposure to air pollution.",
  "They do little against gases such as ozone unless specifically designed for it.",
  "Poor fit, facial hair or damage significantly reduces effectiveness.",
  "They are one layer of protection — reducing time outdoors and improving indoor air matter too.",
];

export default function Masks() {
  return (
    <div>
      <div className="relative h-56 w-full overflow-hidden border-b border-border sm:h-64">
        <img src="https://images.pexels.com/photos/3985183/pexels-photo-3985183.jpeg" alt="Person wearing a protective mask" className="h-full w-full object-cover" loading="lazy" />
        <div className="absolute inset-0 bg-black/55" />
        <div className="absolute inset-0 mx-auto flex max-w-5xl flex-col justify-center px-4 sm:px-6 lg:px-8">
          <h1 className="font-heading text-4xl font-black tracking-tight text-white">Masks & Air Protection</h1>
          <p className="mt-2 max-w-xl text-white/80">General educational information about how particulate-filtering masks work.</p>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-10 flex items-start gap-3 rounded-xl border border-primary/30 bg-primary/5 p-5">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-primary" strokeWidth={1.5} />
          <p className="text-sm text-muted-foreground">
            This page is <span className="font-semibold text-foreground">informational only</span>. OxyZen does not recommend which specific mask to buy. For guidance tailored to your situation, consult local public-health advice.
          </p>
        </div>

        <section className="mb-12">
          <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">Common mask types</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {TYPES.map((t) => (
              <div key={t.name} className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center justify-between">
                  <p className="font-heading text-lg font-bold">{t.name}</p>
                  <span className="rounded-full border border-border px-2.5 py-0.5 text-xs font-medium text-muted-foreground">{t.filt}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{t.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">Filtration concepts</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {CONCEPTS.map((c) => (
              <div key={c.title} className="rounded-xl border border-border bg-card p-5">
                <p className="font-semibold">{c.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{c.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-4 font-heading text-2xl font-black tracking-tight">Limitations to keep in mind</h2>
          <div className="rounded-xl border border-border bg-card p-6">
            <ul className="space-y-2">
              {LIMITS.map((l) => (
                <li key={l} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" /> {l}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}

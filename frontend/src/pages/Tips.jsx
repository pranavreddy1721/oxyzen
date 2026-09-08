import { Home, Wind, Activity, Fan, ShieldCheck, Bell } from "lucide-react";

const SECTIONS = [
  {
    icon: Home, title: "Indoor air quality",
    tips: ["Keep windows closed during outdoor pollution peaks.", "Use HEPA air purifiers in frequently-used rooms.", "Avoid indoor smoking and minimize candle/incense burning.", "Maintain houseplants and clean surfaces to reduce dust."],
  },
  {
    icon: Wind, title: "Outdoor pollution precautions",
    tips: ["Check the AQI before heading out for extended periods.", "Prefer routes away from heavy traffic and industry.", "Limit prolonged outdoor exertion when AQI is high.", "Plan outdoor activity for times when air is cleaner."],
  },
  {
    icon: Activity, title: "Exercise guidance",
    tips: ["Move intense workouts indoors when AQI exceeds ~150.", "Early morning often has lower ozone than hot afternoons.", "Reduce intensity when air is poor — you breathe in more.", "Stay hydrated and listen to your body."],
  },
  {
    icon: Fan, title: "Ventilation guidance",
    tips: ["Ventilate when outdoor air is clean (low AQI).", "Use exhaust fans while cooking to clear NO2 and particles.", "Seal gaps during heavy pollution or wildfire smoke events.", "Change HVAC and purifier filters on schedule."],
  },
  {
    icon: ShieldCheck, title: "Reducing exposure",
    tips: ["Combine several small habits rather than one big change.", "Create a clean-air room at home during severe episodes.", "Protect children, elderly and those with conditions first.", "Well-fitted masks can help outdoors when air is poor."],
  },
  {
    icon: Bell, title: "AQI monitoring habits",
    tips: ["Check AQI as part of your morning routine.", "Save your frequent locations for quick access.", "Set an alert threshold so you're warned on bad days.", "Watch trends, not just single readings."],
  },
];

export default function Tips() {
  return (
    <div>
      <div className="relative h-56 w-full overflow-hidden border-b border-border sm:h-64">
        <img src="https://images.unsplash.com/photo-1686179225818-c07909cd2911" alt="Foggy city skyline" className="h-full w-full object-cover" loading="lazy" />
        <div className="absolute inset-0 bg-black/55" />
        <div className="absolute inset-0 mx-auto flex max-w-5xl flex-col justify-center px-4 sm:px-6 lg:px-8">
          <h1 className="font-heading text-4xl font-black tracking-tight text-white">Health Tips</h1>
          <p className="mt-2 max-w-xl text-white/80">Concise, practical guidance to reduce pollution exposure and protect your health.</p>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {SECTIONS.map((s) => (
            <div key={s.title} className="rounded-xl border border-border bg-card p-6">
              <div className="mb-4 flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><s.icon className="h-5 w-5" strokeWidth={1.5} /></span>
                <h2 className="font-heading text-lg font-bold">{s.title}</h2>
              </div>
              <ul className="space-y-2">
                {s.tips.map((t) => (
                  <li key={t} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" /> {t}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

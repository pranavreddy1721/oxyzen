import { Footprints, Activity, Bike, Dumbbell } from "lucide-react";
import { ACTIVITY_STATUS_COLORS } from "@/lib/aqiColors";

const ICONS = { footprints: Footprints, activity: Activity, bike: Bike, dumbbell: Dumbbell };

export default function ActivityGuidance({ activities, aqi }) {
  if (!activities) return null;
  return (
    <div className="rounded-xl border border-border bg-card p-6" data-testid="activity-guidance">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">Outdoor Activity Guidance</h3>
        {aqi != null && <span className="font-data text-xs text-muted-foreground">at AQI {aqi}</span>}
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {activities.map((a) => {
          const Icon = ICONS[a.icon] || Activity;
          const color = ACTIVITY_STATUS_COLORS[a.statusKey];
          return (
            <div key={a.key} className="flex flex-col items-center rounded-xl border border-border p-4 text-center" data-testid={`activity-${a.key}`}>
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full" style={{ background: `${color}1a`, color }}>
                <Icon className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <p className="text-sm font-semibold">{a.name}</p>
              <p className="mt-1 text-xs font-medium" style={{ color }}>{a.status}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

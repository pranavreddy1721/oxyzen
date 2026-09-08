import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trash2, MapPin, Clock, Bell, AlertTriangle, Plus } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLocation } from "@/context/LocationContext";
import { textOn } from "@/lib/aqiColors";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { PageLoader } from "@/components/states";

export default function Dashboard() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const { setLocation } = useLocation();
  const [data, setData] = useState(null);
  const [threshold, setThreshold] = useState(user?.alertThreshold ?? 150);
  const [enabled, setEnabled] = useState(user?.alertsEnabled ?? true);

  const load = () => api.get("/users/dashboard").then(({ data }) => {
    setData(data);
    setThreshold(data.alertThreshold);
    setEnabled(data.alertsEnabled);
  }).catch(() => {});

  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    try {
      await api.delete(`/users/locations/${id}`);
      toast.success("Location removed.");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const openLoc = (l) => {
    setLocation({ id: l.locationId, name: l.name, country: l.country, lat: l.lat, lon: l.lon });
    navigate("/aqi-monitor");
  };

  const saveAlerts = async () => {
    try {
      const { data } = await api.patch("/auth/alerts", { threshold, enabled });
      updateUser(data.user);
      toast.success("Alert preferences saved.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!data) return <PageLoader />;

  const breached = enabled ? data.savedLocations.filter((l) => l.aqi >= threshold) : [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="font-heading text-3xl font-black tracking-tight sm:text-4xl">Welcome back, {user?.name?.split(" ")[0]}</h1>
        <p className="mt-1 text-muted-foreground">Your saved locations, exposure history and alert preferences.</p>
      </div>

      {breached.length > 0 && (
        <div className="mb-8 flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-4" data-testid="alert-banner">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" strokeWidth={1.5} />
          <p className="text-sm">
            <span className="font-semibold">AQI alert:</span> {breached.map((b) => `${b.name} (${b.aqi})`).join(", ")} exceeded your threshold of {threshold}.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-heading text-xl font-bold">Saved locations</h2>
            <Button variant="outline" size="sm" onClick={() => navigate("/aqi-monitor")}><Plus className="mr-1.5 h-4 w-4" strokeWidth={1.5} /> Add</Button>
          </div>
          {data.savedLocations.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-10 text-center text-muted-foreground" data-testid="no-saved-locations">
              <MapPin className="mx-auto mb-3 h-8 w-8" strokeWidth={1.5} />
              No saved locations yet. Search a location in the AQI Monitor and save it.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {data.savedLocations.map((l) => (
                <div key={l.id} className="rounded-xl border border-border bg-card p-5" data-testid={`saved-location-${l.locationId}`}>
                  <div className="flex items-start justify-between">
                    <button onClick={() => openLoc(l)} className="text-left">
                      <p className="font-heading text-lg font-bold hover:text-primary">{l.name}</p>
                      <p className="text-xs text-muted-foreground">{l.country}</p>
                    </button>
                    <button onClick={() => remove(l.id)} className="text-muted-foreground hover:text-destructive" data-testid={`remove-location-${l.locationId}`}>
                      <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                    </button>
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <div>
                      <span className="font-data text-3xl font-bold" style={{ color: l.color }}>{l.aqi}</span>
                      <span className="ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ background: l.color, color: textOn(l.color) }}>{l.category}</span>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-widest text-muted-foreground">Risk</p>
                      <p className="text-sm font-bold" style={{ color: l.riskColor }}>{l.riskLevel}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <h2 className="mb-4 mt-8 font-heading text-xl font-bold">Recent searches</h2>
          <div className="rounded-xl border border-border bg-card p-2">
            {data.recentSearches.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">No recent searches yet.</p>
            ) : (
              data.recentSearches.map((r, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg px-4 py-3 hover:bg-accent">
                  <div className="flex items-center gap-3">
                    <Clock className="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
                    <span className="text-sm font-medium">{r.locationName}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-data text-sm">{r.aqi}</span>
                    <span className="text-xs text-muted-foreground">{new Date(r.createdAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div>
          <div className="rounded-xl border border-border bg-card p-6" data-testid="alert-settings">
            <div className="mb-4 flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" strokeWidth={1.5} />
              <h2 className="font-heading text-lg font-bold">AQI Alerts</h2>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Enable alerts</span>
              <Switch checked={enabled} onCheckedChange={setEnabled} data-testid="alert-toggle" />
            </div>
            <div className="mt-6">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Alert threshold</span>
                <span className="font-data text-lg font-bold text-primary">{threshold}</span>
              </div>
              <Slider value={[threshold]} min={50} max={300} step={10} onValueChange={(v) => setThreshold(v[0])} data-testid="alert-slider" />
              <p className="mt-2 text-xs text-muted-foreground">You'll be warned when a saved location's AQI reaches this level.</p>
            </div>
            <Button className="mt-6 w-full" onClick={saveAlerts} data-testid="save-alerts-btn">Save preferences</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

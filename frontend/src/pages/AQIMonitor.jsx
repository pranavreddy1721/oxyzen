import { useEffect, useState, useCallback } from "react";
import { Bookmark, BookmarkCheck } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useLocation } from "@/context/LocationContext";
import { useAuth } from "@/context/AuthContext";
import { aqiCategory } from "@/lib/aqiColors";
import LocationSearch from "@/components/LocationSearch";
import AQICard from "@/components/AQICard";
import AQIScale from "@/components/AQIScale";
import PollutantGrid from "@/components/PollutantGrid";
import HealthRiskCard from "@/components/HealthRiskCard";
import ActivityGuidance from "@/components/ActivityGuidance";
import ExposureContext from "@/components/ExposureContext";
import ForecastPanel from "@/components/ForecastPanel";
import { Button } from "@/components/ui/button";
import { CardSkeleton, ErrorState } from "@/components/states";

export default function AQIMonitor() {
  const { location, setLocation } = useLocation();
  const { user } = useAuth();
  const [current, setCurrent] = useState(null);
  const [risk, setRisk] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [error, setError] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setError(false);
    setCurrent(null);
    const params = { locationId: location.id, lat: location.lat, lon: location.lon, locationName: location.name, locationCountry: location.country };
    try {
      const [cur, rk, fc] = await Promise.all([
        api.get("/aqi/current", { params }),
        api.get("/health-risk", { params }),
        api.get("/aqi/forecast", { params: { ...params, days: 5 } }),
      ]);
      setCurrent(cur.data);
      setRisk(rk.data);
      setForecast(fc.data.forecast);
    } catch (e) {
      setError(true);
    }
  }, [location]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!user) { setSaved(false); return; }
    api.get("/users/locations").then(({ data }) => {
      setSaved(data.locations.some((l) => l.locationId === location.id));
    }).catch(() => {});
  }, [user, location]);

  const saveLocation = async () => {
    if (!user) { toast.info("Sign in to save locations."); return; }
    try {
      await api.post("/users/locations", {
        locationId: location.id, name: location.name, country: location.country || "",
        lat: location.lat, lon: location.lon, label: "",
      });
      setSaved(true);
      toast.success(`${location.name} saved to your locations.`);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="font-heading text-3xl font-black tracking-tight sm:text-4xl">AQI Monitor</h1>
          <p className="mt-1 text-muted-foreground">Real-time conditions, pollutant analysis and explainable health risk.</p>
        </div>
        <Button variant={saved ? "secondary" : "outline"} onClick={saveLocation} data-testid="save-location-btn">
          {saved ? <BookmarkCheck className="mr-2 h-4 w-4" strokeWidth={1.5} /> : <Bookmark className="mr-2 h-4 w-4" strokeWidth={1.5} />}
          {saved ? "Saved" : "Save location"}
        </Button>
      </div>

      <div className="mb-8 max-w-3xl">
        <LocationSearch onSelect={setLocation} />
      </div>

      {error ? (
        <ErrorState onRetry={load} message="We couldn't load air-quality data for this location." />
      ) : !current ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-4"><CardSkeleton className="h-80" /></div>
          <div className="lg:col-span-8"><CardSkeleton className="h-80" /></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-4 lg:row-span-2">
            <AQICard {...current} locationName={current.location.name} />
          </div>
          <div className="lg:col-span-8">
            <HealthRiskCard risk={risk} />
          </div>
          <div className="lg:col-span-8">
            <AQIScale aqi={current.aqi} />
          </div>

          <div className="lg:col-span-12">
            <h2 className="mb-4 font-heading text-xl font-bold">Pollutant Analysis</h2>
            <PollutantGrid pollutants={current.pollutants} meta={current.pollutantMeta} location={current.location} />
          </div>

          <div className="lg:col-span-6"><ActivityGuidance activities={risk?.activityGuidance} aqi={current.aqi} /></div>
          <div className="lg:col-span-12"><ExposureContext aqi={current.aqi} /></div>
          <div className="lg:col-span-12"><ForecastPanel forecast={forecast} /></div>
        </div>
      )}
    </div>
  );
}

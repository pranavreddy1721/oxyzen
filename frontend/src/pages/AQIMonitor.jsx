import { useEffect, useState, useCallback } from "react";
import { Bookmark, BookmarkCheck, Wind, Activity } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useLocation } from "@/context/LocationContext";
import { useAuth } from "@/context/AuthContext";
import LocationSearch from "@/components/LocationSearch";
import AQICard from "@/components/AQICard";
import AQIScale from "@/components/AQIScale";
import PollutantGrid from "@/components/PollutantGrid";
import HealthRiskCard from "@/components/HealthRiskCard";
import ActivityGuidance from "@/components/ActivityGuidance";
import ExposureContext from "@/components/ExposureContext";
import ForecastPanel from "@/components/ForecastPanel";
import OfficialStationData from "@/components/OfficialStationData";
import { Button } from "@/components/ui/button";
import { CardSkeleton, ErrorState } from "@/components/states";

export default function AQIMonitor() {
  const { location, setLocation } = useLocation();
  const { user } = useAuth();
  const [current, setCurrent] = useState(null);
  const [risk, setRisk] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [error, setError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setError(false);
    setErrorMessage("");
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
      const detail = e?.response?.data?.detail;
      setErrorMessage(
        detail ||
        \`Live WAQI data is currently unavailable for \${location.name}. There may be no nearby WAQI monitoring station available for this location.\`
      );
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
      toast.success(\`\${location.name} saved to your locations.\`);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  return (
    <main className="dark min-h-screen bg-[#070b0a] text-slate-100" data-testid="aqi-monitor-page">
      <div className="mx-auto max-w-[1600px] px-3 py-5 sm:px-5 lg:px-7">
        <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-center">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">
              <Wind className="h-4 w-4" /> OxyZen Air Intelligence
            </div>
            <h1 className="mt-1 font-heading text-2xl font-black tracking-tight text-white sm:text-3xl">AQI Monitor</h1>
            <p className="mt-1 text-sm text-slate-400">Real-time air quality, pollutant analysis and environmental health insights.</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center xl:w-[min(720px,62%)]">
            <div className="min-w-0 flex-1"><LocationSearch onSelect={setLocation} /></div>
            <Button variant={saved ? "secondary" : "outline"} onClick={saveLocation} data-testid="save-location-btn" className="h-11 shrink-0 border-emerald-500/40 bg-emerald-500/5 text-emerald-300 hover:bg-emerald-500/10">
              {saved ? <BookmarkCheck className="mr-2 h-4 w-4" strokeWidth={1.5} /> : <Bookmark className="mr-2 h-4 w-4" strokeWidth={1.5} />}
              {saved ? "Saved location" : "Save location"}
            </Button>
          </div>
        </div>

        {error ? (
          <ErrorState onRetry={load} message={errorMessage || "We couldn't load air-quality data for this location."} />
        ) : !current ? (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            <div className="lg:col-span-4"><CardSkeleton className="h-[620px]" /></div>
            <div className="space-y-5 lg:col-span-8"><CardSkeleton className="h-72" /><CardSkeleton className="h-56" /></div>
          </div>
        ) : (
          <>
            <div className="mb-5 grid grid-cols-1 items-stretch gap-5 lg:grid-cols-12">
              <section className="min-h-[620px] lg:col-span-4 lg:row-span-2" aria-label="Current air quality">
                <AQICard {...current} locationName={current.location.name} aqiScale={current.aqiScale} />
              </section>
              <section className="lg:col-span-8" aria-label="Environmental health impact">
                <HealthRiskCard risk={risk} />
              </section>
              <section className="lg:col-span-8" aria-label="Air quality index scale">
                <AQIScale aqi={current.aqi} aqiScale={current.aqiScale} />
              </section>
            </div>

            {current.officialStationData && (
              <section className="mb-5" aria-label="Official monitoring station observations">
                <OfficialStationData data={current.officialStationData} />
              </section>
            )}

            <section className="mb-5 rounded-2xl border border-emerald-500/20 bg-[#0c1412] p-4 sm:p-5" aria-label="Pollutant analysis">
              <div className="mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-emerald-400" />
                <div>
                  <h2 className="font-heading text-lg font-bold text-white">Pollutant Analysis</h2>
                  <p className="text-xs text-slate-400">Available pollutant sub-indices and their data sources</p>
                </div>
              </div>
              <PollutantGrid pollutants={current.pollutants} meta={current.pollutantMeta} location={current.location} sources={current.pollutantDataSources} aqiScale={current.aqiScale} />
            </section>

            <div className="mb-5 grid grid-cols-1 gap-5 xl:grid-cols-2">
              <ActivityGuidance activities={risk?.activityGuidance} aqi={current.aqi} />
              <div className="rounded-2xl border border-emerald-500/20 bg-[#0c1412] p-1">
                <ExposureContext aqi={current.aqi} />
              </div>
            </div>

            <section className="mb-5" aria-label="Air quality forecast">
              <ForecastPanel forecast={forecast} />
            </section>
          </>
        )}
      </div>
    </main>
  );
}

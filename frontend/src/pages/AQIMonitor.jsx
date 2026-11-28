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
      setErrorMessage(detail || "Live WAQI data is currently unavailable for " + location.name + ". There may be no nearby WAQI monitoring station available for this location.");
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
      toast.success(location.name + " saved to your locations.");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    }
  };

  return (
    <main className="dark min-h-screen bg-[#050a09] text-slate-100" data-testid="aqi-monitor-page">
      <div className="mx-auto w-full max-w-[1560px] px-4 py-5 sm:px-6 lg:px-7">
        <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="min-w-0 flex-1"><LocationSearch onSelect={setLocation} /></div>
            <Button variant="outline" onClick={() => window.dispatchEvent(new Event("oxyzen-use-location"))} className="hidden h-11 shrink-0 border-emerald-400/50 bg-emerald-400/5 text-white hover:bg-emerald-400/10 sm:inline-flex">
              <Wind className="mr-2 h-4 w-4 text-emerald-400" /> Use My Location
            </Button>
          </div>
          <div className="flex items-center justify-between gap-3 xl:justify-end">
            <p className="text-xs font-data text-slate-400">{current?.updatedAt ? "Last updated: " + new Date(current.updatedAt).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}) : "Live air-quality monitoring"}</p>
            <Button variant={saved ? "secondary" : "outline"} onClick={saveLocation} data-testid="save-location-btn" className="h-10 shrink-0 border-emerald-400/50 bg-emerald-400/5 text-emerald-300 hover:bg-emerald-400/10">
              {saved ? <BookmarkCheck className="mr-2 h-4 w-4" /> : <Bookmark className="mr-2 h-4 w-4" />}
              {saved ? "Saved" : "Save location"}
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
            <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-12">
              <section className="lg:col-span-4" aria-label="Current air quality">
                <AQICard {...current} locationName={current.location.name} aqiScale={current.aqiScale} />
              </section>
              <section className="space-y-4 lg:col-span-8" aria-label="Environmental health impact">
                <HealthRiskCard risk={risk} />
                <AQIScale aqi={current.aqi} aqiScale={current.aqiScale} />
              </section>
            </div>

            {current.officialStationData && (
              <section className="mt-5" aria-label="Official monitoring station observations">
                <OfficialStationData data={current.officialStationData} />
              </section>
            )}

            <section className="mt-5 rounded-2xl border border-emerald-400/25 bg-[#081512] p-4 sm:p-5" aria-label="Pollutant analysis">
              <div className="mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-emerald-400" />
                <div>
                  <h2 className="font-heading text-lg font-bold text-white">Pollutant Analysis</h2>
                  <p className="text-xs text-slate-400">Available pollutant sub-indices and their data sources</p>
                </div>
              </div>
              <PollutantGrid pollutants={current.pollutants} meta={current.pollutantMeta} location={current.location} sources={current.pollutantDataSources} aqiScale={current.aqiScale} />
            </section>

            <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-2">
              <ActivityGuidance activities={risk?.activityGuidance} aqi={current.aqi} />
              <div className="rounded-2xl border border-emerald-400/25 bg-[#081512] p-1">
                <ExposureContext aqi={current.aqi} />
              </div>
            </div>

            <section className="mt-5" aria-label="Air quality forecast">
              <ForecastPanel forecast={forecast} />
            </section>
          </>
        )}
      </div>
    </main>
  );
}

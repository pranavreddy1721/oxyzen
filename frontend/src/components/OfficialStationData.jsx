import { useState } from "react";
import { ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

const POLLUTANT_LABELS = {
  "PM2.5": "PM2.5", "PM10": "PM10", "NO2": "NO₂", "SO2": "SO₂",
  "CO": "CO", "O3": "O₃", "NH3": "NH₃", "PB": "Lead",
  "BENZENE": "Benzene", "TOLUENE": "Toluene",
};

export default function OfficialStationData({ data }) {
  const [expanded, setExpanded] = useState(false);
  if (!data) return null;
  return (
    <section className="rounded-xl border border-border bg-card p-5" data-testid="official-cpcb-stations">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-600">Government monitoring network</p>
          <h2 className="mt-1 font-heading text-xl font-bold">Official CPCB station observations</h2>
          <p className="mt-1 text-sm text-muted-foreground">CPCB station AQI and pollutant sub-indices relayed through a third-party API mirror.</p>
        </div>
        <a href={data.providerUrl || "https://data.gov.in/resource/real-time-air-quality-index-various-locations"} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline">
          Source dataset <ExternalLink className="h-3 w-3" />
        </a>
      </div>
      {!data.available ? (
        <p className="mt-4 rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">{data.reason || "No official station observations are currently available for this city."}</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span><strong className="text-foreground">{data.stations.length}</strong> reporting stations</span>
            {data.updatedAt && <span>Latest feed update: {data.updatedAt}</span>}
          </div>
          <div className="mt-4 space-y-3">
            {(expanded ? data.stations : data.stations.slice(0, 4)).map((station) => (
              <div key={station.station} className="rounded-lg border border-border/70 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold">{station.station}</p>
                  <span className="text-[11px] text-muted-foreground">{station.lastUpdate || "Timestamp unavailable"}</span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
                  {Object.entries(station.pollutants || {}).map(([key, value]) => (
                    <div key={key} className="rounded-md bg-muted/40 px-2 py-2">
                      <p className="text-[10px] font-semibold text-muted-foreground">{POLLUTANT_LABELS[key] || key}</p>
                      <p className="mt-1 font-data text-sm font-bold">{value.average}{value.unit ? <span className="ml-1 text-[10px] font-normal text-muted-foreground">{value.unit}</span> : null}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {data.stations.length > 4 && (
            <button type="button" onClick={() => setExpanded((v) => !v)} className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-emerald-600">
              {expanded ? "Show fewer stations" : `Show all ${data.stations.length} stations`}
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          )}
          <p className="mt-3 text-[11px] text-muted-foreground">Station observations may be incomplete or delayed. Station readings can be incomplete or delayed. Data is attributed to CPCB and relayed by a third-party API mirror.</p>
        </>
      )}
    </section>
  );
}

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { useTheme } from "next-themes";
import { useNavigate } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import api from "@/lib/api";
import { useLocation } from "@/context/LocationContext";
import { textOn } from "@/lib/aqiColors";
import { Button } from "@/components/ui/button";
import { PageLoader } from "@/components/states";

const TILES = {
  dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  light: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
};

export default function MapPage() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const { setLocation } = useLocation();
  const [locations, setLocations] = useState(null);
  const [scale, setScale] = useState([]);

  useEffect(() => {
    api.get("/map").then(({ data }) => { setLocations(data.locations); setScale(data.scale); }).catch(() => setLocations([]));
  }, []);

  const openMonitor = (l) => {
    setLocation({ id: l.id, name: l.name, country: l.country, lat: l.lat, lon: l.lon });
    navigate("/aqi-monitor");
  };

  const radiusFor = (aqi) => 8 + Math.min(18, (aqi / 500) * 18);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="font-heading text-3xl font-black tracking-tight sm:text-4xl">Global Pollution Map</h1>
        <p className="mt-1 text-muted-foreground">Explore real-time air quality across cities. Marker size and color reflect severity.</p>
      </div>

      <div className="mb-4 flex flex-wrap gap-3">
        {scale.map((s) => (
          <div key={s.key} className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-3 w-3 rounded-full" style={{ background: s.color }} /> {s.label.split(" ")[0]}
          </div>
        ))}
      </div>

      {locations === null ? (
        <PageLoader />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border" style={{ height: "70vh" }} data-testid="pollution-map">
          <MapContainer center={[20, 30]} zoom={2} minZoom={2} scrollWheelZoom style={{ height: "100%", width: "100%" }} worldCopyJump>
            <TileLayer url={theme === "light" ? TILES.light : TILES.dark} attribution='&copy; OpenStreetMap &copy; CARTO' />
            {locations.map((l) => (
              <CircleMarker
                key={l.id}
                center={[l.lat, l.lon]}
                radius={radiusFor(l.aqi)}
                pathOptions={{ color: l.color, fillColor: l.color, fillOpacity: 0.55, weight: 1.5 }}
                data-testid={`map-marker-${l.id}`}
              >
                <Popup>
                  <div style={{ minWidth: 160 }}>
                    <p style={{ fontWeight: 700, fontSize: 15, margin: 0 }}>{l.name}</p>
                    <p style={{ margin: "2px 0 8px", fontSize: 12, opacity: 0.7 }}>{l.country}</p>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{ background: l.color, color: textOn(l.color), padding: "2px 8px", borderRadius: 999, fontSize: 12, fontWeight: 700 }}>AQI {l.aqi}</span>
                      <span style={{ fontSize: 12 }}>{l.category}</span>
                    </div>
                    <p style={{ margin: "0 0 8px", fontSize: 12 }}>PM2.5: {l.pm25} · Dominant: {l.dominantPollutant.toUpperCase()}</p>
                    <button
                      onClick={() => openMonitor(l)}
                      style={{ background: "#10B981", color: "#fff", border: "none", padding: "6px 10px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                    >
                      View details →
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      )}
    </div>
  );
}

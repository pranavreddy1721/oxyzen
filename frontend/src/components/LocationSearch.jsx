import { useEffect, useRef, useState } from "react";
import { Search, MapPin, Loader2, Crosshair } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function LocationSearch({ onSelect, size = "default", showLocate = true }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => {
    if (!q.trim()) { setResults([]); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get("/location/search", { params: { q } });
        setResults(data.results);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const handler = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const pick = (loc) => {
    setQ("");
    setResults([]);
    setOpen(false);
    onSelect(loc);
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported by your browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { latitude, longitude } = pos.coords;
          const { data } = await api.get("/location/reverse", { params: { lat: latitude, lon: longitude } });
          pick(data.location);
          toast.success(`Located: ${data.location.name}`);
        } catch (e) {
          toast.error(formatApiError(e.response?.data?.detail) || "Could not resolve your location.");
        } finally {
          setLocating(false);
        }
      },
      () => {
        setLocating(false);
        toast.error("Location permission denied. Try searching instead.");
      },
      { timeout: 10000 }
    );
  };

  const inputPad = size === "lg" ? "h-14 text-base" : "h-11 text-sm";

  return (
    <div className="flex w-full flex-col gap-3 sm:flex-row" ref={boxRef}>
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.5} />
        <input
          data-testid="location-search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder="Search city, region or country..."
          className={`w-full rounded-xl border border-input bg-card pl-11 pr-10 ${inputPad} font-medium outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20`}
        />
        {loading && <Loader2 className="absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" strokeWidth={1.5} />}

        {open && results.length > 0 && (
          <div className="absolute z-50 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-border bg-popover p-1.5 shadow-xl" data-testid="location-results">
            {results.map((r) => (
              <button
                key={r.id}
                onClick={() => pick(r)}
                data-testid={`location-option-${r.id}`}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent"
              >
                <MapPin className="h-4 w-4 shrink-0 text-primary" strokeWidth={1.5} />
                <span className="text-sm font-medium">{r.name}</span>
                {r.country && <span className="text-xs text-muted-foreground">{r.country}</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {showLocate && (
        <Button
          type="button"
          variant="outline"
          onClick={useMyLocation}
          disabled={locating}
          data-testid="use-my-location-btn"
          className={size === "lg" ? "h-14 px-5" : "h-11"}
        >
          {locating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={1.5} /> : <Crosshair className="mr-2 h-4 w-4" strokeWidth={1.5} />}
          Use My Location
        </Button>
      )}
    </div>
  );
}

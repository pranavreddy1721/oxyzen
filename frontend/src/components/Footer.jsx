import { Link } from "react-router-dom";
import { Wind } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card" data-testid="footer">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Wind className="h-5 w-5" strokeWidth={2} />
              </span>
              <span className="font-heading text-xl font-black tracking-tight">OxyZen</span>
            </div>
            <p className="mt-4 max-w-xs text-sm text-muted-foreground">
              Understand your air. Understand your health. Explainable AQI-based environmental health intelligence.
            </p>
          </div>
          <div>
            <h4 className="mb-3 text-sm font-semibold">Platform</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/aqi-monitor" className="transition-colors hover:text-foreground">AQI Monitor</Link></li>
              <li><Link to="/map" className="transition-colors hover:text-foreground">Pollution Map</Link></li>
              <li><Link to="/history" className="transition-colors hover:text-foreground">History & Trends</Link></li>
              <li><Link to="/dashboard" className="transition-colors hover:text-foreground">Dashboard</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="mb-3 text-sm font-semibold">Learn</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/aqi-info" className="transition-colors hover:text-foreground">What is AQI?</Link></li>
              <li><Link to="/tips" className="transition-colors hover:text-foreground">Health Tips</Link></li>
              <li><Link to="/masks" className="transition-colors hover:text-foreground">Masks Info</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="mb-3 text-sm font-semibold">About</h4>
            <p className="text-sm text-muted-foreground">
              An environmental awareness platform. Not a medical diagnostic tool or a substitute for professional medical advice.
            </p>
          </div>
        </div>
        <div className="mt-10 flex flex-col items-start justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} OxyZen · Air Quality Intelligence Platform</p>
          <p className="font-data">Live AQI data via World Air Quality Index (WAQI) · v1.0</p>
        </div>
      </div>
    </footer>
  );
}

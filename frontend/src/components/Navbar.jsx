import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Wind, Menu, X, LayoutDashboard, LogOut, User } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import ThemeToggle from "@/components/ThemeToggle";

const NAV = [
  { to: "/aqi-monitor", label: "AQI Monitor" },
  { to: "/map", label: "Map" },
  { to: "/aqi-info", label: "AQI Info" },
  { to: "/tips", label: "Health Tips" },
  { to: "/masks", label: "Masks" },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border glass" data-testid="navbar">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5" data-testid="brand-logo">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Wind className="h-5 w-5" strokeWidth={2} />
          </span>
          <span className="font-heading text-xl font-black tracking-tight">OxyZen</span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={`nav-${n.to.slice(1)}`}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {user ? (
            <div className="hidden items-center gap-2 sm:flex">
              <Button variant="ghost" size="sm" onClick={() => navigate("/dashboard")} data-testid="nav-dashboard-btn">
                <LayoutDashboard className="mr-1.5 h-4 w-4" strokeWidth={1.5} /> Dashboard
              </Button>
              <Button variant="outline" size="sm" onClick={handleLogout} data-testid="nav-logout-btn">
                <LogOut className="h-4 w-4" strokeWidth={1.5} />
              </Button>
            </div>
          ) : (
            <div className="hidden items-center gap-2 sm:flex">
              <Button variant="ghost" size="sm" onClick={() => navigate("/login")} data-testid="nav-login-btn">Sign in</Button>
              <Button size="sm" onClick={() => navigate("/register")} data-testid="nav-register-btn">Get started</Button>
            </div>
          )}
          <button
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border lg:hidden"
            onClick={() => setOpen((o) => !o)}
            aria-label="Menu"
            data-testid="mobile-menu-btn"
          >
            {open ? <X className="h-4 w-4" strokeWidth={1.5} /> : <Menu className="h-4 w-4" strokeWidth={1.5} />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border bg-card px-4 py-4 lg:hidden" data-testid="mobile-menu">
          <div className="flex flex-col gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? "bg-accent text-primary" : "text-muted-foreground"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
            <div className="mt-2 flex gap-2 border-t border-border pt-3">
              {user ? (
                <>
                  <Button variant="outline" className="flex-1" onClick={() => { setOpen(false); navigate("/dashboard"); }}>
                    <User className="mr-1.5 h-4 w-4" strokeWidth={1.5} /> Dashboard
                  </Button>
                  <Button variant="ghost" onClick={handleLogout}><LogOut className="h-4 w-4" strokeWidth={1.5} /></Button>
                </>
              ) : (
                <>
                  <Button variant="outline" className="flex-1" onClick={() => { setOpen(false); navigate("/login"); }}>Sign in</Button>
                  <Button className="flex-1" onClick={() => { setOpen(false); navigate("/register"); }}>Get started</Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

import { createContext, useContext, useState, useCallback, useEffect } from "react";

const LocationContext = createContext(null);

const DEFAULT = { id: "delhi", name: "Delhi", country: "India", lat: 28.6139, lon: 77.209 };

export function LocationProvider({ children }) {
  const [location, setLocationState] = useState(() => {
    try {
      const saved = localStorage.getItem("oxyzen_location");
      return saved ? JSON.parse(saved) : DEFAULT;
    } catch {
      return DEFAULT;
    }
  });

  useEffect(() => {
    localStorage.setItem("oxyzen_location", JSON.stringify(location));
  }, [location]);

  const setLocation = useCallback((loc) => setLocationState(loc), []);

  return (
    <LocationContext.Provider value={{ location, setLocation }}>
      {children}
    </LocationContext.Provider>
  );
}

export const useLocation = () => useContext(LocationContext);

import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { LocationProvider } from "@/context/LocationContext";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import { PageLoader } from "@/components/states";
import Home from "@/pages/Home";

const AQIMonitor = lazy(() => import("@/pages/AQIMonitor"));
const MapPage = lazy(() => import("@/pages/MapPage"));
const History = lazy(() => import("@/pages/History"));
const Masks = lazy(() => import("@/pages/Masks"));
const AQIInfo = lazy(() => import("@/pages/AQIInfo"));
const Tips = lazy(() => import("@/pages/Tips"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Login = lazy(() => import("@/pages/Login"));
const Register = lazy(() => import("@/pages/Register"));

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <AuthProvider>
        <LocationProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route element={<Layout />}>
                  <Route path="/" element={<Home />} />
                  <Route path="/aqi-monitor" element={<AQIMonitor />} />
                  <Route path="/map" element={<MapPage />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/masks" element={<Masks />} />
                  <Route path="/aqi-info" element={<AQIInfo />} />
                  <Route path="/tips" element={<Tips />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
          <Toaster position="top-right" richColors />
        </LocationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

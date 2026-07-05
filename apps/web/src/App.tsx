import { useEffect } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { LandingPage } from "./components/landing/LandingPage";
import { PatientListPage } from "./components/patients/PatientListPage";
import { PatientCasePage } from "./components/case/PatientCasePage";

// Remount the case page on EVERY navigation (location.key changes even for the same URL),
// so "Reset demo" while already on a case starts from a clean, idle player.
function PatientCaseRoute() {
  const { key } = useLocation();
  return (
    <AppShell>
      <PatientCasePage key={key} />
    </AppShell>
  );
}

// SPA navigation keeps the window scroll position; reset it on route change
// (unless navigating to an in-page #anchor).
function ScrollToTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
}

export function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/app"
          element={
            <AppShell>
              <PatientListPage />
            </AppShell>
          }
        />
        <Route path="/app/patients/:patientId" element={<PatientCaseRoute />} />
      </Routes>
    </BrowserRouter>
  );
}

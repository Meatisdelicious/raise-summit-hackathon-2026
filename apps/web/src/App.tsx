import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { LandingPage } from "./components/landing/LandingPage";
import { PatientListPage } from "./components/patients/PatientListPage";
import { PatientCasePage } from "./components/case/PatientCasePage";

export function App() {
  return (
    <BrowserRouter>
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
        <Route
          path="/app/patients/:patientId"
          element={
            <AppShell>
              <PatientCasePage />
            </AppShell>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { PatientListPage } from "./components/patients/PatientListPage";
import { PatientCasePage } from "./components/case/PatientCasePage";

export function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<PatientListPage />} />
          <Route path="/patients/:patientId" element={<PatientCasePage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

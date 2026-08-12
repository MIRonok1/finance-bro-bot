import { useEffect } from "react";
import { HashRouter, Route, Routes } from "react-router-dom";

import { NavBar } from "./components/NavBar";
import { MentalMathPage } from "./pages/MentalMathPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { ProfilePage } from "./pages/ProfilePage";
import { TheoryPage } from "./pages/TheoryPage";
import { getTelegramWebApp } from "./telegram";

export function App() {
  useEffect(() => {
    const tg = getTelegramWebApp();
    tg?.ready();
    tg?.expand();
  }, []);

  return (
    <HashRouter>
      <div className="app-shell">
        <Routes>
          <Route path="/" element={<ProfilePage />} />
          <Route path="/theory" element={<TheoryPage />} />
          <Route path="/mental-math" element={<MentalMathPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
        </Routes>
        <NavBar />
      </div>
    </HashRouter>
  );
}

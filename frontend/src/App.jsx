import { useState } from "react";
import Sidebar from "./components/Sidebar";
import HomeTab from "./components/HomeTab";
import AppointmentsTab from "./components/AppointmentsTab";
import "./App.css";

export default function App() {
  const [activeTab, setActiveTab] = useState("home");

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="content">
        {activeTab === "home" && <HomeTab />}
        {activeTab === "appointments" && <AppointmentsTab />}
      </main>
    </div>
  );
}

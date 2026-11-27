import { useState } from "react";
import { Bell, ChevronDown, LogOut } from "lucide-react";
import Sidebar from "./components/Sidebar";
import HomeTab from "./components/HomeTab";
import AppointmentsTab from "./components/AppointmentsTab";
import "./App.css";

export default function App({ onLogout }) {
  const [activeTab, setActiveTab] = useState("home");

  return (
    <div className="app-shell">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="main-area">
        <header className="top-header">
          <div className="header-right">
            <button className="header-icon-btn" title="Notifications">
              <Bell size={20} />
            </button>
            <div className="user-profile">
              <div className="user-avatar">S</div>
              <span className="user-name">Sairaj</span>
              <ChevronDown size={16} />
            </div>
            <button className="header-icon-btn" title="Sign out" onClick={onLogout}>
              <LogOut size={20} />
            </button>
          </div>
        </header>
        <main className="content">
          {/* Stays mounted so a pending staff review survives tab switches. */}
          <div hidden={activeTab !== "home"}>
            <HomeTab />
          </div>
          {activeTab === "appointments" && <AppointmentsTab />}
        </main>
      </div>
    </div>
  );
}

import { Heart, Home, Calendar, ShieldCheck } from "lucide-react";

export default function Sidebar({ activeTab, onTabChange }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <Heart size={20} strokeWidth={2.5} />
        </div>
        <div className="brand-text">
          <span>HealthCare</span>
          <span>AI Assistant</span>
        </div>
      </div>

      <nav className="nav">
        <button
          className={`nav-item ${activeTab === "home" ? "active" : ""}`}
          onClick={() => onTabChange("home")}
        >
          <Home size={18} />
          <span>Home</span>
        </button>
        <button
          className={`nav-item ${activeTab === "appointments" ? "active" : ""}`}
          onClick={() => onTabChange("appointments")}
        >
          <Calendar size={18} />
          <span>Appointments</span>
        </button>
      </nav>

      <div className="security-badge">
        <ShieldCheck size={18} />
        <span>Your health data is secure with us</span>
      </div>
    </aside>
  );
}

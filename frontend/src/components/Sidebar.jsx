import { Home, Calendar, ShieldCheck } from "lucide-react";

function HeartPulseIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        d="M14 24.5C14 24.5 3.5 18 3.5 10.5C3.5 7.46 5.96 5 9 5C10.97 5 12.72 6.05 13.72 7.62L14 8.1L14.28 7.62C15.28 6.05 17.03 5 19 5C22.04 5 24.5 7.46 24.5 10.5C24.5 18 14 24.5 14 24.5Z"
        fill="#4A90E2"
      />
      <path
        d="M7 13.5H10.5L12 10.5L14 16.5L16 11.5L17.5 13.5H21"
        stroke="white"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Sidebar({ activeTab, onTabChange }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <HeartPulseIcon />
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

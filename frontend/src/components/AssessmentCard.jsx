import { ClipboardList, AlertTriangle, Info } from "lucide-react";

const RISK_STYLES = {
  low: { bg: "#E8F7EC", text: "#2E7D32", badgeBg: "#CDEFD6", badgeText: "#1B5E20", badge: "Routine" },
  medium: { bg: "#FFF4E5", text: "#E07B00", badgeBg: "#FCE3BE", badgeText: "#B5650A", badge: "Monitor" },
  high: { bg: "#FDEAEA", text: "#D32F2F", badgeBg: "#F8D3D3", badgeText: "#C62828", badge: "Needs Attention" },
  emergency: { bg: "#FBD8D8", text: "#B71C1C", badgeBg: "#F3A6A6", badgeText: "#7F0000", badge: "Urgent" },
};

function capitalize(word) {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

export default function AssessmentCard({ assessment }) {
  const styles = RISK_STYLES[assessment.urgency] || RISK_STYLES.medium;

  return (
    <section className="card">
      <div className="card-header">
        <ClipboardList size={18} className="card-icon" />
        <h2>Your Health Assessment</h2>
        <span className="timestamp">Today, {assessment.time}</span>
      </div>

      <div className="assessment-row">
        <div className="risk-box" style={{ background: styles.bg }}>
          <AlertTriangle size={26} color={styles.text} />
          <div>
            <div className="section-label">Risk Level</div>
            <div className="risk-value" style={{ color: styles.text }}>
              {capitalize(assessment.urgency)}
              <span
                className="risk-badge"
                style={{ background: styles.badgeBg, color: styles.badgeText }}
              >
                {styles.badge}
              </span>
            </div>
          </div>
        </div>

        <div className="symptoms-box">
          <div className="section-label">Your Symptoms</div>
          <div className="pills">
            {assessment.symptoms.map((symptom) => (
              <span key={symptom} className="pill">
                {symptom}
              </span>
            ))}
          </div>
        </div>

        <div className="condition-box">
          <div className="section-label">Stated Need</div>
          <div className="condition-value">{assessment.stated_need || "General consultation"}</div>
        </div>
      </div>

      <div className="about-box">
        <Info size={18} className="about-icon" />
        <div>
          <div className="about-title">Assessment Summary</div>
          <p>{assessment.rationale}</p>
        </div>
      </div>
    </section>
  );
}

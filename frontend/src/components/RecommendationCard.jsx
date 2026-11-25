import { CheckCircle2, Calendar, Phone, Clock } from "lucide-react";

function initials(name) {
  return name
    .split(" ")
    .filter((part) => part !== "Dr.")
    .map((part) => part[0])
    .join("");
}

function formatSlotTime(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const isToday = date.toDateString() === now.toDateString();
  const isTomorrow = date.toDateString() === tomorrow.toDateString();

  const time = date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

  if (isToday) return { label: "Today", time };
  if (isTomorrow) return { label: "Tomorrow", time };
  return {
    label: date.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" }),
    time,
  };
}

function groupSlotsByDoctor(slots) {
  const map = new Map();
  for (const slot of slots) {
    const key = slot.doctor_name;
    if (!map.has(key)) {
      map.set(key, {
        doctor_name: slot.doctor_name,
        specialization: slot.specialization,
        slots: [],
      });
    }
    map.get(key).slots.push(slot);
  }
  return Array.from(map.values());
}

export default function RecommendationCard({
  requiredSpecialization,
  availableSlots,
  recommendedSlotId,
  reasoning,
  selectedSlotId,
  onSelectSlot,
  applied,
  onApply,
}) {
  const doctors = groupSlotsByDoctor(availableSlots);

  return (
    <section className="recommendation-card">
      <div className="rec-header">
        <CheckCircle2 size={18} color="#2E7D32" />
        <span>Recommended Doctor</span>
      </div>

      {availableSlots.length === 0 && (
        <div className="no-slots-box">
          <Clock size={28} />
          <div>
            <div className="no-slots-title">All slots are currently booked</div>
            <p>
              No {requiredSpecialization} appointments are available right now.
              Please try again after some time.
            </p>
            <div className="no-slots-emergency">
              <Phone size={14} />
              <span>If this is an emergency, contact us directly at <strong>0223567568</strong></span>
            </div>
          </div>
        </div>
      )}

      {doctors.map((doc) => (
        <div className="rec-doctor-row" key={doc.doctor_name}>
          <div className="rec-doctor-info">
            <div className="avatar">{initials(doc.doctor_name)}</div>
            <div>
              <div className="doctor-name">{doc.doctor_name}</div>
              <div className="doctor-spec">{doc.specialization}</div>
            </div>
          </div>

          <div className="rec-slots-section">
            <div className="rec-slots-label">
              <Calendar size={13} />
              <span>Available Time Slots</span>
            </div>
            <div className="rec-slot-buttons">
              {doc.slots.map((slot) => {
                const { label, time } = formatSlotTime(slot.slot_time);
                const isSelected = slot.slot_id === selectedSlotId;
                return (
                  <button
                    key={slot.slot_id}
                    type="button"
                    className={`slot-pill selectable ${isSelected ? "selected" : ""}`}
                    onClick={() => onSelectSlot(isSelected ? null : slot.slot_id)}
                    disabled={applied}
                  >
                    <span className="slot-pill-label">{label}</span>
                    <span className="slot-pill-time">{time}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="rec-actions">
            <button
              className="btn-primary"
              onClick={onApply}
              disabled={applied || !selectedSlotId || !doc.slots.some((s) => s.slot_id === selectedSlotId)}
            >
              {applied && doc.slots.some((s) => s.slot_id === selectedSlotId)
                ? "Appointment Applied"
                : "Apply Appointment"}
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}

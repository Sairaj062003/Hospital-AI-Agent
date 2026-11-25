import { useEffect, useState } from "react";
import { Calendar, Stethoscope } from "lucide-react";
import { fetchAppointments, cancelAppointment } from "../api";

function initials(name) {
  return name
    .split(" ")
    .filter((part) => part !== "Dr.")
    .map((part) => part[0])
    .join("");
}

function formatSlotTime(isoString) {
  const date = new Date(isoString);
  return date.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function AppointmentsTab() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAppointments();
      setAppointments(data.appointments);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel(slotId) {
    try {
      await cancelAppointment(slotId);
      setAppointments((prev) => prev.filter((appt) => appt.slot_id !== slotId));
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) {
    return <div className="appointments-tab empty">Loading appointments...</div>;
  }

  if (error) {
    return <div className="appointments-tab empty error-note">{error}</div>;
  }

  if (appointments.length === 0) {
    return (
      <div className="appointments-tab empty">
        <Calendar size={40} />
        <p>You have no appointments yet.</p>
        <p className="muted">Describe your symptoms on the Home tab to get a recommendation.</p>
      </div>
    );
  }

  return (
    <div className="appointments-tab">
      <h1>All Appointments</h1>
      <div className="appointments-list">
        {appointments.map((appointment) => (
          <div className="appointment-card" key={appointment.slot_id}>
            <div className="doctor-info">
              <div className="avatar">{initials(appointment.doctor_name)}</div>
              <div>
                <div className="doctor-name">{appointment.doctor_name}</div>
                <div className="doctor-spec">{appointment.specialization}</div>
              </div>
            </div>
            <div className="appointment-detail">
              <Stethoscope size={14} />
              <span>{appointment.specialization}</span>
            </div>
            <div className="appointment-slot">{formatSlotTime(appointment.slot_time)}</div>
            <div className="appointment-actions">
              <span className="status-pill">Confirmed</span>
              <button className="btn-cancel" onClick={() => handleCancel(appointment.slot_id)}>
                Cancel
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

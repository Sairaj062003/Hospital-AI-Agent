import { useState } from "react";
import { Mic, Send, Bot, AlertOctagon, ShieldAlert, CheckCircle, Clock, Phone } from "lucide-react";
import { submitQuery, resumeWithSlot } from "../api";
import AssessmentCard from "./AssessmentCard";
import RecommendationCard from "./RecommendationCard";

export default function HomeTab() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Set only when the backend pauses at choose_slot - holds everything
  // needed to render the assessment + recommendation.
  const [pending, setPending] = useState(null);
  const [selectedSlotId, setSelectedSlotId] = useState(null);
  const [applied, setApplied] = useState(false);

  const [successMessage, setSuccessMessage] = useState(false);

  const [noSlotsSpec, setNoSlotsSpec] = useState(null);

  // Terminal, non-scheduling outcomes.
  const [blockedReason, setBlockedReason] = useState(null);
  const [emergencyMessage, setEmergencyMessage] = useState(null);

  function resetOutcomes() {
    setPending(null);
    setSelectedSlotId(null);
    setApplied(false);
    setSuccessMessage(false);
    setNoSlotsSpec(null);
    setBlockedReason(null);
    setEmergencyMessage(null);
    setError(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!query.trim() || loading) return;

    resetOutcomes();
    setLoading(true);

    try {
      const result = await submitQuery(query);

      if (result.status === "choose_slot") {
        setPending(result);
      } else if (result.status === "no_slots") {
        setNoSlotsSpec(result.required_specialization);
      } else if (result.status === "blocked") {
        setBlockedReason(result.reason);
      } else if (result.status === "emergency") {
        setEmergencyMessage(result.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleApply() {
    if (!selectedSlotId || !pending) return;
    setLoading(true);
    setError(null);

    try {
      await resumeWithSlot(pending.thread_id, selectedSlotId);
      setApplied(true);
      setSuccessMessage(true);

      setTimeout(() => {
        resetOutcomes();
        setQuery("");
      }, 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="home-tab">
      <section className="greeting-banner">
        <div className="bot-avatar">
          <Bot size={36} />
        </div>
        <div>
          <h1>Hello John!</h1>
          <p>How can I help you with your health today?</p>
        </div>
      </section>

      <form className="query-bar" onSubmit={handleSubmit}>
        <button type="button" className="icon-btn" title="Speak your symptoms (coming soon)">
          <Mic size={18} />
        </button>
        <input
          type="text"
          placeholder="Describe your symptoms or ask a health question..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <button type="submit" className="icon-btn send-btn" title="Submit" disabled={loading}>
          <Send size={18} />
        </button>
      </form>

      {loading && (
        <div className="loading-note">
          Analyzing your symptoms... urgent cases may take a little longer while our
          staff reviews your case.
        </div>
      )}

      {error && <div className="error-note">{error}</div>}

      {blockedReason && (
        <div className="notice-box notice-blocked">
          <ShieldAlert size={20} />
          <div>
            <div className="notice-title">We couldn't process that message</div>
            <p>Please rephrase your message and describe your symptoms directly.</p>
          </div>
        </div>
      )}

      {emergencyMessage && (
        <div className="notice-box notice-emergency">
          <AlertOctagon size={20} />
          <div>
            <div className="notice-title">Emergency</div>
            <p>{emergencyMessage}</p>
          </div>
        </div>
      )}

      {noSlotsSpec && (
        <div className="no-slots-box">
          <Clock size={28} />
          <div>
            <div className="no-slots-title">All slots are currently booked</div>
            <p>
              No {noSlotsSpec} appointments are available right now.
              Please try again after some time.
            </p>
            <div className="no-slots-emergency">
              <Phone size={14} />
              <span>If this is an emergency, contact us directly at <strong>0223567568</strong></span>
            </div>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="success-toast">
          <CheckCircle size={20} />
          <span>Appointment applied successfully!</span>
        </div>
      )}

      {pending && !loading && !successMessage && (
        <>
          <AssessmentCard
            assessment={{
              symptoms: pending.symptoms,
              stated_need: pending.stated_need,
              urgency: pending.urgency,
              rationale: pending.rationale,
              time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            }}
          />
          <RecommendationCard
            requiredSpecialization={pending.required_specialization}
            availableSlots={pending.available_slots}
            recommendedSlotId={pending.recommended_slot_id}
            reasoning={pending.reasoning}
            selectedSlotId={selectedSlotId}
            onSelectSlot={setSelectedSlotId}
            applied={applied}
            onApply={handleApply}
          />
        </>
      )}
    </div>
  );
}

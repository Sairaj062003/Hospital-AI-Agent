import { useState, useRef, useEffect } from "react";
import { Mic, Square, Send, Bot, AlertOctagon, ShieldAlert, CheckCircle, Clock, Phone, X } from "lucide-react";
import { submitQuery, resumeWithSlot } from "../api";
import AssessmentCard from "./AssessmentCard";
import RecommendationCard from "./RecommendationCard";
import useSpeechToText from "../hooks/useSpeechToText";

export default function HomeTab() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [pending, setPending] = useState(null);
  const [selectedSlotId, setSelectedSlotId] = useState(null);
  const [applied, setApplied] = useState(false);

  const [successMessage, setSuccessMessage] = useState(false);
  const [noSlotsSpec, setNoSlotsSpec] = useState(null);

  const [blockedReason, setBlockedReason] = useState(null);
  const [emergencyMessage, setEmergencyMessage] = useState(null);

  const { listening, transcript, error: speechError, startListening, stopListening, clearTranscript } = useSpeechToText();

  const textareaRef = useRef(null);

  useEffect(() => {
    if (transcript) {
      setQuery(transcript);
    }
  }, [transcript]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    }
  }, [query]);

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

  function handleCancelTranscript() {
    setQuery("");
    clearTranscript();
  }

  function handleMicClick() {
    if (listening) {
      stopListening();
    } else {
      startListening();
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!query.trim() || loading) return;

    clearTranscript();
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

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  }

  const showCancelTranscript = transcript && query === transcript;

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

      <div className="query-bar-wrapper">
        <form className="query-bar" onSubmit={handleSubmit}>
          <button
            type="button"
            className={`icon-btn mic-btn ${listening ? "mic-active" : ""}`}
            title={listening ? "Click to stop recording" : "Click to start speaking"}
            onClick={handleMicClick}
            disabled={loading}
          >
            {listening ? <Square size={16} fill="currentColor" /> : <Mic size={18} />}
          </button>
          <textarea
            ref={textareaRef}
            className="query-input"
            placeholder="Describe your symptoms or ask a health question..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button type="submit" className="icon-btn send-btn" title="Submit" disabled={loading}>
            <Send size={18} />
          </button>
        </form>

        {showCancelTranscript && (
          <button type="button" className="cancel-transcript" onClick={handleCancelTranscript}>
            <X size={14} />
            <span>Cancel transcript</span>
          </button>
        )}

        {listening && (
          <div className="listening-indicator">
            <span className="pulse-dot" />
            <span>Listening... speak now</span>
          </div>
        )}

        {speechError && <div className="error-note">{speechError}</div>}
      </div>

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

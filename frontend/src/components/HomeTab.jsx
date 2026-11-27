import { useState, useRef, useEffect } from "react";
import { Mic, Square, Send, AlertOctagon, ShieldAlert, CheckCircle, Clock, Phone, X, Info } from "lucide-react";
import { submitQuery, resumeWithSlot, fetchReviewStatus } from "../api";
import AssessmentCard from "./AssessmentCard";
import RecommendationCard from "./RecommendationCard";
import useSpeechToText from "../hooks/useSpeechToText";

const REVIEW_POLL_MS = 3000;
const REVIEW_OVERDUE_MS = 2 * 60 * 1000;

function RobotIcon() {
  return (
    <svg width="120" height="130" viewBox="0 0 120 130" fill="none" className="robot-svg">
      {/* Antenna */}
      <circle cx="60" cy="8" r="6" fill="#4A90E2" />
      <rect x="57" y="14" width="6" height="16" rx="3" fill="#4A90E2" />
      {/* Head */}
      <rect x="22" y="30" width="76" height="58" rx="22" fill="#1B2D4A" />
      {/* Eyes */}
      <circle cx="43" cy="55" r="10" fill="#4AE0E0" />
      <circle cx="77" cy="55" r="10" fill="#4AE0E0" />
      {/* Smile */}
      <path d="M44 72C48 78 72 78 76 72" stroke="#4A90E2" strokeWidth="3" strokeLinecap="round" fill="none" />
      {/* Left ear */}
      <rect x="6" y="48" width="10" height="26" rx="5" fill="#4A90E2" />
      {/* Right ear */}
      <rect x="104" y="48" width="10" height="26" rx="5" fill="#4A90E2" />
      {/* Left arm */}
      <path d="M18 100C10 96 8 106 16 108" stroke="#4A90E2" strokeWidth="5" strokeLinecap="round" fill="none" />
      {/* Plus button */}
      <circle cx="100" cy="110" r="16" fill="#4A90E2" />
      <line x1="92" y1="110" x2="108" y2="110" stroke="white" strokeWidth="3" strokeLinecap="round" />
      <line x1="100" y1="102" x2="100" y2="118" stroke="white" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

function HeartbeatDecoration() {
  return (
    <svg className="heartbeat-decoration" viewBox="0 0 320 80" fill="none" preserveAspectRatio="none">
      <path
        d="M0 40 H60 L75 20 L90 60 L105 30 L120 50 L135 40 H200 L215 20 L230 60 L245 30 L260 50 L275 40 H320"
        stroke="rgba(255,255,255,0.35)"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function HeartIcon() {
  return (
    <svg width="52" height="48" viewBox="0 0 52 48" fill="none" className="heart-icon">
      <path
        d="M26 46C26 46 2 34 2 16C2 8.82 7.82 3 15 3C19.42 3 23.34 5.36 25.58 8.89L26 9.56L26.42 8.89C28.66 5.36 32.58 3 37 3C44.18 3 50 8.82 50 16C50 34 26 46 26 46Z"
        fill="#6AA6F8"
        opacity="0.8"
      />
    </svg>
  );
}

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
  const [faqAnswer, setFaqAnswer] = useState(null);

  const [reviewThreadId, setReviewThreadId] = useState(null);
  const [reviewOverdue, setReviewOverdue] = useState(false);
  const [adminMessage, setAdminMessage] = useState(null);

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

  useEffect(() => {
    if (!reviewThreadId) return;
    let stopped = false;
    let pollTimer;
    const overdueTimer = setTimeout(() => setReviewOverdue(true), REVIEW_OVERDUE_MS);

    async function poll() {
      try {
        const result = await fetchReviewStatus(reviewThreadId);
        if (stopped) return;
        if (result.status !== "awaiting_review") {
          setReviewThreadId(null);
          handleResult(result);
          return;
        }
      } catch (err) {
        if (stopped) return;
        // 404 means the server lost the request; other failures are retried.
        if (err.status === 404) {
          setReviewThreadId(null);
          setError("Your review request was lost. Please submit it again, or call 0223567568 if it is urgent.");
          return;
        }
      }
      pollTimer = setTimeout(poll, REVIEW_POLL_MS);
    }

    poll();
    return () => {
      stopped = true;
      clearTimeout(pollTimer);
      clearTimeout(overdueTimer);
    };
  }, [reviewThreadId]);

  function handleResult(result) {
    setAdminMessage(result.admin_message || null);

    if (result.status === "choose_slot") {
      setPending(result);
    } else if (result.status === "no_slots") {
      setNoSlotsSpec(result.required_specialization);
    } else if (result.status === "blocked") {
      setBlockedReason(result.reason);
    } else if (result.status === "emergency") {
      setEmergencyMessage(result.message);
    } else if (result.status === "faq_answer") {
      setFaqAnswer(result.message);
    } else if (result.status === "awaiting_review") {
      setReviewThreadId(result.thread_id);
    } else if (result.status === "error") {
      setError(result.message);
    }
  }

  function resetOutcomes() {
    setPending(null);
    setSelectedSlotId(null);
    setApplied(false);
    setSuccessMessage(false);
    setNoSlotsSpec(null);
    setBlockedReason(null);
    setEmergencyMessage(null);
    setFaqAnswer(null);
    setReviewThreadId(null);
    setReviewOverdue(false);
    setAdminMessage(null);
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
    if (!query.trim() || loading || reviewThreadId) return;

    clearTranscript();
    resetOutcomes();
    setLoading(true);

    try {
      handleResult(await submitQuery(query));
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
        <div className="banner-left">
          <RobotIcon />
        </div>
        <div className="banner-text">
          <h1>Hello Sairaj!</h1>
          <p>How can I help you with your health today?</p>
        </div>
        <div className="banner-right">
          <HeartbeatDecoration />
          <HeartIcon />
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
          <button
            type="submit"
            className="icon-btn send-btn"
            title="Submit"
            disabled={loading || Boolean(reviewThreadId)}
          >
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
          Analyzing your symptoms...
        </div>
      )}

      {reviewThreadId && (
        <div className="notice-box notice-blocked" role="status">
          <Clock size={20} />
          <div>
            <div className="notice-title">Our staff is reviewing your case</div>
            <p>Please keep this page open. The reply will appear here.</p>
          </div>
        </div>
      )}

      {reviewThreadId && reviewOverdue && (
        <div className="notice-box notice-emergency" role="alert">
          <Phone size={20} />
          <div>
            <div className="notice-title">Still waiting for a reply</div>
            <p>If your case is urgent, contact us directly at <strong>0223567568</strong>.</p>
          </div>
        </div>
      )}

      {error && <div className="error-note">{error}</div>}

      {adminMessage && (
        <div className="faq-answer-box">
          <div className="faq-answer-icon">
            <Info size={18} />
          </div>
          <p><strong>Message from our staff:</strong> {adminMessage}</p>
        </div>
      )}

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

      {faqAnswer && (
        <div className="faq-answer-box">
          <div className="faq-answer-icon">
            <Info size={18} />
          </div>
          <p>{faqAnswer}</p>
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

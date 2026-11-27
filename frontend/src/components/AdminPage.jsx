import { useState, useEffect } from "react";
import { fetchReviewRequests, submitReviewDecision } from "../api";
import "../App.css";

const POLL_MS = 3000;

const DEFAULT_MESSAGES = {
  yes: "Your case is very serious and highly urgent, so please contact the authorities directly instead of booking here. Phone: 0224567184",
  no: "Our staff has reviewed your case. You can continue with booking an appointment.",
};

function ReviewCard({ request, onDecided }) {
  const [decision, setDecision] = useState(null);
  const [drafts, setDrafts] = useState(DEFAULT_MESSAGES);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  async function handleSend() {
    setSending(true);
    setError(null);
    try {
      await submitReviewDecision(request.thread_id, decision, drafts[decision]);
      onDecided(request.thread_id);
    } catch (err) {
      setError(err.message);
      setSending(false);
    }
  }

  return (
    <section className="card">
      <div className="card-header">
        <span className={`urgency-tag urgency-${request.urgency}`}>{request.urgency}</span>
        <h2>{request.full_name || "Name not provided"}</h2>
        <span className="timestamp">{new Date(request.created_at).toLocaleString()}</span>
      </div>

      <div className="section-label">Phone</div>
      <p className="review-text">{request.phone_number || "Not provided"}</p>

      <div className="section-label">Patient message</div>
      <p className="review-text">{request.raw_message}</p>

      <div className="section-label">AI assessment</div>
      <p className="review-text">{request.rationale}</p>

      <div className="section-label">Tell the patient to contact authorities immediately?</div>
      <div className="review-choices">
        <button
          type="button"
          className={`choice-btn yes ${decision === "yes" ? "selected" : ""}`}
          onClick={() => setDecision("yes")}
          disabled={sending}
        >
          Yes, contact authorities
        </button>
        <button
          type="button"
          className={`choice-btn no ${decision === "no" ? "selected" : ""}`}
          onClick={() => setDecision("no")}
          disabled={sending}
        >
          No, continue to booking
        </button>
      </div>

      {decision && (
        <>
          <textarea
            className="review-message"
            aria-label="Message to patient"
            value={drafts[decision]}
            onChange={(event) => setDrafts({ ...drafts, [decision]: event.target.value })}
            maxLength={1000}
            rows={3}
            disabled={sending}
          />
          <button
            type="button"
            className="btn-primary"
            onClick={handleSend}
            disabled={sending || !drafts[decision].trim()}
          >
            {sending ? "Sending..." : "Send decision"}
          </button>
        </>
      )}

      {error && <div className="error-note review-error">{error}</div>}
    </section>
  );
}

export default function AdminPage({ onLogout }) {
  const [requests, setRequests] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stopped = false;
    let timer;

    async function poll() {
      try {
        const data = await fetchReviewRequests();
        if (stopped) return;
        setRequests(data.requests);
        setError(null);
      } catch (err) {
        if (!stopped) setError(err.message);
      }
      if (!stopped) timer = setTimeout(poll, POLL_MS);
    }

    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  function removeRequest(threadId) {
    setRequests((current) => current.filter((r) => r.thread_id !== threadId));
  }

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Urgent case review</h1>
        <button type="button" className="btn-outline" onClick={onLogout}>Sign out</button>
      </div>
      <p className="muted">New requests appear automatically.</p>

      {error && <div className="error-note">{error}</div>}
      {requests?.length === 0 && <p className="muted">No requests waiting.</p>}
      {requests?.map((request) => (
        <ReviewCard key={request.thread_id} request={request} onDecided={removeRequest} />
      ))}
    </div>
  );
}

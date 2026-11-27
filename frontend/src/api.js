export const AUTH_EXPIRED_EVENT = "auth:expired";

async function parseOrThrow(response) {
  if (!response.ok) {
    // A 401 from the login call is just a wrong password, not an ended session.
    if (response.status === 401 && !response.url.endsWith("/api/auth/login")) {
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    }
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail || `Request failed with status ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function fetchCurrentUser() {
  const response = await fetch("/api/auth/me");
  return parseOrThrow(response);
}

export async function login(email, password) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseOrThrow(response);
}

export async function logout() {
  const response = await fetch("/api/auth/logout", { method: "POST" });
  return parseOrThrow(response);
}

export async function fetchReviewStatus(threadId) {
  const response = await fetch(`/api/review/${threadId}`);
  return parseOrThrow(response);
}

export async function fetchReviewRequests() {
  const response = await fetch("/api/admin/requests");
  return parseOrThrow(response);
}

export async function submitReviewDecision(threadId, decision, message) {
  const response = await fetch(`/api/admin/requests/${threadId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, message }),
  });
  return parseOrThrow(response);
}

export async function submitQuery(message) {
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return parseOrThrow(response);
}

export async function resumeWithSlot(threadId, slotId) {
  const response = await fetch("/api/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, slot_id: slotId }),
  });
  return parseOrThrow(response);
}

export async function fetchAppointments() {
  const response = await fetch("/api/appointments");
  return parseOrThrow(response);
}

export async function cancelAppointment(slotId) {
  const response = await fetch(`/api/appointments/${slotId}`, {
    method: "DELETE",
  });
  return parseOrThrow(response);
}

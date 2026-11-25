const API_BASE = "http://127.0.0.1:8000";

async function parseOrThrow(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${response.status}`);
  }
  return response.json();
}

export async function submitQuery(message) {
  const response = await fetch(`${API_BASE}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return parseOrThrow(response);
}

export async function resumeWithSlot(threadId, slotId) {
  const response = await fetch(`${API_BASE}/api/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, slot_id: slotId }),
  });
  return parseOrThrow(response);
}

export async function fetchAppointments() {
  const response = await fetch(`${API_BASE}/api/appointments`);
  return parseOrThrow(response);
}

export async function cancelAppointment(slotId) {
  const response = await fetch(`${API_BASE}/api/appointments/${slotId}`, {
    method: "DELETE",
  });
  return parseOrThrow(response);
}

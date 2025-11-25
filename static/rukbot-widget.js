// ================================
// RUKBOT WIDGET SCRIPT (FINAL)
// ================================

async function sendMessage(e) {
  e.preventDefault();

  const input = document.getElementById("rukbot-input");
  const chat = document.getElementById("rukbot-chat");
  const message = input.value.trim();
  input.value = "";

  if (!message) return;

  // --- Add user bubble ---
  const userDiv = document.createElement("div");
  userDiv.className = "rukbot-user";
  userDiv.textContent = message;
  chat.appendChild(userDiv);

  chat.scrollTop = chat.scrollHeight;

  // --- Determine backend URL ---
  const API_URL =
    window.location.hostname.includes("localhost") ||
    window.location.hostname.includes("127.0.0.1")
      ? "http://127.0.0.1:8000/chat"
      : "https://rukbot-backend.onrender.com/chat";

  // --- Call backend ---
  let cleanResponse = "⚠️ Something went wrong — try again!";

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await res.json();

    // ========================
    // 💥 THE MAGIC FIX
    // Strip out any JSON wrapper
    // ========================    
    if (typeof data.response === "string") {
      cleanResponse = data.response.trim();

      // Remove accidental JSON wrappers, if they appear
      if (cleanResponse.startsWith("{") && cleanResponse.includes("response")) {
        try {
          const parsed = JSON.parse(cleanResponse);
          if (parsed.response) cleanResponse = parsed.response;
        } catch (err) {
          // If parsing fails, fall back to the raw string
        }
      }
    }

  } catch (err) {
    cleanResponse = "⚠️ Connection issue — please try again in a moment.";
  }

  // --- Add bot bubble ---
  const botDiv = document.createElement("div");
  botDiv.className = "rukbot-response";
  botDiv.textContent = cleanResponse;
  chat.appendChild(botDiv);

  chat.scrollTop = chat.scrollHeight;
}

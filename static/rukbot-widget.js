async function sendMessage(e) {
  e.preventDefault();

  const input = document.getElementById("rukbot-input");
  const chat = document.getElementById("rukbot-chat");
  const message = input.value.trim();

  if (!message) return; // prevent empty sends
  input.value = "";

  // Add user message to chat window
  const userDiv = document.createElement("div");
  userDiv.className = "rukbot-user";
  userDiv.textContent = message;
  chat.appendChild(userDiv);

  // Determine backend URL (local vs production)
  const API_URL =
    window.location.hostname.includes("localhost") ||
    window.location.hostname.includes("127.0.0.1")
      ? "http://127.0.0.1:8000/chat"
      : "https://rukbot-backend.onrender.com/chat";

  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();

    // Create bot reply bubble
    const botDiv = document.createElement("div");
    botDiv.className = "rukbot-response";

    // IMPORTANT: Only show the text, not the full JSON
    botDiv.textContent =
      (data && data.response) ||
      "🧠 I'm having trouble right now — mind trying again?";

    chat.appendChild(botDiv);
  } catch (err) {
    // Network/API fallback
    const errorDiv = document.createElement("div");
    errorDiv.className = "rukbot-response";
    errorDiv.textContent =
      "🧠 I'm having trouble reaching my brain right now (backend connection issue).";
    chat.appendChild(errorDiv);
  }

  // Auto-scroll to bottom
  chat.scrollTop = chat.scrollHeight;
}

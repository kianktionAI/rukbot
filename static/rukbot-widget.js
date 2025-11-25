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
  let data;
  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    data = await res.json();
  } catch (err) {
    data = { response: "⚠️ Connection issue — please try again in a moment!" };
  }

  // --- Add bot bubble ---
  const botDiv = document.createElement("div");
  botDiv.className = "rukbot-response";

  // ✅ FIX: show ONLY the clean text, no JSON {} wrapper
  botDiv.textContent =
    typeof data.response === "string"
      ? data.response.trim()
      : JSON.stringify(data.response);

  chat.appendChild(botDiv);
  chat.scrollTop = chat.scrollHeight;
}

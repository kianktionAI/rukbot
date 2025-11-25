// =============================
//  RUKBOT WIDGET SCRIPT
// =============================

async function sendMessage(e) {
  e.preventDefault();

  const input = document.getElementById("rukbot-input");
  const chat = document.getElementById("rukbot-chat");
  const message = input.value.trim();
  input.value = "";

  if (!message) return;

  //----------------------------
  // Add User Bubble
  //----------------------------
  const userDiv = document.createElement("div");
  userDiv.className = "rukbot-user";
  userDiv.textContent = message;
  chat.appendChild(userDiv);

  chat.scrollTop = chat.scrollHeight;

  //----------------------------
  // Determine Backend URL
  //----------------------------
  const API_URL =
    window.location.hostname.includes("localhost") ||
    window.location.hostname.includes("127.0.0.1")
      ? "http://127.0.0.1:8000/chat"
      : "https://rukbot-backend.onrender.com/chat";

  //----------------------------
  // Call Backend
  //----------------------------
  let data;
  try {
    const res = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    data = await res.json();
  } catch (err) {
    console.error("RUKBOT Network Error:", err);
    data = { response: "⚠️ Connection issue — please try again in a moment!" };
  }

  //----------------------------
  // Add Bot Bubble (CLEAN OUTPUT)
  //----------------------------
  const botDiv = document.createElement("div");
  botDiv.className = "rukbot-response";

  // ✨ ALWAYS show only clean natural text — no {}, no quotes
  let cleanText = "";

  if (typeof data?.response === "string") {
    cleanText = data.response.trim();
  } else if (data?.response) {
    cleanText = String(data.response).trim();
  } else {
    cleanText = "⚠️ Unexpected response format.";
  }

  botDiv.textContent = cleanText;
  chat.appendChild(botDiv);

  chat.scrollTop = chat.scrollHeight;
}



// =============================
//  ENTER KEY HANDLER
// =============================
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("rukbot-form");
  const input = document.getElementById("rukbot-input");

  form.addEventListener("submit", sendMessage);

  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      form.dispatchEvent(new Event("submit"));
    }
  });
});

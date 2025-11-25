async function sendMessage(e) {
  e.preventDefault();
  const input = document.getElementById("rukbot-input");
  const chat = document.getElementById("rukbot-chat");
  const message = input.value;
  input.value = "";

  const userDiv = document.createElement("div");
  userDiv.className = "rukbot-user";
  userDiv.textContent = message;
  chat.appendChild(userDiv);

  const API_URL =
    window.location.hostname.includes("localhost") ||
    window.location.hostname.includes("127.0.0.1")
        ? "http://127.0.0.1:8000/chat"
        : "https://rukbot-backend.onrender.com/chat";

  const res = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  
  const data = await res.json();

  const botDiv = document.createElement("div");
  botDiv.className = "rukbot-response";
  botDiv.textContent = data.response || "Oops! Something went wrong.";
  chat.appendChild(botDiv);

  chat.scrollTop = chat.scrollHeight;
}

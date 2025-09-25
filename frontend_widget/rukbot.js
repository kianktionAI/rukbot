// static/rukbot-widget.js

document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("rukbot-button");
  const chat = document.getElementById("rukbot-chat");
  const closeBtn = document.getElementById("rukbot-close");
  const input = document.getElementById("rukbot-input");
  const sendBtn = document.getElementById("rukbot-send");
  const messages = document.getElementById("rukbot-messages");

  // Toggle chat visibility
  button.addEventListener("click", () => {
    chat.style.display = chat.style.display === "flex" ? "none" : "flex";
  });

  closeBtn.addEventListener("click", () => {
    chat.style.display = "none";
  });

  // Add message to chat window
  function addMessage(text, sender = "bot") {
    const msg = document.createElement("div");
    msg.classList.add("rukbot-msg");
    if (sender === "user") msg.classList.add("rukbot-user");
    msg.innerText = text;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight; // Auto-scroll
  }

  // Send user input to backend
  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user");
    input.value = "";

    try {
      const response = await fetch("/ask_rukbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });

      const data = await response.json();
      if (data.answer) {
        addMessage(data.answer, "bot");
      } else {
        addMessage("⚠️ Sorry, I didn’t catch that. Try again?", "bot");
      }
    } catch (err) {
      console.error("Error:", err);
      addMessage("⚠️ Oops, something went wrong. Try again later.", "bot");
    }
  }

  // Send on button click or Enter key
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
});

function toggleRukbot() {
  const widget = document.getElementById("rukbot-widget");
  widget.style.display = widget.style.display === "none" ? "block" : "none";
}

async function sendMessage(e) {
  e.preventDefault();
  const input = document.getElementById("rukbot-input");
  const chat = document.getElementById("rukbot-chat");
  const message = input.value;
  input.value = "";

  const userMsg = document.createElement("div");
  userMsg.className = "rukbot-user";
  userMsg.textContent = message;
  chat.appendChild(userMsg);

  const res = await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });

  const data = await res.json();
  const botMsg = document.createElement("div");
  botMsg.className = "rukbot-response";
  botMsg.textContent = data.response || "Hmm... I couldn't fetch that!";
  chat.appendChild(botMsg);

  chat.scrollTop = chat.scrollHeight;
}

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

  const res = await fetch("/ask", {
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

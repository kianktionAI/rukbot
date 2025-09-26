(function () {
  // === Inject CSS dynamically ===
  const css = `
  #rukbot-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    font-family: Arial, sans-serif;
    z-index: 9999;
  }
  #rukbot-button {
    background: #FFD500;
    border-radius: 50%;
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
  }
  #rukbot-button img { width: 40px; height: 40px; }
  #rukbot-chat {
    width: 320px;
    height: 420px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 6px 10px rgba(0,0,0,0.25);
    display: none;
    flex-direction: column;
    overflow: hidden;
  }
  #rukbot-header {
    background: #FFD500;
    color: #000;
    font-weight: bold;
    display: flex;
    align-items: center;
    padding: 10px;
  }
  #rukbot-header img { width: 28px; height: 28px; margin-right: 8px; }
  #rukbot-header span { flex: 1; }
  #rukbot-close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #000;
  }
  #rukbot-messages {
    flex: 1;
    padding: 10px;
    overflow-y: auto;
    background: #f9f9f9;
    display: flex;
    flex-direction: column;
  }
  .rukbot-msg {
    max-width: 80%;
    padding: 8px 12px;
    margin: 6px 0;
    border-radius: 10px;
    font-size: 14px;
    line-height: 1.4;
    word-wrap: break-word;
  }
  .rukbot-msg.bot {
    background: #eee;
    align-self: flex-start;
  }
  .rukbot-msg.user {
    background: #FFD500;
    align-self: flex-end;
    text-align: right;
  }
  #rukbot-input-area {
    display: flex;
    border-top: 1px solid #ddd;
  }
  #rukbot-input {
    flex: 1;
    border: none;
    padding: 12px;
    font-size: 14px;
    outline: none;
  }
  #rukbot-send {
    background: #FFD500;
    border: none;
    padding: 0 15px;
    cursor: pointer;
    font-size: 16px;
  }
  `;
  const style = document.createElement("style");
  style.innerText = css;
  document.head.appendChild(style);

  // === Build HTML dynamically ===
  const container = document.createElement("div");
  container.id = "rukbot-container";
  container.innerHTML = `
    <div id="rukbot-button">
      <img src="https://rukbot.onrender.com/static/images/rukbot_icon.png" alt="Chat">
    </div>
    <div id="rukbot-chat">
      <div id="rukbot-header">
        <img src="https://rukbot.onrender.com/static/images/RUKSAK-icon.png" alt="RUKSAK Logo">
        <span>RUKBOT</span>
        <button id="rukbot-close">×</button>
      </div>
      <div id="rukbot-messages"></div>
      <div id="rukbot-input-area">
        <input id="rukbot-input" type="text" placeholder="Ask me anything...">
        <button id="rukbot-send">➤</button>
      </div>
    </div>
  `;
  document.body.appendChild(container);

  // === Behaviour ===
  const button = document.getElementById("rukbot-button");
  const chat = document.getElementById("rukbot-chat");
  const closeBtn = document.getElementById("rukbot-close");
  const input = document.getElementById("rukbot-input");
  const sendBtn = document.getElementById("rukbot-send");
  const messages = document.getElementById("rukbot-messages");

  function addMessage(text, sender = "bot") {
    const msg = document.createElement("div");
    msg.classList.add("rukbot-msg", sender);
    msg.innerText = text;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, "user");
    input.value = "";

    try {
      const response = await fetch("https://rukbot.onrender.com/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        addMessage("⚠️ Server error — please try again.", "bot");
        return;
      }

      const data = await response.json().catch(() => null);

      if (data && data.response) {
        addMessage(data.response, "bot");
      } else {
        addMessage("⚠️ No response received from RUKBOT.", "bot");
      }

    } catch (err) {
      console.error("Fetch error:", err);
      addMessage("⚠️ Oops, something went wrong.", "bot");
    }
  }

  button.addEventListener("click", () => {
    chat.style.display = "flex";
    button.style.display = "none";
  });
  closeBtn.addEventListener("click", () => {
    chat.style.display = "none";
    button.style.display = "flex";
  });
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });
})();

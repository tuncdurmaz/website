/**
 * Chat Widget for tuncdurmaz.com
 * 
 * Floating bottom-right chat panel powered by Cloudflare Worker + Anthropic API.
 * Drop-in: just add <script src="chat-widget.js"></script> before </body>.
 *
 * CONFIGURE: Change WORKER_URL below to your deployed Cloudflare Worker URL.
 */

(function () {
  // ═══════════════════════════════════════════
  //  CONFIGURATION — change this after deployment
  // ═══════════════════════════════════════════
  const WORKER_URL = 'https://durmaz-chat.tuncdurmaz.workers.dev';
  // After deploying your Cloudflare Worker, replace the URL above.
  // Example: 'https://durmaz-chat.tuncdurmaz.workers.dev'

  // ═══════════════════════════════════════════
  //  STYLES
  // ═══════════════════════════════════════════
  const style = document.createElement('style');
  style.textContent = `
    #td-chat-fab {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 56px; height: 56px; border-radius: 50%;
      background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
      border: none; cursor: pointer;
      box-shadow: 0 4px 20px rgba(56,189,248,0.35);
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    #td-chat-fab:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 28px rgba(56,189,248,0.5);
    }
    #td-chat-fab svg { width: 26px; height: 26px; fill: #0f172a; transition: opacity 0.15s; }
    #td-chat-fab .td-close-icon { display: none; }
    #td-chat-fab.open .td-chat-icon { display: none; }
    #td-chat-fab.open .td-close-icon { display: block; }

    #td-chat-panel {
      position: fixed; bottom: 92px; right: 24px; z-index: 9998;
      width: 380px; max-width: calc(100vw - 32px);
      height: 520px; max-height: calc(100vh - 120px);
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 16px;
      box-shadow: 0 12px 48px rgba(0,0,0,0.5);
      display: flex; flex-direction: column;
      overflow: hidden;
      opacity: 0; transform: translateY(16px) scale(0.95);
      pointer-events: none;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }
    #td-chat-panel.open {
      opacity: 1; transform: translateY(0) scale(1);
      pointer-events: auto;
    }

    /* Header */
    .td-chat-header {
      padding: 16px 20px;
      background: #1e293b;
      border-bottom: 1px solid #334155;
      flex-shrink: 0;
    }
    .td-chat-header h3 {
      margin: 0; font-size: 15px; font-weight: 700; color: #f1f5f9;
      font-family: Inter, system-ui, sans-serif;
    }
    .td-chat-header p {
      margin: 4px 0 0; font-size: 12px; color: #94a3b8;
      font-family: Inter, system-ui, sans-serif;
    }

    /* Messages area */
    .td-chat-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 12px;
    }
    .td-chat-messages::-webkit-scrollbar { width: 5px; }
    .td-chat-messages::-webkit-scrollbar-track { background: transparent; }
    .td-chat-messages::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

    .td-msg {
      max-width: 85%; padding: 10px 14px;
      border-radius: 12px; font-size: 13.5px; line-height: 1.55;
      font-family: Inter, system-ui, sans-serif;
      word-wrap: break-word;
    }
    .td-msg a { color: #38bdf8; text-decoration: underline; }
    .td-msg strong { font-weight: 600; }
    .td-msg-user {
      align-self: flex-end;
      background: #38bdf8; color: #0f172a;
      border-bottom-right-radius: 4px;
    }
    .td-msg-assistant {
      align-self: flex-start;
      background: #1e293b; color: #e2e8f0;
      border: 1px solid #334155;
      border-bottom-left-radius: 4px;
    }

    /* Typing indicator */
    .td-typing { display: flex; gap: 5px; padding: 12px 16px; align-self: flex-start; }
    .td-typing span {
      width: 7px; height: 7px; border-radius: 50%; background: #475569;
      animation: td-bounce 1.2s ease-in-out infinite;
    }
    .td-typing span:nth-child(2) { animation-delay: 0.15s; }
    .td-typing span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes td-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    /* Suggested questions */
    .td-suggestions {
      display: flex; flex-direction: column; gap: 6px;
      padding: 0 16px 12px;
      flex-shrink: 0;
    }
    .td-suggestions button {
      background: #1e293b; border: 1px solid #334155;
      color: #94a3b8; font-size: 12px; padding: 8px 12px;
      border-radius: 8px; cursor: pointer; text-align: left;
      font-family: Inter, system-ui, sans-serif;
      transition: border-color 0.15s, color 0.15s;
    }
    .td-suggestions button:hover {
      border-color: #38bdf8; color: #f1f5f9;
    }

    /* Input area */
    .td-chat-input {
      display: flex; gap: 8px; padding: 12px 16px;
      background: #1e293b; border-top: 1px solid #334155;
      flex-shrink: 0;
    }
    .td-chat-input input {
      flex: 1; background: #0f172a; border: 1px solid #334155;
      color: #f1f5f9; padding: 10px 14px; border-radius: 10px;
      font-size: 13.5px; outline: none;
      font-family: Inter, system-ui, sans-serif;
      transition: border-color 0.15s;
    }
    .td-chat-input input::placeholder { color: #64748b; }
    .td-chat-input input:focus { border-color: #38bdf8; }
    .td-chat-input button {
      background: #38bdf8; border: none; border-radius: 10px;
      width: 40px; height: 40px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.15s;
      flex-shrink: 0;
    }
    .td-chat-input button:hover { background: #7dd3fc; }
    .td-chat-input button:disabled { opacity: 0.4; cursor: not-allowed; }
    .td-chat-input button svg { width: 18px; height: 18px; fill: #0f172a; }

    /* Footer */
    .td-chat-footer {
      text-align: center; padding: 6px; font-size: 10px; color: #475569;
      font-family: Inter, system-ui, sans-serif;
      border-top: 1px solid #1e293b;
    }

    /* ── 'Ask me' label that floats beside the FAB ── */
    #td-chat-label {
      position: fixed; bottom: 32px; right: 92px; z-index: 9999;
      pointer-events: none;
      background: #1e293b;
      color: #f1f5f9;
      font: 600 13px/1 Inter, system-ui, sans-serif;
      padding: 7px 12px;
      border-radius: 999px;
      border: 1px solid #334155;
      box-shadow: 0 2px 10px rgba(0,0,0,0.25);
      opacity: 0; transform: translateX(6px);
      transition: opacity 0.25s ease, transform 0.25s ease;
    }
    #td-chat-label.visible { opacity: 1; transform: translateX(0); }
    #td-chat-fab.open ~ #td-chat-label { opacity: 0; }

    /* ── One-time hello bubble (shows a sample question) ── */
    #td-chat-hello {
      position: fixed; bottom: 96px; right: 24px; z-index: 9999;
      max-width: 280px;
      background: #1e293b;
      color: #f1f5f9;
      font: 500 13px/1.45 Inter, system-ui, sans-serif;
      padding: 12px 14px 12px 16px;
      border-radius: 14px 14px 4px 14px;
      border: 1px solid #38bdf8;
      box-shadow: 0 8px 28px rgba(56,189,248,0.25);
      opacity: 0; transform: translateY(8px);
      pointer-events: none;
      transition: opacity 0.35s ease, transform 0.35s ease;
    }
    #td-chat-hello.visible { opacity: 1; transform: translateY(0); pointer-events: auto; }
    #td-chat-hello::after {
      content: ''; position: absolute; bottom: -7px; right: 18px;
      width: 12px; height: 12px; background: #1e293b;
      border-right: 1px solid #38bdf8; border-bottom: 1px solid #38bdf8;
      transform: rotate(45deg);
    }
    #td-chat-hello .td-hello-prompt {
      display: block; color: #94a3b8; font-size: 11px; font-weight: 500;
      text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px;
    }
    #td-chat-hello .td-hello-q {
      cursor: pointer; color: #38bdf8;
    }
    #td-chat-hello .td-hello-q:hover { color: #f1f5f9; text-decoration: underline; }
    #td-chat-hello .td-hello-close {
      position: absolute; top: 4px; right: 4px;
      width: 22px; height: 22px; border: 0; background: transparent;
      color: #64748b; cursor: pointer; font-size: 16px; line-height: 1;
      border-radius: 50%;
    }
    #td-chat-hello .td-hello-close:hover { color: #f1f5f9; background: #0f172a; }

    /* ── One-time gentle pulse on the FAB (synced with bubble) ── */
    @keyframes td-pulse-once {
      0%   { box-shadow: 0 4px 20px rgba(56,189,248,0.35), 0 0 0 0   rgba(56,189,248,0.55); }
      70%  { box-shadow: 0 4px 20px rgba(56,189,248,0.35), 0 0 0 16px rgba(56,189,248,0);    }
      100% { box-shadow: 0 4px 20px rgba(56,189,248,0.35), 0 0 0 0   rgba(56,189,248,0);    }
    }
    #td-chat-fab.td-pulse { animation: td-pulse-once 1.6s ease-out 2; }

    /* Mobile adjustments */
    @media (max-width: 480px) {
      #td-chat-panel {
        right: 8px; bottom: 84px;
        width: calc(100vw - 16px);
        height: calc(100vh - 100px);
        border-radius: 12px;
      }
      #td-chat-fab { bottom: 16px; right: 16px; }
      #td-chat-label { bottom: 24px; right: 84px; font-size: 12px; padding: 6px 10px; }
      #td-chat-hello { right: 16px; bottom: 88px; max-width: calc(100vw - 32px); }
    }
  `;
  document.head.appendChild(style);

  // ═══════════════════════════════════════════
  //  DOM
  // ═══════════════════════════════════════════

  // FAB button
  const fab = document.createElement('button');
  fab.id = 'td-chat-fab';
  fab.setAttribute('aria-label', "Ask Tunç's AI assistant");
  fab.innerHTML = `
    <svg class="td-chat-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/>
      <circle cx="8" cy="10" r="1.2"/><circle cx="12" cy="10" r="1.2"/><circle cx="16" cy="10" r="1.2"/>
    </svg>
    <svg class="td-close-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
    </svg>
  `;
  document.body.appendChild(fab);

  // Permanent 'Ask me' label floating beside the FAB (always visible, fades out when chat opens)
  const labelEl = document.createElement('div');
  labelEl.id = 'td-chat-label';
  labelEl.setAttribute('aria-hidden', 'true');  // FAB's aria-label already covers it for screen readers
  labelEl.textContent = 'Ask me';
  document.body.appendChild(labelEl);

  // One-time hello bubble — shows a single sample question on first device visit
  const helloEl = document.createElement('div');
  helloEl.id = 'td-chat-hello';
  helloEl.setAttribute('role', 'status');
  document.body.appendChild(helloEl);

  // Chat panel
  const panel = document.createElement('div');
  panel.id = 'td-chat-panel';
  panel.innerHTML = `
    <div class="td-chat-header">
      <h3>Ask about Prof. Durmaz</h3>
      <p>AI assistant · answers from this website's content</p>
    </div>
    <div class="td-chat-messages" id="td-messages">
      <div class="td-msg td-msg-assistant">Hi! I can answer questions about Prof. Durmaz's research, publications, teaching, and background. What would you like to know?</div>
    </div>
    <div class="td-suggestions" id="td-suggestions"></div>
    <div class="td-chat-input">
      <input type="text" id="td-input" placeholder="Ask a question..." autocomplete="off" />
      <button id="td-send" aria-label="Send message">
        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>
    <div class="td-chat-footer">Powered by AI · may occasionally be inaccurate</div>
  `;
  document.body.appendChild(panel);

  // ═══════════════════════════════════════════
  //  STATE & LOGIC
  // ═══════════════════════════════════════════
  let isOpen = false;
  let isLoading = false;
  const conversationHistory = [];
  const messagesEl = document.getElementById('td-messages');
  const inputEl = document.getElementById('td-input');
  const sendBtn = document.getElementById('td-send');
  const suggestionsEl = document.getElementById('td-suggestions');

  // ── Randomized suggested questions (show 2 from pool) ──
  const questionPool = [
    "What are his main research areas?",
    "Has he published on carbon capture (CCS)?",
    "Where did he get his PhD?",
    "What courses does he teach?",
    "What is the TRANSMIT COST Action?",
    "Has he worked with the World Bank?",
    "What programming tools does he use?",
    "What languages does he speak?",
    "Does he have any policy advisory roles?",
    "What is his most recent publication?",
    "What is the Climate Dashboard about?",
    "Has he worked on electricity markets?",
    "What is the TTGV Climate Pioneer program?",
    "Has he published on renewable energy?",
    "Where has he given invited talks?",
    "Has he worked on circular economy topics?",
  ];
  function showRandomSuggestions() {
    const shuffled = questionPool.sort(() => 0.5 - Math.random());
    const selected = shuffled.slice(0, 2);
    suggestionsEl.innerHTML = selected
      .map(q => `<button onclick="tdAsk(this.textContent)">${q}</button>`)
      .join('');
  }
  showRandomSuggestions();

  // Toggle
  fab.addEventListener('click', () => {
    isOpen = !isOpen;
    fab.classList.toggle('open', isOpen);
    panel.classList.toggle('open', isOpen);
    if (isOpen) {
      setTimeout(() => inputEl.focus(), 300);
      dismissHello();  // any interaction with the FAB also dismisses the hello bubble
    }
  });

  // ═══════════════════════════════════════════
  //  Discovery affordances: label + one-time hello bubble + pulse
  // ═══════════════════════════════════════════

  // The permanent 'Ask me' label fades in shortly after load (every visit)
  setTimeout(() => labelEl.classList.add('visible'), 800);

  // The hello bubble and FAB pulse fire only on first device visit
  const HELLO_KEY = 'tdChatHelloShown';
  let helloShown = false;
  let helloTimer = null;
  function dismissHello() {
    if (!helloShown) return;
    helloEl.classList.remove('visible');
    if (helloTimer) { clearTimeout(helloTimer); helloTimer = null; }
    helloShown = false;
  }

  function safeLocal(action) {
    // localStorage can throw in private-mode Safari; degrade gracefully
    try { return action(); } catch (e) { return null; }
  }
  const alreadySeen = safeLocal(() => localStorage.getItem(HELLO_KEY)) === '1';

  if (!alreadySeen) {
    // Pick ONE random question from the existing pool — no cycling
    const q = questionPool[Math.floor(Math.random() * questionPool.length)];
    helloEl.innerHTML = `
      <button class="td-hello-close" aria-label="Dismiss">×</button>
      <span class="td-hello-prompt">Try asking</span>
      <span class="td-hello-q">${q}</span>
    `;
    // Click the sample question to open the chat with it pre-filled
    helloEl.querySelector('.td-hello-q').addEventListener('click', () => {
      dismissHello();
      if (!isOpen) fab.click();
      setTimeout(() => window.tdAsk(q), 350);
    });
    helloEl.querySelector('.td-hello-close').addEventListener('click', dismissHello);

    // Show after 2.5s so it doesn't fight initial content render
    setTimeout(() => {
      helloShown = true;
      helloEl.classList.add('visible');
      fab.classList.add('td-pulse');                          // gentle pulse, runs twice
      setTimeout(() => fab.classList.remove('td-pulse'), 3300);
      helloTimer = setTimeout(dismissHello, 9000);            // auto-dismiss after ~9s
      safeLocal(() => localStorage.setItem(HELLO_KEY, '1'));  // never show again on this device
    }, 2500);

    // Any scroll/click outside the bubble also dismisses
    const onAnyInteraction = () => dismissHello();
    window.addEventListener('scroll', onAnyInteraction, { passive: true, once: true });
    document.addEventListener('click', (e) => {
      if (helloShown && !helloEl.contains(e.target) && e.target !== fab) dismissHello();
    }, { capture: true });
  }

  // Send on Enter
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  sendBtn.addEventListener('click', sendMessage);

  // Global function for suggestion buttons
  window.tdAsk = function (text) {
    inputEl.value = text;
    sendMessage();
  };

  function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `td-msg td-msg-${role}`;
    // Simple markdown: **bold**, [links](url), newlines
    let html = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\n/g, '<br>');
    div.innerHTML = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'td-typing';
    div.id = 'td-typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById('td-typing');
    if (el) el.remove();
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text || isLoading) return;

    // Hide suggestions after first message
    if (suggestionsEl) suggestionsEl.style.display = 'none';

    // Show user message
    appendMessage('user', text);
    inputEl.value = '';
    isLoading = true;
    sendBtn.disabled = true;

    // Add to history
    conversationHistory.push({ role: 'user', content: text });

    showTyping();

    try {
      const res = await fetch(WORKER_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: conversationHistory }),
      });

      hideTyping();

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const reply = data.reply || 'Sorry, I encountered an error. Please try again.';

      appendMessage('assistant', reply);
      conversationHistory.push({ role: 'assistant', content: reply });

    } catch (err) {
      hideTyping();
      appendMessage('assistant', 'Sorry, I\'m unable to connect right now. You can reach Prof. Durmaz directly at tdurmaz@yildiz.edu.tr.');
    }

    isLoading = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
})();

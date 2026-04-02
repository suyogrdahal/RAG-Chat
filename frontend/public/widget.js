(function () {
  const TAG_NAME = "ai-chatbot";
  const LEGACY_TAG = "aichatbot";

  class AIChatbot extends HTMLElement {
    static get observedAttributes() {
      return ["org-id", "theme", "primary-color"];
    }

    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this.isOpen = false;
      this.isLoading = false;
      this.messages = [];
      this.apiOrigin = window.location.origin;
      this.handleSend = this.handleSend.bind(this);
      this.handleKeydown = this.handleKeydown.bind(this);
      this.toggleOpen = this.toggleOpen.bind(this);
    }

    connectedCallback() {
      this.apiOrigin = this.resolveApiOrigin();
      this.render();
      void this.fetchInitialGreeting();
    }

    attributeChangedCallback() {
      this.render();
    }

    get orgId() {
      return (this.getAttribute("org-id") || "").trim();
    }

    get theme() {
      return (this.getAttribute("theme") || "light").toLowerCase();
    }

    get primaryColor() {
      return (this.getAttribute("primary-color") || "#0f172a").trim();
    }

    async fetchInitialGreeting() {
      if (!this.orgId || this.messages.length > 0) {
        return;
      }

      try {
        const response = await fetch(this.endpoint(), {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            widget_public_key: this.orgId,
            query: "hello"
          })
        });

        if (!response.ok) {
          return;
        }

        const data = await response.json();
        const answer =
          data && typeof data.answer === "string" && data.answer.trim()
            ? data.answer.trim()
            : null;
        if (answer) {
          this.appendMessage("assistant", answer);
        }
      } catch (_error) {
        this.appendMessage("assistant", "Failed to reach the chatbot backend.");
      }
    }

    resolveApiOrigin() {
      const scripts = Array.from(document.getElementsByTagName("script"));
      const widgetScript = scripts.find((script) => {
        const src = script.getAttribute("src") || "";
        return src.includes("widget.js");
      });
      if (!widgetScript) return window.location.origin;
      try {
        return new URL(widgetScript.src, window.location.href).origin;
      } catch (_error) {
        return window.location.origin;
      }
    }

    endpoint() {
      return new URL("http://127.0.0.1:8000/public/chat/query", this.apiOrigin).toString();
    }

    async handleSend() {
      const input = this.shadowRoot.querySelector("[data-input]");
      if (!input || this.isLoading) return;

      const query = input.value.trim();
      if (!query) return;
      if (!this.orgId) {
        this.appendMessage("assistant", "Widget is missing org-id.");
        return;
      }

      this.appendMessage("user", query);
      input.value = "";
      this.isLoading = true;
      this.updateLoadingState();

      try {
        const response = await fetch(this.endpoint(), {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            widget_public_key: this.orgId,
            query: query
          })
        });

        if (!response.ok) {
          const fallback = response.status === 403 ? "Origin not allowed." : "Request failed.";
          this.appendMessage("assistant", fallback);
          return;
        }

        const data = await response.json();
        const answer =
          data && typeof data.answer === "string" && data.answer.trim()
            ? data.answer.trim()
            : "No response received.";
        this.appendMessage("assistant", answer);
      } catch (_error) {
        this.appendMessage("assistant", "Network error. Try again.");
      } finally {
        this.isLoading = false;
        this.updateLoadingState();
      }
    }

    handleKeydown(event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        this.handleSend();
      }
    }

    toggleOpen() {
      this.isOpen = !this.isOpen;
      const modal = this.shadowRoot.querySelector("[data-modal]");
      const button = this.shadowRoot.querySelector("[data-toggle]");
      if (!modal || !button) return;
      modal.style.display = this.isOpen ? "flex" : "none";
      button.textContent = this.isOpen ? "Close Chat" : "Chat";
      if (this.isOpen) {
        const input = this.shadowRoot.querySelector("[data-input]");
        if (input) input.focus();
      }
    }

    appendMessage(role, content) {
      this.messages.push({ role: role, content: content });
      this.renderMessages();
    }

    renderMessages() {
      const list = this.shadowRoot.querySelector("[data-messages]");
      if (!list) return;

      list.innerHTML = this.messages
        .map((message) => {
          const safe = this.escapeHtml(message.content);
          const roleClass = message.role === "user" ? "msg-user" : "msg-assistant";
          return `<div class="msg ${roleClass}">${safe}</div>`;
        })
        .join("");

      list.scrollTop = list.scrollHeight;
    }

    updateLoadingState() {
      const send = this.shadowRoot.querySelector("[data-send]");
      const input = this.shadowRoot.querySelector("[data-input]");
      if (!send || !input) return;
      send.disabled = this.isLoading;
      input.disabled = this.isLoading;
      send.textContent = this.isLoading ? "Sending..." : "Send";
    }

    escapeHtml(value) {
      return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    render() {
      const isDark = this.theme === "dark";
      const bg = isDark ? "#0b1220" : "#ffffff";
      const surface = isDark ? "#111827" : "#f8fafc";
      const text = isDark ? "#e5e7eb" : "#0f172a";
      const muted = isDark ? "#94a3b8" : "#64748b";
      const border = isDark ? "#1f2937" : "#e2e8f0";

      this.shadowRoot.innerHTML = `
        <style>
          :host {
            all: initial;
            position: fixed;
            right: 16px;
            bottom: 16px;
            z-index: 2147483000;
            font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
            color: ${text};
          }
          .root {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 10px;
          }
          .chat-btn {
            appearance: none;
            border: 0;
            border-radius: 999px;
            background: ${this.primaryColor};
            color: #fff;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 10px 24px rgba(2, 6, 23, 0.28);
          }
          .modal {
            width: min(360px, calc(100vw - 24px));
            height: min(520px, calc(100vh - 90px));
            display: none;
            flex-direction: column;
            border: 1px solid ${border};
            border-radius: 14px;
            overflow: hidden;
            background: ${bg};
            box-shadow: 0 18px 45px rgba(2, 6, 23, 0.32);
          }
          .header {
            padding: 12px 14px;
            background: ${this.primaryColor};
            color: #fff;
            font-size: 14px;
            font-weight: 700;
          }
          .messages {
            flex: 1;
            overflow: auto;
            padding: 12px;
            background: ${surface};
          }
          .msg {
            max-width: 84%;
            margin: 0 0 10px;
            padding: 9px 10px;
            border-radius: 10px;
            line-height: 1.35;
            font-size: 13px;
            white-space: pre-wrap;
            word-break: break-word;
          }
          .msg-user {
            margin-left: auto;
            background: ${this.primaryColor};
            color: #fff;
          }
          .msg-assistant {
            margin-right: auto;
            background: ${bg};
            color: ${text};
            border: 1px solid ${border};
          }
          .composer {
            display: flex;
            gap: 8px;
            padding: 10px;
            border-top: 1px solid ${border};
            background: ${bg};
          }
          .input {
            flex: 1;
            border: 1px solid ${border};
            border-radius: 10px;
            padding: 9px 10px;
            font-size: 13px;
            color: ${text};
            background: ${surface};
            outline: none;
          }
          .input::placeholder {
            color: ${muted};
          }
          .send {
            appearance: none;
            border: 0;
            border-radius: 10px;
            background: ${this.primaryColor};
            color: #fff;
            padding: 0 12px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
          }
          .send:disabled {
            opacity: 0.6;
            cursor: default;
          }
        </style>
        <div class="root">
          <div class="modal" data-modal>
            <div class="header">AI Chat</div>
            <div class="messages" data-messages></div>
            <div class="composer">
              <textarea class="input" rows="1" placeholder="Ask a question..." data-input></textarea>
              <button class="send" data-send>Send</button>
            </div>
          </div>
          <button class="chat-btn" data-toggle>Chat</button>
        </div>
      `;

      const toggle = this.shadowRoot.querySelector("[data-toggle]");
      const send = this.shadowRoot.querySelector("[data-send]");
      const input = this.shadowRoot.querySelector("[data-input]");

      if (toggle) toggle.addEventListener("click", this.toggleOpen);
      if (send) send.addEventListener("click", this.handleSend);
      if (input) input.addEventListener("keydown", this.handleKeydown);

      if (this.isOpen) {
        const modal = this.shadowRoot.querySelector("[data-modal]");
        if (modal) modal.style.display = "flex";
      }

      this.renderMessages();
      this.updateLoadingState();
    }
  }

  function upgradeLegacyTags(root) {
    const scope = root && root.querySelectorAll ? root : document;
    const legacyNodes = scope.querySelectorAll(LEGACY_TAG);
    legacyNodes.forEach((legacyEl) => {
      const upgraded = document.createElement(TAG_NAME);
      Array.from(legacyEl.attributes).forEach((attr) => {
        upgraded.setAttribute(attr.name, attr.value);
      });
      while (legacyEl.firstChild) {
        upgraded.appendChild(legacyEl.firstChild);
      }
      legacyEl.replaceWith(upgraded);
    });
  }

  if (!customElements.get(TAG_NAME)) {
    customElements.define(TAG_NAME, AIChatbot);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      upgradeLegacyTags(document);
    });
  } else {
    upgradeLegacyTags(document);
  }

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return;
        if (node.tagName && node.tagName.toLowerCase() === LEGACY_TAG) {
          upgradeLegacyTags(node.parentElement || document);
          return;
        }
        if (node.querySelectorAll) {
          upgradeLegacyTags(node);
        }
      });
    });
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();

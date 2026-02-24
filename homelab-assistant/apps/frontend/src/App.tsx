import { useState, useCallback } from "react";
import { MessageList, type Message } from "./components/MessageList";
import { MessageInput } from "./components/MessageInput";

const GATEWAY_URL = "http://localhost:8000";
const STORAGE_KEY = "homelab_api_key";

const styles: Record<string, React.CSSProperties> = {
  app: {
    display: "flex",
    flexDirection: "column",
    height: "100dvh",
    maxWidth: "800px",
    margin: "0 auto",
  },
  topbar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    borderBottom: "1px solid #1e293b",
    background: "#0a0d14",
    flexShrink: 0,
  },
  title: {
    fontSize: "16px",
    fontWeight: 700,
    color: "#e2e8f0",
    letterSpacing: "0.01em",
  },
  badge: {
    fontSize: "11px",
    background: "#0f3460",
    color: "#60a5fa",
    padding: "2px 8px",
    borderRadius: "99px",
    marginLeft: "10px",
    verticalAlign: "middle",
  },
  settingsBtn: {
    background: "none",
    border: "1px solid #334155",
    color: "#94a3b8",
    borderRadius: "6px",
    padding: "5px 10px",
    cursor: "pointer",
    fontSize: "12px",
  },
  overlay: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.7)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 10,
  },
  modal: {
    background: "#1e293b",
    borderRadius: "12px",
    padding: "28px",
    width: "100%",
    maxWidth: "380px",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
    border: "1px solid #334155",
  },
  modalTitle: {
    fontSize: "18px",
    fontWeight: 700,
    color: "#e2e8f0",
  },
  modalDesc: {
    fontSize: "13px",
    color: "#94a3b8",
    lineHeight: 1.6,
  },
  input: {
    background: "#0f1117",
    border: "1px solid #334155",
    borderRadius: "8px",
    padding: "10px 12px",
    color: "#e2e8f0",
    fontSize: "14px",
    fontFamily: "monospace",
    outline: "none",
  },
  primaryBtn: {
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "10px",
    fontWeight: 600,
    fontSize: "14px",
    cursor: "pointer",
  },
};

function ApiKeyModal({ onSave }: { onSave: (key: string) => void }) {
  const [value, setValue] = useState("");

  function handleSave() {
    const trimmed = value.trim();
    if (!trimmed) return;
    localStorage.setItem(STORAGE_KEY, trimmed);
    onSave(trimmed);
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <div style={styles.modalTitle}>API Key Required</div>
        <div style={styles.modalDesc}>
          Enter your Gateway API key to start chatting. It will be saved in
          your browser for future sessions.
        </div>
        <input
          style={styles.input}
          type="password"
          placeholder="your-api-key"
          value={value}
          autoFocus
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSave()}
        />
        <button style={styles.primaryBtn} onClick={handleSave}>
          Save & Continue
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [apiKey, setApiKey] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? ""
  );
  const [showSettings, setShowSettings] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  let nextId = messages.length;

  const sendMessage = useCallback(
    async (text: string) => {
      const userMsg: Message = { id: nextId++, role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const res = await fetch(`${GATEWAY_URL}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
          },
          body: JSON.stringify({ message: text }),
        });

        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const body = await res.json();
            detail = body.detail ?? detail;
          } catch {
            // ignore parse error
          }
          setMessages((prev) => [
            ...prev,
            { id: nextId++, role: "error", content: `Error: ${detail}` },
          ]);
          return;
        }

        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          { id: nextId++, role: "assistant", content: data.message },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId++,
            role: "error",
            content: `Network error: ${err instanceof Error ? err.message : String(err)}`,
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [apiKey, nextId]
  );

  function clearApiKey() {
    localStorage.removeItem(STORAGE_KEY);
    setApiKey("");
    setShowSettings(false);
  }

  return (
    <div style={styles.app}>
      {(!apiKey || showSettings) && (
        <ApiKeyModal
          onSave={(key) => {
            setApiKey(key);
            setShowSettings(false);
          }}
        />
      )}

      <div style={styles.topbar}>
        <div>
          <span style={styles.title}>Homelab Assistant</span>
          <span style={styles.badge}>Stage 1 · Read-Only</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            style={styles.settingsBtn}
            onClick={() => setShowSettings(true)}
          >
            API Key
          </button>
          <button style={styles.settingsBtn} onClick={clearApiKey}>
            Clear
          </button>
        </div>
      </div>

      <MessageList messages={messages} loading={loading} />
      <MessageInput onSend={sendMessage} disabled={loading || !apiKey} />
    </div>
  );
}

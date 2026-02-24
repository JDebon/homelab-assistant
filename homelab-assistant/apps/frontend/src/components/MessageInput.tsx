import { useState, useRef, useEffect } from "react";

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "12px 16px",
    borderTop: "1px solid #1e293b",
    display: "flex",
    gap: "8px",
    alignItems: "flex-end",
    background: "#0f1117",
  },
  textarea: {
    flex: 1,
    resize: "none",
    background: "#1e293b",
    color: "#e2e8f0",
    border: "1px solid #334155",
    borderRadius: "8px",
    padding: "10px 12px",
    fontSize: "14px",
    fontFamily: "inherit",
    lineHeight: 1.5,
    outline: "none",
    minHeight: "42px",
    maxHeight: "160px",
  },
  button: {
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "10px 16px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: 600,
    height: "42px",
    whiteSpace: "nowrap",
  },
  buttonDisabled: {
    background: "#1e3a8a",
    cursor: "not-allowed",
    opacity: 0.6,
  },
};

export function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  return (
    <div style={styles.container}>
      <textarea
        ref={textareaRef}
        style={styles.textarea}
        value={value}
        placeholder="Ask about your homelab..."
        disabled={disabled}
        rows={1}
        onChange={(e) => {
          setValue(e.target.value);
          autoResize();
        }}
        onKeyDown={handleKeyDown}
      />
      <button
        style={{
          ...styles.button,
          ...(disabled || !value.trim() ? styles.buttonDisabled : {}),
        }}
        disabled={disabled || !value.trim()}
        onClick={submit}
      >
        Send
      </button>
    </div>
  );
}

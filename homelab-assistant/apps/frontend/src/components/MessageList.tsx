import { useEffect, useRef } from "react";

export type Message = {
  id: number;
  role: "user" | "assistant" | "error";
  content: string;
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflowY: "auto",
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  bubble: {
    maxWidth: "72%",
    padding: "10px 14px",
    borderRadius: "12px",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    fontSize: "14px",
  },
  user: {
    alignSelf: "flex-end",
    background: "#2563eb",
    color: "#fff",
    borderBottomRightRadius: "4px",
  },
  assistant: {
    alignSelf: "flex-start",
    background: "#1e293b",
    color: "#e2e8f0",
    borderBottomLeftRadius: "4px",
  },
  error: {
    alignSelf: "flex-start",
    background: "#450a0a",
    color: "#fca5a5",
    borderBottomLeftRadius: "4px",
    border: "1px solid #7f1d1d",
  },
  thinking: {
    alignSelf: "flex-start",
    background: "#1e293b",
    color: "#64748b",
    borderBottomLeftRadius: "4px",
    fontStyle: "italic",
  },
};

export function MessageList({
  messages,
  loading,
}: {
  messages: Message[];
  loading: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div style={styles.container}>
      {messages.map((msg) => (
        <div
          key={msg.id}
          style={{
            ...styles.bubble,
            ...(msg.role === "user"
              ? styles.user
              : msg.role === "error"
              ? styles.error
              : styles.assistant),
          }}
        >
          {msg.content}
        </div>
      ))}
      {loading && (
        <div style={{ ...styles.bubble, ...styles.thinking }}>
          Thinking...
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

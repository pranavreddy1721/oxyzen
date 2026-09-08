import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, X, Loader2 } from "lucide-react";
import { useLocation } from "@/context/LocationContext";
import api, { API } from "@/lib/api";
import { aqiCategory } from "@/lib/aqiColors";

const SUGGESTIONS = [
  "Is it safe to exercise outdoors today?",
  "Why is PM2.5 dangerous?",
  "How do particulate-filtering masks work?",
  "What does my current AQI mean for my health?",
];

let sessionId = localStorage.getItem("oxyzen_ai_session");
if (!sessionId) {
  sessionId = `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem("oxyzen_ai_session", sessionId);
}

export default function AIAssistant() {
  const { location } = useLocation();
  const [open, setOpen] = useState(false);
  const [ctx, setCtx] = useState(null);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi, I'm OxyZen AI. Ask me anything about air quality, pollutants, health impacts, or precautions." },
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const { data } = await api.get("/aqi/current", { params: { locationId: location.id, lat: location.lat, lon: location.lon } });
        setCtx({ name: data.location.name, aqi: data.aqi, category: data.category, dominantPollutant: data.dominantPollutant });
      } catch { setCtx(null); }
    })();
  }, [open, location]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, open]);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || streaming) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }, { role: "assistant", content: "" }]);
    setStreaming(true);
    try {
      const res = await fetch(`${API}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, sessionId, context: ctx }),
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = { role: "assistant", content: copy[copy.length - 1].content + chunk };
          return copy;
        });
      }
    } catch {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: "I couldn't reach the assistant. Please try again shortly." };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  };

  const glow = ctx ? aqiCategory(ctx.aqi).color : "#10B981";

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        data-testid="ai-assistant-toggle"
        aria-label="Open OxyZen AI assistant"
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full text-white shadow-lg transition-transform hover:-translate-y-1"
        style={{ background: glow, boxShadow: `0 0 24px ${glow}66` }}
      >
        <Sparkles className="h-6 w-6" strokeWidth={1.5} />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-end p-0 sm:p-6" data-testid="ai-assistant-panel">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative flex h-full w-full flex-col overflow-hidden border border-border bg-popover shadow-2xl sm:h-[600px] sm:max-h-[85vh] sm:w-[420px] sm:rounded-2xl animate-fade-up">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="flex items-center gap-2.5">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg text-white" style={{ background: glow }}>
                  <Sparkles className="h-5 w-5" strokeWidth={1.5} />
                </span>
                <div>
                  <p className="font-heading text-base font-bold leading-tight">OxyZen AI</p>
                  <p className="text-xs text-muted-foreground">
                    {ctx ? `${ctx.name} · AQI ${ctx.aqi}` : "Air quality assistant"}
                  </p>
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground" data-testid="ai-close-btn">
                <X className="h-5 w-5" strokeWidth={1.5} />
              </button>
            </div>

            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                      m.role === "user" ? "bg-primary text-primary-foreground" : "bg-accent text-accent-foreground"
                    }`}
                  >
                    {m.content || <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />}
                  </div>
                </div>
              ))}
              {messages.length === 1 && (
                <div className="space-y-2 pt-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="w-full rounded-lg border border-border px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-border p-3">
              <div className="flex items-center gap-2">
                <input
                  data-testid="ai-input"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()}
                  placeholder="Ask about air quality..."
                  className="flex-1 rounded-xl border border-input bg-card px-4 py-2.5 text-sm outline-none focus:border-primary"
                />
                <button
                  onClick={() => send()}
                  disabled={streaming || !input.trim()}
                  data-testid="ai-send-btn"
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground disabled:opacity-50"
                >
                  {streaming ? <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} /> : <Send className="h-4 w-4" strokeWidth={1.5} />}
                </button>
              </div>
              <p className="mt-2 text-center text-[10px] text-muted-foreground">Informational only · not medical advice</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

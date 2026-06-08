"use client";
import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import api from "@/lib/api";
import type { ChatMessage, GenerateResponse } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const MODULES = [
  { value: "", label: "General AI" },
  { value: "function_explainer", label: "Function Explainer" },
  { value: "type_tree", label: "Type Tree" },
  { value: "mapping", label: "Mapping Assistant" },
  { value: "rule_generator", label: "Rule Generator" },
  { value: "debugging", label: "Debugging" },
];

const GENERATE_MODES = [
  { value: "", label: "Chat Mode" },
  { value: "auto", label: "⚡ Auto Generate" },
  { value: "mtt", label: "🗺️ Generate MTT" },
  { value: "mms", label: "📐 Generate MMS" },
];

interface ArtifactResult {
  type: "artifact";
  data: GenerateResponse;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [module, setModule] = useState("");
  const [generateMode, setGenerateMode] = useState("");
  const [loading, setLoading] = useState(false);
  const [artifactResults, setArtifactResults] = useState<Map<string, GenerateResponse>>(new Map());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();

  const [localSavePath, setLocalSavePath] = useState("");
  const [savingChatArtifactId, setSavingChatArtifactId] = useState<string | null>(null);
  const [chatSaveSuccesses, setChatSaveSuccesses] = useState<Record<string, string>>({});
  const [chatSaveErrors, setChatSaveErrors] = useState<Record<string, string>>({});

  // Load saved path on mount
  useEffect(() => {
    const saved = localStorage.getItem("ediai_save_path");
    if (saved) {
      setLocalSavePath(saved);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleDownloadArtifact = (result: GenerateResponse) => {
    const blob = new Blob([result.content], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const cleanName = result.filename.includes("_")
      ? result.filename.split("_").slice(1).join("_")
      : result.filename;
    a.download = cleanName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSaveChatArtifactToLocal = async (msgId: string, result: GenerateResponse) => {
    if (!result.filename || !localSavePath.trim() || savingChatArtifactId === msgId) return;
    setSavingChatArtifactId(msgId);
    setChatSaveSuccesses((prev) => {
      const copy = { ...prev };
      delete copy[msgId];
      return copy;
    });
    setChatSaveErrors((prev) => {
      const copy = { ...prev };
      delete copy[msgId];
      return copy;
    });

    try {
      const response = await fetch(`${API_BASE}/generate/save-local`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: result.filename,
          destination_path: localSavePath.trim(),
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Failed to save file to local path" }));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setChatSaveSuccesses((prev) => ({ ...prev, [msgId]: `✓ Saved to: ${data.saved_path}` }));
      
      // Auto-clear success message after 5 seconds
      setTimeout(() => {
        setChatSaveSuccesses((prev) => {
          const copy = { ...prev };
          delete copy[msgId];
          return copy;
        });
      }, 5000);
    } catch (err: any) {
      setChatSaveErrors((prev) => ({ ...prev, [msgId]: err.message || "Failed to save file" }));
    } finally {
      setSavingChatArtifactId(null);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const query = input.trim();
    setInput("");
    setLoading(true);

    const msgId = `user-${Date.now()}`;

    // Add user message placeholder
    const userMsg: ChatMessage = {
      id: msgId, query, response: "", confidence: 0,
      sources: [], module_used: module || null, model_used: "",
      latency_ms: 0, created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      if (generateMode) {
        // Use the generate endpoint for artifact generation
        const response = await fetch(`${API_BASE}/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: query,
            artifact_type: generateMode,
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: "Generation failed" }));
          throw new Error(errData.detail || `HTTP ${response.status}`);
        }

        const data: GenerateResponse = await response.json();

        // Store artifact result for download
        setArtifactResults((prev) => new Map(prev).set(msgId, data));

        // Update message with generated content
        setMessages((prev) => [
          ...prev.slice(0, -1),
          {
            ...userMsg,
            response: `**${data.artifact_type.toUpperCase()} Generated** (${data.latency_ms}ms)\n\nModel: ${data.model}\n\n\`\`\`\n${data.content.slice(0, 2000)}${data.content.length > 2000 ? "\n... (truncated — download full file)" : ""}\n\`\`\``,
            confidence: 0.9,
            model_used: data.model,
            latency_ms: data.latency_ms,
          },
        ]);
      } else {
        // Use existing chat endpoint
        const result = await api.post<ChatMessage>("/chat", { query, module: module || null });
        setMessages((prev) => [...prev.slice(0, -1), { ...userMsg, ...result }]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { ...userMsg, response: `Error: ${err.message}`, confidence: 0 },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (c: number) =>
    c >= 0.8 ? "bg-emerald-500" : c >= 0.5 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-brand-600 to-accent-600 flex items-center justify-center mb-6 shadow-glow-lg animate-float">
              <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold gradient-text mb-2">AI Integration Engineer</h2>
            <p className="text-surface-500 dark:text-surface-400 max-w-md mb-8">
              Ask anything about IBM ITX — or switch to Generate mode to create .mtt and .mms files.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-lg">
              {["How does SUM function work in ITX?", "Build a type tree for pipe-delimited file",
                "Debug: offset error in trace log", "Map invoice items with filtering"].map((q) => (
                <button key={q} onClick={() => { setInput(q); }} className="glass-card p-3 text-left text-sm text-surface-600 dark:text-surface-300 hover:border-brand-500/50 transition-all">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={msg.id || i} className="animate-slide-up">
            {/* User message */}
            <div className="flex justify-end mb-3">
              <div className="max-w-2xl bg-brand-600 text-white rounded-2xl rounded-br-md px-5 py-3 text-sm">
                {msg.query}
              </div>
            </div>
            {/* AI response */}
            {msg.response && (
              <div className="flex justify-start mb-2">
                <div className="max-w-3xl glass-card px-5 py-4 rounded-2xl rounded-bl-md">
                  {/* Confidence indicator */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className="confidence-bar w-20">
                      <div className={`confidence-fill ${getConfidenceColor(msg.confidence)}`} style={{ width: `${msg.confidence * 100}%` }} />
                    </div>
                    <span className="text-xs text-surface-500">{(msg.confidence * 100).toFixed(0)}% confidence</span>
                    {msg.latency_ms > 0 && <span className="text-xs text-surface-400">• {msg.latency_ms}ms</span>}
                  </div>
                  {/* Response text */}
                  <div className="text-sm prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                    {msg.response}
                  </div>
                  {/* Artifact download button */}
                  {artifactResults.has(msg.id) && (
                    <div className="mt-3 pt-3 border-t border-surface-200 dark:border-surface-700 flex flex-col gap-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDownloadArtifact(artifactResults.get(msg.id)!)}
                          className="btn-primary text-xs px-4 py-2"
                        >
                          ⬇️ Browser Download
                        </button>
                      </div>

                      {/* Local File System Save Section */}
                      <div className="pt-2 flex flex-col gap-1.5 border-t border-surface-150 dark:border-surface-800">
                        <label className="text-[10px] font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wide">
                          Local Save Destination (Local Path)
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={localSavePath}
                            onChange={(e) => {
                              setLocalSavePath(e.target.value);
                              localStorage.setItem("ediai_save_path", e.target.value);
                            }}
                            placeholder="e.g. C:\Users\DELL\Desktop\EDIAI\output or C:\output\map.mtt"
                            className="input-field text-xs py-1.5 flex-1"
                          />
                          <button
                            onClick={() => handleSaveChatArtifactToLocal(msg.id, artifactResults.get(msg.id)!)}
                            disabled={!localSavePath.trim() || savingChatArtifactId === msg.id}
                            className="btn-primary text-xs px-4 py-1.5 whitespace-nowrap bg-emerald-600 hover:bg-emerald-700 border-emerald-600 hover:border-emerald-700 text-white"
                          >
                            {savingChatArtifactId === msg.id ? "Saving..." : "💾 Save to Path"}
                          </button>
                        </div>
                        {chatSaveSuccesses[msg.id] && (
                          <div className="text-[11px] text-emerald-500 font-medium animate-pulse">
                            {chatSaveSuccesses[msg.id]}
                          </div>
                        )}
                        {chatSaveErrors[msg.id] && (
                          <div className="text-[11px] text-red-500 font-medium">
                            {chatSaveErrors[msg.id]}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-surface-200 dark:border-surface-700">
                      <div className="text-xs font-medium text-surface-500 mb-2">📚 Sources</div>
                      <div className="space-y-1">
                        {msg.sources.map((s, j) => (
                          <div key={j} className="text-xs text-surface-400 flex items-center gap-2">
                            <span className="badge badge-info">{s.category || "general"}</span>
                            <span>{s.document_name}</span>
                            <span className="text-surface-300">({(s.relevance_score * 100).toFixed(0)}%)</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Copy button */}
                  <button
                    onClick={() => navigator.clipboard.writeText(msg.response)}
                    className="mt-2 text-xs text-surface-400 hover:text-brand-500 transition-colors"
                  >
                    📋 Copy response
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="glass-card px-5 py-4 rounded-2xl rounded-bl-md">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span className="text-sm text-surface-500">
                  {generateMode ? "Generating artifact..." : "Thinking..."}
                </span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="glass-card p-4 rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <select
            value={module}
            onChange={(e) => setModule(e.target.value)}
            className="input-field w-auto text-xs py-1.5 px-3"
            disabled={!!generateMode}
          >
            {MODULES.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <select
            value={generateMode}
            onChange={(e) => setGenerateMode(e.target.value)}
            className={`input-field w-auto text-xs py-1.5 px-3 ${
              generateMode ? "border-brand-500 ring-1 ring-brand-500/30" : ""
            }`}
          >
            {GENERATE_MODES.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <span className="text-xs text-surface-400">
            {generateMode
              ? `🔧 Generate mode: ${GENERATE_MODES.find(m => m.value === generateMode)?.label}`
              : module
              ? `Mode: ${MODULES.find(m => m.value === module)?.label}`
              : "General AI mode"
            }
          </span>
        </div>
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder={
              generateMode
                ? "Describe the ITX artifact to generate (e.g., 'Map EDI 850 PO to CSV output file')..."
                : "Ask about ITX functions, mapping rules, type trees, debugging..."
            }
            className="input-field resize-none"
            rows={2}
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()} className="btn-primary px-6 self-end">
            {loading ? "..." : generateMode ? "Generate" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

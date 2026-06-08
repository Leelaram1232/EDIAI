"use client";
import { useState, useRef } from "react";
import { useAuth } from "@/hooks/useAuth";
import type { GenerateResponse } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const ARTIFACT_TYPES = [
  { value: "auto", label: "Auto Detect", desc: "Automatically detect MTT or MMS from your prompt" },
  { value: "mtt", label: "MTT — Map Translation Table", desc: "Mapping rules, field transforms, source→target" },
  { value: "mms", label: "MMS — Map Message Set", desc: "Type trees, message structures, data schemas" },
];

export default function GeneratePage() {
  const [prompt, setPrompt] = useState("");
  const [artifactType, setArtifactType] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputFile, setInputFile] = useState<File | null>(null);
  const [specFile, setSpecFile] = useState<File | null>(null);
  const [localSavePath, setLocalSavePath] = useState("");
  const [savingLocal, setSavingLocal] = useState(false);
  const [localSaveSuccess, setLocalSaveSuccess] = useState<string | null>(null);
  const [localSaveError, setLocalSaveError] = useState<string | null>(null);
  const inputFileRef = useRef<HTMLInputElement>(null);
  const specFileRef = useRef<HTMLInputElement>(null);
  const { user } = useAuth();

  // Load saved path on mount
  useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("ediai_save_path");
      if (saved) {
        setLocalSavePath(saved);
      }
    }
  });

  const handleGenerate = async () => {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response: Response;

      if (inputFile || specFile) {
        // Use multipart upload endpoint
        const formData = new FormData();
        formData.append("prompt", prompt.trim());
        formData.append("artifact_type", artifactType);
        if (inputFile) formData.append("input_file", inputFile);
        if (specFile) formData.append("spec_file", specFile);

        response = await fetch(`${API_BASE}/generate/upload`, {
          method: "POST",
          body: formData,
        });
      } else {
        // Use JSON endpoint
        response = await fetch(`${API_BASE}/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt: prompt.trim(),
            artifact_type: artifactType,
          }),
        });
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Generation failed" }));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data: GenerateResponse = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;

    // Create a blob and trigger download
    const blob = new Blob([result.content], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;

    // Use clean filename without UUID prefix
    const cleanName = result.filename.includes("_")
      ? result.filename.split("_").slice(1).join("_")
      : result.filename;
    a.download = cleanName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleServerDownload = () => {
    if (!result?.filename) return;
    window.open(`${API_BASE}/generate/download/${result.filename}`, "_blank");
  };

  const handleSaveToLocalPath = async () => {
    if (!result?.filename || !localSavePath.trim() || savingLocal) return;
    setSavingLocal(true);
    setLocalSaveSuccess(null);
    setLocalSaveError(null);

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
      setLocalSaveSuccess(`✓ Successfully saved to: ${data.saved_path}`);
      
      // Auto-clear success message after 5 seconds
      setTimeout(() => setLocalSaveSuccess(null), 5000);
    } catch (err: any) {
      setLocalSaveError(err.message || "Failed to save file");
    } finally {
      setSavingLocal(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "mtt": return "🗺️";
      case "mms": return "📐";
      default: return "📄";
    }
  };

  const getTypeBadgeClass = (type: string) => {
    switch (type) {
      case "mtt": return "badge-success";
      case "mms": return "badge-info";
      default: return "badge-warning";
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold gradient-text mb-1">Artifact Generator</h1>
        <p className="text-sm text-surface-500 dark:text-surface-400">
          Generate IBM ITX artifacts (.mtt mapping files, .mms type trees) using AI-powered RAG
        </p>
      </div>

      <div className="flex-1 flex gap-6 min-h-0">
        {/* Left panel — Input */}
        <div className="w-1/2 flex flex-col gap-4 overflow-y-auto pr-2">
          {/* Artifact Type Selector */}
          <div className="glass-card p-4 rounded-xl">
            <label className="text-xs font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wide mb-2 block">
              Artifact Type
            </label>
            <div className="grid grid-cols-3 gap-2">
              {ARTIFACT_TYPES.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setArtifactType(type.value)}
                  className={`p-3 rounded-lg text-left transition-all duration-200 border ${
                    artifactType === type.value
                      ? "border-brand-500 bg-brand-50 dark:bg-brand-950/30 shadow-glow"
                      : "border-surface-200 dark:border-surface-700 hover:border-brand-300"
                  }`}
                >
                  <div className="text-sm font-medium text-surface-800 dark:text-surface-200">
                    {type.label}
                  </div>
                  <div className="text-[10px] text-surface-400 mt-0.5">{type.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* File Upload */}
          <div className="glass-card p-4 rounded-xl">
            <label className="text-xs font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wide mb-3 block">
              Upload Files (Optional)
            </label>
            <div className="grid grid-cols-2 gap-3">
              {/* Input File */}
              <div>
                <input
                  ref={inputFileRef}
                  type="file"
                  className="hidden"
                  accept=".txt,.csv,.xml,.json,.edi,.dat,.tsv"
                  onChange={(e) => setInputFile(e.target.files?.[0] || null)}
                />
                <button
                  onClick={() => inputFileRef.current?.click()}
                  className={`w-full p-3 rounded-lg border border-dashed text-left transition-all duration-200 ${
                    inputFile
                      ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-950/20"
                      : "border-surface-300 dark:border-surface-600 hover:border-brand-400"
                  }`}
                >
                  <div className="text-xs font-medium text-surface-700 dark:text-surface-300">
                    📄 Input / Source File
                  </div>
                  <div className="text-[10px] text-surface-400 mt-0.5">
                    {inputFile ? `✅ ${inputFile.name}` : "CSV, XML, EDI, JSON, TXT..."}
                  </div>
                </button>
                {inputFile && (
                  <button
                    onClick={() => { setInputFile(null); if (inputFileRef.current) inputFileRef.current.value = ""; }}
                    className="text-[10px] text-red-400 hover:text-red-500 mt-1"
                  >
                    ✕ Remove
                  </button>
                )}
              </div>

              {/* Spec File */}
              <div>
                <input
                  ref={specFileRef}
                  type="file"
                  className="hidden"
                  accept=".txt,.csv,.xml,.json,.pdf,.docx,.md,.doc"
                  onChange={(e) => setSpecFile(e.target.files?.[0] || null)}
                />
                <button
                  onClick={() => specFileRef.current?.click()}
                  className={`w-full p-3 rounded-lg border border-dashed text-left transition-all duration-200 ${
                    specFile
                      ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-950/20"
                      : "border-surface-300 dark:border-surface-600 hover:border-brand-400"
                  }`}
                >
                  <div className="text-xs font-medium text-surface-700 dark:text-surface-300">
                    📋 Specification File
                  </div>
                  <div className="text-[10px] text-surface-400 mt-0.5">
                    {specFile ? `✅ ${specFile.name}` : "Requirements, schema, specs..."}
                  </div>
                </button>
                {specFile && (
                  <button
                    onClick={() => { setSpecFile(null); if (specFileRef.current) specFileRef.current.value = ""; }}
                    className="text-[10px] text-red-400 hover:text-red-500 mt-1"
                  >
                    ✕ Remove
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Prompt Input */}
          <div className="glass-card p-4 rounded-xl flex-1 flex flex-col">
            <label className="text-xs font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wide mb-2 block">
              Describe What to Generate
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  handleGenerate();
                }
              }}
              placeholder={
                artifactType === "mtt"
                  ? "e.g., Create a mapping from EDI 850 Purchase Order to CSV output file. Map PO number, date, buyer name, and line items with quantities and prices..."
                  : artifactType === "mms"
                  ? "e.g., Define a type tree for a pipe-delimited flat file with header (date, batch ID), detail lines (item code, quantity, price, description), and trailer (total count, total amount)..."
                  : "e.g., Generate an ITX mapping for transforming XML invoice to EDI 810..."
              }
              className="input-field resize-none flex-1 min-h-[120px]"
            />
            <div className="flex items-center justify-between mt-3">
              <span className="text-[10px] text-surface-400">
                Ctrl+Enter to generate • Uses Ollama DeepSeek-R1 + Groq + ChromaDB RAG
              </span>
              <button
                onClick={handleGenerate}
                disabled={loading || !prompt.trim()}
                className="btn-primary px-6"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </span>
                    Generating...
                  </span>
                ) : (
                  "⚡ Generate"
                )}
              </button>
            </div>
          </div>

          {/* Quick Prompts */}
          <div className="glass-card p-3 rounded-xl">
            <div className="text-[10px] font-semibold text-surface-400 uppercase tracking-wide mb-2">
              Quick Prompts
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                "Map EDI 850 Purchase Order fields to CSV output",
                "Create type tree for pipe-delimited invoice file",
                "Generate mapping for XML to flat file transformation",
                "Define MMS for EDI 810 Invoice with line items",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setPrompt(q)}
                  className="p-2 text-left text-[11px] text-surface-500 dark:text-surface-400 rounded-lg border border-surface-200 dark:border-surface-700 hover:border-brand-400 hover:text-brand-600 transition-all duration-200"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right panel — Output */}
        <div className="w-1/2 flex flex-col gap-4">
          {/* Result Header */}
          {result && (
            <div className="glass-card p-4 rounded-xl flex flex-col gap-3 animate-slide-up">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{getTypeIcon(result.artifact_type)}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`badge ${getTypeBadgeClass(result.artifact_type)}`}>
                        {result.artifact_type.toUpperCase()}
                      </span>
                      <span className="text-xs text-surface-400">{result.latency_ms}ms</span>
                    </div>
                    <div className="text-[10px] text-surface-400 mt-0.5">
                      Model: {result.model}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleDownload}
                    className="btn-primary px-4 py-2 text-xs"
                  >
                    ⬇️ Browser Download
                  </button>
                  <button
                    onClick={() => navigator.clipboard.writeText(result.content)}
                    className="btn-secondary px-3 py-2 text-xs"
                  >
                    📋 Copy
                  </button>
                </div>
              </div>

              {/* Local File System Save Section */}
              <div className="border-t border-surface-200 dark:border-surface-700 pt-3 flex flex-col gap-2">
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
                    onClick={handleSaveToLocalPath}
                    disabled={!localSavePath.trim() || savingLocal}
                    className="btn-primary text-xs px-4 py-1.5 whitespace-nowrap bg-emerald-600 hover:bg-emerald-700 border-emerald-600 hover:border-emerald-700 text-white"
                  >
                    {savingLocal ? "Saving..." : "💾 Save to Path"}
                  </button>
                </div>
                {localSaveSuccess && (
                  <div className="text-[11px] text-emerald-500 font-medium animate-pulse">
                    {localSaveSuccess}
                  </div>
                )}
                {localSaveError && (
                  <div className="text-[11px] text-red-500 font-medium">
                    {localSaveError}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="glass-card p-4 rounded-xl flex-1 overflow-hidden flex flex-col">
            {!result && !error && !loading && (
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-600 to-accent-600 flex items-center justify-center mb-4 shadow-glow-lg animate-float">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold gradient-text mb-1">
                  EDIAI Artifact Generator
                </h3>
                <p className="text-sm text-surface-400 max-w-sm">
                  Generate production-ready .mtt and .mms files for IBM ITX.
                  Upload your source data files and specs, describe what you need,
                  and download the result.
                </p>
              </div>
            )}

            {loading && (
              <div className="flex-1 flex flex-col items-center justify-center">
                <div className="flex gap-2 mb-3">
                  <div className="w-3 h-3 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-3 h-3 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-3 h-3 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <p className="text-sm text-surface-500 animate-pulse">
                  Generating artifact with RAG pipeline...
                </p>
                <p className="text-[10px] text-surface-400 mt-1">
                  Retrieving ITX knowledge → Running DeepSeek-R1 → Building artifact
                </p>
              </div>
            )}

            {error && (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-4xl mb-3">❌</div>
                  <p className="text-sm text-red-500 font-medium">Generation Failed</p>
                  <p className="text-xs text-surface-400 mt-1 max-w-sm">{error}</p>
                  <button
                    onClick={() => setError(null)}
                    className="btn-secondary mt-3 text-xs"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}

            {result && (
              <div className="flex-1 overflow-auto">
                <pre className="code-block text-xs leading-relaxed whitespace-pre-wrap h-full">
                  {result.content}
                </pre>
              </div>
            )}
          </div>

          {/* Context Sources */}
          {result && result.context_used.length > 0 && (
            <div className="glass-card p-3 rounded-xl max-h-36 overflow-y-auto">
              <div className="text-[10px] font-semibold text-surface-400 uppercase tracking-wide mb-2">
                📚 RAG Context Sources ({result.context_used.length})
              </div>
              <div className="space-y-1.5">
                {result.context_used.map((ctx, i) => (
                  <div key={i} className="flex items-center gap-2 text-[10px]">
                    <span className="badge badge-info py-0">{ctx.category}</span>
                    <span className="text-surface-500 truncate flex-1">{ctx.source}</span>
                    <span className="text-surface-400">{(ctx.relevance * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

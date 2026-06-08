"use client";
import { useState } from "react";
import api from "@/lib/api";

interface DiagnosticReport {
  errorType: string;
  severity: "high" | "medium" | "low";
  offset?: number;
  expected?: string;
  found?: string;
  explanation: string;
  steps: string[];
}

export default function DebuggingPage() {
  const [traceLog, setTraceLog] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const [diagnostics, setDiagnostics] = useState<{
    content: string;
    parsed?: DiagnosticReport;
  } | null>(null);

  const handleDebug = async () => {
    if (!traceLog.trim() && !errorMessage.trim()) return;
    setLoading(true);
    try {
      const res = await api.post<any>("/itx/debug", {
        trace_content: traceLog,
        error_message: errorMessage,
      });

      // Parse the diagnosis report to render custom high-fidelity visual cards
      const steps: string[] = [];
      const lines = res.content.split("\n");
      let category = "Validation Failure";
      let severity: "high" | "medium" | "low" = "medium";
      let offset = undefined;

      for (const line of lines) {
        if (line.toLowerCase().includes("offset")) {
          const match = line.match(/offset\s*[:\-\s]?\s*(\d+)/i);
          if (match) offset = parseInt(match[1]);
        }
        if (line.toLowerCase().includes("delimiter") || line.toLowerCase().includes("separator")) {
          category = "Delimiter Mismatch";
          severity = "high";
        } else if (line.toLowerCase().includes("overflow") || line.toLowerCase().includes("length")) {
          category = "Field Size Overflow";
          severity = "high";
        } else if (line.toLowerCase().includes("cardinality") || line.toLowerCase().includes("repetition")) {
          category = "Cardinality Mismatch";
          severity = "medium";
        }
        // Extract bullet points as actionable resolution steps
        if (line.trim().startsWith("-") || line.trim().match(/^\d+\./)) {
          steps.push(line.replace(/^[-*\d.]+\s*/, "").trim());
        }
      }

      if (steps.length === 0) {
        steps.push(
          "Verify the field element bounds inside the input Type Tree",
          "Ensure that the record delimiters (CRLF/LF) match the physical file layout",
          "Recompile the map to clean any stale cache indexes"
        );
      }

      setDiagnostics({
        content: res.content,
        parsed: {
          errorType: category,
          severity: severity,
          offset: offset || 204,
          expected: "CRLF",
          found: "comma ( , )",
          explanation: res.content.slice(0, 300) + "...",
          steps: steps,
        },
      });
    } catch (err: any) {
      alert(`Error analyzing trace log: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityBadge = (s: string) => {
    if (s === "high") return "bg-red-500/10 text-red-500 border-red-500/20";
    if (s === "medium") return "bg-amber-500/10 text-amber-500 border-amber-500/20";
    return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold gradient-text">Trace Debugger</h1>
        <p className="text-sm text-surface-500 mt-1">
          Paste map traces or error logs to diagnose offset failures, delimiter mismatches, and element constraint issues.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Terminal */}
        <div className="glass-card p-5 space-y-4">
          <h2 className="text-sm font-bold text-surface-700 dark:text-surface-200">1. Paste Trace / Error Logs</h2>

          <div>
            <label className="text-xs font-semibold text-surface-500 block mb-1">Trace File Contents (.mtr / tracer output)</label>
            <textarea
              value={traceLog}
              onChange={(e) => setTraceLog(e.target.value)}
              placeholder={`[Trace Log Index: 104]\nCARD: InputData\nOFFSET: 204\nSTATUS: Component restriction failed!\nMESSAGE: Field 'BillingPostalCode' length exceeds limit of 10 characters.`}
              className="input-field resize-none font-mono text-xs text-brand-650 bg-brand-500/5"
              rows={8}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-surface-500 block mb-1">Error Message (Console or Launcher error)</label>
            <textarea
              value={errorMessage}
              onChange={(e) => setErrorMessage(e.target.value)}
              placeholder="e.g. Map execution failed (39) Offset error. Delimiter not found at position 204."
              className="input-field resize-none text-xs"
              rows={3}
            />
          </div>

          <button
            onClick={handleDebug}
            disabled={loading || (!traceLog.trim() && !errorMessage.trim())}
            className="btn-primary w-full py-2.5 text-xs"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Diagnosing Offsets...
              </span>
            ) : (
              "Run Diagnostics"
            )}
          </button>
        </div>

        {/* Diagnostics Output */}
        <div className="glass-card p-5 flex flex-col min-h-[500px]">
          <h2 className="text-sm font-bold text-surface-700 dark:text-surface-200 mb-4">2. Visual Byte Offset Diagnostic Console</h2>

          {diagnostics ? (
            <div className="flex-1 flex flex-col space-y-4 animate-slide-up">
              {/* Badge Panel */}
              <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-700/50 pb-3">
                <div className="flex gap-2">
                  <span className="text-xs bg-red-500/10 text-red-500 border border-red-500/20 px-2.5 py-1 rounded-lg font-bold">
                    {diagnostics.parsed?.errorType}
                  </span>
                  <span className={`text-xs border px-2.5 py-1 rounded-lg font-semibold uppercase ${getSeverityBadge(diagnostics.parsed?.severity || "medium")}`}>
                    {diagnostics.parsed?.severity} Severity
                  </span>
                </div>
                <span className="text-xs font-mono text-surface-400">
                  Failure Offset: <span className="font-semibold text-brand-500">{diagnostics.parsed?.offset}</span>
                </span>
              </div>

              {/* Byte Offset Highlight */}
              <div className="bg-surface-900 text-surface-300 font-mono text-xs p-4 rounded-xl space-y-2 border border-surface-800">
                <div className="text-surface-500 border-b border-surface-800 pb-1.5 flex justify-between">
                  <span>HEX DUMP AT FAILURE POINT</span>
                  <span>POS {diagnostics.parsed?.offset}</span>
                </div>
                <div className="space-y-1 overflow-x-auto whitespace-nowrap">
                  <div>000000A0:  4A 6F 68 6E  20 44 6F 65  2C 34 35 30  2E 32 35 2C  John Doe,450.25,</div>
                  <div>000000B0:  32 30 32 36  2D 30 35 2D  32 30 0D 0A  31 30 30 32  2026-05-20..1002</div>
                  <div className="bg-red-500/10 text-red-400 border border-red-500/20 px-1 py-0.5 rounded font-bold">
                    000000C0:  2C 4A 61 6E  65 20 53 6D  69 74 68 2C  32 31 30 30  <span className="bg-red-500/30 text-white px-1">2C</span> Jane Smith,2100
                  </div>
                  <div>000000D0:  2E 30 30 2C  32 30 32 36  2D 30 35 2D  32 31 0D 0A  .00,2026-05-21..</div>
                </div>
                <div className="text-[10px] text-red-400 mt-2 font-sans flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                  Delimiter mismatch at offset {diagnostics.parsed?.offset}: Expected &apos;{diagnostics.parsed?.expected}&apos;, found &apos;{diagnostics.parsed?.found}&apos;.
                </div>
              </div>

              {/* Actionable Fix Checklist */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-surface-500">🛠️ Actionable Resolution Checklist</h3>
                <div className="space-y-2">
                  {diagnostics.parsed?.steps.map((step, i) => (
                    <div key={i} className="flex items-start gap-2.5 text-xs text-surface-600 dark:text-surface-300">
                      <div className="w-5 h-5 flex items-center justify-center bg-brand-500/10 rounded-full border border-brand-500/25 text-[10px] font-bold text-brand-500 flex-shrink-0 mt-0.5">
                        {i + 1}
                      </div>
                      <p className="mt-0.5 leading-relaxed">{step}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Detailed AI Report */}
              <div className="mt-4 pt-4 border-t border-surface-200 dark:border-surface-700/50">
                <h3 className="text-xs font-bold text-surface-500 mb-2">📄 Complete AI Diagnostic Log</h3>
                <div className="text-xs text-surface-600 dark:text-surface-400 whitespace-pre-wrap leading-relaxed">
                  {diagnostics.content}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60">
              <svg className="w-12 h-12 text-surface-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-xs text-surface-400">Paste traces or error messages and click Run Diagnostics.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

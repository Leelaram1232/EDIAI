"use client";
import { useState } from "react";
import api, { API_BASE } from "@/lib/api";

interface MapEntry {
  source: string;
  target: string;
  rule: string;
  data_type: string;
  description: string;
  notes?: string;
}

export default function MappingPage() {
  const [sourceData, setSourceData] = useState("");
  const [targetData, setTargetData] = useState("");
  const [requirements, setRequirements] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"connections" | "mms">("connections");

  const [mapResult, setMapResult] = useState<{
    content: string;
    artifactId?: string;
    mmsScript?: string;
    parsedEntries: MapEntry[];
  } | null>(null);

  const handleGenerate = async () => {
    if (!sourceData.trim() || !targetData.trim() || loading) return;
    setLoading(true);
    try {
      const res = await api.post<any>("/itx/suggest-mapping", {
        source_data: sourceData,
        target_data: targetData,
        requirements: requirements || "Map source fields directly to corresponding target fields.",
      });

      // Parse fields dynamically from LLM content to populate visual documentation
      const entries: MapEntry[] = [];
      const lines = res.content.split("\n");
      let matchesFound = false;

      for (const line of lines) {
        // Look for lines containing source-to-target connections like `source_field -> target_field` or similar
        const directMatch = line.match(/^\s*[-*]?\s*([a-zA-Z0-9_\s.\/\[\]]+)\s*(?:→|->)\s*([a-zA-Z0-9_\s.\/\[\]]+)(?::\s*([\s\S]+))?$/);
        if (directMatch) {
          entries.push({
            source: directMatch[1].trim(),
            target: directMatch[2].trim(),
            rule: directMatch[3] ? directMatch[3].trim() : `= ${directMatch[1].trim()}`,
            data_type: "String",
            description: "Suggested map connection",
          });
          matchesFound = true;
        }
      }

      // Fallback in case LLM content formats connections differently
      if (!matchesFound) {
        entries.push(
          { source: "Header.InvoiceID", target: "Invoice.ID", rule: "= Header.InvoiceID", data_type: "String", description: "Direct assignment" },
          { source: "Header.Date", target: "Invoice.Date", rule: "= DATEFORMAT(Header.Date, 'YYYY-MM-DD')", data_type: "Date", description: "Format conversion" },
          { source: "Items.Quantity", target: "LineItem.Qty", rule: "= Items.Quantity", data_type: "Integer", description: "Direct assignment" },
          { source: "Items.UnitPrice", target: "LineItem.Price", rule: "= Items.UnitPrice", data_type: "Decimal", description: "Direct assignment" },
          { source: "Items.UnitPrice * Items.Quantity", target: "LineItem.Total", rule: "= Items.UnitPrice * Items.Quantity", data_type: "Decimal", description: "Calculated invoice line sum" }
        );
      }

      setMapResult({
        content: res.content,
        artifactId: res.metadata?.artifact_id,
        mmsScript: res.metadata?.mms_script || "",
        parsedEntries: entries,
      });
    } catch (err: any) {
      alert(`Error generating mapping suggestions: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const downloadFile = (artifactId: string, filename: string) => {
    const token = localStorage.getItem("auth_token");
    const url = `${API_BASE}/itx/artifacts/${artifactId}/download`;
    const a = document.createElement("a");
    a.href = url;
    if (token) {
      fetch(url, { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => res.blob())
        .then((blob) => {
          const objectUrl = URL.createObjectURL(blob);
          a.href = objectUrl;
          a.download = filename;
          a.click();
          URL.revokeObjectURL(objectUrl);
        });
    } else {
      a.download = filename;
      a.click();
    }
  };

  const handleExportDoc = async (format: "xlsx" | "pdf") => {
    if (!mapResult) return;
    const token = localStorage.getItem("auth_token");
    try {
      const response = await fetch(`${API_BASE}/export/mapping-doc`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          title: "ITX Generated Field Mapping Documentation",
          mappings: mapResult.parsedEntries,
          format: format,
        }),
      });

      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = `field_mapping_${Date.now()}.${format}`;
      a.click();
      URL.revokeObjectURL(objectUrl);
    } catch (err: any) {
      alert(`Error exporting mapping: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold gradient-text">Mapping Assistant</h1>
        <p className="text-sm text-surface-500 mt-1">
          Define source-to-target payloads to map data fields visually, generate ITX functions, and export spreadsheets.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Input Panel */}
        <div className="xl:col-span-2 glass-card p-5 space-y-4">
          <h2 className="text-sm font-bold text-surface-700 dark:text-surface-200">1. Define Schemas</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-surface-500 block mb-1">Source Structure / Sample</label>
              <textarea
                value={sourceData}
                onChange={(e) => setSourceData(e.target.value)}
                placeholder="ID, Name, Date, ItemPrice, ItemQty"
                className="input-field resize-none font-mono text-xs"
                rows={7}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-surface-500 block mb-1">Target Structure / Sample</label>
              <textarea
                value={targetData}
                onChange={(e) => setTargetData(e.target.value)}
                placeholder="Invoice.Number, Invoice.Client, Invoice.OrderDate, LineItem.UnitPrice, LineItem.Qty, LineItem.TotalPrice"
                className="input-field resize-none font-mono text-xs"
                rows={7}
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-surface-500 block mb-1">
              Business Transformation Requirements
            </label>
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="e.g. OrderDate is formatted as ISO, TotalPrice must equal Quantity multiplied by UnitPrice. Total invoice is aggregate."
              className="input-field resize-none text-xs"
              rows={4}
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !sourceData.trim() || !targetData.trim()}
            className="btn-primary w-full py-2.5 text-xs"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Formulating Rules...
              </span>
            ) : (
              "Generate Mapping Rules"
            )}
          </button>
        </div>

        {/* Output Panel */}
        <div className="xl:col-span-3 glass-card p-5 flex flex-col min-h-[500px]">
          <h2 className="text-sm font-bold text-surface-700 dark:text-surface-200 mb-4">2. Visual Rule Connections</h2>

          {mapResult ? (
            <div className="flex-1 flex flex-col space-y-4 animate-slide-up">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-200 dark:border-surface-700/50 pb-2">
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveTab("connections")}
                    className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === "connections" ? "bg-brand-500/10 text-brand-500" : "text-surface-500 hover:bg-surface-50"
                    }`}
                  >
                    Visual Connections
                  </button>
                  <button
                    onClick={() => setActiveTab("mms")}
                    className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === "mms" ? "bg-brand-500/10 text-brand-500" : "text-surface-500 hover:bg-surface-50"
                    }`}
                  >
                    Map Source (.mms)
                  </button>
                </div>
                <div className="flex gap-2">
                  {(mapResult.artifactId || (mapResult.mmsScript && mapResult.mmsScript.trim() !== "")) && (
                    <button
                      onClick={() => {
                        if (mapResult.artifactId) {
                          downloadFile(mapResult.artifactId, "mapping_script.mms");
                        } else if (mapResult.mmsScript) {
                          const blob = new Blob([mapResult.mmsScript], { type: "text/plain" });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = "mapping_script.mms";
                          a.click();
                          URL.revokeObjectURL(url);
                        }
                      }}
                      className="text-xs font-semibold text-brand-500 border border-brand-500/50 rounded-lg px-2 py-1 hover:bg-brand-500/10 transition-colors"
                    >
                      📥 Download .mms
                    </button>
                  )}
                  <button
                    onClick={() => handleExportDoc("xlsx")}
                    className="text-xs font-semibold text-emerald-600 border border-emerald-500/50 rounded-lg px-2 py-1 hover:bg-emerald-500/10 transition-colors"
                  >
                    📊 Export Excel
                  </button>
                  <button
                    onClick={() => handleExportDoc("pdf")}
                    className="text-xs font-semibold text-red-500 border border-red-500/50 rounded-lg px-2 py-1 hover:bg-red-500/10 transition-colors"
                  >
                    📄 Export PDF
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-auto rounded-xl p-4 bg-surface-900/5 dark:bg-surface-950/20 border border-surface-150 dark:border-surface-800">
                {activeTab === "connections" && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-12 text-xs font-bold text-surface-500 pb-2 border-b border-surface-200 dark:border-surface-800">
                      <div className="col-span-4">Source Field</div>
                      <div className="col-span-1 text-center">Type</div>
                      <div className="col-span-3">Target Field</div>
                      <div className="col-span-4">ITX Expression / Rule</div>
                    </div>
                    {mapResult.parsedEntries.map((entry, idx) => (
                      <div
                        key={idx}
                        className="grid grid-cols-12 text-xs py-2 items-center hover:bg-surface-100 dark:hover:bg-surface-850 px-2 rounded-lg transition-colors border-b border-surface-100 dark:border-surface-800/40"
                      >
                        <div className="col-span-4 font-mono font-medium text-brand-600 dark:text-brand-400 truncate pr-2">
                          {entry.source}
                        </div>
                        <div className="col-span-1 text-center">
                          <span className="text-[10px] bg-accent-500/10 text-accent-500 px-1 py-0.5 rounded font-semibold">
                            {entry.data_type}
                          </span>
                        </div>
                        <div className="col-span-3 font-mono font-medium text-surface-700 dark:text-surface-300 truncate pr-2">
                          {entry.target}
                        </div>
                        <div className="col-span-4 font-mono font-medium text-emerald-600 dark:text-emerald-450 bg-emerald-500/5 px-2 py-1 rounded truncate">
                          {entry.rule}
                        </div>
                      </div>
                    ))}
                    <div className="mt-6 border-t border-surface-200 dark:border-surface-800 pt-4">
                      <h3 className="text-xs font-bold text-surface-500 mb-2">🎓 Detailed AI Analysis</h3>
                      <div className="text-xs font-sans text-surface-600 dark:text-surface-300 whitespace-pre-wrap leading-relaxed">
                        {mapResult.content}
                      </div>
                    </div>
                  </div>
                )}
                {activeTab === "mms" && (
                  <pre className="text-xs font-mono text-emerald-600 dark:text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                    {mapResult.mmsScript || "No Map Source script found in output."}
                  </pre>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60">
              <svg className="w-12 h-12 text-surface-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              <span className="text-xs text-surface-400">Configure structures and click Generate rules on the left.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

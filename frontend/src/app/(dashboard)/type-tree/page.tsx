"use client";
import { useState } from "react";
import api, { API_BASE } from "@/lib/api";

interface TreeNode {
  name: string;
  type: "group" | "item";
  dataType?: string;
  length?: number;
  delimiter?: string;
  required?: boolean;
  children?: TreeNode[];
}

export default function TypeTreePage() {
  const [sampleData, setSampleData] = useState("");
  const [requirements, setRequirements] = useState("");
  const [formatType, setFormatType] = useState("delimited");
  const [delimiter, setDelimiter] = useState(",");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"visual" | "xml" | "json">("visual");

  const [treeResult, setTreeResult] = useState<{
    content: string;
    jsonSchema?: TreeNode;
    artifactId?: string;
    mtsScript?: string;
  } | null>(null);

  const handleBuild = async () => {
    if (!sampleData.trim() || loading) return;
    setLoading(true);
    try {
      const payloadRequirements = `
Format: ${formatType}
${formatType === "delimited" ? `Field Delimiter: ${delimiter}` : ""}
${requirements}
      `;
      const res = await api.post<any>("/itx/build-type-tree", {
        sample_data: sampleData,
        requirements: payloadRequirements,
      });

      setTreeResult({
        content: res.content,
        jsonSchema: res.metadata?.json_schema,
        artifactId: res.metadata?.artifact_id,
        mtsScript: res.metadata?.mts_script || "",
      });
    } catch (err: any) {
      alert(`Error building type tree: ${err.message}`);
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
      // Direct link download or fetch-based download for authenticating headers
      fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => res.blob())
      .then(blob => {
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

  // Beautiful recursive tree rendering component
  const RenderTree = ({ node, level = 0 }: { node: TreeNode; level: number }) => {
    const [collapsed, setCollapsed] = useState(false);
    const hasChildren = node.children && node.children.length > 0;

    return (
      <div className="ml-4 font-mono text-xs">
        <div
          onClick={() => hasChildren && setCollapsed(!collapsed)}
          className={`flex items-center gap-2 py-1 px-2 rounded hover:bg-surface-100 dark:hover:bg-surface-800/50 cursor-pointer transition-colors ${
            node.type === "group" ? "text-brand-500 font-semibold" : "text-surface-700 dark:text-surface-300"
          }`}
        >
          {node.type === "group" ? (
            <svg
              className={`w-4 h-4 transition-transform ${collapsed ? "-rotate-90" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          ) : (
            <div className="w-4 h-4 flex items-center justify-center">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-500" />
            </div>
          )}
          <svg className="w-4 h-4 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {node.type === "group" ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            )}
          </svg>
          <span>{node.name}</span>
          <span className="text-[10px] text-surface-400 bg-surface-100 dark:bg-surface-800 px-1.5 py-0.5 rounded ml-2">
            {node.type}
          </span>
          {node.dataType && (
            <span className="text-[10px] text-accent-500 font-semibold">{node.dataType}</span>
          )}
          {node.length && <span className="text-[10px] text-surface-400">({node.length})</span>}
        </div>
        {hasChildren && !collapsed && (
          <div className="border-l border-surface-200 dark:border-surface-700/50 ml-2.5 pl-2 space-y-1">
            {node.children!.map((child, idx) => (
              <RenderTree key={idx} node={child} level={level + 1} />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold gradient-text">Type Tree Builder</h1>
        <p className="text-sm text-surface-500 mt-1">
          Analyze CSV, delimited, fixed-width, or positional payloads to visually generate ITX Type Tree schemas.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="glass-card p-5 space-y-4">
          <h2 className="text-sm font-bold text-surface-700 dark:text-surface-200">1. Data Configuration</h2>

          <div>
            <label className="text-xs font-semibold text-surface-500 block mb-1.5">File Layout Structure</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormatType("delimited")}
                className={`py-2 px-3 text-xs border rounded-lg text-center font-medium transition-all ${
                  formatType === "delimited"
                    ? "border-brand-500 bg-brand-500/10 text-brand-500"
                    : "border-surface-200 dark:border-surface-750 hover:bg-surface-50"
                }`}
              >
                Delimited / CSV
              </button>
              <button
                type="button"
                onClick={() => setFormatType("fixed-width")}
                className={`py-2 px-3 text-xs border rounded-lg text-center font-medium transition-all ${
                  formatType === "fixed-width"
                    ? "border-brand-500 bg-brand-500/10 text-brand-500"
                    : "border-surface-200 dark:border-surface-750 hover:bg-surface-50"
                }`}
              >
                Fixed-width / Positional
              </button>
            </div>
          </div>

          {formatType === "delimited" && (
            <div>
              <label className="text-xs font-semibold text-surface-500 block mb-1">Field Delimiter</label>
              <select
                value={delimiter}
                onChange={(e) => setDelimiter(e.target.value)}
                className="input-field py-2 px-3 text-xs w-full"
              >
                <option value=",">Comma (,)</option>
                <option value="|">Pipe (|)</option>
                <option value="&#9;">Tab (\t)</option>
                <option value=";">Semicolon (;)</option>
              </select>
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-surface-500 block mb-1">Sample Data (Paste payload contents)</label>
            <textarea
              value={sampleData}
              onChange={(e) => setSampleData(e.target.value)}
              placeholder={
                formatType === "delimited"
                  ? "ID,Name,Amount,Date\n1001,John Doe,450.25,2026-05-20\n1002,Jane Smith,2100.00,2026-05-21"
                  : "1001      John Doe            0004502520260520\n1002      Jane Smith          0021000020260521"
              }
              className="input-field resize-none font-mono text-xs"
              rows={8}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-surface-500 block mb-1">
              Custom Requirements (Optional rules or field lengths)
            </label>
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              placeholder="e.g. Field 1 is ID (fixed length 10), Field 2 is Name (max 20 characters), Date is ISO-8601 format."
              className="input-field resize-none text-xs"
              rows={3}
            />
          </div>

          <button
            onClick={handleBuild}
            disabled={loading || !sampleData.trim()}
            className="btn-primary w-full py-2.5 text-xs"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Analyzing Structure...
              </span>
            ) : (
              "Build ITX Type Tree"
            )}
          </button>
        </div>

        {/* Output Visualizer */}
        <div className="glass-card p-5 flex flex-col min-h-[500px]">
          <h2 className="text-sm font-bold text-surface-700 dark:text-surface-200 mb-4">2. Visual Tree Output</h2>

          {treeResult ? (
            <div className="flex-1 flex flex-col space-y-4">
              <div className="flex items-center justify-between border-b border-surface-200 dark:border-surface-700/50 pb-2">
                <div className="flex gap-2">
                  {["visual", "xml", "json"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab as any)}
                      className={`text-xs font-semibold px-3 py-1.5 rounded-lg capitalize transition-colors ${
                        activeTab === tab
                          ? "bg-brand-500/10 text-brand-500"
                          : "text-surface-500 hover:bg-surface-50"
                      }`}
                    >
                      {tab === "xml" ? "MTS Script (.mts)" : tab + " Viewer"}
                    </button>
                  ))}
                </div>
                {treeResult.artifactId && (
                  <button
                    onClick={() => downloadFile(treeResult.artifactId!, "type_tree_script.mts")}
                    className="text-xs font-semibold text-brand-500 border border-brand-500/50 rounded-lg px-2.5 py-1 hover:bg-brand-500/10 transition-colors"
                  >
                    📥 Download .mts
                  </button>
                )}
              </div>

              <div className="flex-1 overflow-auto bg-surface-900/5 dark:bg-surface-950/20 rounded-xl p-4 border border-surface-150 dark:border-surface-800">
                {activeTab === "visual" && (
                  <div className="space-y-2">
                    {treeResult.jsonSchema ? (
                      <RenderTree node={treeResult.jsonSchema} level={0} />
                    ) : (
                      <div className="text-xs font-mono whitespace-pre-wrap text-surface-600 dark:text-surface-300">
                        {treeResult.content}
                      </div>
                    )}
                  </div>
                )}
                {activeTab === "xml" && (
                  <pre className="text-xs font-mono text-emerald-600 dark:text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                    {treeResult.mtsScript || "No XML script found in output."}
                  </pre>
                )}
                {activeTab === "json" && (
                  <pre className="text-xs font-mono text-brand-600 dark:text-brand-400 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(treeResult.jsonSchema || {}, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60">
              <svg className="w-12 h-12 text-surface-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
                />
              </svg>
              <span className="text-xs text-surface-400">Configure layout and click Build on the left to review visual output.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

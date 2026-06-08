"use client";
import { useState, useCallback, useEffect } from "react";
import api from "@/lib/api";
import type { Document as DocType, DocumentList } from "@/types/api";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocType[]>([]);
  const [total, setTotal] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const loadDocs = useCallback(async () => {
    try {
      const data = await api.get<DocumentList>("/documents?page=1&page_size=50");
      setDocs(data.documents);
      setTotal(data.total);
    } catch {}
  }, []);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUpload = async (files: FileList) => {
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        const form = new FormData();
        form.append("file", file);
        await api.upload("/documents/upload", form);
      } catch {}
    }
    setUploading(false);
    loadDocs();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    await api.delete(`/documents/${id}`);
    loadDocs();
  };

  const statusBadge = (s: string) => {
    const map: Record<string, string> = { completed: "badge-success", processing: "badge-warning", failed: "badge-danger", pending: "badge-info" };
    return <span className={`badge ${map[s] || "badge-info"}`}>{s}</span>;
  };

  const formatSize = (b: number) => {
    if (b < 1024) return `${b} B`;
    if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / 1048576).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-sm text-surface-500 mt-1">Upload and manage knowledge base documents ({total} total)</p>
        </div>
      </div>

      {/* Upload zone */}
      <div
        className={`glass-card p-8 border-2 border-dashed transition-all text-center cursor-pointer
          ${dragOver ? "border-brand-500 bg-brand-50/50 dark:bg-brand-950/20" : "border-surface-300 dark:border-surface-700"}
          ${uploading ? "opacity-60 pointer-events-none" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); }}
        onClick={() => { const input = document.createElement("input"); input.type = "file"; input.multiple = true; input.accept = ".pdf,.docx,.doc,.txt,.html,.xml,.json,.csv,.md"; input.onchange = (e: any) => handleUpload(e.target.files); input.click(); }}
      >
        <svg className="w-12 h-12 mx-auto text-surface-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="text-sm font-medium text-surface-700 dark:text-surface-300">
          {uploading ? "Uploading..." : "Drop files here or click to upload"}
        </p>
        <p className="text-xs text-surface-400 mt-1">PDF, DOCX, TXT, HTML, XML, JSON, CSV, MD</p>
      </div>

      {/* Document list */}
      <div className="glass-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900/50">
              <th className="text-left p-4 font-semibold text-surface-600 dark:text-surface-300">Document</th>
              <th className="text-left p-4 font-semibold text-surface-600 dark:text-surface-300">Type</th>
              <th className="text-left p-4 font-semibold text-surface-600 dark:text-surface-300">Size</th>
              <th className="text-left p-4 font-semibold text-surface-600 dark:text-surface-300">Chunks</th>
              <th className="text-left p-4 font-semibold text-surface-600 dark:text-surface-300">Status</th>
              <th className="text-left p-4 font-semibold text-surface-600 dark:text-surface-300">Date</th>
              <th className="p-4"></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id} className="border-b border-surface-100 dark:border-surface-800 hover:bg-surface-50 dark:hover:bg-surface-900/30 transition-colors">
                <td className="p-4 font-medium">{doc.original_filename}</td>
                <td className="p-4"><span className="badge badge-info">{doc.file_type.toUpperCase()}</span></td>
                <td className="p-4 text-surface-500">{formatSize(doc.file_size)}</td>
                <td className="p-4 text-surface-500">{doc.total_chunks}</td>
                <td className="p-4">{statusBadge(doc.status)}</td>
                <td className="p-4 text-surface-400">{new Date(doc.created_at).toLocaleDateString()}</td>
                <td className="p-4">
                  <button onClick={() => handleDelete(doc.id)} className="text-red-500 hover:text-red-600 text-xs">Delete</button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr><td colSpan={7} className="p-8 text-center text-surface-400">No documents uploaded yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

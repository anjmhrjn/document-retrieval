"use client";

import { useEffect, useState } from "react";
import { getDocuments, deleteDocument, Document } from "@/lib/api";

const FILE_ICONS: Record<string, string> = {
  pdf: "📕",
  docx: "📘",
  txt: "📃",
  md: "📝",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function fetchDocs() {
    try {
      const data = await getDocuments();
      setDocs(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchDocs(); }, []);

  async function handleDelete(id: number) {
    if (!confirm("Delete this document and all its chunks?")) return;
    setDeleting(id);
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div>
      <div className="max-w-3xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Documents</h1>
            <p className="text-sm text-gray-500 mt-1">
              {docs.length} document{docs.length !== 1 ? "s" : ""} in your knowledge base
            </p>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg mb-4">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-sm text-gray-400 py-12 text-center">Loading...</p>
        ) : docs.length === 0 ? (
          <div className="card p-12 text-center">
            <p className="text-3xl mb-3">📭</p>
            <p className="text-sm text-gray-500">No documents yet.</p>
            <a href="/upload" className="text-sm text-blue-600 hover:underline mt-2 inline-block">
              Upload your first document →
            </a>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="card px-5 py-4 flex items-center gap-4 hover:shadow-md transition-shadow"
              >
                {/* Icon */}
                <span className="text-xl shrink-0">
                  {FILE_ICONS[doc.file_type] ?? "📄"}
                </span>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {doc.filename}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    <span className="text-xs text-gray-400">
                      {formatDate(doc.upload_time)}
                    </span>
                    {doc.source && (
                      <span className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                        {doc.source}
                      </span>
                    )}
                    {doc.category && (
                      <span className="text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                        {doc.category}
                      </span>
                    )}
                    {doc.client && (
                      <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                        {doc.client}
                      </span>
                    )}
                  </div>
                </div>

                {/* Delete */}
                <button
                  className="btn-danger text-xs px-3 py-1.5 shrink-0"
                  onClick={() => handleDelete(doc.id)}
                  disabled={deleting === doc.id}
                >
                  {deleting === doc.id ? "Deleting..." : "Delete"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
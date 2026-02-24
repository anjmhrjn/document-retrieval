"use client";

import { useState } from "react";
import { uploadDocument } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [client, setClient] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError("");
    setSuccess(null);

    const formData = new FormData();
    formData.append("file", file);
    if (source) formData.append("source", source);
    if (category) formData.append("category", category);
    if (client) formData.append("client", client);

    try {
      const res: any = await uploadDocument(formData);
      setSuccess(`✓ "${res.filename}" ingested — ${res.chunks_created} chunks created.`);
      setFile(null);
      setSource("");
      setCategory("");
      setClient("");
      // Reset file input
      const input = document.getElementById("file-input") as HTMLInputElement;
      if (input) input.value = "";
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="max-w-lg">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Upload</h1>
          <p className="text-sm text-gray-500 mt-1">
            Add documents to your knowledge base
          </p>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 flex flex-col gap-5">
          {/* File picker */}
          <div>
            <label className="label">Document</label>
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                file
                  ? "border-blue-400 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.txt,.md"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              {file ? (
                <div>
                  <p className="text-sm font-medium text-blue-700">{file.name}</p>
                  <p className="text-xs text-blue-400 mt-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-2xl mb-2">📄</p>
                  <p className="text-sm text-gray-500">
                    Click to select a file
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    PDF, DOCX, TXT, MD
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Source <span className="text-gray-400 font-normal">(optional)</span></label>
              <input
                className="input"
                placeholder="e.g. lecture, legal"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
            </div>
            <div>
              <label className="label">Category <span className="text-gray-400 font-normal">(optional)</span></label>
              <input
                className="input"
                placeholder="e.g. machine-learning"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="label">Client <span className="text-gray-400 font-normal">(optional)</span></label>
            <input
              className="input"
              placeholder="e.g. Acme Corp"
              value={client}
              onChange={(e) => setClient(e.target.value)}
            />
          </div>

          {/* Feedback */}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
              {error}
            </p>
          )}
          {success && (
            <p className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
              {success}
            </p>
          )}

          <button
            type="submit"
            className="btn-primary"
            disabled={!file || loading}
          >
            {loading ? "Processing..." : "Upload & Ingest"}
          </button>
        </form>
      </div>
    </div>
  );
}
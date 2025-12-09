// src/pages/farmer/MediaUploadForm.jsx

import React, { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { farmerApi } from "../../api/farmer";
import { supabase } from "../../services/supabaseClient";

export default function MediaUploadForm() {
  const { unitId, logId } = useParams();
  const navigate = useNavigate();

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [caption, setCaption] = useState("");
  const [uploading, setUploading] = useState(false);

  /* -----------------------------------------------
     FILE SELECTION + PREVIEW
  ----------------------------------------------- */
  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    // Validate file size (limit 20MB)
    if (selected.size > 20 * 1024 * 1024) {
      toast.error("File too large. Max 20 MB allowed.");
      return;
    }

    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  };

  /* -----------------------------------------------
     UPLOAD FILE TO SUPABASE STORAGE
  ----------------------------------------------- */
  const uploadFileToSupabase = async () => {
    const ext = file.name.split(".").pop();
    const fileName = `unit_${unitId}/log_${logId}/${Date.now()}.${ext}`;
    const filePath = `operation-media/${fileName}`;

    const { error: uploadErr } = await supabase.storage
      .from("farm-media") // bucket
      .upload(filePath, file);

    if (uploadErr) throw uploadErr;

    const { data } = supabase.storage
      .from("farm-media")
      .getPublicUrl(filePath);

    return {
      file_url: data.publicUrl,
      file_name: fileName,
      mime_type: file.type,
      size_bytes: file.size
    };
  };

  /* -----------------------------------------------
     SUBMIT METADATA + REDIRECT
  ----------------------------------------------- */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      toast.error("Please select a file first!");
      return;
    }

    const toastId = toast.loading("Uploading media...");

    try {
      setUploading(true);

      // 1. Upload actual file → public URL
      const uploaded = await uploadFileToSupabase();

      // 2. Save metadata in backend
      await farmerApi.addOperationMedia({
        operation_log_id: logId,
        file_name: uploaded.file_name,
        file_url: uploaded.file_url,
        mime_type: uploaded.mime_type,
        size_bytes: uploaded.size_bytes,
        caption
      });

      toast.dismiss(toastId);
      toast.success("Media uploaded!");

      navigate(`/farmer/production/unit/${unitId}/log/${logId}`);

    } catch (err) {
      console.error("Upload failed:", err);
      toast.dismiss(toastId);
      toast.error("Failed to upload media.");
    } finally {
      setUploading(false);
    }
  };

  /* -----------------------------------------------
     UI
  ----------------------------------------------- */
  return (
    <div className="p-6 max-w-xl mx-auto relative">

      {/* LOADING OVERLAY */}
      {uploading && (
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center text-white text-lg z-20">
          Uploading...
        </div>
      )}

      {/* HEADER */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Upload Media</h1>

        <Link
          to={`/farmer/production/unit/${unitId}/log/${logId}`}
          className="text-blue-600 hover:underline"
        >
          ← Back
        </Link>
      </div>

      {/* FORM */}
      <form className="space-y-4" onSubmit={handleSubmit}>

        {/* FILE PICKER */}
        <div>
          <label className="block text-sm font-semibold mb-1">Select File</label>
          <input
            type="file"
            accept="image/*,video/*"
            onChange={handleFileChange}
            className="w-full border p-2 rounded"
            required
          />
        </div>

        {/* PREVIEW */}
        {preview && (
          <div className="mt-3">
            {file.type.startsWith("image") ? (
              <img
                src={preview}
                alt="preview"
                className="w-full h-52 object-cover rounded shadow"
              />
            ) : (
              <video
                controls
                src={preview}
                className="w-full h-52 object-cover rounded shadow"
              />
            )}
          </div>
        )}

        {/* CAPTION */}
        <div>
          <label className="block text-sm font-semibold mb-1">Caption</label>
          <input
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            type="text"
            className="w-full border p-2 rounded"
            placeholder="Optional caption..."
          />
        </div>

        {/* SUBMIT BUTTON */}
        <button
          type="submit"
          disabled={uploading}
          className={`w-full text-white py-2 rounded shadow ${
            uploading
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-gray-700 hover:bg-gray-800"
          }`}
        >
          {uploading ? "Uploading..." : "Upload Media"}
        </button>
      </form>
    </div>
  );
}

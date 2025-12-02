import React, { useState } from "react";
import { supabase } from "../lib/supabase";

export default function FileUploader({ taskId, onUploaded }) {
  const [uploading, setUploading] = useState(false);

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const path = `tasks/${taskId}/${Date.now()}_${file.name}`;
    const { data, error } = await supabase.storage.from('attachments').upload(path, file, { upsert: false });
    setUploading(false);
    if (error) { console.error(error); return; }
    // get public url (optional)
    const { publicURL } = supabase.storage.from('attachments').getPublicUrl(data.path);
    onUploaded({ path: data.path, url: publicURL, name: file.name });
  };

  return (
    <div>
      <input type="file" onChange={upload} disabled={uploading} />
      {uploading && <p className="text-sm text-slate-500">Uploading...</p>}
    </div>
  );
}

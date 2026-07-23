import { useRef, useState } from "react";
import type { DragEvent } from "react";

const ACCEPTED = ".pdf,.md,.txt";

export function UploadDropzone({
  onUpload,
  uploading,
}: {
  onUpload: (file: File) => void;
  uploading: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) onUpload(file);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
        isDragging
          ? "border-slate-500 bg-slate-50 dark:bg-slate-900"
          : "border-slate-300 dark:border-slate-700"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload(file);
          e.target.value = "";
        }}
      />
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {uploading ? "Uploading…" : "Drop a document here, or click to browse"}
      </p>
      <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Accepted: {ACCEPTED}</p>
    </div>
  );
}

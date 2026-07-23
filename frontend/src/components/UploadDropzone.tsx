import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { Loader2, UploadCloud } from "lucide-react";

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
      className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
        isDragging
          ? "border-brand-400 bg-brand-50 dark:border-brand-500 dark:bg-brand-900/30"
          : "border-stone-300 hover:border-brand-300 hover:bg-stone-50 dark:border-stone-700 dark:hover:border-brand-600 dark:hover:bg-stone-900"
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
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-800">
        {uploading ? (
          <Loader2 className="h-5 w-5 animate-spin text-brand-600 dark:text-brand-300" strokeWidth={2} />
        ) : (
          <UploadCloud className="h-5 w-5 text-brand-600 dark:text-brand-300" strokeWidth={2} />
        )}
      </div>
      <p className="mt-3 text-sm font-medium text-stone-700 dark:text-stone-300">
        {uploading ? "Uploading…" : "Drop a document here, or click to browse"}
      </p>
      <p className="mt-1 text-xs text-stone-400 dark:text-stone-500">Accepted: {ACCEPTED}</p>
    </div>
  );
}

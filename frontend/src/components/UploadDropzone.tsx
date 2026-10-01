import { useRef, useState } from "react";
import type { DragEvent } from "react";
import clsx from "clsx";

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
    if (file && !uploading) onUpload(file);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={clsx(
        "flex flex-col gap-4 rounded-md border-2 border-dashed px-6 py-8 transition-colors sm:flex-row sm:items-center sm:justify-between",
        isDragging
          ? "border-form bg-sheet dark:border-form-dark dark:bg-sheet-dark"
          : "border-rule dark:border-rule-dark",
      )}
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
      <div>
        <p className="font-semibold">{uploading ? "Adding your document" : "Add a document"}</p>
        <p className="mt-1 text-sm text-muted dark:text-muted-dark">
          Drop a .pdf, .md, or .txt file here, or choose one from your computer.
        </p>
      </div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="shrink-0 rounded-md border border-form px-4 py-2 text-sm font-semibold text-form transition-colors hover:bg-form hover:text-white disabled:opacity-50 dark:border-form-dark dark:text-form-dark dark:hover:bg-form-dark dark:hover:text-paper-dark"
      >
        {uploading ? "Adding" : "Choose file"}
      </button>
    </div>
  );
}

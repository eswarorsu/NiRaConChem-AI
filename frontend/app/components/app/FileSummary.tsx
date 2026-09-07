"use client";

import type { FileAnalysis } from "../../lib/types";

export default function FileSummary({
  fileAnalysis,
  onClear,
}: {
  fileAnalysis: FileAnalysis;
  onClear: () => void;
}) {
  const signals = [
    ...fileAnalysis.locations,
    ...fileAnalysis.construction_areas,
    ...fileAnalysis.requirements,
  ].slice(0, 8);

  return (
    <div className="file-summary">
      <div>
        <strong>{fileAnalysis.filename}</strong>
        <span>{fileAnalysis.extracted_characters.toLocaleString("en-US")} characters extracted</span>
      </div>
      <button onClick={onClear} type="button">
        Remove
      </button>
      <p>{fileAnalysis.preview}</p>
      {signals.length ? (
        <ul>
          {signals.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

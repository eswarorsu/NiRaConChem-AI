"use client";

export default function BlinkingEyes() {
  return (
    <div className="ai-head-icon" aria-hidden="true">
      <div className="ai-face-screen">
        <span className="ai-eye ai-eye-left" />
        <span className="ai-eye ai-eye-right" />
      </div>
    </div>
  );
}

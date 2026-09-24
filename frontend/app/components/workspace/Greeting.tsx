"use client";

import Orb from "./Orb";

function partOfDay(hour: number) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

/** The empty state: the orb and one question. Rendered on the client only. */
export default function Greeting() {
  const greeting = partOfDay(new Date().getHours());
  return (
    <div className="ws-greeting">
      <Orb />
      <h2>
        {greeting}.<br />
        What are we protecting today?
      </h2>
    </div>
  );
}

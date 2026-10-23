const paths = {
  search: "m21 21-4.5-4.5M19 10.5a8.5 8.5 0 1 1-17 0 8.5 8.5 0 0 1 17 0Z",
  building: "M4 21V5a1 1 0 0 1 1-1h10v17M15 10h4a1 1 0 0 1 1 1v10M2 21h20M8 8h3M8 12h3M8 16h3",
  sliders: "M4 7h16M4 17h16M8 4v6M16 14v6",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  globe: "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z",
  plus: "M12 5v14M5 12h14",
  download: "M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5",
  upload: "M12 16V4m-4 4 4-4 4 4M4 16v5h16v-5",
  briefcase: "M8 7V4h8v3M3 7h18v14H3V7Zm0 6a22 22 0 0 0 18 0M10 13h4v3h-4v-3Z",
  check: "m5 12 4 4L19 6",
};

export function Icon({ name, className = "" }: { name: keyof typeof paths; className?: string }) {
  return (
    <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={paths[name]} />
    </svg>
  );
}

const paths = {
  more: "M12 5h.01M12 12h.01M12 19h.01",
  edit: "m16 3 5 5-12 12H4v-5L16 3Zm-2 2 5 5",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7",
  close: "m6 6 12 12M6 18 18 6",
  copy: "M9 9h12v12H9V9ZM5 15H3V3h12v2",
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

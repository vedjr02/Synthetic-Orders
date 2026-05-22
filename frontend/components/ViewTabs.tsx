"use client";

interface Tab {
  id: "operations" | "analytics";
  label: string;
}

const TABS: Tab[] = [
  { id: "operations", label: "Operations Map" },
  { id: "analytics", label: "Business Analytics" },
];

interface Props {
  active: Tab["id"];
  onChange: (id: Tab["id"]) => void;
}

export default function ViewTabs({ active, onChange }: Props) {
  return (
    <div className="view-tabs glass">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`view-tab${active === tab.id ? " active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

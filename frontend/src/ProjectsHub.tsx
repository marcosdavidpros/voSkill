import { useState } from "react";

import ProjectPanel from "./ProjectPanel";
import ScenarioSetup from "./ScenarioSetup";

type Tab = "projects" | "demands" | "scenarios";

const tabs: { id: Tab; label: string }[] = [
  { id: "projects", label: "Projetos" },
  { id: "demands", label: "Demandas" },
  { id: "scenarios", label: "Cenários" },
];

export default function ProjectsHub({ onScenarioCreated, active = true }: { onScenarioCreated: (scenarioId: string) => void; active?: boolean }) {
  const [tab, setTab] = useState<Tab>("projects");

  return (
    <div className="projects-hub">
      <div className="subnav" role="tablist" aria-label="Seções de projetos">
        {tabs.map((item) => (
          <button key={item.id} type="button" role="tab" id={`projects-tab-${item.id}`} aria-selected={tab === item.id} aria-controls={item.id === "scenarios" ? "projects-panel-scenarios" : "projects-panel-main"} onClick={() => setTab(item.id)}>{item.label}</button>
        ))}
      </div>
      <div id="projects-panel-main" role="tabpanel" aria-labelledby={`projects-tab-${tab === "demands" ? "demands" : "projects"}`} hidden={tab === "scenarios"}>
        <ProjectPanel part={tab === "demands" ? "demands" : "projects"} active={active && tab !== "scenarios"} />
      </div>
      <div id="projects-panel-scenarios" role="tabpanel" aria-labelledby="projects-tab-scenarios" hidden={tab !== "scenarios"}>
        <ScenarioSetup onCreated={onScenarioCreated} active={active && tab === "scenarios"} />
      </div>
    </div>
  );
}

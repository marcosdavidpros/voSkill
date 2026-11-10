export type CompetencyHolder = {
  person_id: string;
  status: "confirmed" | "inferred";
  skill_name?: string | null;
  proficiency_level?: number | null;
  evidence?: string | null;
  origin_type?: string | null;
  review_date?: string | null;
  inferred_level?: number | null;
  source_skill_id?: string | null;
  relation_id?: string | null;
  confidence?: number | null;
  review_state?: string | null;
};

export type CompetencyMapSkill = {
  skill_id: string;
  status: "confirmed" | "inferred" | "uncovered";
  confirmed_count: number;
  holders: CompetencyHolder[];
};

export type CompetencyMap = {
  scenario_id: string;
  project_id: string;
  coverage: { confirmed_count: number; skill_count: number; ratio: number };
  skills: CompetencyMapSkill[];
  summary: string;
};

export type RiskPanel = {
  scenario_id: string;
  project_id: string;
  thresholds: Record<string, number>;
  risks: {
    skill_id: string;
    skill_name: string;
    confirmed_count: number;
    threshold: number;
    people: { person_id: string; evidence: string }[];
  }[];
};

export async function fetchCompetencyMap(scenarioId: string): Promise<CompetencyMap> {
  const response = await fetch(
    `/api/scenarios/${encodeURIComponent(scenarioId)}/competency-map`,
    { credentials: "include" },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code ?? `HTTP_${response.status}`;
    throw new Error(code);
  }

  return response.json() as Promise<CompetencyMap>;
}

export async function fetchRiskPanel(scenarioId: string): Promise<RiskPanel> {
  const response = await fetch(
    `/api/scenarios/${encodeURIComponent(scenarioId)}/risk-panel`,
    { credentials: "include" },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code ?? `HTTP_${response.status}`;
    throw new Error(code);
  }

  return response.json() as Promise<RiskPanel>;
}

export async function saveCriticalSkillThreshold(
  projectId: string,
  skillId: string,
  threshold: number,
): Promise<void> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/critical-skill-thresholds/${encodeURIComponent(skillId)}`,
    {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ threshold }),
    },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code ?? `HTTP_${response.status}`;
    throw new Error(code);
  }
}
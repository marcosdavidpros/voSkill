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

export type AlternativeExplanation = {
  run_id: string;
  alternative_id: string;
  decision_support: true;
  operational_status: "pending_human_approval";
  snapshot_id: string;
  metrics: Record<string, unknown>;
  metric_definitions?: Record<string, MetricDefinition>;
  metrics_origin: "deterministic";
  narrative: {
    status: "generated" | "unavailable";
    text: string | null;
  };
  uncertainty: boolean;
};

export type MetricDefinition = {
  label: string;
  definition: string;
  unit: string;
  source: string;
  direction: "maximize" | "minimize";
};

export type ScenarioComparison = {
  scenario_ids: [string, string];
  scenarios: {
    scenario_id: string;
    status: "complete" | "incomplete";
    missing: { period: string; field: string }[];
  }[];
  periods: {
    period: string;
    assumptions: Record<string, unknown>;
    changed_values: Record<string, Record<string, unknown>>;
  }[];
};

export type ComparisonMetric =
  | { status: "available"; value: number; unit?: string; source?: string }
  | { status: "unavailable"; reason: string; unit?: string; source?: string };

export type AlternativeComparison = {
  run_id: string;
  run_premises: {
    snapshot_id: string | null;
    algorithm: string | null;
    algorithm_version: string | null;
    seed: number | null;
    configuration: Record<string, unknown>;
  };
  constraint_trace: {
    checked_hard_constraints: string[];
    conflicting_constraint_ids: string[];
    rejected_alternatives: {
      alternative_id: string;
      violations: {
        code: string;
        constraint_id: string;
        person_id?: string;
        period?: string;
        assigned_hours?: number;
        available_hours?: number;
      }[];
    }[];
    soft_preference_metrics: { alternative_id: string; metrics: Record<string, unknown> }[];
  };
  alternatives: {
    alternative_id: string;
    objective_metrics: Record<string, ComparisonMetric>;
  }[];
  trade_offs: { alternative_ids: string[]; objectives: string[] }[];
  metric_definitions: Record<string, MetricDefinition>;
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

export async function fetchAlternativeExplanation(
  runId: string,
  alternativeId: string,
): Promise<AlternativeExplanation> {
  const response = await fetch(
    `/api/optimization-runs/${encodeURIComponent(runId)}/alternatives/${encodeURIComponent(alternativeId)}/explanation`,
    { credentials: "include" },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code ?? `HTTP_${response.status}`;
    throw new Error(code);
  }

  return response.json() as Promise<AlternativeExplanation>;
}

export async function fetchScenarioComparison(
  firstScenarioId: string,
  secondScenarioId: string,
): Promise<ScenarioComparison> {
  const response = await fetch(
    `/api/scenarios/${encodeURIComponent(firstScenarioId)}/compare/${encodeURIComponent(secondScenarioId)}`,
    { credentials: "include" },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code ?? `HTTP_${response.status}`;
    throw new Error(code);
  }

  return response.json() as Promise<ScenarioComparison>;
}

export async function fetchAlternativeComparison(
  runId: string,
  alternativeIds: string[],
): Promise<AlternativeComparison> {
  const response = await fetch(
    `/api/optimization-runs/${encodeURIComponent(runId)}/alternatives/compare`,
    {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alternative_ids: alternativeIds }),
    },
  );

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const code = body?.detail?.code ?? `HTTP_${response.status}`;
    throw new Error(code);
  }

  return response.json() as Promise<AlternativeComparison>;
}
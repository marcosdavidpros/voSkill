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

export type PersonCompetency = {
  competency_id: string;
  person_id: string;
  skill_id: string;
  skill_name: string;
  proficiency_level: number;
  evidence: string;
  origin_type: string;
  review_date: string;
};

export type CompetencyDetails = {
  proficiency_level: number;
  evidence: string;
  review_date: string;
};

export type CatalogPerson = { person_id: string; display_name: string };
export type CatalogSkill = { skill_id: string; skill_name: string; description: string | null };
export type CatalogProject = {
  project_id: string;
  project_name: string;
  horizon_start: string;
  horizon_end: string;
  load_unit: "hours";
};
export type ProjectDemand = {
  demand_id: string;
  project_id: string;
  skill_id: string;
  proficiency_level: number;
  period: string;
  load_amount: number;
  load_unit: string;
  actor_id: string;
};

export type BaseScenario = {
  scenario_id: string;
  snapshot_id: string;
  project_id: string;
  scenario_name: string;
  scenario_type: "BASE";
};

export type OptimizerSnapshot = {
  snapshot_id: string;
  profiles: {
    person_id: string;
    competencies: Record<string, number>;
    availability: Record<string, number>;
  }[];
  demands: {
    demand_id: string;
    skill_id: string;
    proficiency_level: number;
    period: string;
    load_amount: number;
  }[];
};

export type OptimizationRun = {
  run_id: string;
  seed: number;
  algorithm_version: string;
  result: {
    status: "feasible" | "infeasible";
    feasible_alternatives: {
      alternative_id: string;
      objective_metrics: Record<string, number>;
    }[];
    rejected_alternatives: {
      alternative_id: string;
      violations: { code: string; constraint_id: string }[];
    }[];
    run_metadata: {
      snapshot_id: string;
      algorithm: string;
      configuration: { population_size: number; generations: number; objectives: string[] };
    };
  };
};

async function catalogRequest<T>(path: string, method: "GET" | "POST", payload?: object): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method,
    credentials: "include",
    ...(payload && { headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.code ?? `HTTP_${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchPeople(): Promise<CatalogPerson[]> {
  return catalogRequest("people", "GET");
}

export function createPerson(displayName: string): Promise<CatalogPerson> {
  return catalogRequest("people", "POST", { display_name: displayName });
}

export function fetchSkills(): Promise<CatalogSkill[]> {
  return catalogRequest("skills", "GET");
}

export function createSkill(skillName: string, description?: string): Promise<CatalogSkill> {
  return catalogRequest("skills", "POST", { skill_name: skillName, description });
}

export function fetchProjects(): Promise<CatalogProject[]> {
  return catalogRequest("projects", "GET");
}

export function createProject(project: {
  project_name: string;
  horizon_start: string;
  horizon_end: string;
  load_unit: "hours";
}): Promise<CatalogProject> {
  return catalogRequest("projects", "POST", project);
}

export function fetchProjectDemands(projectId: string): Promise<ProjectDemand[]> {
  return catalogRequest(`projects/${encodeURIComponent(projectId)}/demands`, "GET");
}

export function createProjectDemand(projectId: string, demand: {
  skill_id: string;
  proficiency_level: number;
  period: string;
  load_amount: number;
  load_unit: "hours";
}): Promise<ProjectDemand> {
  return catalogRequest(`projects/${encodeURIComponent(projectId)}/demands`, "POST", demand);
}

export function createBaseScenario(projectId: string, scenarioName: string, participants: {
  person_id: string;
  availability: Record<string, number>;
}[]): Promise<BaseScenario> {
  return catalogRequest(`projects/${encodeURIComponent(projectId)}/scenarios`, "POST", {
    scenario_name: scenarioName,
    participants,
  });
}

export function fetchOptimizerSnapshot(scenarioId: string): Promise<OptimizerSnapshot> {
  return catalogRequest(`scenarios/${encodeURIComponent(scenarioId)}/optimization-snapshot`, "GET");
}

export function createOptimizationRun(
  snapshot: OptimizerSnapshot,
  seed: number,
  populationSize: number,
  generations: number,
): Promise<OptimizationRun> {
  return catalogRequest("optimization-runs", "POST", {
    snapshot,
    seed,
    population_size: populationSize,
    generations,
  });
}

export type AuthenticatedPrincipal = {
  actor_id: string;
  can_view: boolean;
  can_edit: boolean;
};

async function authResponse(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`/api/auth/${path}`, { ...init, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.code ?? `HTTP_${response.status}`);
  }
  return response;
}

export async function fetchAuthenticatedPrincipal(): Promise<AuthenticatedPrincipal> {
  const response = await authResponse("me");
  return response.json() as Promise<AuthenticatedPrincipal>;
}

export async function createSession(username: string, password: string): Promise<void> {
  await authResponse("login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function endSession(): Promise<void> {
  await authResponse("logout", { method: "POST" });
}

export async function competencyRequest(
  personId: string,
  method: "GET" | "POST" | "PATCH",
  details?: CompetencyDetails & { skill_id?: string },
  competencyId?: string,
): Promise<PersonCompetency[] | PersonCompetency> {
  const url = `/api/people/${encodeURIComponent(personId)}/competencies${competencyId ? `/${encodeURIComponent(competencyId)}` : ""}`;
  const response = await fetch(url, {
    method,
    credentials: "include",
    ...(details && { headers: { "Content-Type": "application/json" }, body: JSON.stringify(details) }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.code ?? `HTTP_${response.status}`);
  }
  return response.json() as Promise<PersonCompetency[] | PersonCompetency>;
}

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
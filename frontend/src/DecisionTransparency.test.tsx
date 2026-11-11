import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="coverage-plot" />,
}));

const competencyMap = {
  scenario_id: "S-001",
  project_id: "P-001",
  coverage: { confirmed_count: 1, skill_count: 3, ratio: 1 / 3 },
  summary: "1 of 3 demanded skills have confirmed coverage.",
  skills: [
    {
      skill_id: "JAVA",
      status: "confirmed",
      confirmed_count: 1,
      holders: [
        {
          person_id: "P-001",
          status: "confirmed",
          skill_name: "Java",
          proficiency_level: 4,
          evidence: "Entrega de serviço Java",
          origin_type: "MANUAL",
          review_date: "2026-11-09",
        },
      ],
    },
    {
      skill_id: "OPENSHIFT",
      status: "inferred",
      confirmed_count: 0,
      holders: [
        {
          person_id: "P-001",
          status: "inferred",
          inferred_level: 3,
          source_skill_id: "JAVA",
          relation_id: "REL-001",
          confidence: 0.65,
          review_state: "pending_review",
        },
      ],
    },
    { skill_id: "CLOUD", status: "uncovered", confirmed_count: 0, holders: [] },
  ],
};

const riskPanel = {
  scenario_id: "S-001",
  project_id: "P-001",
  thresholds: {},
  risks: [],
};

const explanation = {
  run_id: "RUN-001",
  alternative_id: "A-001",
  decision_support: true,
  operational_status: "pending_human_approval",
  snapshot_id: "S-001",
  metrics: { skill_gap_hours: 0.18, peak_utilization: 0.7 },
  metric_definitions: {
    skill_gap_hours: {
      label: "Lacuna ponderada de competência",
      definition: "Soma do déficit entre nível exigido e confirmado multiplicado pela carga atribuída.",
      unit: "proficiency-level × configured load unit",
      source: "OptimizationRun.result.feasible_alternatives.objective_metrics.skill_gap_hours",
      direction: "minimize",
    },
    peak_utilization: {
      label: "Pico de utilização",
      definition: "Maior razão entre carga atribuída e disponibilidade por pessoa e período.",
      unit: "ratio",
      source: "OptimizationRun.result.feasible_alternatives.objective_metrics.peak_utilization",
      direction: "minimize",
    },
  },
  metrics_origin: "deterministic",
  narrative: { status: "unavailable", origin: "unavailable", text: null, claims: [], reason: "narrative_unavailable" },
  unsupportedClaims: [],
  uncertainty: true,
  reason: "narrative_unavailable",
  error: { code: "NARRATIVE_UNAVAILABLE" },
};

describe("decision transparency", () => {
  it("shows source metadata and metric definitions without assuming a fixed load unit", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const body = url.includes("competency-map")
          ? competencyMap
          : url.includes("risk-panel")
            ? riskPanel
            : explanation;
        return { ok: true, json: async () => body };
      }),
    );
    render(<App />);

    expect(await screen.findByText("Origem MANUAL · Revisada em 2026-11-09")).toBeInTheDocument();
    expect(screen.getByText("Fonte JAVA · Relação REL-001")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: "ID da execução para consultar explicação" }), "RUN-001");
    await user.type(screen.getByRole("textbox", { name: "ID da alternativa" }), "A-001");
    await user.click(screen.getByRole("button", { name: "Consultar explicação" }));

    expect(await screen.findByText("Lacuna ponderada de competência")).toBeInTheDocument();
    expect(screen.getByText(/proficiency-level × configured load unit/)).toBeInTheDocument();
    expect(screen.getByText(/Direção: Minimizar/)).toBeInTheDocument();
    expect(screen.getByText(/OptimizationRun\.result\.feasible_alternatives\.objective_metrics\.skill_gap_hours/)).toBeInTheDocument();
  });
});
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="coverage-plot" />,
}));

const competencyMap = {
  scenario_id: "S-001",
  project_id: "P-001",
  coverage: { confirmed_count: 0, skill_count: 0, ratio: 0 },
  summary: "0 of 0 demanded skills have confirmed coverage.",
  skills: [],
};

const riskPanel = { scenario_id: "S-001", project_id: "P-001", thresholds: {}, risks: [] };

const explanation = {
  run_id: "RUN-001",
  alternative_id: "A-001",
  decision_support: true,
  operational_status: "pending_human_approval",
  snapshot_id: "S-001",
  metrics: {
    skill_gap_hours: 0.18,
    cost: { status: "unavailable", reason: "missing_cost_input" },
  },
  metric_definitions: {
    skill_gap_hours: {
      label: "Lacuna ponderada de competência",
      definition: "Déficit de nível ponderado pela carga.",
      unit: "proficiency-level × configured load unit",
      source: "OptimizationRun.result.feasible_alternatives.objective_metrics.skill_gap_hours",
      direction: "minimize",
    },
  },
  metrics_origin: "deterministic",
  narrative: { status: "unavailable", origin: "unavailable", text: null, claims: [], reason: "narrative_unavailable" },
  unsupportedClaims: [],
  uncertainty: true,
  reason: "missing_cost_input",
  error: { code: "NARRATIVE_UNAVAILABLE" },
};

describe("metric availability", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the configured load unit and the reason a metric is unavailable", async () => {
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

    await screen.findByRole("button", { name: "Carregar mapa" });
    await user.type(screen.getByRole("textbox", { name: "ID da execução para consultar explicação" }), "RUN-001");
    await user.type(screen.getByRole("textbox", { name: "ID da alternativa" }), "A-001");
    await user.click(screen.getByRole("button", { name: "Consultar explicação" }));

    expect(await screen.findByText(/proficiency-level × configured load unit/)).toBeInTheDocument();
    expect(screen.getByText("Indisponível: missing_cost_input")).toBeInTheDocument();
  });
});
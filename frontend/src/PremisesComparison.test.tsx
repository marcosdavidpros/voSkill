import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
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

const scenarioComparison = {
  scenario_ids: ["S-001", "S-002"],
  scenarios: [
    { scenario_id: "S-001", status: "complete", missing: [] },
    { scenario_id: "S-002", status: "complete", missing: [] },
  ],
  periods: [
    {
      period: "2026-02",
      assumptions: {
        "S-001": { demand: { Kubernetes: { load_amount: 40 } }, availability: { "P-001": { hours: 40 } } },
        "S-002": { demand: { Kubernetes: { load_amount: 40 } }, availability: { "P-001": { hours: 40 } } },
      },
      changed_values: {},
    },
  ],
};

const alternativeComparison = {
  run_id: "RUN-001",
  run_premises: {
    snapshot_id: "S-001",
    algorithm: "NSGA-II",
    algorithm_version: "pymoo-0.6.2",
    seed: 42,
    configuration: { population_size: 64, generations: 40, objectives: ["skill_gap_hours", "peak_utilization"] },
  },
  constraint_trace: {
    checked_hard_constraints: ["availability_missing", "capacity_exceeded"],
    conflicting_constraint_ids: ["capacity:P-001:2026-01"],
    rejected_alternatives: [
      {
        alternative_id: "A-003",
        violations: [
          { code: "capacity_exceeded", person_id: "P-001", period: "2026-01", assigned_hours: 48, available_hours: 40 },
        ],
      },
    ],
    soft_preference_metrics: [],
  },
  alternatives: [
    {
      alternative_id: "A-001",
      objective_metrics: {
        skill_gap_hours: { status: "available", value: 0.18, unit: "configured load unit", source: "OptimizationRun" },
        peak_utilization: { status: "available", value: 0.7, unit: "ratio", source: "OptimizationRun" },
      },
    },
    {
      alternative_id: "A-002",
      objective_metrics: {
        skill_gap_hours: { status: "available", value: 0.22, unit: "configured load unit", source: "OptimizationRun" },
        peak_utilization: { status: "unavailable", reason: "missing_peak_utilization_input" },
      },
    },
  ],
  trade_offs: [],
  metric_definitions: {
    skill_gap_hours: {
      label: "Lacuna ponderada de competência",
      definition: "Déficit ponderado pela carga.",
      unit: "configured load unit",
      source: "OptimizationRun",
      direction: "minimize",
    },
    peak_utilization: {
      label: "Pico de utilização",
      definition: "Maior carga sobre disponibilidade.",
      unit: "ratio",
      source: "OptimizationRun",
      direction: "minimize",
    },
  },
};

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.includes("competency-map")
        ? competencyMap
        : url.includes("risk-panel")
          ? riskPanel
          : url.includes("/compare/S-002")
            ? scenarioComparison
            : alternativeComparison;
      return { ok: true, json: async () => body };
    }),
  );
}

describe("comparison premises", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows assumptions for both scenarios even when values are unchanged", async () => {
    const user = userEvent.setup();
    stubFetch();
    render(<App />);

    const panel = screen.getByRole("tabpanel", { name: "Cenários" });
    await user.type(within(panel).getByRole("textbox", { name: "Cenário base" }), "S-001");
    await user.type(within(panel).getByRole("textbox", { name: "Cenário para comparar" }), "S-002");
    await user.click(within(panel).getByRole("button", { name: "Comparar cenários" }));

    const results = await screen.findByRole("region", { name: "Comparação de cenários" });
    expect(within(results).getAllByText(/Kubernetes.*load_amount.*40/)).toHaveLength(2);
    expect(within(results).getAllByText(/P-001.*hours.*40/)).toHaveLength(2);
    expect(within(results).getAllByText("Sem alteração").length).toBeGreaterThan(0);
  });

  it("shows recorded run premises and constraint violations as text", async () => {
    const user = userEvent.setup();
    stubFetch();
    render(<App />);

    await user.click(screen.getByRole("tab", { name: "Alternativas" }));
    const panel = screen.getByRole("tabpanel", { name: "Alternativas" });
    await user.type(within(panel).getByRole("textbox", { name: "ID da execução" }), "RUN-001");
    await user.type(within(panel).getByRole("textbox", { name: "Alternativa 1" }), "A-001");
    await user.type(within(panel).getByRole("textbox", { name: "Alternativa 2" }), "A-002");
    await user.click(within(panel).getByRole("button", { name: "Comparar alternativas" }));

    const premises = await screen.findByRole("region", { name: "Premissas da execução" });
    expect(within(premises).getByText("S-001")).toBeInTheDocument();
    expect(within(premises).getByText("NSGA-II")).toBeInTheDocument();
    expect(within(premises).getByText("42")).toBeInTheDocument();
    expect(within(premises).getByText(/capacity_exceeded.*48.*40/)).toBeInTheDocument();
    expect(within(premises).getByText("availability_missing · capacity_exceeded")).toBeInTheDocument();
  });
});
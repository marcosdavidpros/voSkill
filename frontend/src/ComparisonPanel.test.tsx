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
  coverage: { confirmed_count: 1, skill_count: 1, ratio: 1 },
  summary: "1 of 1 demanded skills have confirmed coverage.",
  skills: [],
};

const riskPanel = { scenario_id: "S-001", project_id: "P-001", thresholds: {}, risks: [] };

const scenarioComparison = {
  scenario_ids: ["S-001", "S-002"],
  scenarios: [
    { scenario_id: "S-001", status: "complete", missing: [] },
    { scenario_id: "S-002", status: "incomplete", missing: [{ period: "2026-02", field: "availability" }] },
  ],
  periods: [
    {
      period: "2026-02",
      assumptions: {
        "S-001": { demand: 40 },
        "S-002": { demand: 48 },
      },
      changed_values: { demand: { "S-001": 40, "S-002": 48 } },
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
    conflicting_constraint_ids: [],
    rejected_alternatives: [],
    soft_preference_metrics: [],
  },
  alternatives: [
    {
      alternative_id: "A-001",
      objective_metrics: {
        skill_gap_hours: { status: "available", value: 0.18, unit: "proficiency-level × configured load unit", source: "OptimizationRun" },
        peak_utilization: { status: "available", value: 0.7, unit: "ratio", source: "OptimizationRun" },
      },
    },
    {
      alternative_id: "A-002",
      objective_metrics: {
        skill_gap_hours: { status: "available", value: 0.22, unit: "proficiency-level × configured load unit", source: "OptimizationRun" },
        peak_utilization: { status: "unavailable", reason: "missing_peak_utilization_input" },
      },
    },
  ],
  trade_offs: [{ alternative_ids: ["A-001", "A-002"], objectives: ["peak_utilization", "skill_gap_hours"] }],
  metric_definitions: {
    skill_gap_hours: {
      label: "Lacuna ponderada de competência",
      definition: "Déficit de nível ponderado pela carga.",
      unit: "proficiency-level × configured load unit",
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

function stubDashboardFetch() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes("competency-map")
      ? competencyMap
      : url.includes("risk-panel")
        ? riskPanel
        : url.includes("/compare/S-002")
          ? scenarioComparison
          : alternativeComparison;
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("accessible comparison panel", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("compares scenarios and labels missing inputs in text", async () => {
    const user = userEvent.setup();
    stubDashboardFetch();
    render(<App />);

    await user.click(await screen.findByRole("tab", { name: "Cenários" }));
    await user.type(screen.getByRole("textbox", { name: "Cenário base" }), "S-001");
    await user.type(screen.getByRole("textbox", { name: "Cenário para comparar" }), "S-002");
    await user.click(screen.getByRole("button", { name: "Comparar cenários" }));

    const results = await screen.findByRole("region", { name: "Comparação de cenários" });
    expect(within(results).getAllByRole("listitem")[1]).toHaveTextContent("S-002");
    expect(within(results).getAllByRole("listitem")[1]).toHaveTextContent("Incompleto");
    expect(within(results).getByText(/2026-02.*availability/)).toBeInTheDocument();
    const table = within(results).getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Estado" })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /2026-02 demand 40 48 Alterada/ })).toBeInTheDocument();
  });

  it("compares alternatives without ranking and exposes unavailable reasons", async () => {
    const user = userEvent.setup();
    const fetchMock = stubDashboardFetch();
    render(<App />);

    await user.click(await screen.findByRole("tab", { name: "Alternativas" }));
    const panel = screen.getByRole("tabpanel", { name: "Alternativas" });
    await user.type(within(panel).getByRole("textbox", { name: "ID da execução" }), "RUN-001");
    await user.type(within(panel).getByRole("textbox", { name: "Alternativa 1" }), "A-001");
    await user.type(within(panel).getByRole("textbox", { name: "Alternativa 2" }), "A-002");
    await user.click(within(panel).getByRole("button", { name: "Comparar alternativas" }));

    const results = await screen.findByRole("region", { name: "Comparação de alternativas" });
    expect(within(results).getByRole("table")).toBeInTheDocument();
    expect(within(results).getByText("Trade-off")).toBeInTheDocument();
    expect(within(results).getByText(/missing_peak_utilization_input/)).toBeInTheDocument();
    expect(within(results).queryByText(/score agregado/i)).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/optimization-runs/RUN-001/alternatives/compare",
      expect.objectContaining({ method: "POST", body: '{"alternative_ids":["A-001","A-002"]}' }),
    );
  });

  it("moves tab focus and selection with the keyboard", async () => {
    const user = userEvent.setup();
    stubDashboardFetch();
    render(<App />);

    const scenariosTab = await screen.findByRole("tab", { name: "Cenários" });
    const alternativesTab = screen.getByRole("tab", { name: "Alternativas" });
    scenariosTab.focus();
    await user.keyboard("{ArrowRight}");

    expect(alternativesTab).toHaveFocus();
    expect(alternativesTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Alternativas" })).toBeInTheDocument();
  });

  it("moves keyboard focus to the scenario comparison table after submission", async () => {
    const user = userEvent.setup();
    stubDashboardFetch();
    render(<App />);

    const panel = screen.getByRole("tabpanel", { name: "Cenários" });
    await user.type(within(panel).getByRole("textbox", { name: "Cenário base" }), "S-001");
    await user.type(within(panel).getByRole("textbox", { name: "Cenário para comparar" }), "S-002");
    await user.click(within(panel).getByRole("button", { name: "Comparar cenários" }));

    const results = await screen.findByRole("region", { name: "Comparação de cenários" });
    const tableRegion = within(results).getByRole("region", { name: "Tabela de comparação de cenários" });
    await user.tab();
    expect(tableRegion).toHaveFocus();
  });
});
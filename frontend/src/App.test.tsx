import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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
  thresholds: { JAVA: 2 },
  risks: [
    {
      skill_id: "JAVA",
      skill_name: "Java",
      confirmed_count: 1,
      threshold: 2,
      people: [{ person_id: "P-001", evidence: "Entrega de serviço Java" }],
    },
  ],
};

function stubMapAndRiskPanel() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => ({
      ok: true,
      json: async () => (String(input).includes("risk-panel") ? riskPanel : competencyMap),
    })),
  );
}

describe("competency map", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows explicit states and confidence, not color-only signals", async () => {
    stubMapAndRiskPanel();
    render(<App />);

    const coverageTable = await screen.findByRole("table");
    expect(within(coverageTable).getByText("Java")).toBeInTheDocument();
    expect(screen.getByText("Confirmada")).toBeInTheDocument();
    expect(screen.getByText("Inferida")).toBeInTheDocument();
    expect(screen.getByText("Sem cobertura")).toBeInTheDocument();
    expect(screen.getByText(/65% de confiança/)).toBeInTheDocument();
    expect(screen.getByText(/pending_review/)).toBeInTheDocument();
    expect(screen.getByText("1 de 3 skills com cobertura confirmada")).toBeInTheDocument();
  });

  it("allows keyboard access to the scenario control and load action", async () => {
    const user = userEvent.setup();
    stubMapAndRiskPanel();
    render(<App />);

    await screen.findByRole("button", { name: "Carregar mapa" });
    const wordmark = screen.getByRole("link", { name: "voSkill, ir ao conteúdo" });
    const scenarioInput = screen.getByRole("textbox", { name: /Cenário/ });
    const loadButton = screen.getByRole("button", { name: "Carregar mapa" });
    const tableRegion = screen.getByRole("region", {
      name: "Tabela de cobertura de competências",
    });
    await user.tab();
    expect(wordmark).toHaveFocus();
    await user.tab();
    expect(scenarioInput).toHaveFocus();
    await user.tab();
    expect(loadButton).toHaveFocus();
    await user.tab();
    expect(tableRegion).toHaveFocus();
  });

  it("shows a configured critical-skill risk and saves a new threshold", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "PUT") {
        return { ok: true, json: async () => ({ ...riskPanel.thresholds, JAVA: 3 }) };
      }
      return {
        ok: true,
        json: async () => (url.includes("risk-panel") ? riskPanel : competencyMap),
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByText("1 confirmado de 2 necessários")).toBeInTheDocument();
    const riskPanelRegion = screen.getByRole("region", {
      name: "Risco por limiar configurado",
    });
    expect(within(riskPanelRegion).getByText(/Entrega de serviço Java/)).toBeInTheDocument();
    const thresholdInput = screen.getByRole("spinbutton", {
      name: "Limiar de pessoas confirmadas",
    });
    await waitFor(() => expect(thresholdInput).toHaveValue(2));
    await user.clear(thresholdInput);
    await user.type(thresholdInput, "3");
    await user.click(screen.getByRole("button", { name: "Salvar limiar" }));

    expect(await screen.findByText("Limiar salvo.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/P-001/critical-skill-thresholds/JAVA",
      expect.objectContaining({ method: "PUT", body: '{"threshold":3}' }),
    );
  });
});
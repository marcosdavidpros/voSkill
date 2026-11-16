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

const alternativeExplanation = {
  run_id: "RUN-001",
  alternative_id: "A-001",
  decision_support: true,
  operational_status: "pending_human_approval",
  snapshot_id: "S-001",
  metrics: { coverage: 0.82, load: 0.7, cost: 1200 },
  metrics_origin: "deterministic",
  narrative: {
    status: "generated",
    origin: "generated",
    text: "Cobertura apoiada pelas evidências registradas.",
    claims: [],
    reason: null,
  },
  unsupportedClaims: [],
  uncertainty: false,
  reason: null,
  error: null,
};

const scenarioList = [
  { scenario_id: "S-001", scenario_name: "Baseline", scenario_type: "BASE", project_id: "P-001", project_name: "Atlas" },
];

function stubMapAndRiskPanel() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) };
      }
      if (url === "/api/scenarios") return { ok: true, json: async () => scenarioList };
      return {
        ok: true,
        json: async () => (url.includes("risk-panel") ? riskPanel : competencyMap),
      };
    }),
  );
}

describe("competency map", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows login and does not request protected data without a session", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: { code: "AUTHENTICATION_REQUIRED" } }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByLabelText("Matrícula")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/me", expect.objectContaining({ credentials: "include" }));
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("competency-map"), expect.anything());
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

    await screen.findByRole("region", { name: "Tabela de cobertura de competências" });
    const wordmark = screen.getByRole("link", { name: "NorteiaSkills, ir ao conteúdo" });
    const scenarioInput = screen.getByRole("combobox", { name: "Cenário" });
    const loadButton = screen.getByRole("button", { name: "Carregar mapa" });
    const signOutButton = screen.getByRole("button", { name: "Sair" });
    const tableRegion = screen.getByRole("region", {
      name: "Tabela de cobertura de competências",
    });
    await user.tab();
    expect(wordmark).toHaveFocus();
    for (const name of ["Mapa do cenário", "Decisão operacional", "Cálculo", "Pessoas", "Skills", "Projetos"]) {
      await user.tab();
      expect(screen.getByRole("button", { name })).toHaveFocus();
    }
    await user.tab();
    expect(signOutButton).toHaveFocus();
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
      if (url.endsWith("/auth/me")) {
        return { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) };
      }
      if (init?.method === "PUT") {
        return { ok: true, json: async () => ({ ...riskPanel.thresholds, JAVA: 3 }) };
      }
      if (url === "/api/scenarios") return { ok: true, json: async () => scenarioList };
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

  it("labels an alternative as decision support awaiting human approval", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/auth/me")) {
          return { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) };
        }
        if (url === "/api/scenarios") return { ok: true, json: async () => scenarioList };
        if (url === "/api/optimization-runs") {
          return { ok: true, json: async () => [{ run_id: "RUN-001", created_at: "2026-11-09T12:00:00Z", scenario_name: "Baseline", project_name: "Atlas", alternative_ids: ["A-001"] }] };
        }
        return {
          ok: true,
          json: async () =>
            url.includes("/explanation")
              ? alternativeExplanation
              : url.includes("risk-panel")
                ? riskPanel
                : competencyMap,
        };
      }),
    );
    render(<App />);

    await screen.findByRole("button", { name: "Carregar mapa" });
    await user.click(screen.getByRole("button", { name: "Cálculo" }));
    const lookup = await screen.findByRole("region", { name: "Explicação da alternativa" });
    await within(lookup).findByRole("option", { name: /Atlas · Baseline · / });
    await user.selectOptions(within(lookup).getByRole("combobox", { name: "Execução" }), "RUN-001");
    await user.selectOptions(within(lookup).getByRole("combobox", { name: "Alternativa" }), "A-001");
    await user.click(screen.getByRole("button", { name: "Consultar explicação" }));

    expect(await screen.findByText("Apoio à decisão")).toBeInTheDocument();
    expect(screen.getByText("Pendente de aprovação humana")).toBeInTheDocument();
    expect(screen.getByText("0,82")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aplicar alternativa" })).not.toBeInTheDocument();
  });

  it("logs in, shows the canonical matricula and clears data on logout", async () => {
    const user = userEvent.setup();
    let authenticated = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return authenticated
          ? { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) }
          : { ok: false, status: 401, json: async () => ({ detail: { code: "AUTHENTICATION_REQUIRED" } }) };
      }
      if (url.endsWith("/auth/login")) {
        authenticated = true;
        return { ok: true, status: 204, json: async () => null };
      }
      if (url.endsWith("/auth/logout")) {
        authenticated = false;
        return { ok: true, status: 204, json: async () => null };
      }
      return { ok: true, json: async () => (url === "/api/scenarios" ? scenarioList : url.includes("risk-panel") ? riskPanel : competencyMap) };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.type(await screen.findByLabelText("Matrícula"), "a0091250");
    await user.type(screen.getByLabelText("Senha"), "secret");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("A0091250")).toBeInTheDocument();
    expect(await screen.findByRole("table")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Sair" }));
    expect(await screen.findByLabelText("Matrícula")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("lets the user pick a registered scenario by name and loads its map", async () => {
    const user = userEvent.setup();
    const scenarios = [
      ...scenarioList,
      { scenario_id: "S-002", scenario_name: "Cenário Q3", scenario_type: "BASE", project_id: "P-001", project_name: "Atlas" },
    ];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) };
      }
      if (url === "/api/scenarios") return { ok: true, json: async () => scenarios };
      return { ok: true, json: async () => (url.includes("risk-panel") ? riskPanel : competencyMap) };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const select = await screen.findByRole("combobox", { name: "Cenário" });
    await screen.findByRole("table");
    expect(within(select).getByRole("option", { name: "Atlas · Cenário Q3" })).toBeInTheDocument();
    await user.selectOptions(select, "S-002");
    await user.click(screen.getByRole("button", { name: "Carregar mapa" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/scenarios/S-002/competency-map", expect.anything()));
  });

  it("shows project, scenario and skill names instead of ids", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) };
      }
      if (url === "/api/scenarios") return { ok: true, json: async () => scenarioList };
      if (url === "/api/skills") return { ok: true, json: async () => [{ skill_id: "CLOUD", skill_name: "Nuvem", description: null }] };
      return { ok: true, json: async () => (url.includes("risk-panel") ? riskPanel : competencyMap) };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const table = await screen.findByRole("table");
    expect(within(table).getByRole("rowheader", { name: "Nuvem" })).toBeInTheDocument();
    expect(within(table).queryByText("CLOUD")).not.toBeInTheDocument();
    expect(screen.getByText(/Projeto Atlas/)).toHaveTextContent("Projeto Atlas · Cenário Baseline");
  });

  it("organizes the sections in a main menu and shows one area at a time", async () => {
    const user = userEvent.setup();
    stubMapAndRiskPanel();
    render(<App />);

    const menu = await screen.findByRole("navigation", { name: "Menu principal" });
    expect(within(menu).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Mapa do cenário", "Decisão operacional", "Cálculo", "Pessoas", "Skills", "Projetos",
    ]);
    expect(within(menu).getByRole("button", { name: "Mapa do cenário" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByRole("heading", { name: "Risco por limiar configurado" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Otimização do cenário" })).not.toBeInTheDocument();

    await user.click(within(menu).getByRole("button", { name: "Cálculo" }));
    for (const heading of ["Otimização do cenário", "Explicação da alternativa", "Cenários e alternativas"]) {
      expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    }
    expect(screen.queryByRole("heading", { name: "Risco por limiar configurado" })).not.toBeInTheDocument();

    await user.click(within(menu).getByRole("button", { name: "Decisão operacional" }));
    expect(await screen.findByRole("heading", { name: "Plano operacional da alternativa" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Otimização do cenário" })).not.toBeInTheDocument();

    await user.click(within(menu).getByRole("button", { name: "Pessoas" }));
    expect(await screen.findByRole("heading", { name: "Competências por pessoa" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Nova skill")).not.toBeInTheDocument();

    await user.click(within(menu).getByRole("button", { name: "Projetos" }));
    const tabs = await screen.findByRole("tablist", { name: "Seções de projetos" });
    expect(within(tabs).getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Projetos", "Demandas", "Cenários"]);
  });

  it("shows the brand login screen without the application menu", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: { code: "AUTHENTICATION_REQUIRED" } }),
    })));
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Entrar no NorteiaSkills" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Vivo" })).toHaveAttribute("src", "/images/vivo-logo-branco.png");
    expect(screen.queryByRole("navigation", { name: "Menu principal" })).not.toBeInTheDocument();
  });

  it("guides the user to create a scenario when none exists", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return { ok: true, json: async () => ({ actor_id: "A0091250", can_view: true, can_edit: false }) };
      }
      return { ok: true, json: async () => [] };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByText("Crie um cenário-base abaixo para consultar a cobertura")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Carregar mapa" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("competency-map"), expect.anything());
  });
});
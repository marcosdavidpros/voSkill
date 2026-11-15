import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import CompetencyPanel from "./CompetencyPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("loads, creates and corrects competencies for an existing person", async () => {
  const user = userEvent.setup();
  const record = {
    competency_id: "C-001", person_id: "P-001", skill_id: "SKILL-1",
    skill_name: "Java", proficiency_level: 4, evidence: "Projeto", origin_type: "MANUAL",
    actor_id: "local-development", review_date: "2026-11-12",
  };
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => ({
    ok: true,
    json: async () => {
      const url = String(_input);
      if (url === "/api/people") return [{ person_id: "P-001", display_name: "Alex" }];
      if (url === "/api/skills") return [{ skill_id: "SKILL-1", skill_name: "Java", description: null }];
      return init?.method === "POST" || init?.method === "PATCH" ? record : [record];
    },
  }));
  vi.stubGlobal("fetch", fetchMock);
  render(<CompetencyPanel />);

  await user.click(screen.getByRole("button", { name: "Carregar pessoas e skills" }));
  await screen.findByRole("option", { name: "Alex" });
  await user.selectOptions(screen.getByLabelText("Pessoa"), "P-001");
  await user.click(screen.getByRole("button", { name: "Consultar competências" }));
  expect(await screen.findByRole("row", { name: /Java/ })).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Skill"), "SKILL-1");
  await user.selectOptions(screen.getByLabelText("Nível"), "4");
  await user.type(screen.getByLabelText("Evidência"), "Projeto");
  await user.type(screen.getByLabelText("Data da revisão"), "2026-11-12");
  await user.click(screen.getByRole("button", { name: "Cadastrar competência" }));
  expect(fetchMock).toHaveBeenCalledWith("/api/people/P-001/competencies", expect.objectContaining({
    method: "POST",
  }));
  const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({ skill_id: "SKILL-1", proficiency_level: 4, evidence: "Projeto", review_date: "2026-11-12" });
  const row = screen.getByRole("row", { name: /Java/ });
  await user.click(within(row).getByRole("button", { name: /editar/i }));
  await user.clear(screen.getByLabelText("Evidência"));
  await user.type(screen.getByLabelText("Evidência"), "Projeto revisado");
  await user.click(screen.getByRole("button", { name: "Salvar alteração" }));
  expect(fetchMock).toHaveBeenCalledWith("/api/people/P-001/competencies/C-001", expect.objectContaining({
    method: "PATCH",
    body: JSON.stringify({ proficiency_level: 4, evidence: "Projeto revisado", review_date: "2026-11-12" }),
  }));
});

it("explains when a person is not authorized", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    json: async () => ({ detail: { code: "FORBIDDEN" } }),
  })));
  const user = userEvent.setup();
  render(<CompetencyPanel />);
  await user.click(screen.getByRole("button", { name: "Carregar pessoas e skills" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Seu perfil pode consultar, mas não cadastrar");
});

it("loads the catalog and creates selectable people and skills", async () => {
  const people = [{ person_id: "P-001", display_name: "Alex" }];
  const skills = [{ skill_id: "SKILL-1", skill_name: "Java", description: null }];
  const competencies: unknown[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/people/P-002/competencies" && init?.method === "GET") {
      return { ok: true, json: async () => competencies };
    }
    if (url === "/api/people" && init?.method === "POST") {
      const person = { person_id: "P-002", display_name: "Sam" };
      people.push(person);
      return { ok: true, json: async () => person };
    }
    if (url === "/api/skills" && init?.method === "POST") {
      const skill = { skill_id: "SKILL-2", skill_name: "Go", description: null };
      skills.push(skill);
      return { ok: true, json: async () => skill };
    }
    return { ok: true, json: async () => url === "/api/people" ? people : url === "/api/skills" ? skills : competencies };
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<CompetencyPanel />);

  await user.click(screen.getByRole("button", { name: "Carregar pessoas e skills" }));
  expect(await screen.findByRole("option", { name: "Alex" })).toBeInTheDocument();

  await user.type(screen.getByLabelText("Nova pessoa"), "Sam");
  await user.click(screen.getByRole("button", { name: "Cadastrar pessoa" }));
  expect(await screen.findByRole("option", { name: "Sam" })).toBeInTheDocument();
  expect(screen.getByLabelText("Pessoa")).toHaveValue("P-002");
  await user.click(screen.getByRole("button", { name: "Consultar competências" }));
  expect(await screen.findByRole("option", { name: "Java" })).toBeInTheDocument();

  await user.type(screen.getByLabelText("Nova skill"), "Go");
  await user.click(screen.getByRole("button", { name: "Cadastrar skill" }));
  expect(await screen.findByRole("option", { name: "Go" })).toBeInTheDocument();
  expect(screen.getByLabelText("Skill")).toHaveValue("SKILL-2");
});
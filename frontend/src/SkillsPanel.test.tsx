import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SkillsPanel from "./SkillsPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const python = { skill_id: "SK-1", skill_name: "Python", description: "Linguagem" };

it("lists the catalog skills on open and creates a new one", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "POST") {
      return { ok: true, status: 201, json: async () => ({ skill_id: "SK-2", skill_name: "Go", description: null }) };
    }
    return { ok: true, status: 200, json: async () => [python] };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<SkillsPanel />);

  const table = await screen.findByRole("region", { name: "Skills cadastradas" });
  expect(await within(table).findByRole("row", { name: /Python Linguagem/ })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/skills", expect.objectContaining({ method: "GET" }));

  await user.type(screen.getByLabelText("Nova skill"), "Go");
  await user.click(screen.getByRole("button", { name: "Cadastrar skill" }));

  const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({ skill_name: "Go" });
  expect(await screen.findByText("Skill Go cadastrada.")).toBeInTheDocument();
  expect(within(table).getByRole("row", { name: /Go/ })).toBeInTheDocument();
});

it("explains permission and duplicate errors without changing the list", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => (
    init?.method === "POST"
      ? { ok: false, status: 409, json: async () => ({ detail: { code: "SKILL_ALREADY_EXISTS" } }) }
      : { ok: true, status: 200, json: async () => [python] }
  )));
  render(<SkillsPanel />);

  await screen.findByRole("row", { name: /Python/ });
  await user.type(screen.getByLabelText("Nova skill"), "Python");
  await user.click(screen.getByRole("button", { name: "Cadastrar skill" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Essa skill já existe no catálogo.");
  expect(screen.getAllByRole("row", { name: /Python/ })).toHaveLength(1);
});

it("edits the name and description of an existing skill with PATCH", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => (
    init?.method === "PATCH"
      ? { ok: true, status: 200, json: async () => ({ skill_id: "SK-1", ...JSON.parse(String(init.body)) }) }
      : { ok: true, status: 200, json: async () => [python] }
  ));
  vi.stubGlobal("fetch", fetchMock);
  render(<SkillsPanel />);

  await user.click(await screen.findByRole("button", { name: "Editar Python" }));
  expect(screen.getByLabelText("Nome da skill")).toHaveValue("Python");
  expect(screen.getByLabelText("Descrição")).toHaveValue("Linguagem");
  await user.clear(screen.getByLabelText("Nome da skill"));
  await user.type(screen.getByLabelText("Nome da skill"), "Python 3");
  await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

  const patchCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
  expect(patchCall?.[0]).toBe("/api/skills/SK-1");
  expect(JSON.parse(String(patchCall?.[1]?.body))).toEqual({ skill_name: "Python 3", description: "Linguagem" });
  expect(await screen.findByText("Skill Python 3 atualizada.")).toBeInTheDocument();
  expect(screen.getByRole("row", { name: /Python 3 Linguagem/ })).toBeInTheDocument();
  expect(screen.getByLabelText("Nova skill")).toHaveValue("");
});

it("cancels an edit without saving", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => ({ ok: true, status: 200, json: async () => [python] }));
  vi.stubGlobal("fetch", fetchMock);
  render(<SkillsPanel />);

  await user.click(await screen.findByRole("button", { name: "Editar Python" }));
  await user.click(screen.getByRole("button", { name: "Cancelar edição" }));

  expect(screen.getByLabelText("Nova skill")).toHaveValue("");
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
});

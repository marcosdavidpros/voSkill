import { useEffect, useState } from "react";

import { createPerson, createSkill, fetchPeople, fetchSkills, type CatalogPerson, type CatalogSkill } from "./api";

type CatalogSetupProps = {
  loaded: boolean;
  onLoaded: (people: CatalogPerson[], skills: CatalogSkill[]) => void;
  onPersonCreated: (person: CatalogPerson) => void;
  onSkillCreated: (skill: CatalogSkill) => void;
  showSkillForm?: boolean;
  active?: boolean;
};

function friendlyError(caught: unknown): string {
  const code = caught instanceof Error ? caught.message : "Erro de conexão";
  const messages: Record<string, string> = {
    AUTHENTICATION_REQUIRED: "Acesso não autenticado. Verifique a configuração do servidor.",
    FORBIDDEN: "Seu perfil pode consultar, mas não cadastrar pessoas ou skills.",
    REQUIRED_DISPLAY_NAME: "Informe o nome da pessoa.",
    REQUIRED_SKILL_NAME: "Informe o nome da skill.",
    SKILL_ALREADY_EXISTS: "Essa skill já existe no catálogo.",
  };
  return messages[code] ?? code;
}

export default function CatalogSetup({ loaded, onLoaded, onPersonCreated, onSkillCreated, showSkillForm = true, active = true }: CatalogSetupProps) {
  const [personName, setPersonName] = useState("");
  const [skillName, setSkillName] = useState("");
  const [skillDescription, setSkillDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadCatalogs() {
    setBusy(true);
    setError(null);
    try {
      const [people, skills] = await Promise.all([fetchPeople(), fetchSkills()]);
      if (!Array.isArray(people) || !Array.isArray(skills)) throw new Error("INVALID_CATALOG_RESPONSE");
      onLoaded(people, skills);
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (active) void loadCatalogs();
  }, [active]);

  async function submitPerson(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const person = await createPerson(personName.trim());
      onPersonCreated(person);
      setPersonName("");
      setMessage(`Pessoa ${person.display_name} cadastrada e selecionada.`);
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function submitSkill(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const skill = await createSkill(skillName.trim(), skillDescription.trim() || undefined);
      onSkillCreated(skill);
      setSkillName("");
      setSkillDescription("");
      setMessage(`Skill ${skill.skill_name} cadastrada e selecionada.`);
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="catalog-setup">
      {!loaded ? (
        busy ? <p role="status">Carregando pessoas e skills…</p> : (
          <button type="button" onClick={() => void loadCatalogs()}>Tentar carregar novamente</button>
        )
      ) : (
        <div className="catalog-forms">
          <form className="competency-lookup" onSubmit={submitPerson}>
            <label htmlFor="new-person-name">Nova pessoa<input id="new-person-name" value={personName} disabled={busy} onChange={(event) => setPersonName(event.target.value)} required maxLength={200} /></label>
            <button type="submit" disabled={busy || !personName.trim()}>Cadastrar pessoa</button>
          </form>
          {showSkillForm && <form className="competency-lookup" onSubmit={submitSkill}>
            <label htmlFor="new-skill-name">Nova skill<input id="new-skill-name" value={skillName} disabled={busy} onChange={(event) => setSkillName(event.target.value)} required maxLength={150} /></label>
            <label htmlFor="new-skill-description">Descrição<input id="new-skill-description" value={skillDescription} disabled={busy} onChange={(event) => setSkillDescription(event.target.value)} maxLength={1000} /></label>
            <button type="submit" disabled={busy || !skillName.trim()}>Cadastrar skill</button>
          </form>}
        </div>
      )}
      {error && <p className="competency-error" role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </div>
  );
}

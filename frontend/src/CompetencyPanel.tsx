import { useState } from "react";

import {
  competencyRequest,
  type CatalogPerson,
  type CatalogSkill,
  type PersonCompetency,
} from "./api";
import CatalogSetup from "./CatalogSetup";
import { Pager, usePagination } from "./Pagination";

function errorMessage(caught: unknown): string {
  const code = caught instanceof Error ? caught.message : "Erro de conexão";
  const messages: Record<string, string> = {
    AUTHENTICATION_REQUIRED: "Acesso não autenticado. Verifique a configuração do servidor.",
    FORBIDDEN: "Esta pessoa não está autorizada para o acesso atual.",
    REQUIRED_DISPLAY_NAME: "Informe o nome da pessoa.",
    REQUIRED_SKILL_NAME: "Informe o nome da skill.",
    PERSON_NOT_FOUND: "Pessoa não encontrada. Confira o ID informado.",
    UNKNOWN_SKILL: "Skill não encontrada. Confira o ID informado.",
    COMPETENCY_ALREADY_EXISTS: "Esta pessoa já possui a skill. Use Editar para corrigir o registro.",
    COMPETENCY_NOT_FOUND: "Competência não encontrada. Consulte a pessoa novamente.",
    SKILL_ALREADY_EXISTS: "Essa skill já existe no catálogo.",
    VALIDATION_ERROR: "Confira o nível, a evidência e a data informados.",
  };
  return messages[code] ?? code;
}

export default function CompetencyPanel({ peopleOnly = false, active = true }: { peopleOnly?: boolean; active?: boolean }) {
  const [people, setPeople] = useState<CatalogPerson[]>([]);
  const [skills, setSkills] = useState<CatalogSkill[]>([]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);
  const [personId, setPersonId] = useState("");
  const [loadedPerson, setLoadedPerson] = useState("");
  const [records, setRecords] = useState<PersonCompetency[]>([]);
  const [skillId, setSkillId] = useState("");
  const [level, setLevel] = useState("3");
  const [evidence, setEvidence] = useState("");
  const [reviewDate, setReviewDate] = useState("");
  const [editing, setEditing] = useState<PersonCompetency | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const recordPages = usePagination(records, undefined, loadedPerson);

  function updateCatalogs(personCatalog: CatalogPerson[], skillCatalog: CatalogSkill[]) {
    setPeople(personCatalog);
    setSkills(skillCatalog);
    setCatalogLoaded(true);
  }

  function addPerson(person: CatalogPerson) {
    setPeople((current) => [...current.filter((item) => item.person_id !== person.person_id), person]
      .sort((first, second) => first.display_name.localeCompare(second.display_name)));
    setPersonId(person.person_id);
    setLoadedPerson("");
    resetForm();
    setMessage(`Pessoa ${person.display_name} cadastrada e selecionada.`);
  }

  function addSkill(skill: CatalogSkill) {
    setSkills((current) => [...current.filter((item) => item.skill_id !== skill.skill_id), skill]
      .sort((first, second) => first.skill_name.localeCompare(second.skill_name)));
    setSkillId(skill.skill_id);
    setMessage(`Skill ${skill.skill_name} cadastrada e selecionada.`);
  }

  function resetForm() {
    setEditing(null);
    setSkillId("");
    setLevel("3");
    setEvidence("");
    setReviewDate("");
  }

  async function load(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = personId.trim();
    if (!target) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    setLoadedPerson("");
    resetForm();
    try {
      const result = await competencyRequest(target, "GET");
      setRecords(result as PersonCompetency[]);
      setLoadedPerson(target);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    const details = { proficiency_level: Number(level), evidence: evidence.trim(), review_date: reviewDate };
    try {
      await competencyRequest(loadedPerson, editing ? "PATCH" : "POST", editing ? details : { ...details, skill_id: skillId.trim() }, editing?.competency_id);
      resetForm();
      setMessage("Competência salva.");
      try {
        setRecords(await competencyRequest(loadedPerson, "GET") as PersonCompetency[]);
      } catch {
        setLoadedPerson("");
        setError("A competência foi salva, mas a lista não pôde ser atualizada. Consulte novamente.");
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  function edit(record: PersonCompetency) {
    setEditing(record);
    setSkillId(record.skill_id);
    setLevel(String(record.proficiency_level));
    setEvidence(record.evidence);
    setReviewDate(record.review_date);
    setMessage(null);
    setError(null);
  }

  return (
    <section className="competency-section" aria-labelledby="competency-heading">
      <div className="section-heading"><div><p className="eyebrow">PESSOAS</p><h2 id="competency-heading">Competências por pessoa</h2></div></div>
      <CatalogSetup
        loaded={catalogLoaded}
        onLoaded={updateCatalogs}
        onPersonCreated={addPerson}
        onSkillCreated={addSkill}
        showSkillForm={!peopleOnly}
        active={active}
      />
      {catalogLoaded && <>
          <form className="competency-lookup" onSubmit={load}>
            <label htmlFor="catalog-person">Pessoa<select id="catalog-person" value={personId} disabled={busy} onChange={(event) => { setPersonId(event.target.value); setLoadedPerson(""); resetForm(); }} required>
              <option value="">Selecione uma pessoa</option>
              {people.map((person) => <option key={person.person_id} value={person.person_id}>{person.display_name}</option>)}
            </select></label>
            <button type="submit" disabled={busy || !personId}>Consultar competências</button>
          </form>
        </>}
      {error && <p className="competency-error" role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {loadedPerson && <>
        <h3>Competências de {loadedPerson}</h3>
        {records.length === 0 ? <p>Nenhuma competência cadastrada.</p> : <div className="table-scroll" role="region" aria-label="Competências cadastradas" tabIndex={0}>
          <table><caption className="visually-hidden">Competências cadastradas da pessoa</caption><thead><tr><th scope="col">Skill</th><th scope="col">Nível</th><th scope="col">Evidência</th><th scope="col">Revisão</th><th scope="col">Ação</th></tr></thead>
            <tbody>{recordPages.visible.map((record) => <tr key={record.competency_id}><th scope="row">{record.skill_name}</th><td>{record.proficiency_level}/5</td><td>{record.evidence}</td><td>{record.review_date}</td><td><button type="button" disabled={busy} onClick={() => edit(record)} aria-label={`Editar ${record.skill_name}`}>Editar</button></td></tr>)}</tbody>
          </table>
          <Pager pagination={recordPages} label="competências" />
        </div>}
        <form className="competency-form" onSubmit={save}>
          <h3>{editing ? `Editar ${editing.skill_name}` : "Cadastrar competência"}</h3>
          <label htmlFor="competency-skill">Skill<select id="competency-skill" value={skillId} onChange={(event) => setSkillId(event.target.value)} disabled={busy || !!editing} required>
            <option value="">Selecione uma skill</option>
            {skills.map((skill) => <option key={skill.skill_id} value={skill.skill_id}>{skill.skill_name}</option>)}
          </select></label>
          <label>Nível<select value={level} onChange={(event) => setLevel(event.target.value)} disabled={busy}>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Evidência<textarea value={evidence} onChange={(event) => setEvidence(event.target.value)} disabled={busy} maxLength={4000} required /></label>
          <label>Data da revisão<input type="date" value={reviewDate} onChange={(event) => setReviewDate(event.target.value)} disabled={busy} required /></label>
          <div className="competency-actions"><button type="submit" disabled={busy || !evidence.trim() || !skillId.trim()}>{editing ? "Salvar alteração" : "Cadastrar competência"}</button>{editing && <button type="button" disabled={busy} onClick={resetForm}>Cancelar edição</button>}</div>
        </form>
      </>}
    </section>
  );
}
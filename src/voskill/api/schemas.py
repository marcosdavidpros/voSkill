from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class DemandPayload(BaseModel):
    skill_id: str = Field(min_length=1)
    proficiency_level: int = Field(ge=1, le=5)
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    load_amount: Decimal = Field(ge=0)
    load_unit: str = Field(min_length=1)

    @property
    def period_start(self) -> date:
        year, month = (int(value) for value in self.period.split("-"))
        return date(year, month, 1)


class CompetencyPayload(BaseModel):
    skill_id: str = Field(min_length=1)
    proficiency_level: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=1)
    review_date: date


class CompetencyCorrectionPayload(BaseModel):
    proficiency_level: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=1)
    review_date: date


class ExtractionPayload(BaseModel):
    source_text: str = Field(max_length=20000)


class ExtractedCompetency(BaseModel):
    skill_name: str = Field(min_length=1, max_length=150)
    proficiency_level: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = Field(min_length=1, max_length=4000)


class SuggestionReviewPayload(BaseModel):
    decision: Literal["accept", "edit", "reject"]
    reviewed_level: int | None = Field(default=None, ge=1, le=5)
    reviewed_evidence: str | None = Field(default=None, min_length=1)


class SkillRelationPayload(BaseModel):
    source_skill_id: str = Field(min_length=1)
    target_skill_id: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class DemandResponse(BaseModel):
    demand_id: str
    project_id: str
    skill_id: str
    proficiency_level: int
    period: str
    load_amount: float
    load_unit: str
    actor_id: str


class CompetencyResponse(BaseModel):
    competency_id: str
    person_id: str
    skill_id: str
    skill_name: str
    proficiency_level: int
    evidence: str
    origin_type: str
    actor_id: str
    review_date: date


class SuggestionResponse(BaseModel):
    suggestion_id: str
    person_id: str
    skill_name: str
    proficiency_level: int
    confidence: float
    evidence_span: str
    source_sha256: str
    status: str
    actor_id: str
    created_at: datetime


class SuggestionReviewResponse(SuggestionResponse):
    reviewed_by: str
    reviewed_at: datetime
    reviewed_level: int | None
    reviewed_evidence: str | None
    competency_id: str | None = None


class SkillRelationResponse(BaseModel):
    relation_id: str
    source_skill_id: str
    target_skill_id: str
    confidence: float
    active: bool
    actor_id: str


class SkillInferenceResponse(BaseModel):
    status: Literal["inferred", "insufficient_evidence"]
    person_id: str
    target_skill_id: str
    inferred_level: int | None
    source_skill_id: str | None
    relation_id: str | None = Field(serialization_alias="relationId")
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: Literal["insufficient_evidence"] | None


class AlternativePayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    deltas: dict[str, object] = Field(min_length=1)


class AlternativeResponse(BaseModel):
    scenario_id: str
    base_scenario_id: str
    project_id: str
    snapshot_id: str
    name: str
    actor_id: str
    created_at: datetime
    deltas: dict[str, object]


class OptimizationRunPayload(BaseModel):
    snapshot: dict[str, object]
    seed: int
    population_size: int = Field(default=64, ge=2, le=10000)
    generations: int = Field(default=40, ge=1, le=10000)


class OptimizationRunResponse(BaseModel):
    run_id: str
    snapshot_hash: str
    algorithm_version: str
    configuration: dict[str, object]
    seed: int
    alternatives_hash: str
    result: dict[str, object]
    actor_id: str
    created_at: datetime


class AlternativeExplanationClaimResponse(BaseModel):
    text: str
    metric_references: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class AlternativeNarrativeResponse(BaseModel):
    status: Literal["generated", "unavailable"]
    origin: Literal["generated", "unavailable"]
    text: str | None
    claims: list[AlternativeExplanationClaimResponse]
    reason: Literal["narrative_unavailable"] | None = None


class AlternativeExplanationResponse(BaseModel):
    run_id: str
    alternative_id: str
    decision_support: Literal[True]
    operational_status: Literal["pending_human_approval"]
    snapshot_id: str
    metrics: dict[str, object]
    metrics_origin: Literal["deterministic"]
    narrative: AlternativeNarrativeResponse
    unsupported_claims: list[AlternativeExplanationClaimResponse] = Field(
        default_factory=list,
        serialization_alias="unsupportedClaims",
    )
    uncertainty: bool
    reason: Literal["missing_evidence", "missing_cost_input", "narrative_unavailable"] | None = None
    error: dict[str, str] | None = None


class CompetencyMapHolderResponse(BaseModel):
    person_id: str
    status: Literal["confirmed", "inferred"]
    skill_name: str | None = None
    proficiency_level: int | None = None
    evidence: str | None = None
    origin_type: str | None = None
    review_date: str | None = None
    inferred_level: int | None = None
    source_skill_id: str | None = None
    relation_id: str | None = None
    confidence: float | None = None
    review_state: str | None = None


class CompetencyMapSkillResponse(BaseModel):
    skill_id: str
    status: Literal["confirmed", "inferred", "uncovered"]
    confirmed_count: int
    holders: list[CompetencyMapHolderResponse]


class CompetencyMapCoverageResponse(BaseModel):
    confirmed_count: int
    skill_count: int
    ratio: float


class CompetencyMapResponse(BaseModel):
    scenario_id: str
    project_id: str
    coverage: CompetencyMapCoverageResponse
    skills: list[CompetencyMapSkillResponse]
    summary: str


class CriticalSkillThresholdPayload(BaseModel):
    threshold: int = Field(strict=True)


class CriticalSkillThresholdResponse(BaseModel):
    project_id: str
    skill_id: str
    threshold: int
    actor_id: str
    updated_at: datetime


class RiskContributorResponse(BaseModel):
    person_id: str
    evidence: str


class CriticalSkillRiskResponse(BaseModel):
    skill_id: str
    skill_name: str
    confirmed_count: int
    threshold: int
    people: list[RiskContributorResponse]


class RiskPanelResponse(BaseModel):
    scenario_id: str
    project_id: str
    thresholds: dict[str, int]
    risks: list[CriticalSkillRiskResponse]
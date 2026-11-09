from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from ...suggestion_review import SuggestionReviewRepository
from ...suggestions import SuggestionError
from ..dependencies import (
    CompetencyExtractor,
    get_competency_editor,
    get_competency_extractor,
    get_competency_reviewer,
    get_suggestion_repository,
)
from ..errors import raise_suggestion_error
from ..schemas import (
    ExtractedCompetency,
    ExtractionPayload,
    SuggestionResponse,
    SuggestionReviewPayload,
    SuggestionReviewResponse,
)

router = APIRouter()


@router.post(
    "/people/{person_id}/competency-suggestions/extract",
    status_code=201,
    response_model=SuggestionResponse,
)
def extract_person_competency_suggestion(
    person_id: str,
    payload: ExtractionPayload,
    actor_id: Annotated[str, Depends(get_competency_editor)],
    extractor: Annotated[CompetencyExtractor, Depends(get_competency_extractor)],
    repository: Annotated[SuggestionReviewRepository, Depends(get_suggestion_repository)],
) -> dict[str, object]:
    if not payload.source_text.strip():
        raise HTTPException(status_code=422, detail={"code": "EMPTY_SOURCE"})

    try:
        extracted = ExtractedCompetency.model_validate(extractor.extract(payload.source_text))
    except SuggestionError as error:
        raise_suggestion_error(error)
    except ValidationError:
        raise_suggestion_error(SuggestionError("INVALID_EXTRACTOR_OUTPUT", 502))

    if extracted.evidence_span not in payload.source_text:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "EVIDENCE_NOT_IN_SOURCE",
                "fieldErrors": {"evidence_span": "EVIDENCE_NOT_IN_SOURCE"},
            },
        )

    try:
        return repository.create_suggestion(
            person_id=person_id,
            skill_name=extracted.skill_name,
            proficiency_level=extracted.proficiency_level,
            confidence=extracted.confidence,
            evidence_span=extracted.evidence_span,
            source_sha256=sha256(payload.source_text.encode("utf-8")).hexdigest(),
            actor_id=actor_id,
        )
    except SuggestionError as error:
        raise_suggestion_error(error)


@router.post(
    "/people/{person_id}/competency-suggestions/{suggestion_id}/review",
    response_model=SuggestionReviewResponse,
)
def review_person_competency_suggestion(
    person_id: str,
    suggestion_id: str,
    payload: SuggestionReviewPayload,
    reviewer_id: Annotated[str, Depends(get_competency_reviewer)],
    repository: Annotated[SuggestionReviewRepository, Depends(get_suggestion_repository)],
) -> dict[str, object]:
    try:
        return repository.review_suggestion(
            person_id=person_id,
            suggestion_id=suggestion_id,
            decision=payload.decision,
            reviewer_id=reviewer_id,
            reviewed_level=payload.reviewed_level,
            reviewed_evidence=payload.reviewed_evidence,
        )
    except SuggestionError as error:
        raise_suggestion_error(error)
from .competencies import router as competencies
from .demands import router as demands
from .optimization_runs import router as optimization_runs
from .scenarios import router as scenarios
from .skill_relations import router as skill_relations
from .suggestions import router as suggestions

__all__ = [
	"competencies",
	"demands",
	"optimization_runs",
	"scenarios",
	"skill_relations",
	"suggestions",
]
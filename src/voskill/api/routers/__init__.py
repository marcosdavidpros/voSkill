from .competencies import router as competencies
from .competency_map import router as competency_map
from .demands import router as demands
from .optimization_runs import router as optimization_runs
from .risk_panel import router as risk_panel
from .scenarios import router as scenarios
from .skill_relations import router as skill_relations
from .suggestions import router as suggestions

__all__ = [
	"competencies",
	"competency_map",
	"demands",
	"optimization_runs",
	"risk_panel",
	"scenarios",
	"skill_relations",
	"suggestions",
]
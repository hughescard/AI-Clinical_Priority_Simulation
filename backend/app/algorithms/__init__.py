from app.algorithms.astar import AStarPlanningAlgorithm
from app.algorithms.base import PlanningAlgorithm
from app.algorithms.cpsat import CPSATPlanningAlgorithm
from app.algorithms.fifo import FIFOPlanningAlgorithm
from app.algorithms.greedy import DynamicGreedyPlanningAlgorithm
from app.algorithms.simulated_annealing import SimulatedAnnealingPlanningAlgorithm


def get_algorithm(name: str) -> PlanningAlgorithm:
    algorithms: dict[str, PlanningAlgorithm] = {
        "fifo": FIFOPlanningAlgorithm(),
        "greedy": DynamicGreedyPlanningAlgorithm(),
        "astar": AStarPlanningAlgorithm(),
        "cpsat": CPSATPlanningAlgorithm(),
        "simulated_annealing": SimulatedAnnealingPlanningAlgorithm(),
    }
    try:
        return algorithms[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported algorithm: {name}") from exc


def list_supported_algorithms() -> tuple[str, ...]:
    return ("fifo", "greedy", "astar", "cpsat", "simulated_annealing")

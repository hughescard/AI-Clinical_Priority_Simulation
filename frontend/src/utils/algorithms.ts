import type { Algorithm } from "../types";

export function formatAlgorithmName(algorithm: Algorithm | string): string {
  if (algorithm === "astar") {
    return "A*";
  }
  if (algorithm === "cpsat") {
    return "CP-SAT";
  }
  if (algorithm === "simulated_annealing") {
    return "Simulated Annealing";
  }
  return algorithm.toUpperCase();
}

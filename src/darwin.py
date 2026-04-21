"""
达尔文进化框架 — 让AI资产自主进化

核心机制：变异→选择→遗传→棘轮（只保留改进）
"""
import json
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class EvolutionResult:
    generation: int
    fitness: float
    mutations: List[str]
    kept: bool
    reason: str

class DarwinEngine:
    def __init__(self, min_improvement=0.01):
        self.min_improvement = min_improvement
        self.best_fitness = 0.0
        self.generation = 0
    
    def evolve(self, current_fitness: float, mutations: List[str]) -> EvolutionResult:
        """进化一轮"""
        self.generation += 1
        improved = current_fitness > self.best_fitness + self.min_improvement
        
        if improved:
            self.best_fitness = current_fitness
            return EvolutionResult(
                generation=self.generation,
                fitness=current_fitness,
                mutations=mutations,
                kept=True,
                reason=f"改进 {(current_fitness-self.best_fitness)*100:.1f}%，保留"
            )
        return EvolutionResult(
            generation=self.generation,
            fitness=current_fitness,
            mutations=mutations,
            kept=False,
            reason="未达到改进阈值，丢弃"
        )
    
    def get_stats(self) -> Dict:
        return {
            "generation": self.generation,
            "best_fitness": self.best_fitness,
        }

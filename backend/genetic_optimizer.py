"""
Genetic Algorithm Optimization for Trading Strategies
Multi-objective optimization for strategy parameter tuning
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import random
from enum import Enum

from backtesting import Backtester, BacktestConfig, BacktestResult
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FitnessMetric(Enum):
    """Fitness metrics for optimization"""
    SHARPE_RATIO = "sharpe_ratio"
    PROFIT_FACTOR = "profit_factor"
    TOTAL_PNL = "total_pnl"
    WIN_RATE = "win_rate"
    MAX_DRAWDOWN = "max_drawdown"
    ADJUSTED_RETURN = "adjusted_return"  # Custom metric


@dataclass
class GeneticAlgorithmConfig:
    """Configuration for genetic algorithm"""
    population_size: int = 50
    max_generations: int = 100
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1
    elite_ratio: float = 0.1
    tournament_size: int = 3
    convergence_threshold: float = 0.01
    stagnation_limit: int = 20
    multi_objective: bool = False
    optimization_metrics: List[FitnessMetric] = field(default_factory=lambda: [FitnessMetric.SHARPE_RATIO])


@dataclass
class Chromosome:
    """Represents a strategy parameter set"""
    genes: Dict[str, Any]
    fitness: float = 0.0
    objectives: Dict[str, float] = field(default_factory=dict)
    rank: int = 0
    crowding_distance: float = 0.0
    generation: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.objectives:
            self.objectives = {}

    def dominates(self, other: 'Chromosome') -> bool:
        """Check if this chromosome dominates another in multi-objective optimization"""
        if not self.objectives or not other.objectives:
            return False

        better_in_all = all(self.objectives[obj] >= other.objectives[obj]
                          for obj in self.objectives.keys())
        better_in_at_least_one = any(self.objectives[obj] > other.objectives[obj]
                                   for obj in self.objectives.keys())

        return better_in_all and better_in_at_least_one


@dataclass
class GeneticOptimizationResult:
    """Results from genetic optimization"""
    best_chromosome: Optional[Chromosome] = None
    pareto_front: List[Chromosome] = field(default_factory=list)
    population_by_generation: List[List[Chromosome]] = field(default_factory=list)
    best_fitness_history: List[float] = field(default_factory=list)
    avg_fitness_history: List[float] = field(default_factory=list)
    top_parameters: List[Dict] = field(default_factory=list)
    execution_time: float = 0.0
    generations_completed: int = 0


class GeneticOptimizer:
    """
    Genetic Algorithm Optimizer for trading strategy parameters
    Supports both single-objective and multi-objective optimization
    """

    def __init__(self, config: GeneticAlgorithmConfig):
        self.config = config
        self.population: List[Chromosome] = []
        self.backtester = Backtester(BacktestConfig())

    def optimize(
        self,
        data: pd.DataFrame,
        strategy: Callable,
        parameter_ranges: Dict[str, Dict[str, Any]],
        weights: Optional[Dict[FitnessMetric, float]] = None
    ) -> GeneticOptimizationResult:
        """
        Run genetic algorithm optimization

        Args:
            data: Historical data for backtesting
            strategy: Strategy function to optimize
            parameter_ranges: Dictionary of parameter ranges
                Example: {"fast_ma": {"min": 5, "max": 50, "type": "int"}}
            weights: Weights for multi-objective optimization

        Returns:
            GeneticOptimizationResult object
        """
        start_time = datetime.now()

        # Initialize population
        self.population = self._initialize_population(parameter_ranges)

        # Evaluate initial population
        self._evaluate_population(data, strategy)

        best_fitness_history = []
        avg_fitness_history = []
        generations_without_improvement = 0
        best_overall_fitness = float('-inf')

        for generation in range(self.config.max_generations):
            logger.debug(f"Generation {generation + 1}/{self.config.max_generations}")

            # Perform genetic operations
            offspring = self._create_offspring(parameter_ranges)

            # Evaluate offspring
            self._evaluate_offspring(offspring, data, strategy)

            # Environmental selection
            if self.config.multi_objective:
                self._nsga_selection(offspring)
            else:
                self._single_objective_selection(offspring)

            # Store population for analysis
            self.population.sort(key=lambda x: x.fitness, reverse=True)
            best_fitness = self.population[0].fitness
            avg_fitness = np.mean([c.fitness for c in self.population])

            best_fitness_history.append(best_fitness)
            avg_fitness_history.append(avg_fitness)

            # Check for improvement
            if best_fitness > best_overall_fitness + self.config.convergence_threshold:
                best_overall_fitness = best_fitness
                generations_without_improvement = 0
            else:
                generations_without_improvement += 1

            if generations_without_improvement >= self.config.stagnation_limit:
                logger.info(f"Convergence reached at generation {generation + 1}")
                break

            # Log progress
            if (generation + 1) % 10 == 0:
                logger.info(f"Gen {generation + 1}: Best={best_fitness:.4f}, Avg={avg_fitness:.4f}")

        # Final population evaluation
        self._evaluate_population(data, strategy)

        # Prepare results
        execution_time = (datetime.now() - start_time).total_seconds()

        result = GeneticOptimizationResult(
            best_chromosome=self.population[0],
            population_by_generation=[self.population],  # Simplified
            best_fitness_history=best_fitness_history,
            avg_fitness_history=avg_fitness_history,
            execution_time=execution_time,
            generations_completed=len(best_fitness_history)
        )

        if self.config.multi_objective:
            result.pareto_front = self._extract_pareto_front(self.population)

        return result

    def _initialize_population(self, parameter_ranges: Dict[str, Dict]) -> List[Chromosome]:
        """Initialize population with random chromosomes"""
        population = []

        for _ in range(self.config.population_size):
            genes = self._create_random_chromosome(parameter_ranges)
            chrom = Chromosome(
                genes=genes,
                objectives={metric.value: 0.0 for metric in self.config.optimization_metrics},
                metrics={}
            )
            population.append(chrom)

        return population

    def _create_random_chromosome(self, parameter_ranges: Dict[str, Dict]) -> Dict[str, Any]:
        """Create a random chromosome within parameter ranges"""
        genes = {}

        for param_name, param_config in parameter_ranges.items():
            if param_config["type"] == "int":
                genes[param_name] = random.randint(param_config["min"], param_config["max"])
            elif param_config["type"] == "float":
                genes[param_name] = random.uniform(param_config["min"], param_config["max"])
            elif param_config["type"] == "categorical":
                genes[param_name] = random.choice(param_config["values"])
            else:
                # Default to float
                genes[param_name] = random.uniform(param_config["min"], param_config["max"])

        return genes

    def _evaluate_population(self, data: pd.DataFrame, strategy: Callable):
        """Evaluate fitness of entire population"""
        for chromosome in self.population:
            if chromosome.fitness == 0:  # Not yet evaluated
                self._evaluate_chromosome(chromosome, data, strategy)

    def _evaluate_chromosome(self, chromosome: Chromosome, data: pd.DataFrame, strategy: Callable):
        """Evaluate a single chromosome"""
        try:
            # Run backtest
            config = BacktestConfig()
            result = self.backtester.run_backtest(data, strategy, chromosome.genes)

            # Store metrics
            chromosome.metrics = {
                "total_trades": result.total_trades,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "sharpe_ratio": result.sharpe_ratio,
                "total_pnl": result.total_pnl,
                "max_drawdown": result.max_drawdown,
                "sortino_ratio": result.sortino_ratio
            }

            # Calculate objectives
            for metric in self.config.optimization_metrics:
                if metric == FitnessMetric.SHARPE_RATIO:
                    chromosome.objectives[metric.value] = result.sharpe_ratio
                elif metric == FitnessMetric.PROFIT_FACTOR:
                    chromosome.objectives[metric.value] = result.profit_factor
                elif metric == FitnessMetric.TOTAL_PNL:
                    chromosome.objectives[metric.value] = result.total_pnl / 1000
                elif metric == FitnessMetric.WIN_RATE:
                    chromosome.objectives[metric.value] = result.win_rate
                elif metric == FitnessMetric.MAX_DRAWDOWN:
                    chromosome.objectives[metric.value] = -result.max_drawdown  # Lower is better
                elif metric == FitnessMetric.ADJUSTED_RETURN:
                    # Custom metric that balances returns and risk
                    adjusted_return = (result.total_pnl / 1000) * (1 - result.max_drawdown)
                    chromosome.objectives[metric.value] = adjusted_return

            # Single fitness value for single-objective optimization
            if not self.config.multi_objective:
                chromosome.fitness = np.mean(list(chromosome.objectives.values()))
            else:
                chromosome.fitness = 0  # Pareto ranking will be used

        except Exception as e:
            logger.warning(f"Error evaluating chromosome: {e}")
            chromosome.fitness = float('-inf')
            for metric in self.config.optimization_metrics:
                chromosome.objectives[metric.value] = float('-inf')

    def _evaluate_offspring(self, offspring: List[Chromosome], data: pd.DataFrame, strategy: Callable):
        """Evaluate offspring chromosomes"""
        for chromosome in offspring:
            self._evaluate_chromosome(chromosome, data, strategy)

    def _create_offspring(self, parameter_ranges: Dict) -> List[Chromosome]:
        """Create offspring through crossover and mutation"""
        offspring = []
        num_parents = len(self.population) - self._elite_count()

        while len(offspring) < num_parents:
            # Tournament selection
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()

            # Crossover
            if random.random() < self.config.crossover_rate:
                child_genes = self._crossover(parent1.genes, parent2.genes, parameter_ranges)
            else:
                child_genes = random.choice([parent1, parent2]).genes.copy()

            # Mutation
            if random.random() < self.config.mutation_rate:
                child_genes = self._mutate(child_genes, parameter_ranges)

            child = Chromosome(genes=child_genes)
            offspring.append(child)

        return offspring

    def _elite_count(self) -> int:
        """Calculate elite count"""
        return max(1, int(self.config.elite_ratio * len(self.population)))

    def _tournament_selection(self) -> Chromosome:
        """Tournament selection for parents"""
        tournament = random.sample(self.population, self.config.tournament_size)
        tournament.sort(key=lambda x: x.fitness, reverse=True)
        return tournament[0]

    def _crossover(self, genes1: Dict, genes2: Dict, parameter_ranges: Dict) -> Dict:
        """Perform crossover between two chromosomes"""
        child_genes = {}

        for param_name in genes1.keys():
            # Single-point crossover for each parameter
            if random.random() < 0.5:
                child_genes[param_name] = genes1[param_name]
            else:
                child_genes[param_name] = genes2[param_name]

        # Introduce some blending crossover for numeric parameters
        self._blend_numeric_genes(child_genes, genes1, genes2, parameter_ranges)

        return child_genes

    def _blend_numeric_genes(self, child_genes: Dict, genes1: Dict, genes2: Dict, parameter_ranges: Dict):
        """Blend numeric genes using weighted average"""
        for param_name in genes1.keys():
            if param_name in parameter_ranges:
                param_type = parameter_ranges[param_name].get("type", "float")

                if param_type in ["int", "float"]:
                    # Blend between parent values
                    alpha = random.random()
                    blended_value = genes1[param_name] * alpha + genes2[param_name] * (1 - alpha)

                    # Ensure within bounds
                    min_val = parameter_ranges[param_name]["min"]
                    max_val = parameter_ranges[param_name]["max"]

                    if param_type == "int":
                        child_genes[param_name] = int(np.clip(blended_value, min_val, max_val))
                    else:
                        child_genes[param_name] = np.clip(blended_value, min_val, max_val)

    def _mutate(self, genes: Dict, parameter_ranges: Dict) -> Dict:
        """Mutate chromosome"""
        mutated_genes = genes.copy()

        for param_name in genes.keys():
            if param_name in parameter_ranges:
                if random.random() < self.config.mutation_rate:
                    param_config = parameter_ranges[param_name]

                    if param_config["type"] == "int":
                        # Random mutation within range
                        mutated_genes[param_name] = random.randint(
                            param_config["min"],
                            param_config["max"]
                        )
                    elif param_config["type"] == "float":
                        # Gaussian mutation
                        current_value = genes[param_name]
                        range_width = param_config["max"] - param_config["min"]
                        std_dev = range_width * 0.1  # 10% of range

                        new_value = current_value + random.gauss(0, std_dev)
                        mutated_genes[param_name] = np.clip(
                            new_value,
                            param_config["min"],
                            param_config["max"]
                        )
                    elif param_config["type"] == "categorical":
                        # Random selection from valid values
                        mutated_genes[param_name] = random.choice(param_config["values"])

        return mutated_genes

    def _single_objective_selection(self, offspring: List[Chromosome]):
        """Environmental selection for single-objective optimization"""
        # Combine current population with offspring
        combined = self.population + offspring

        # Sort by fitness
        combined.sort(key=lambda x: x.fitness, reverse=True)

        # Select top population
        self.population = combined[:self.config.population_size]

        # Log best solution
        best = self.population[0]
        logger.debug(f"Best fitness: {best.fitness:.4f}")
        logger.debug(f"Best params: {best.genes}")

    def _nsga_selection(self, offspring: List[Chromosome]):
        """NSGA-II environmental selection for multi-objective optimization"""
        # Combine current population with offspring
        combined = self.population + offspring

        # Fast non-dominated sorting
        fronts = self._fast_non_dominated_sort(combined)

        # Create new population
        new_population = []
        front_idx = 0

        while len(new_population) + len(fronts[front_idx]) <= self.config.population_size:
            new_population.extend(fronts[front_idx])
            front_idx += 1

        # If we need more individuals, use crowding distance
        if len(new_population) < self.config.population_size:
            remaining = self.config.population_size - len(new_population)
            last_front = fronts[front_idx]
            last_front.sort(key=lambda x: x.crowding_distance, reverse=True)
            new_population.extend(last_front[:remaining])

        self.population = new_population

    def _fast_non_dominated_sort(self, population: List[Chromosome]) -> List[List[Chromosome]]:
        """Fast non-dominated sorting algorithm"""
        fronts = [[]]
        dominating = {i: [] for i in range(len(population))}
        dominated_count = [0] * len(population)

        # Calculate domination
        for i, chrom_i in enumerate(population):
            for j, chrom_j in enumerate(population):
                if i == j:
                    continue

                if chrom_i.dominates(chrom_j):
                    dominating[i].append(j)
                elif chrom_j.dominates(chrom_i):
                    dominated_count[i] += 1

        # First front (non-dominated)
        for i, count in enumerate(dominated_count):
            if count == 0:
                chromosome = population[i]
                chromosome.rank = 0
                fronts[0].append(chromosome)

        # Create subsequent fronts
        front_idx = 0
        while fronts[front_idx]:
            next_front = []

            for chrom in fronts[front_idx]:
                # Find index of this chromosome in original population
                for i in range(len(population)):
                    if population[i] is chrom:
                        for j in dominating[i]:
                            dominated_count[j] -= 1

                            if dominated_count[j] == 0:
                                population[j].rank = front_idx + 1
                                next_front.append(population[j])

            front_idx += 1
            fronts.append(next_front)

        # Remove empty last front
        if fronts and not fronts[-1]:
            fronts.pop()

        # Calculate crowding distance for each front
        for front in fronts:
            self._calculate_crowding_distance(front)

        return fronts

    def _calculate_crowding_distance(self, front: List[Chromosome]):
        """Calculate crowding distance for Pareto front"""
        if len(front) <= 2:
            for chrom in front:
                chrom.crowding_distance = float("inf")
            return

        num_objectives = len(front[0].objectives)

        for obj_idx in range(num_objectives):
            # Sort by this objective
            objective_key = list(front[0].objectives.keys())[obj_idx]
            front.sort(key=lambda x: x.objectives[objective_key])

            # Set boundary points to infinite distance
            front[0].crowding_distance = float("inf")
            front[-1].crowding_distance = float("inf")

            # Calculate distances for intermediate points
            min_value = front[0].objectives[objective_key]
            max_value = front[-1].objectives[objective_key]

            if max_value > min_value:
                for i in range(1, len(front) - 1):
                    distance = (front[i + 1].objectives[objective_key] - front[i - 1].objectives[objective_key]) / (max_value - min_value)
                    front[i].crowding_distance += distance

    def _extract_pareto_front(self, population: List[Chromosome]) -> List[Chromosome]:
        """Extract Pareto front from population"""
        fronts = self._fast_non_dominated_sort(population)
        return fronts[0] if fronts else []

    def get_optimization_recommendations(self, result: GeneticOptimizationResult,  parameter_ranges: Dict) -> List[Dict]:
        """Generate recommendations based on optimization results"""
        recommendations = []

        # Parameter sensitivity analysis
        sensitivity = self._analyze_parameter_sensitivity(result, parameter_ranges)

        # Find robust parameter ranges
        if result.pareto_front:
            for param_name in parameter_ranges.keys():
                param_values = [float(chrom.genes[param_name]) for chrom in result.pareto_front if param_name in chrom.genes]
                if param_values:
                    param_min = min(param_values)
                    param_max = max(param_values)

                    recommendations.append({
                        "parameter": param_name,
                        "type": "robust_range",
                        "min": param_min,
                        "max": param_max,
                        "recommendation": f"Keep {param_name} between {param_min:.2f} and {param_max:.2f} for robust performance"
                    })

        # Check if optimization converged
        if len(result.best_fitness_history) < self.config.max_generations:
            recommendations.append({
                "type": "convergence",
                "message": "Optimization converged early - good convergence",
                "recommendation": "Consider tightening parameter ranges or increasing population diversity"
            })

        return recommendations

    def _analyze_parameter_sensitivity(self, result: GeneticOptimizationResult, parameter_ranges: Dict) -> Dict[str, float]:
        """Analyze parameter sensitivity"""
        sensitivity = {}

        # Calculate correlation between each parameter and fitness
        for param_name in parameter_ranges.keys():
            param_values = []
            fitness_values = []

            for chrom in self.population:
                if param_name in chrom.genes:
                    param_values.append(float(chrom.genes[param_name]))
                    fitness_values.append(chrom.fitness)

            if param_values and fitness_values:
                correlation = np.corrcoef(param_values, fitness_values)[0, 1]
                sensitivity[param_name] = abs(correlation) if not np.isnan(correlation) else 0

        return sensitivity


if __name__ == "__main__":
    # Example usage
    config = GeneticAlgorithmConfig(
        population_size=100,
        max_generations=10,
        optimization_metrics=[FitnessMetric.SHARPE_RATIO, FitnessMetric.PROFIT_FACTOR]
    )

    from backtesting import moving_average_crossover_strategy
    import numpy as np
    import pandas as pd

    # Create sample data
    dates = pd.date_range("2020-01-01", periods=252)
    prices = 100 + np.cumsum(np.random.normal(0, 1, 252))
    data = pd.DataFrame({
        "open": prices,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": 1000000
    }, index=dates)

    # Define parameter ranges
    parameter_ranges = {
        "fast_ma": {"min": 5, "max": 50, "type": "int"},
        "slow_ma": {"min": 20, "max": 200, "type": "int"}
    }

    optimizer = GeneticOptimizer(config)
    result = optimizer.optimize(data, moving_average_crossover_strategy, parameter_ranges)

    if result.best_chromosome:
        print(f"Best parameters: {result.best_chromosome.genes}")
        print(f"Best fitness: {result.best_chromosome.fitness:.4f}")
        print(f"Generations: {result.generations_completed}")

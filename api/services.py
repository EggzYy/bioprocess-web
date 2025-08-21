"""
API Service Layer
Handles business logic, job management, background tasks, and caching.
"""

import json
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
import pickle
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, Future

from loguru import logger

from bioprocess.models import ScenarioInput, ScenarioResult
from bioprocess.orchestrator import (
    run_scenario as run_scenario_func,
    run_sensitivity_analysis as run_sensitivity_func,
    generate_excel_report,
)
from bioprocess.optimizer_enhanced import (
    optimize_with_progressive_constraints,
    optimize_with_capacity_enforcement,
)
from .schemas import JobStatus, JobInfo


class JobManager:
    """Manages background jobs with progress tracking."""

    def __init__(self, max_workers: int = 4, cache_dir: Optional[Path] = None):
        """
        Initialize job manager.

        Args:
            max_workers: Maximum number of concurrent workers
            cache_dir: Directory for caching results
        """
        self.jobs: Dict[str, JobInfo] = {}
        self.results_cache: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: Dict[str, Future] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.cancel_flags: Dict[str, bool] = {}

        # Setup cache directory
        self.cache_dir = cache_dir or Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Cleanup old cache files on startup
        self._cleanup_old_cache()

    def create_job(self, job_type: str, description: Optional[str] = None) -> str:
        """
        Create a new job.

        Args:
            job_type: Type of job (scenario, optimization, etc.)
            description: Optional job description

        Returns:
            Job ID
        """
        job_id = str(uuid4())
        job_info = JobInfo(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            progress=0.0,
            message=description or f"Job {job_type} created",
            job_type=job_type,
        )
        self.jobs[job_id] = job_info
        self.cancel_flags[job_id] = False
        logger.info(f"Created job {job_id} of type {job_type}")
        return job_id

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        """Update job information."""
        if job_id not in self.jobs:
            logger.warning(f"Attempted to update non-existent job {job_id}")
            return

        job = self.jobs[job_id]
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = min(1.0, max(0.0, progress))
        if message is not None:
            job.message = message
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error

        job.updated_at = datetime.now().isoformat()

        # Notify progress callbacks
        if job_id in self.progress_callbacks:
            for callback in self.progress_callbacks[job_id]:
                try:
                    callback(job)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")

    def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job information."""
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancellation was initiated
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        # Set cancel flag
        self.cancel_flags[job_id] = True

        # Cancel future if exists
        if job_id in self.futures:
            future = self.futures[job_id]
            if not future.done():
                future.cancel()

        self.update_job(
            job_id, status=JobStatus.CANCELLED, message="Job cancelled by user"
        )

        logger.info(f"Cancelled job {job_id}")
        return True

    def submit_job(self, job_id: str, func: Callable, *args, **kwargs) -> Future:
        """
        Submit a job for execution.

        Args:
            job_id: Job ID
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Future object
        """

        def wrapped_func():
            try:
                self.update_job(job_id, status=JobStatus.RUNNING, progress=0.1)

                # Check for cancellation periodically
                kwargs["cancel_check"] = lambda: self.cancel_flags.get(job_id, False)
                kwargs["progress_callback"] = lambda p, m=None: self.update_job(
                    job_id, progress=p, message=m
                )

                result = func(*args, **kwargs)

                if self.cancel_flags.get(job_id, False):
                    self.update_job(
                        job_id, status=JobStatus.CANCELLED, message="Job was cancelled"
                    )
                else:
                    self.update_job(
                        job_id,
                        status=JobStatus.COMPLETED,
                        progress=1.0,
                        result=result,
                        message="Job completed successfully",
                    )

                return result

            except Exception as e:
                logger.error(f"Error in job {job_id}: {e}")
                self.update_job(
                    job_id,
                    status=JobStatus.FAILED,
                    error=str(e),
                    message=f"Job failed: {str(e)}",
                )
                raise

        future = self.executor.submit(wrapped_func)
        self.futures[job_id] = future
        return future

    def register_progress_callback(
        self, job_id: str, callback: Callable[[JobInfo], None]
    ):
        """Register a callback for job progress updates."""
        if job_id not in self.progress_callbacks:
            self.progress_callbacks[job_id] = []
        self.progress_callbacks[job_id].append(callback)

    def _cleanup_old_cache(self, max_age_hours: int = 24):
        """Remove cache files older than max_age_hours."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        for cache_file in self.cache_dir.glob("*.cache"):
            if datetime.fromtimestamp(cache_file.stat().st_mtime) < cutoff_time:
                try:
                    cache_file.unlink()
                    logger.info(f"Removed old cache file: {cache_file}")
                except Exception as e:
                    logger.error(f"Error removing cache file {cache_file}: {e}")


class ScenarioCache:
    """Caches scenario results to avoid recomputation."""

    def __init__(self, cache_dir: Optional[Path] = None, max_size: int = 100):
        """
        Initialize scenario cache.

        Args:
            cache_dir: Directory for persistent cache
            max_size: Maximum number of cached results in memory
        """
        self.memory_cache: Dict[str, ScenarioResult] = {}
        self.cache_order: List[str] = []
        self.max_size = max_size
        self.cache_dir = cache_dir or Path("./cache/scenarios")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, scenario: ScenarioInput) -> str:
        """Generate cache key from scenario input."""
        # Create a deterministic hash of the scenario
        scenario_json = json.dumps(scenario.model_dump(), sort_keys=True, default=str)
        return hashlib.sha256(scenario_json.encode()).hexdigest()

    def get(self, scenario: ScenarioInput) -> Optional[ScenarioResult]:
        """
        Get cached result for scenario.

        Args:
            scenario: Input scenario

        Returns:
            Cached result or None
        """
        cache_key = self._get_cache_key(scenario)

        # Check memory cache
        if cache_key in self.memory_cache:
            logger.debug(f"Cache hit (memory): {cache_key}")
            # Move to end (LRU)
            self.cache_order.remove(cache_key)
            self.cache_order.append(cache_key)
            return self.memory_cache[cache_key]

        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.pickle"
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    result = pickle.load(f)
                logger.debug(f"Cache hit (disk): {cache_key}")

                # Add to memory cache
                self._add_to_memory_cache(cache_key, result)
                return result
            except Exception as e:
                logger.error(f"Error loading cache file {cache_file}: {e}")
                # Remove corrupted cache file
                cache_file.unlink()

        logger.debug(f"Cache miss: {cache_key}")
        return None

    def set(self, scenario: ScenarioInput, result: ScenarioResult):
        """
        Cache scenario result.

        Args:
            scenario: Input scenario
            result: Calculation result
        """
        cache_key = self._get_cache_key(scenario)

        # Add to memory cache
        self._add_to_memory_cache(cache_key, result)

        # Save to disk
        cache_file = self.cache_dir / f"{cache_key}.pickle"
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(result, f)
            logger.debug(f"Cached result: {cache_key}")
        except Exception as e:
            logger.error(f"Error saving cache file {cache_file}: {e}")

    def _add_to_memory_cache(self, cache_key: str, result: ScenarioResult):
        """Add result to memory cache with LRU eviction."""
        if cache_key in self.memory_cache:
            self.cache_order.remove(cache_key)
        elif len(self.memory_cache) >= self.max_size:
            # Evict oldest
            oldest = self.cache_order.pop(0)
            del self.memory_cache[oldest]

        self.memory_cache[cache_key] = result
        self.cache_order.append(cache_key)

    def clear(self):
        """Clear all cached results."""
        self.memory_cache.clear()
        self.cache_order.clear()

        # Remove disk cache files
        for cache_file in self.cache_dir.glob("*.pickle"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"Error removing cache file {cache_file}: {e}")


class ScenarioService:
    """Service for running scenarios with caching and progress tracking."""

    def __init__(self, job_manager: JobManager, cache: ScenarioCache):
        """
        Initialize scenario service.

        Args:
            job_manager: Job manager instance
            cache: Scenario cache instance
        """
        self.job_manager = job_manager
        self.cache = cache

    def run_scenario(
        self, scenario: ScenarioInput, use_cache: bool = True, async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Run a scenario with optional caching.

        Args:
            scenario: Input scenario
            use_cache: Whether to use cached results
            async_mode: Whether to run asynchronously

        Returns:
            Result dictionary or job info
        """
        # Check cache first
        if use_cache:
            cached_result = self.cache.get(scenario)
            if cached_result:
                logger.info(f"Using cached result for scenario: {scenario.name}")
                return {"result": cached_result, "cached": True, "status": "completed"}

        if async_mode:
            # Create job and run asynchronously
            job_id = self.job_manager.create_job(
                "scenario", f"Running scenario: {scenario.name}"
            )

            def run_with_cache():
                result = run_scenario_func(scenario)
                if use_cache:
                    self.cache.set(scenario, result)
                return result

            self.job_manager.submit_job(job_id, run_with_cache)

            return {
                "job_id": job_id,
                "status": "pending",
                "message": "Scenario queued for processing",
            }
        else:
            # Run synchronously
            result = run_scenario_func(scenario)
            if use_cache:
                self.cache.set(scenario, result)

            return {"result": result, "cached": False, "status": "completed"}

    def run_batch_scenarios(
        self, scenarios: List[ScenarioInput], use_cache: bool = True
    ) -> str:
        """
        Run multiple scenarios in batch.

        Args:
            scenarios: List of scenarios to run
            use_cache: Whether to use cached results

        Returns:
            Job ID
        """
        job_id = self.job_manager.create_job(
            "batch", f"Running {len(scenarios)} scenarios"
        )

        def run_batch(cancel_check, progress_callback):
            results = []
            for i, scenario in enumerate(scenarios):
                if cancel_check():
                    break

                progress = (i + 1) / len(scenarios)
                progress_callback(
                    progress,
                    f"Processing scenario {i + 1}/{len(scenarios)}: {scenario.name}",
                )

                # Check cache
                if use_cache:
                    cached_result = self.cache.get(scenario)
                    if cached_result:
                        results.append(cached_result)
                        continue

                # Run scenario
                try:
                    result = run_scenario_func(scenario)
                    if use_cache:
                        self.cache.set(scenario, result)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error in batch scenario {i + 1}: {e}")
                    results.append({"error": str(e)})

            return results

        self.job_manager.submit_job(job_id, run_batch)
        return job_id


class OptimizationService:
    """Service for running optimization with progress tracking."""

    def __init__(self, job_manager: JobManager):
        """
        Initialize optimization service.

        Args:
            job_manager: Job manager instance
        """
        self.job_manager = job_manager

    def run_optimization(
        self, scenario: ScenarioInput, max_evaluations: Optional[int] = None
    ) -> str:
        """
        Run optimization for a scenario.

        Args:
            scenario: Input scenario with optimization enabled
            max_evaluations: Maximum number of evaluations

        Returns:
            Job ID
        """
        job_id = self.job_manager.create_job(
            "optimization", f"Optimizing scenario: {scenario.name}"
        )

        def optimize(cancel_check, progress_callback):
            # Enable optimization in scenario
            scenario.optimize_equipment = True
            if max_evaluations:
                scenario.optimization.max_evaluations = max_evaluations

            # Run optimization with enhanced capacity enforcement
            if getattr(scenario, "use_multiobjective", True):
                # Use progressive constraints for multi-objective optimization
                best_solution, all_results_df = optimize_with_capacity_enforcement(
                    scenario,
                    max_reactors=getattr(scenario, "max_reactors", 60),  # Match original
                    max_ds_lines=getattr(scenario, "max_ds_lines", 12),  # Match original
                    volume_options=scenario.volumes.volume_options_l,
                    enforce_capacity=True,
                    max_allowed_excess=0.2,  # Max 20% excess
                )
            else:
                # Use strict capacity enforcement for single objective
                best_solution, all_results_df = optimize_with_capacity_enforcement(
                    scenario,
                    max_reactors=getattr(scenario, "max_reactors", 60),  # Match original
                    max_ds_lines=getattr(scenario, "max_ds_lines", 12),  # Match original
                    volume_options=scenario.volumes.volume_options_l,
                    enforce_capacity=True,
                    max_allowed_excess=0.2,  # Max 20% excess
                )

            # Report progress
            if progress_callback:
                progress_callback(1.0, "Optimization complete")

            # Format result for API response
            result = {
                "optimization": {
                    "best_solution": best_solution,
                    "pareto_front": [best_solution] if best_solution else [],
                    "n_evaluations": len(all_results_df)
                    if not all_results_df.empty
                    else 0,
                    "selected_fermenter_volume": best_solution.get(
                        "fermenter_volume_l", scenario.volumes.base_fermenter_vol_l
                    )
                    if best_solution
                    else None,
                    "selected_reactors": best_solution.get("reactors", 4)
                    if best_solution
                    else None,
                    "selected_ds_lines": best_solution.get("ds_lines", 2)
                    if best_solution
                    else None,
                }
                if best_solution
                else None
            }

            # Include any warnings about capacity constraints
            if best_solution and "warning" in best_solution:
                result["warnings"] = [best_solution["warning"]]

            return result

        self.job_manager.submit_job(job_id, optimize)
        return job_id


class SensitivityService:
    """Service for sensitivity analysis."""

    def __init__(self, job_manager: JobManager):
        """
        Initialize sensitivity service.

        Args:
            job_manager: Job manager instance
        """
        self.job_manager = job_manager

    def run_sensitivity_analysis(
        self,
        scenario: ScenarioInput,
        parameters: List[str],
        delta_percentage: float = 0.1,
    ) -> str:
        """
        Run sensitivity analysis.

        Args:
            scenario: Input scenario
            parameters: Parameters to vary
            delta_percentage: Percentage change for analysis

        Returns:
            Job ID
        """
        job_id = self.job_manager.create_job(
            "sensitivity", f"Sensitivity analysis for: {scenario.name}"
        )

        def analyze(cancel_check, progress_callback):
            # Configure sensitivity
            scenario.sensitivity.enabled = True
            scenario.sensitivity.parameters = parameters
            scenario.sensitivity.delta_percentage = delta_percentage

            # Get base configuration
            base_result = run_scenario_func(scenario)
            base_config = {
                "reactors": scenario.equipment.reactors_total or 4,
                "ds_lines": scenario.equipment.ds_lines_total or 2,
                "fermenter_volume_l": scenario.volumes.base_fermenter_vol_l,
            }

            # Run sensitivity analysis
            result = run_sensitivity_func(scenario, base_config)

            return {"base_result": base_result, "sensitivity": result}

        self.job_manager.submit_job(job_id, analyze)
        return job_id


class ExportService:
    """Service for exporting results."""

    def __init__(self):
        """Initialize export service."""
        self.export_dir = Path("./exports")
        self.export_dir.mkdir(exist_ok=True)

    def export_to_excel(
        self,
        result: ScenarioResult,
        scenario: Optional[ScenarioInput] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export results to Excel.

        Args:
            result: Scenario results
            scenario: Original scenario input
            filename: Optional filename

        Returns:
            Export information
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scenario_{timestamp}.xlsx"

        filepath = self.export_dir / filename

        try:
            # Generate Excel report
            excel_bytes = generate_excel_report(result, scenario)

            # Save to file
            with open(filepath, "wb") as f:
                f.write(excel_bytes)

            return {
                "filename": filename,
                "filepath": str(filepath),
                "size_bytes": len(excel_bytes),
                "created_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            raise


# Global service instances
job_manager = JobManager()
scenario_cache = ScenarioCache()
scenario_service = ScenarioService(job_manager, scenario_cache)
optimization_service = OptimizationService(job_manager)
sensitivity_service = SensitivityService(job_manager)
export_service = ExportService()


def get_job_manager() -> JobManager:
    """Get job manager instance."""
    return job_manager


def get_scenario_service() -> ScenarioService:
    """Get scenario service instance."""
    return scenario_service


def get_optimization_service() -> OptimizationService:
    """Get optimization service instance."""
    return optimization_service


def get_sensitivity_service() -> SensitivityService:
    """Get sensitivity service instance."""
    return sensitivity_service


def get_export_service() -> ExportService:
    """Get export service instance."""
    return export_service

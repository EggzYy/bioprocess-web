"""
API router endpoints for the bioprocess web application.
"""

from typing import Optional, Dict
from uuid import uuid4
from datetime import datetime
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)

from .schemas import (
    RunScenarioRequest,
    RunScenarioResponse,
    ExportRequest,
    ExportResponse,
    OptimizationRequest,
    OptimizationResponse,
    JobInfo,
    JobProgressResponse,
    ConfigSaveRequest,
    ConfigSaveResponse,
    ConfigListResponse,
    SensitivityRequest,
    BatchScenarioRequest,
    BatchScenarioResponse,
    StrainDatabaseResponse,
    JobStatus,
)

# Import bioprocess modules
import sys

sys.path.append(str(Path(__file__).parent.parent))

from bioprocess.orchestrator import (
    run_scenario as run_scenario_func,
    run_optimization as run_optimization_func,
    run_sensitivity_analysis as run_sensitivity_func,
    generate_excel_report,
)
from bioprocess.presets import ASSUMPTIONS
from bioprocess.models import ScenarioInput, ScenarioResult

# Router instance
router = APIRouter()

# In-memory job store (replace with Redis in production)
JOBS: Dict[str, JobInfo] = {}

# Configuration directory
CONFIG_DIR = Path(__file__).parent.parent / "configs"
CONFIG_DIR.mkdir(exist_ok=True)

# Export directory
EXPORT_DIR = Path(__file__).parent.parent / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


# Helper functions
def create_job(status: JobStatus = JobStatus.PENDING) -> str:
    """Create a new job entry."""
    job_id = str(uuid4())
    JOBS[job_id] = JobInfo(
        job_id=job_id,
        status=status,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        progress=0.0,
    )
    return job_id


def update_job(job_id: str, **kwargs):
    """Update job information."""
    if job_id in JOBS:
        job = JOBS[job_id]
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        job.updated_at = datetime.now().isoformat()


async def run_scenario_background(job_id: str, scenario: ScenarioInput):
    """Run scenario in background."""
    try:
        update_job(job_id, status=JobStatus.RUNNING, progress=0.1)

        update_job(job_id, progress=0.2, message="Loading strain data...")

        # Run the scenario
        result = run_scenario_func(scenario)

        update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=1.0,
            result=result.model_dump(),
            message="Scenario completed successfully",
        )
    except Exception as e:
        logger.error(f"Error in background scenario: {e}")
        update_job(
            job_id, status=JobStatus.FAILED, error=str(e), message=f"Failed: {str(e)}"
        )


# Scenario endpoints
@router.post("/scenarios/run", response_model=RunScenarioResponse)
async def run_scenario(request: RunScenarioRequest, background_tasks: BackgroundTasks):
    """Run a bioprocess scenario."""
    try:
        # Ensure raw_prices are included - use defaults if not provided
        from bioprocess.presets import RAW_PRICES

        if not request.scenario.prices.raw_prices:
            request.scenario.prices.raw_prices = RAW_PRICES.copy()

        if request.async_mode:
            # Run in background
            job_id = create_job(JobStatus.PENDING)
            background_tasks.add_task(run_scenario_background, job_id, request.scenario)
            return RunScenarioResponse(
                job_id=job_id,
                status=JobStatus.PENDING,
                message="Scenario queued for processing",
            )
        else:
            # Run synchronously
            logger.info(f"Running scenario with input: {request.scenario.model_dump()}")
            result = run_scenario_func(request.scenario)
            return RunScenarioResponse(
                result=result,
                status=JobStatus.COMPLETED,
                message="Scenario completed successfully",
            )
    except Exception as e:
        logger.error(f"Error running scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenarios/batch", response_model=BatchScenarioResponse)
async def run_batch_scenarios(
    request: BatchScenarioRequest, background_tasks: BackgroundTasks
):
    """Run multiple scenarios in batch."""
    try:
        job_id = create_job(JobStatus.PENDING)

        async def run_batch():
            update_job(job_id, status=JobStatus.RUNNING)
            results = []

            for i, scenario in enumerate(request.scenarios):
                progress = (i + 1) / len(request.scenarios)
                update_job(
                    job_id,
                    progress=progress,
                    message=f"Processing scenario {i + 1}/{len(request.scenarios)}",
                )

                try:
                    result = run_scenario_func(scenario)
                    results.append(result.model_dump())
                except Exception as e:
                    logger.error(f"Error in batch scenario {i + 1}: {e}")
                    results.append({"error": str(e)})

            update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                result=results,
                message="Batch processing completed",
            )

        background_tasks.add_task(run_batch)

        return BatchScenarioResponse(
            job_id=job_id,
            total_scenarios=len(request.scenarios),
            status=JobStatus.PENDING,
            message="Batch job queued for processing",
        )
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Optimization endpoints
@router.post("/optimization/run", response_model=OptimizationResponse)
async def run_optimization(
    request: OptimizationRequest, background_tasks: BackgroundTasks
):
    """Run optimization for a scenario."""
    try:
        job_id = create_job(JobStatus.PENDING)

        async def optimize():
            update_job(job_id, status=JobStatus.RUNNING)

            # Enable optimization in scenario
            request.scenario.optimize_equipment = True
            if request.volume_options:
                request.scenario.volumes.volume_options_l = request.volume_options

            # Run optimization
            result = run_optimization_func(request.scenario)

            update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                result=result,
                message="Optimization completed",
            )

        background_tasks.add_task(optimize)

        return OptimizationResponse(
            job_id=job_id, status=JobStatus.PENDING, message="Optimization job queued"
        )
    except Exception as e:
        logger.error(f"Error starting optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sensitivity/run")
async def run_sensitivity_analysis(
    request: SensitivityRequest, background_tasks: BackgroundTasks
):
    """Run sensitivity analysis."""
    try:
        job_id = create_job(JobStatus.PENDING)

        async def analyze():
            update_job(job_id, status=JobStatus.RUNNING)

            # Configure sensitivity in scenario
            request.scenario.sensitivity.enabled = True
            request.scenario.sensitivity.parameters = request.parameters
            request.scenario.sensitivity.delta_percentage = request.delta_percentage

            # Run sensitivity analysis
            result = run_sensitivity_func(request.scenario, request.base_configuration)

            update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=1.0,
                result=result,
                message="Sensitivity analysis completed",
            )

        background_tasks.add_task(analyze)

        return {
            "job_id": job_id,
            "status": JobStatus.PENDING,
            "message": "Sensitivity analysis queued",
        }
    except Exception as e:
        logger.error(f"Error starting sensitivity analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export endpoints
@router.post("/export/excel", response_model=ExportResponse)
async def export_to_excel(request: ExportRequest):
    """Export scenario results to Excel."""
    try:
        # Get result from job if job_id provided
        if request.job_id:
            if request.job_id not in JOBS:
                raise HTTPException(status_code=404, detail="Job not found")

            job = JOBS[request.job_id]
            if job.status != JobStatus.COMPLETED:
                raise HTTPException(status_code=400, detail="Job not completed")

            if not job.result:
                raise HTTPException(status_code=400, detail="No result available")

            # Convert dict back to ScenarioResult
            result = ScenarioResult(**job.result)
        elif request.result:
            result = request.result
        else:
            raise HTTPException(
                status_code=400, detail="Either job_id or result must be provided"
            )

        # Generate Excel file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.scenario_name}_{timestamp}.xlsx"
        filepath = EXPORT_DIR / filename

        # Generate Excel report
        excel_bytes = generate_excel_report(
            result, request.scenario_input or ScenarioInput()
        )

        # Save to file
        with open(filepath, "wb") as f:
            f.write(excel_bytes)

        # Get file size
        file_size = filepath.stat().st_size

        return ExportResponse(
            filename=filename,
            download_url=f"/export/download/{filename}",
            size_bytes=file_size,
            created_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error exporting to Excel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/download/{filename}")
async def download_export(filename: str):
    """Download exported file."""
    filepath = EXPORT_DIR / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# Job management endpoints
@router.get("/jobs/{job_id}", response_model=JobInfo)
async def get_job_status(job_id: str):
    """Get job status and result."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    return JOBS[job_id]


@router.get("/jobs/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(job_id: str):
    """Get job progress."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS[job_id]
    return JobProgressResponse(
        job_id=job_id, status=job.status, progress=job.progress, message=job.message
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS[job_id]
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400, detail="Cannot cancel completed or failed job"
        )

    update_job(job_id, status=JobStatus.CANCELLED, message="Job cancelled by user")

    return {"message": "Job cancelled"}


# Configuration management
@router.post("/configs/save", response_model=ConfigSaveResponse)
async def save_configuration(request: ConfigSaveRequest):
    """Save scenario configuration."""
    try:
        filename = f"{request.name}.json"
        filepath = CONFIG_DIR / filename

        if filepath.exists() and not request.overwrite:
            raise HTTPException(status_code=409, detail="Configuration already exists")

        config_data = {
            "name": request.name,
            "description": request.description,
            "scenario": request.scenario.model_dump(),
            "saved_at": datetime.now().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(config_data, f, indent=2)

        return ConfigSaveResponse(
            name=request.name,
            saved_at=config_data["saved_at"],
            file_path=str(filepath),
            message="Configuration saved successfully",
        )
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs", response_model=ConfigListResponse)
async def list_configurations():
    """List saved configurations."""
    try:
        configs = []
        for filepath in CONFIG_DIR.glob("*.json"):
            with open(filepath) as f:
                config = json.load(f)
                configs.append(
                    {
                        "name": config.get("name"),
                        "description": config.get("description"),
                        "saved_at": config.get("saved_at"),
                        "filename": filepath.name,
                    }
                )

        return ConfigListResponse(configs=configs, count=len(configs))
    except Exception as e:
        logger.error(f"Error listing configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/configs/{name}")
async def load_configuration(name: str):
    """Load a saved configuration."""
    try:
        filepath = CONFIG_DIR / f"{name}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Configuration not found")

        with open(filepath) as f:
            config = json.load(f)

        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/configs/{name}")
async def delete_configuration(name: str):
    """Delete a saved configuration."""
    try:
        filepath = CONFIG_DIR / f"{name}.json"

        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Configuration not found")

        filepath.unlink()

        return {"message": "Configuration deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from bioprocess.models import StrainInput


STRAIN_DB_FILE = Path(__file__).parent.parent / "data" / "strains.json"

def _load_strains_from_db() -> List[StrainInput]:
    if not STRAIN_DB_FILE.exists():
        return []
    with open(STRAIN_DB_FILE, "r") as f:
        data = json.load(f)
        return [StrainInput(**item) for item in data]

def _save_strains_to_db(strains: List[StrainInput]):
    with open(STRAIN_DB_FILE, "w") as f:
        json.dump([s.model_dump() for s in strains], f, indent=2)

@router.post("/strains", status_code=201, response_model=StrainInput)
async def add_strain(strain: StrainInput):
    """Add a new strain to the database."""
    strains = _load_strains_from_db()
    if any(s.name == strain.name for s in strains):
        raise HTTPException(status_code=409, detail="Strain with this name already exists")
    strains.append(strain)
    _save_strains_to_db(strains)
    return strain

@router.put("/strains/{strain_name}", response_model=StrainInput)
async def update_strain(strain_name: str, strain: StrainInput):
    """Update an existing strain."""
    if strain_name != strain.name:
        raise HTTPException(status_code=400, detail="Strain name in path does not match body")
    strains = _load_strains_from_db()
    for i, s in enumerate(strains):
        if s.name == strain_name:
            strains[i] = strain
            _save_strains_to_db(strains)
            return strain
    raise HTTPException(status_code=404, detail="Strain not found")

@router.delete("/strains/{strain_name}", status_code=204)
async def delete_strain(strain_name: str):
    """Delete a strain."""
    strains = _load_strains_from_db()
    original_len = len(strains)
    strains = [s for s in strains if s.name != strain_name]
    if len(strains) == original_len:
        raise HTTPException(status_code=404, detail="Strain not found")
    _save_strains_to_db(strains)
    return


# Strain database endpoints
@router.get("/strains", response_model=StrainDatabaseResponse)
async def get_strains(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search term"),
):
    """Get available strains from database."""
    try:
        from bioprocess.presets import get_all_strains

        strains = []
        categories = {}

        # Get properly merged strain data
        all_strains = get_all_strains()

        for strain_name, strain_data in all_strains.items():
            # Apply search filter
            if search and search.lower() not in strain_name.lower():
                continue

            # Apply category filter
            strain_category = strain_data.get("category", "uncategorized")
            if category and strain_category != category:
                continue

            strains.append(
                {"name": strain_name, "data": strain_data, "category": strain_category}
            )

            # Track categories
            if strain_category not in categories:
                categories[strain_category] = []
            categories[strain_category].append(strain_name)

        return StrainDatabaseResponse(
            strains=strains, count=len(strains), categories=categories
        )
    except Exception as e:
        logger.error(f"Error fetching strains: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strains/{strain_name}")
async def get_strain_details(strain_name: str):
    """Get details for a specific strain."""
    from bioprocess.presets import get_all_strains

    all_strains = get_all_strains()

    if strain_name not in all_strains:
        raise HTTPException(status_code=404, detail="Strain not found")

    return {"name": strain_name, "data": all_strains[strain_name]}


# Default assumptions endpoint
@router.get("/defaults")
async def get_default_assumptions():
    """Get default economic assumptions and parameters."""
    from bioprocess.presets import RAW_PRICES, get_all_strains

    return {
        "assumptions": ASSUMPTIONS,
        "raw_prices": RAW_PRICES,
        "available_strains": get_all_strains(),
        "available_volumes": [500, 1000, 2000, 5000, 10000, 20000, 50000],
        "allocation_policies": ["equal", "proportional", "inverse_ct"],
        "optimization_objectives": ["npv", "irr", "capex", "opex", "payback"],
    }


# Raw prices endpoint
@router.get("/raw-prices")
async def get_raw_prices():
    """Get raw material prices."""
    from bioprocess.presets import RAW_PRICES

    return RAW_PRICES


# Health check (already in main.py but can be extended)
@router.get("/status")
async def get_system_status():
    """Get detailed system status."""
    active_jobs = sum(1 for job in JOBS.values() if job.status == JobStatus.RUNNING)

    return {
        "status": "healthy",
        "active_jobs": active_jobs,
        "total_jobs": len(JOBS),
        "timestamp": datetime.now().isoformat(),
    }

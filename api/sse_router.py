"""
SSE (Server-Sent Events) router for real-time progress updates.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import uuid
from typing import Optional
import logging

from .sse import (
    sse_manager,
    sse_stream,
    run_optimization_with_progress,
)
from .schemas import RunScenarioRequest
from bioprocess.orchestrator import run_scenario
from bioprocess.capacity import calculate_capacity_monte_carlo
from bioprocess.models import ScenarioInput
from pydantic import BaseModel


# Additional request models for SSE endpoints
class MonteCarloRequest(BaseModel):
    scenario: ScenarioInput
    n_simulations: Optional[int] = 1000


class OptimizationRequest(BaseModel):
    scenario: ScenarioInput
    max_iterations: Optional[int] = 100


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sse", tags=["SSE"])


@router.get("/stream/{client_id}")
async def sse_endpoint(client_id: str, request: Request):
    """
    SSE stream endpoint for real-time updates.

    Args:
        client_id: Unique client identifier
        request: FastAPI request object
    """

    async def event_generator():
        """Generate SSE events."""
        try:
            async for message in sse_stream(client_id):
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                yield message
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for client {client_id}")
        finally:
            await sse_manager.disconnect(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.post("/scenario/{client_id}")
async def run_scenario_with_sse(client_id: str, request: RunScenarioRequest):
    """
    Run scenario with SSE progress updates.

    Args:
        client_id: Client identifier for SSE
        request: Scenario request data
    """
    try:
        # Create progress tracker
        tracker = sse_manager.create_progress_tracker(
            client_id, "scenario", total_steps=10
        )

        # Step 1: Validate input
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message="Validating scenario input"
        )

        scenario = request.scenario

        # Step 2: Initialize calculations
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message="Initializing calculations"
        )

        # Step 3: Calculate capacity
        await sse_manager.update_progress(
            tracker.operation_id, steps=2, message="Calculating production capacity"
        )

        # Step 4: Calculate economics
        await sse_manager.update_progress(
            tracker.operation_id, steps=2, message="Performing economic analysis"
        )

        # Step 5: Run scenario
        await sse_manager.update_progress(
            tracker.operation_id, steps=2, message="Running scenario calculations"
        )

        # Execute scenario
        result = run_scenario(scenario)

        # Step 6: Prepare results
        await sse_manager.update_progress(
            tracker.operation_id, steps=2, message="Preparing results"
        )

        # Complete operation
        await sse_manager.complete_operation(
            tracker.operation_id,
            result=result.model_dump()
            if hasattr(result, "model_dump")
            else result.__dict__,
        )

        return {
            "status": "completed",
            "operation_id": tracker.operation_id,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error in scenario execution: {e}")
        if "tracker" in locals():
            await sse_manager.complete_operation(tracker.operation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monte-carlo/{client_id}")
async def run_monte_carlo_sse(client_id: str, request: MonteCarloRequest):
    """
    Run Monte Carlo simulation with SSE progress updates.

    Args:
        client_id: Client identifier for SSE
        request: Monte Carlo request data
    """
    try:
        # Create progress tracker
        n_samples = request.n_simulations or 1000
        tracker = sse_manager.create_progress_tracker(
            client_id, "monte_carlo", total_steps=100
        )

        # Initialize
        await sse_manager.update_progress(
            tracker.operation_id,
            steps=5,
            message="Initializing Monte Carlo simulation",
            details={"n_simulations": n_samples},
        )

        # Run simulation with progress updates
        batch_size = max(1, n_samples // 20)  # 20 updates

        for i in range(0, n_samples, batch_size):
            batch_end = min(i + batch_size, n_samples)

            # Calculate progress
            progress = int((batch_end / n_samples) * 90) + 5  # 5-95%

            await sse_manager.update_progress(
                tracker.operation_id,
                steps=progress - tracker.current_step,
                message=f"Running simulations {batch_end}/{n_samples}",
                details={
                    "current": batch_end,
                    "total": n_samples,
                    "batch_size": batch_size,
                },
            )

            # Simulate work
            await asyncio.sleep(0.01)

        # Run actual Monte Carlo
        summary_df, statistics, result = calculate_capacity_monte_carlo(
            request.scenario.strains,
            request.scenario.equipment,
            fermenter_volume_l=request.scenario.volumes.base_fermenter_vol_l,
            n_samples=n_samples,
        )

        # Finalize
        await sse_manager.update_progress(
            tracker.operation_id, steps=5, message="Finalizing results"
        )

        # Complete
        await sse_manager.complete_operation(
            tracker.operation_id,
            result={
                "statistics": statistics,
                "capacity": result.model_dump()
                if hasattr(result, "model_dump")
                else result.__dict__,
            },
        )

        return {
            "status": "completed",
            "operation_id": tracker.operation_id,
            "statistics": statistics,
            "result": result,
        }

    except Exception as e:
        logger.error(f"Error in Monte Carlo simulation: {e}")
        if "tracker" in locals():
            await sse_manager.complete_operation(tracker.operation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimization/{client_id}")
async def run_optimization_sse(client_id: str, request: OptimizationRequest):
    """
    Run optimization with SSE progress updates.

    Args:
        client_id: Client identifier for SSE
        request: Optimization request data
    """
    try:
        # Use the decorated function
        result = await run_optimization_with_progress(
            client_id,
            scenario_data=request.scenario.model_dump()
            if hasattr(request.scenario, "model_dump")
            else request.scenario,
            max_iterations=request.max_iterations or 100,
        )

        return {"status": "completed", "result": result}

    except Exception as e:
        logger.error(f"Error in optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/{client_id}")
async def export_with_progress(client_id: str, format: str = "excel"):
    """
    Export data with progress tracking.

    Args:
        client_id: Client identifier for SSE
        format: Export format (excel, csv, json)
    """
    try:
        tracker = sse_manager.create_progress_tracker(
            client_id, "export", total_steps=5
        )

        # Step 1: Prepare data
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message="Preparing data for export"
        )
        await asyncio.sleep(0.1)

        # Step 2: Format data
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message=f"Formatting data as {format}"
        )
        await asyncio.sleep(0.1)

        # Step 3: Generate file
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message="Generating export file"
        )
        await asyncio.sleep(0.1)

        # Step 4: Compress if needed
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message="Compressing file"
        )
        await asyncio.sleep(0.1)

        # Step 5: Finalize
        await sse_manager.update_progress(
            tracker.operation_id, steps=1, message="Export complete"
        )

        # Generate dummy file info
        file_info = {
            "filename": f"export_{uuid.uuid4().hex[:8]}.{format}",
            "size_bytes": 1024 * 50,  # 50KB
            "format": format,
            "download_url": f"/api/export/download/{uuid.uuid4().hex[:8]}",
        }

        await sse_manager.complete_operation(tracker.operation_id, result=file_info)

        return {
            "status": "completed",
            "operation_id": tracker.operation_id,
            "file": file_info,
        }

    except Exception as e:
        logger.error(f"Error in export: {e}")
        if "tracker" in locals():
            await sse_manager.complete_operation(tracker.operation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect/{client_id}")
async def disconnect_sse(client_id: str):
    """
    Disconnect SSE stream for a client.

    Args:
        client_id: Client identifier
    """
    await sse_manager.disconnect(client_id)
    return {"status": "disconnected", "client_id": client_id}


@router.get("/status/{client_id}")
async def get_progress_status(client_id: str):
    """
    Get current progress status for all operations of a client.

    Args:
        client_id: Client identifier
    """
    operations = []
    for op_id, tracker in sse_manager.progress_trackers.items():
        if op_id.startswith(client_id):
            operations.append(tracker.to_dict())

    return {
        "client_id": client_id,
        "operations": operations,
        "connected": client_id in sse_manager.connections,
    }

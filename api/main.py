"""
FastAPI main application.
Provides REST API for bioprocess facility design calculations.
"""

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import json
import asyncio
from typing import Dict
from pathlib import Path
from datetime import datetime
import logging
from dotenv import load_dotenv

from api.routers import router
from api.sse_router import router as sse_router
from api.schemas import HealthResponse
from bioprocess.models import ScenarioInput
from bioprocess.orchestrator import (
    prepare_scenario as orch_prepare,
    run_optimization as orch_run_optimization,
    run_capacity_calculation as orch_run_capacity,
    run_equipment_sizing as orch_run_equipment,
    run_economic_analysis as orch_run_econ,
    run_sensitivity_analysis as orch_run_sensitivity,
    run_scenario as orch_run_scenario,
    load_strain_from_database as orch_load_strain,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Bioprocess Facility Design API")

    # Create necessary directories
    for dir_name in ["data", "exports", "configs", "temp", "logs"]:
        Path(dir_name).mkdir(exist_ok=True)

    yield

    # Shutdown
    logger.info("Shutting down API")


# Create FastAPI app
app = FastAPI(
    title="Bioprocess Facility Design API",
    description="API for bioprocess facility design, optimization, and economic analysis",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:8000"]'))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint - redirect to comprehensive UI
@app.get("/")
async def root():
    """Redirect to comprehensive UI."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/app-pro", status_code=303)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check."""
    # Check if critical directories exist
    dirs_ok = all(Path(d).exists() for d in ["data", "exports", "configs"])

    status = "healthy" if dirs_ok else "degraded"

    return HealthResponse(
        status=status,
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        details={"directories": "ok" if dirs_ok else "error"},
    )


# Include API routes
app.include_router(router, prefix="/api")
app.include_router(sse_router, prefix="/api")


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.jobs: Dict[str, asyncio.Task] = {}
        self.cancel_flags: Dict[str, bool] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)


manager = ConnectionManager()


async def _run_scenario_job(websocket: WebSocket, job_id: str, scenario_payload: dict):
    try:
        # Build ScenarioInput and accept both dicts and preset strain names (strings)
        payload = dict(scenario_payload)
        try:
            strains = payload.get("strains", [])
            if isinstance(strains, list) and any(isinstance(s, str) for s in strains):
                converted = []
                for s in strains:
                    if isinstance(s, str):
                        si = orch_load_strain(s)
                        converted.append(si)
                    else:
                        converted.append(s)
                payload["strains"] = converted
        except Exception as conv_err:
            logger.warning(f"WS job {job_id}: strain conversion warning: {conv_err}")
        scenario = ScenarioInput(**payload)
        scenario = orch_prepare(scenario)
        # Small initial cancellation window before any progress is sent
        for _ in range(5):  # ~250ms window total
            await asyncio.sleep(0.05)
            if manager.cancel_flags.get(job_id):
                logger.info(f"WS job {job_id}: cancelled before first progress")
                return
        await websocket.send_json(
            {"type": "progress", "progress": 0.1, "message": "Prepared scenario"}
        )
        logger.info(
            f"WS job {job_id}: scenario prepared (optimize={scenario.optimize_equipment}, volumes={scenario.volumes.volume_options_l})"
        )

        # If optimize requested, run optimization
        if scenario.optimize_equipment:
            opt = orch_run_optimization(scenario)
            logger.info(
                f"WS job {job_id}: optimization completed; best={getattr(opt, 'best_solution', None)}"
            )
            await websocket.send_json(
                {
                    "type": "progress",
                    "progress": 0.3,
                    "message": "Optimization completed",
                }
            )
            if opt and opt.best_solution:
                best = opt.best_solution
                fermenter_volume_l = best.get(
                    "fermenter_volume_l", scenario.volumes.base_fermenter_vol_l
                )
                reactors = best.get("reactors", 4)
                ds_lines = best.get("ds_lines", 2)
            else:
                fermenter_volume_l = scenario.volumes.base_fermenter_vol_l
                reactors = scenario.equipment.reactors_total or 4
                ds_lines = scenario.equipment.ds_lines_total or 2
        else:
            fermenter_volume_l = scenario.volumes.base_fermenter_vol_l
            reactors = (
                scenario.equipment.reactors_total
                if scenario.equipment.reactors_total is not None
                else 4
            )
            ds_lines = (
                scenario.equipment.ds_lines_total
                if scenario.equipment.ds_lines_total is not None
                else 2
            )

        cap_res, batches = orch_run_capacity(
            scenario, fermenter_volume_l, reactors, ds_lines
        )
        logger.info(
            f"WS job {job_id}: capacity done; total_kg={getattr(cap_res, 'total_annual_kg', None)}"
        )
        await websocket.send_json(
            {"type": "progress", "progress": 0.5, "message": "Capacity calculated"}
        )
        equip_res = orch_run_equipment(
            scenario,
            fermenter_volume_l,
            reactors,
            ds_lines,
            target_tpa=scenario.target_tpa,
        )
        await websocket.send_json(
            {"type": "progress", "progress": 0.7, "message": "Equipment sized"}
        )
        econ_res = orch_run_econ(
            scenario, cap_res, equip_res, batches, fermenter_volume_l
        )
        await websocket.send_json(
            {"type": "progress", "progress": 0.9, "message": "Economics calculated"}
        )

        # Stream final result similar to REST output
        await websocket.send_json(
            {
                "type": "result",
                "result": {
                    "kpis": {
                        "npv": econ_res.npv,
                        "irr": econ_res.irr,
                        "payback_years": econ_res.payback_years,
                        "tpa": cap_res.total_annual_kg / 1000,
                        "target_tpa": scenario.target_tpa,
                        "capex": econ_res.total_capex,
                        "opex": econ_res.total_opex,
                        "meets_tpa": cap_res.total_annual_kg + 1e-6 >= scenario.target_tpa * 1000,
                        "production_kg": cap_res.total_annual_kg,
                    },
                    "capacity": cap_res.model_dump()
                    if hasattr(cap_res, "model_dump")
                    else cap_res.__dict__,
                    "economics": econ_res.model_dump()
                    if hasattr(econ_res, "model_dump")
                    else econ_res.__dict__,
                },
            }
        )
    finally:
        manager.jobs.pop(job_id, None)
        manager.cancel_flags.pop(job_id, None)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    from uuid import uuid4

    client_id = None
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle different message types
            if data.get("type") == "connection":
                client_id = data.get("client_id", "anonymous")
                # Don't call manager.connect since we already accepted
                manager.active_connections[client_id] = websocket
                await websocket.send_json(
                    {"type": "connection_ack", "message": f"Connected as {client_id}"}
                )

            elif data.get("type") == "ping":
                await websocket.send_json(
                    {"type": "pong", "timestamp": datetime.now().isoformat()}
                )

            elif data.get("type") == "run_scenario":
                scenario = data.get("scenario")
                if not isinstance(scenario, dict) or not scenario.get("name"):
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid scenario payload"}
                    )
                    continue
                job_id = str(uuid4())
                manager.cancel_flags[job_id] = False
                await websocket.send_json({"type": "job_started", "job_id": job_id})
                # Launch orchestration as background task so we can process cancellations
                task = asyncio.create_task(_run_scenario_job(websocket, job_id, scenario))
                manager.jobs[job_id] = task

            elif data.get("type") == "cancel_job":
                job_id = data.get("job_id")
                task = manager.jobs.get(job_id)
                if task:
                    manager.cancel_flags[job_id] = True
                    try:
                        task.cancel()
                    except Exception:
                        pass
                await websocket.send_json({"type": "job_cancelled", "job_id": job_id})

            elif data.get("type") == "run_batch":
                scenarios = data.get("scenarios", [])
                if not isinstance(scenarios, list) or not scenarios:
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid scenarios list"}
                    )
                    continue
                total = len(scenarios)
                results = []
                # Initial progress notification
                await websocket.send_json(
                    {"type": "batch_progress", "completed": 0, "total": total}
                )
                await asyncio.sleep(0)
                for i, sc_payload in enumerate(scenarios):
                    try:
                        sc = ScenarioInput(**sc_payload)
                        sc = orch_prepare(sc)
                        # Run scenario in a worker thread to keep event loop responsive; skip_snap_opt=True only disables fallback
                        future = asyncio.to_thread(orch_run_scenario, sc, None, True)
                        # Heartbeat while computing to avoid client timeouts
                        while True:
                            try:
                                res = await asyncio.wait_for(future, timeout=1.0)
                                break
                            except asyncio.TimeoutError:
                                await websocket.send_json(
                                    {
                                        "type": "batch_progress",
                                        "completed": i,
                                        "total": total,
                                    }
                                )
                                await asyncio.sleep(0)
                        results.append(
                            res.model_dump()
                            if hasattr(res, "model_dump")
                            else res.__dict__
                        )
                    except Exception as e:
                        results.append({"error": str(e)})
                    # Progress after each scenario regardless of success
                    await websocket.send_json(
                        {"type": "batch_progress", "completed": i + 1, "total": total}
                    )
                    await asyncio.sleep(0)
                await websocket.send_json(
                    {"type": "batch_complete", "results": results, "total": total}
                )
                await asyncio.sleep(0)

            elif data.get("type") == "run_sensitivity":
                scenario = data.get("scenario")
                params = data.get("parameters", [])
                delta = float(data.get("delta_percentage", 0.1))
                try:
                    # Accept string strain names in sensitivity path as well
                    payload = dict(scenario)
                    strains = payload.get("strains", [])
                    if isinstance(strains, list) and any(isinstance(s, str) for s in strains):
                        converted = []
                        for s in strains:
                            if isinstance(s, str):
                                converted.append(orch_load_strain(s))
                            else:
                                converted.append(s)
                        payload["strains"] = converted
                    sc = ScenarioInput(**payload)
                    sc = orch_prepare(sc)
                    # Apply incoming sensitivity parameters and delta and enable sensitivity
                    sc.sensitivity.enabled = True
                    if params:
                        sc.sensitivity.parameters = params
                    sc.sensitivity.delta_percentage = delta
                    # Base configuration: use optimization result to mirror original flow
                    base_best = orch_run_optimization(sc)
                    if base_best and getattr(base_best, "best_solution", None):
                        best = base_best.best_solution
                        base_config = {
                            "fermenter_volume_l": best.get("fermenter_volume_l", sc.volumes.base_fermenter_vol_l),
                            "reactors": best.get("reactors", 4),
                            "ds_lines": best.get("ds_lines", 2),
                        }
                    else:
                        base_config = {
                            "fermenter_volume_l": sc.volumes.base_fermenter_vol_l,
                            "reactors": sc.equipment.reactors_total or 4,
                            "ds_lines": sc.equipment.ds_lines_total or 2,
                        }
                    await websocket.send_json(
                        {
                            "type": "sensitivity_progress",
                            "parameter": params[0] if params else "",
                            "progress": 0.5,
                        }
                    )
                    sens = orch_run_sensitivity(sc, base_config)
                    await websocket.send_json(
                        {
                            "type": "sensitivity_result",
                            "results": sens.model_dump()
                            if sens and hasattr(sens, "model_dump")
                            else (sens.__dict__ if sens else {}),
                        }
                    )
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif data.get("type") == "run_analysis":
                scenario = data.get("scenario")
                if not isinstance(scenario, dict) or not scenario.get("name"):
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid scenario payload"}
                    )
                    continue
                job_id = str(uuid4())
                manager.cancel_flags[job_id] = False
                await websocket.send_json({"type": "job_started", "job_id": job_id})
                # Reuse the same orchestration for analysis for now
                await _run_scenario_job(websocket, job_id, scenario)

            elif data.get("type") == "get_job_status":
                await websocket.send_json({"status": "completed"})

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {data.get('type')}",
                    }
                )

    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if client_id:
            manager.disconnect(client_id)


# Mount static files
web_dir = Path(__file__).parent.parent / "web"
if (web_dir / "static").exists():
    app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")


# Serve web UI
@app.get("/app")
async def serve_app():
    """Serve the web application."""
    index_file = web_dir / "templates" / "index.html"
    if index_file.exists():
        with open(index_file) as f:
            return HTMLResponse(content=f.read())
    return JSONResponse(
        status_code=404, content={"message": "Frontend not yet implemented"}
    )


# Serve comprehensive UI
@app.get("/app-pro")
async def serve_app_pro():
    """Serve the comprehensive web application."""
    index_file = web_dir / "templates" / "index_comprehensive.html"
    if index_file.exists():
        with open(index_file) as f:
            return HTMLResponse(content=f.read())
    return JSONResponse(
        status_code=404, content={"message": "Comprehensive frontend not found"}
    )


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "debug").lower(),
    )

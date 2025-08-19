"""
API schemas for request and response models.
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Import bioprocess models
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from bioprocess.models import (
    ScenarioInput,
    ScenarioResult,
    StrainInput,
    EquipmentConfig,
    OptimizationConfig,
    SensitivityConfig,
)


# API-specific models
class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class MetaResponse(BaseModel):
    """API metadata response."""

    version: str
    description: str
    available_strains: List[str]
    default_assumptions: Dict[str, Any]
    raw_material_prices: Dict[str, float]
    endpoints: List[str]


class RunScenarioRequest(BaseModel):
    """Request model for running a scenario."""

    scenario: ScenarioInput
    optimize: Optional[bool] = None
    async_mode: bool = Field(False, description="Run in background if True")


class RunScenarioResponse(BaseModel):
    """Response model for scenario run."""

    job_id: Optional[str] = Field(None, description="Job ID if async mode")
    result: Optional[ScenarioResult] = Field(None, description="Result if sync mode")
    status: JobStatus
    message: Optional[str] = None


class ExportRequest(BaseModel):
    """Request model for Excel export."""

    scenario_name: str
    result: Optional[ScenarioResult] = None
    scenario_input: Optional[ScenarioInput] = None
    job_id: Optional[str] = Field(None, description="Job ID to export results from")


class ExportResponse(BaseModel):
    """Response model for export."""

    filename: str
    download_url: str
    size_bytes: int
    created_at: str


class OptimizationRequest(BaseModel):
    """Request model for optimization."""

    scenario: ScenarioInput
    max_reactors: int = Field(20, ge=2, le=60)
    max_ds_lines: int = Field(10, ge=1, le=20)
    volume_options: Optional[List[float]] = None
    objectives: Optional[List[str]] = Field(
        default=["irr", "capex"], description="Optimization objectives"
    )


class OptimizationResponse(BaseModel):
    """Response model for optimization."""

    job_id: str
    status: JobStatus
    message: str


class JobInfo(BaseModel):
    """Job information."""

    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    progress: float = Field(0.0, ge=0, le=1)
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    job_type: Optional[str] = None


class JobProgressResponse(BaseModel):
    """Job progress response."""

    job_id: str
    status: JobStatus
    progress: float
    message: Optional[str] = None
    eta_seconds: Optional[float] = None


class ConfigSaveRequest(BaseModel):
    """Request model for saving configuration."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    scenario: ScenarioInput
    overwrite: bool = Field(False, description="Overwrite if exists")


class ConfigSaveResponse(BaseModel):
    """Response model for configuration save."""

    name: str
    saved_at: str
    file_path: str
    message: str


class ConfigListResponse(BaseModel):
    """Response model for configuration list."""

    configs: List[Dict[str, Any]]
    count: int


class SensitivityRequest(BaseModel):
    """Request model for sensitivity analysis."""

    scenario: ScenarioInput
    base_configuration: Dict[str, Any]
    parameters: List[str] = Field(
        default=[
            "discount_rate",
            "tax_rate",
            "electricity_cost",
            "product_price",
            "raw_material_cost",
        ]
    )
    delta_percentage: float = Field(0.1, gt=0, le=0.5)


class BatchScenarioRequest(BaseModel):
    """Request model for batch scenario processing."""

    scenarios: List[ScenarioInput]
    parallel: bool = Field(True, description="Process in parallel")
    max_workers: Optional[int] = Field(None, ge=1, le=10)


class BatchScenarioResponse(BaseModel):
    """Response model for batch processing."""

    job_id: str
    total_scenarios: int
    status: JobStatus
    message: str


class StrainDatabaseResponse(BaseModel):
    """Response model for strain database."""

    strains: List[Dict[str, Any]]
    count: int
    categories: Dict[str, List[str]]


class ValidationError(BaseModel):
    """Validation error model."""

    field: str
    message: str
    value: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None
    validation_errors: Optional[List[ValidationError]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"


class PaginatedResponse(BaseModel):
    """Base model for paginated responses."""

    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# Re-export bioprocess models for convenience
__all__ = [
    # API models
    "JobStatus",
    "HealthResponse",
    "MetaResponse",
    "RunScenarioRequest",
    "RunScenarioResponse",
    "ExportRequest",
    "ExportResponse",
    "OptimizationRequest",
    "OptimizationResponse",
    "JobInfo",
    "JobProgressResponse",
    "ConfigSaveRequest",
    "ConfigSaveResponse",
    "ConfigListResponse",
    "SensitivityRequest",
    "BatchScenarioRequest",
    "BatchScenarioResponse",
    "StrainDatabaseResponse",
    "ValidationError",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
    # Bioprocess models
    "ScenarioInput",
    "ScenarioResult",
    "StrainInput",
    "EquipmentConfig",
    "OptimizationConfig",
    "SensitivityConfig",
]

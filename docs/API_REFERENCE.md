# API Reference

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently, the API does not require authentication. In production, implement API keys or OAuth2.

## Content Type
All requests and responses use `application/json` unless otherwise specified.

## API Endpoints

### System Endpoints

#### Health Check
```http
GET /health
```

Response
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-08-18T10:00:00Z",
  "details": {"directories": "ok"}
}
```

---

### Scenario Management

#### Run Scenario
Execute a bioprocess scenario with the provided configuration.

```http
POST /scenarios/run
```

Request body
```json
{
  "scenario": {
    "name": "Yogurt Facility 10 TPA",
    "target_tpa": 10.0,
    "strains": [
      { "name": "S. thermophilus", "titer_g_per_l": 80.0 }
    ],
    "equipment": { "reactors_total": 4, "ds_lines_total": 2 },
    "volumes": { "base_fermenter_vol_l": 2000 },
    "prices": { "raw_prices": {"Glucose": 0.5} }
  },
  "async_mode": false
}
```
- Notes:
  - StrainInput accepts minimal payloads; legacy field titer_g_per_l maps to yield_g_per_L; unknown fields ignored
  - WVF is fixed to 0.8 on the client/UI; server honors provided volumes.base_fermenter_vol_l

Response (sync)
```json
{
  "result": {
    "scenario_name": "Yogurt Facility 10 TPA",
    "timestamp": "2025-08-18T10:00:00Z",
    "kpis": {
      "npv": 25000000,
      "irr": 0.35,
      "payback_years": 3.2,
      "tpa": 11.45,
      "target_tpa": 10.0,
      "capex": 5.05e6,
      "opex": 1.96e6,
      "meets_tpa": true,
      "production_kg": 11450.0
    },
    "capacity": { /* CapacityResult schema */ },
    "equipment": { /* EquipmentResult schema */ },
    "economics": { /* EconomicsResult schema */ }
  },
  "status": "completed",
  "message": "Scenario completed successfully"
}
```

**Response:**
```json
{
  "name": "Yogurt Facility 10 TPA",
  "timestamp": "2024-12-15T10:00:00Z",
  "capacity": {
    "total_annual_kg": 22376.7,
    "total_feasible_batches": 1189.2,
    "total_good_batches": 1165.5,
    "weighted_up_utilization": 1.0,
    "weighted_ds_utilization": 0.302,
    "bottleneck": "upstream"
  },
  "economics": {
    "total_revenue": 8950680,
    "total_opex": 2058726,
    "total_capex": 5000000,
    "ebitda": 6891954,
    "ebitda_margin": 0.77
  },
  "kpis": {
    "npv": 25000000,
    "irr": 0.35,
    "payback_years": 3.2,
    "roi": 4.5
  }
}
```

**Status Codes:**
- `200 OK` - Scenario executed successfully
- `400 Bad Request` - Invalid input parameters
- `500 Internal Server Error` - Calculation error

#### WebSocket (/ws)

Message types
- connection: { type: "connection", client_id }
- ping/pong
- run_scenario: { type: "run_scenario", scenario }
- cancel_job: { type: "cancel_job", job_id }
- run_batch: { type: "run_batch", scenarios }
- run_sensitivity: { type: "run_sensitivity", scenario, parameters, delta_percentage }

Events
- connection_ack
- job_started: { job_id }
- progress: { progress (0..1), message }
- result: { result: ScenarioResult-like structure with kpis (includes meets_tpa, production_kg) }
- error
- batch_progress: { completed, total }
- batch_complete: { results, total }

---

#### Run Scenario (Async)
Submit a scenario for asynchronous processing.

```http
POST /scenarios/run-async
```

**Request:** Same as synchronous endpoint

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-12-15T10:00:00Z"
}
```

---

#### Batch Processing
Process multiple scenarios in parallel.

```http
POST /scenarios/batch
```

**Request Body:**
```json
{
  "scenarios": [
    { /* Scenario 1 */ },
    { /* Scenario 2 */ },
    { /* Scenario 3 */ }
  ],
  "parallel": true
}
```

**Response:**
```json
{
  "job_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "total_scenarios": 3,
  "status": "processing"
}
```

---

### Optimization

#### Run Optimization
Execute single or multi-objective optimization.

```http
POST /optimization/run
```

**Request Body:**
```json
{
  "scenario": { /* Base scenario configuration */ },
  "config": {
    "mode": "multi_objective",
    "objectives": ["npv", "irr"],
    "max_evaluations": 100,
    "population_size": 50,
    "constraints": {
      "min_capacity_kg": 10000,
      "max_capex": 10000000
    }
  }
}
```

**Response:**
```json
{
  "job_id": "opt-550e8400-e29b-41d4-a716-446655440000",
  "status": "optimizing",
  "estimated_time_seconds": 120
}
```

---

### Sensitivity Analysis

#### Run Sensitivity Analysis
Perform parameter sensitivity analysis.

```http
POST /sensitivity/run
```

**Request Body:**
```json
{
  "scenario": { /* Base scenario */ },
  "config": {
    "parameters": [
      {
        "name": "yield_g_per_L",
        "variations": [-20, -10, 0, 10, 20]
      },
      {
        "name": "media_cost_usd",
        "variations": [-30, -15, 0, 15, 30]
      }
    ],
    "target_metrics": ["npv", "irr", "payback_years"]
  }
}
```

**Response:**
```json
{
  "results": {
    "yield_g_per_L": {
      "npv_impact": [
        {"variation": -20, "value": 20000000},
        {"variation": 0, "value": 25000000},
        {"variation": 20, "value": 30000000}
      ]
    }
  }
}
```

---

### Export

#### Generate Excel Report
Create a comprehensive Excel workbook.

```http
POST /export/excel
```

**Request Body:**
```json
{
  "scenario_result": { /* Complete scenario result */ },
  "include_charts": true,
  "include_sensitivity": true
}
```

**Response:**
Binary Excel file (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)

**Headers:**
```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="bioprocess_report_20241215.xlsx"
```

---

### Job Management

#### Get Job Status
Check the status of an asynchronous job.

```http
GET /jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-12-15T10:00:00Z",
  "completed_at": "2024-12-15T10:02:00Z",
  "result_available": true
}
```

**Status Values:**
- `pending` - Job queued
- `running` - Job in progress
---

### Defaults & Strains

#### Get defaults
```http
GET /defaults
```
Response
```json
{
  "assumptions": { /* EconomicAssumptions defaults */ },
  "raw_prices": { /* RAW_PRICES */ },
  "available_strains": { "S. thermophilus": { /* preset */ }, ... },
  "allocation_policies": ["equal","proportional","inverse_ct"],
  "optimization_objectives": ["npv","irr","capex","opex","payback"]
}
```

#### List strains
```http
GET /strains
```

#### Get strain details
```http
GET /strains/{strain_name}
```

- `completed` - Job finished successfully
- `failed` - Job failed with error
- `cancelled` - Job cancelled by user

---

#### Get Job Result
Retrieve the result of a completed job.

```http
GET /jobs/{job_id}/result
```

**Response:** Depends on job type (scenario result, optimization result, etc.)

---

#### Cancel Job
Cancel a running job.

```http
POST /jobs/{job_id}/cancel
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Job cancelled successfully"
}
```

---

### Configuration Management

#### Save Configuration
Save a scenario configuration for later use.

```http
POST /configs/save
```

**Request Body:**
```json
{
  "name": "My Yogurt Facility",
  "description": "10 TPA yogurt production facility",
  "scenario": { /* Complete scenario configuration */ },
  "tags": ["yogurt", "10tpa", "validated"]
}
```

**Response:**
```json
{
  "config_id": "config-123",
  "name": "My Yogurt Facility",
  "saved_at": "2024-12-15T10:00:00Z"
}
```

---

#### Load Configuration
Load a saved configuration.

```http
GET /configs/{name}
```

**Response:**
```json
{
  "name": "My Yogurt Facility",
  "description": "10 TPA yogurt production facility",
  "scenario": { /* Complete scenario configuration */ },
  "tags": ["yogurt", "10tpa", "validated"],
  "created_at": "2024-12-15T10:00:00Z",
  "modified_at": "2024-12-15T10:00:00Z"
}
```

---

#### List Configurations
Get all saved configurations.

```http
GET /configs
```

**Response:**
```json
{
  "configs": [
    {
      "name": "My Yogurt Facility",
      "description": "10 TPA yogurt production facility",
      "tags": ["yogurt", "10tpa"],
      "created_at": "2024-12-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### Delete Configuration
Delete a saved configuration.

```http
DELETE /configs/{name}
```

**Response:**
```json
{
  "message": "Configuration 'My Yogurt Facility' deleted successfully"
}
```

---

### Strain Database

#### Get All Strains
Retrieve the complete strain database.

```http
GET /strains
```

**Response:**
```json
{
  "strains": [
    {
      "name": "S. thermophilus",
      "category": "yogurt",
      "fermentation_time_h": 14.0,
      "yield_g_per_L": 12.0,
      "media_cost_usd": 88.95,
      "cryo_cost_usd": 191.62
    }
  ],
  "total": 15
}
```

---

#### Get Strain by Name
Get details for a specific strain.

```http
GET /strains/{strain_name}
```

**Response:**
```json
{
  "name": "S. thermophilus",
  "category": "yogurt",
  "fermentation_time_h": 14.0,
  "turnaround_time_h": 9.0,
  "downstream_time_h": 4.0,
  "yield_g_per_L": 12.0,
  "media_cost_usd": 88.95,
  "cryo_cost_usd": 191.62,
  "utility_rates": {
    "fermentation_kw": 300,
    "centrifugation_kw": 15,
    "lyophilization_kw": 1.5,
    "steam_cost": 0.0228
  }
}
```

---

### Default Values

#### Get Default Assumptions
Retrieve default economic assumptions and parameters.

```http
GET /defaults
```

**Response:**
```json
{
  "economic_assumptions": {
    "discount_rate": 0.10,
    "tax_rate": 0.25,
    "depreciation_years": 10,
    "hours_per_year": 8760
  },
  "equipment_defaults": {
    "upstream_availability": 0.92,
    "downstream_availability": 0.90,
    "quality_yield": 0.98
  },
  "labor_defaults": {
    "plant_manager_salary": 104000,
    "fermentation_specialist_salary": 39000
  },
  "price_defaults": {
    "raw_materials": {
      "Glucose": 0.22,
      "Lactose": 0.93
    },
    "products": {
      "yogurt": 400,
      "lacto_bifido": 400
    }
  }
}
```

---

## WebSocket Endpoints

### Real-time Updates
```ws
ws://localhost:8000/ws
```

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

**Message Types:**

**Progress Update:**
```json
{
  "type": "progress",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "progress": 45,
  "message": "Processing strain 2 of 4..."
}
```

**Job Complete:**
```json
{
  "type": "complete",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success"
}
```

**Error:**
```json
{
  "type": "error",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Calculation failed: Invalid yield value"
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": {
      "field": "strains[0].yield_g_per_L",
      "issue": "Must be greater than 0"
    }
  },
  "timestamp": "2024-12-15T10:00:00Z",
  "request_id": "req-123456"
}
```

### Error Codes
- `VALIDATION_ERROR` - Input validation failed
- `NOT_FOUND` - Resource not found
- `CALCULATION_ERROR` - Computation failed
- `JOB_NOT_FOUND` - Job ID does not exist
- `JOB_FAILED` - Async job failed
- `INTERNAL_ERROR` - Server error

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- **Default limit**: 100 requests per minute per IP
- **Batch/optimization endpoints**: 10 requests per minute per IP
- **Export endpoints**: 20 requests per minute per IP

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1702638000
```

---

## Data Types

### Common Types

#### StrainInput
```typescript
interface StrainInput {
  name: string;
  fermentation_time_h: number;
  turnaround_time_h: number;
  downstream_time_h: number;
  yield_g_per_L: number;
  media_cost_usd: number;
  cryo_cost_usd: number;
  utility_rate_ferm_kw: number;
  utility_rate_cent_kw: number;
  utility_rate_lyo_kw: number;
  utility_cost_steam: number;
  licensing_fixed_cost_usd?: number;
  licensing_royalty_pct?: number;
}
```

#### EquipmentConfig
```typescript
interface EquipmentConfig {
  reactors_total: number;
  ds_lines_total: number;
  upstream_availability: number;  // 0-1
  downstream_availability: number; // 0-1
  quality_yield: number;          // 0-1
  allocation_policy?: 'equal' | 'proportional' | 'inverse_ct';
  shared_downstream?: boolean;
}
```

#### ScenarioInput
```typescript
interface ScenarioInput {
  name: string;
  target_tpa: number;
  strains: StrainInput[];
  equipment: EquipmentConfig;
  volumes?: VolumePlan;
  prices?: PriceTables;
  assumptions?: EconomicAssumptions;
  capex?: CapexConfig;
  opex?: OpexConfig;
  labor?: LaborConfig;
}
```

---

## Examples

### Example 1: Simple Scenario Run
```bash
curl -X POST http://localhost:8000/api/scenarios/run \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "target_tpa": 10,
    "strains": [{
      "name": "S. thermophilus",
      "fermentation_time_h": 14,
      "turnaround_time_h": 9,
      "downstream_time_h": 4,
      "yield_g_per_L": 12,
      "media_cost_usd": 100,
      "cryo_cost_usd": 50,
      "utility_rate_ferm_kw": 300,
      "utility_rate_cent_kw": 15,
      "utility_rate_lyo_kw": 1.5,
      "utility_cost_steam": 0.0228
    }],
    "equipment": {
      "reactors_total": 4,
      "ds_lines_total": 2
    }
  }'
```

### Example 2: Async Job with Polling
```python
import requests
import time

# Submit job
response = requests.post('http://localhost:8000/api/scenarios/run-async',
                         json=scenario_data)
job_id = response.json()['job_id']

# Poll for completion
while True:
    status = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
    if status.json()['status'] == 'completed':
        break
    time.sleep(2)

# Get result
result = requests.get(f'http://localhost:8000/api/jobs/{job_id}/result')
print(result.json())
```

### Example 3: WebSocket Progress Monitoring
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'progress') {
    console.log(`Progress: ${data.progress}% - ${data.message}`);
  } else if (data.type === 'complete') {
    console.log('Job completed!');
  }
};

// Submit scenario via API
fetch('/api/scenarios/run-async', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(scenarioData)
});
```

---

## Version History

- **v1.0.0** (2024-12-15): Initial release
  - Core scenario calculations
  - Optimization engine
  - Excel export
  - WebSocket support

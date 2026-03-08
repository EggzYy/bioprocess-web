# Bioprocess Facility Design Web Application

A comprehensive web application for designing and optimizing bioprocess fermentation facilities with economic analysis, capacity planning, and multi-objective optimization.

## Features

- 🧬 **Multi-Strain Management**: Configure bacterial and yeast strains with complete process parameters
- 💰 **Economic Analysis**: CAPEX/OPEX calculations with NPV, IRR, and payback period
- 📊 **Interactive Dashboards**: Real-time visualization with Plotly.js charts
- 🎯 **Optimization**: Single and multi-objective optimization with Pareto frontier analysis
- 🎲 **Monte Carlo Simulation**: Stochastic analysis for risk assessment
- 📑 **Excel Export**: Generate detailed multi-sheet workbooks
- 🔄 **Sensitivity Analysis**: Tornado charts and parameter sweeps

## Project Structure

```
bioprocess-web/
├── bioprocess/          # Core computational engine
│   ├── __init__.py
│   ├── models.py       # Pydantic data models
│   ├── capacity.py     # Capacity calculations
│   ├── econ.py         # Economic calculations
│   ├── sizing.py       # Equipment sizing
│   ├── optimizer.py    # Optimization algorithms
│   ├── excel.py        # Excel export utilities
│   └── presets.py      # Default configurations
├── api/                # FastAPI backend
│   ├── __init__.py
│   ├── main.py        # API application
│   ├── routes.py      # API endpoints
│   ├── jobs.py        # Background job management
│   └── schemas.py     # API schemas
├── web/               # Frontend application
│   ├── static/        # Static assets
│   │   ├── css/       # Stylesheets
│   │   ├── js/        # JavaScript
│   │   └── assets/    # Images, fonts
│   └── templates/     # HTML templates
├── tests/             # Test suite
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── docs/              # Documentation
├── data/              # Data files
└── exports/           # Generated exports


## Documentation Index

See docs/README.md for the documentation index (Getting Started, Parity Mode, Validation, API reference draft, and archived docs).

```

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Node.js 16+ (for frontend build tools, optional)
- Modern web browser (Chrome, Firefox, Safari)

### Installation

1. Clone the repository:
```bash
cd bioprocess-web
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy existing calculation modules:
```bash
cp ../fermentation_capacity_calculator.py bioprocess/
cp ../pricing_integrated.py bioprocess/pricing_integrated_original.py
```

### Running the Application

1. Start the FastAPI backend:
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

2. Open your browser and navigate to:
   - Application: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Alternative API Docs: http://localhost:8000/redoc

### Development

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=bioprocess --cov=api tests/
```

Format code:
```bash
black bioprocess/ api/ tests/
isort bioprocess/ api/ tests/
```

Lint code:
```bash
flake8 bioprocess/ api/ tests/
mypy bioprocess/ api/
```

## API Endpoints

### Core Endpoints

- `GET /api/meta` - Get system metadata and defaults
- `POST /api/run` - Run scenario calculation
- `POST /api/export` - Generate Excel export
- `POST /api/optimize` - Start optimization job
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/results/{job_id}` - Get job results

### Configuration

- `POST /api/config/save` - Save scenario configuration
- `GET /api/config/load/{name}` - Load saved configuration
- `GET /api/config/list` - List saved configurations

## Configuration

The application uses environment variables for configuration:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Computation Limits
MAX_MONTE_CARLO_SAMPLES=10000
MAX_OPTIMIZATION_CONFIGS=1000
MAX_EXPORT_SIZE_MB=100

# File Storage
DATA_DIR=./data
EXPORT_DIR=./exports
CONFIG_DIR=./configs

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation and serialization
- **NumPy/Pandas**: Numerical computation
- **XlsxWriter**: Excel file generation
- **Uvicorn**: ASGI server

### Frontend
- **Bootstrap 5**: UI components and styling
- **Plotly.js**: Interactive charts
- **Vanilla JavaScript**: Core functionality
- **HTML5/CSS3**: Structure and styling

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

The project includes comprehensive test coverage:

- **Unit Tests**: Test individual functions and calculations
- **Integration Tests**: Test API endpoints and workflows
- **Regression Tests**: Ensure parity with original calculations

Run specific test suites:
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/regression/
```

## Documentation

See docs/README.md for the full documentation index.
- API Reference (draft): docs/API_REFERENCE.md
- Parity Mode: docs/ParityMode.md
- Validation: docs/VALIDATION.md
- Test Suite Report: docs/TEST_SUITE_REPORT.md

## License

This project is proprietary software. All rights reserved.

## Support

For issues, questions, or suggestions, please open an issue in the repository.

## Acknowledgments

Based on the original `pricing_integrated.py` and `fermentation_capacity_calculator.py` computational engines.

# Bioprocess Facility Design Web Application
## Project Scope & Requirements Document

### 1. PROJECT SCOPE

#### 1.1 Overview
Build a comprehensive web application that provides a user-friendly interface for bioprocess facility design and economic analysis, leveraging the existing `pricing_integrated.py` and `fermentation_capacity_calculator.py` computational engines.

#### 1.2 Core Functionality
- **Full Parameter Control**: Enable users to modify all aspects of facility design through an intuitive web interface
- **Multi-Strain Management**: Add, edit, and delete bacterial/yeast strains with complete process parameters
- **Economic Analysis**: Comprehensive CAPEX/OPEX calculations with NPV, IRR, and payback period
- **Optimization**: Single and multi-objective optimization for equipment sizing and configuration
- **Monte Carlo Simulation**: Stochastic analysis for risk assessment
- **Excel Export**: Generate detailed multi-sheet workbooks with all calculations
- **Interactive Dashboards**: Real-time visualization of KPIs, capacity, and financial metrics

### 2. SUCCESS CRITERIA

### Policy Updates (Aug 2025)
- Working Volume Fraction is fixed to 0.8 across original and new stacks; no UI override
- Parity policy: production parity must be exact; CAPEX typically within ~5% under parity_mode; IRR/NPV may diverge due to optimizer selection and is acceptable per policy
- Parity-mode economics: original-style CAPEX and OPEX ramp (fixed+variable split) are enabled in the new stack


#### 2.1 Functional Requirements
✓ Users can manage strains with all associated parameters:
  - Process times (fermentation, turnaround, downstream)
  - Media and cryoprotectant costs
  - Utility consumption rates
  - Licensing terms
  - Yield parameters

✓ Users can control economic assumptions:
  - Product pricing by category
  - Raw material prices
  - Labor costs and headcount
  - Tax rates and depreciation
  - Discount rates for NPV

✓ Users can configure equipment:
  - Fermenter volumes (500L to 5000L)
  - Reactor and downstream line counts
  - Allocation policies (equal, proportional, inverse_ct)
  - Equipment ratios and sizing rules

✓ System supports multiple analysis modes:
  - Deterministic capacity calculation
  - Monte Carlo simulation with configurable samples
  - Multi-objective optimization with Pareto frontier
  - Sensitivity analysis with tornado charts

✓ System generates comprehensive outputs:
  - Multi-sheet Excel workbook matching original format
  - Interactive charts for all KPIs
  - Downloadable reports and scenarios
n
#### 2.2 Performance Requirements
- Deterministic calculations complete in < 10 min
- Monte Carlo (1000 samples) complete in < 30 min
- Optimization (100 configurations) complete in < 60 min
- Excel export in < 5 min
- UI responsive with < 100ms interaction feedback

#### 2.3 Quality Requirements
- Production parity exact; CAPEX proximity typically within ~5% under parity_mode; IRR/NPV divergence accepted when due to optimizer selection
- All inputs validated with meaningful error messages
- Progress indicators for long-running operations
- Graceful error recovery and cancellation

### 3. CONSTRAINTS

#### 3.1 Technical Constraints
- **Computational Parity**: Must preserve exact calculation logic from original scripts
- **Frontend Independence**: No heavy framework dependencies (React/Vue/Angular)
  - Use vanilla JavaScript with minimal libraries
  - Bootstrap 5 for UI components
  - Plotly.js for charting
- **Backend Architecture**: FastAPI with Python 3.10+
- **Browser Support**: Chrome, Firefox, Safari (latest 2 versions)

#### 3.2 Design Constraints
- **Single Page Application**: All functionality in one cohesive interface
- **Responsive Design**: Support desktop (1920x1080) and tablet (1024x768) viewports
- **Async Operations**: Heavy computations must not block UI
- **Progress Visibility**: Real-time updates for long-running tasks
- **Cancellation**: Users can abort optimization/Monte Carlo runs

#### 3.3 Data Constraints
- **Session Management**: Scenarios persist during browser session
- **File Limits**: Excel exports up to 100MB
- **Computation Limits**: Max 10,000 Monte Carlo samples
- **Optimization Limits**: Max 1,000 configurations evaluated

### 4. SYSTEM BOUNDARIES

#### 4.1 In Scope
- Web-based parameter input and editing
- Capacity and economic calculations
- Optimization algorithms (single and multi-objective)
- Excel report generation
- Interactive data visualization
- Scenario save/load functionality
- Sensitivity analysis tools

#### 4.2 Out of Scope
- User authentication and multi-tenancy
- Cloud deployment infrastructure
- Real-time collaboration features
- Integration with external ERP/MES systems
- Mobile phone viewport optimization
- Automated report scheduling
- Historical data tracking

### 5. DELIVERABLES

#### 5.1 Software Components
1. **Backend API Service** (`/api`)
   - FastAPI application with comprehensive endpoints
   - Pydantic models for validation
   - Background job processing

2. **Frontend Web Application** (`/web`)
   - Single page HTML application
   - Responsive Bootstrap 5 UI
   - Interactive Plotly.js dashboards

3. **Computational Core** (`/bioprocess`)
   - Refactored calculation engine
   - Optimization algorithms
   - Excel export utilities

4. **Documentation** (`/docs`)
   - API reference
   - User guide
   - Developer setup instructions
   - Data dictionary

#### 5.2 Testing Suite
- Unit tests for calculation accuracy
- Integration tests for API endpoints
- UI component tests
- Performance benchmarks
- Regression test suite

### 6. ACCEPTANCE CRITERIA

#### 6.1 Functional Acceptance
- [ ] Demo Scenario 1: fac1 in pricing_integrated_original.py file
- [ ] Demo Scenario 2: fac2 in pricing_integrated_original.py file
- [ ] Demo Scenario 3: fac3 in pricing_integrated_original.py file
- [ ] Demo Scenario 4: fac4 in pricing_integrated_original.py file
- [ ] Demo Scenario 5: fac5 in pricing_integrated_original.py file
- [ ] Cross-validation: Results match original script outputs ±5%

#### 6.2 Technical Acceptance
- [ ] All unit tests passing (>90% coverage)
- [ ] API documentation reviewed and updated after docs re-organization
- [ ] No critical security vulnerabilities
- [ ] Performance benchmarks met
- [ ] Clean code review passed

#### 6.3 User Acceptance
- [ ] Intuitive navigation without training
- [ ] Clear error messages and validation
- [ ] Responsive UI with no lag
- [ ] Excel exports open correctly
- [ ] Charts display accurately

### 7. RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| Calculation differences from original | High | Extensive unit testing, snapshot comparisons |
| Performance issues with large datasets | Medium | Implement caching, pagination, async processing |
| Browser compatibility issues | Low | Use standard web APIs, test on multiple browsers |
- Last Updated: 2025-08-18
- Status: ACTIVE

| Complex UI overwhelming users | Medium | Progressive disclosure, tooltips, help documentation |
| Long computation times | Medium | Progress indicators, cancellation, background jobs |

### 8. VERSION CONTROL

- Version: 1.0.0
- Created: 2024-01-15
- Last Updated: 2024-01-15
- Status: APPROVED

---
*This document defines the complete scope and requirements for the Bioprocess Facility Design Web Application project.*

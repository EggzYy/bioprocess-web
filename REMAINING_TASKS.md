# Task List for Next Phase: Frontend and Deployment

This document outlines the remaining tasks for the bioprocess web application project. The backend calculation engine has been validated for parity with the original scripts and is considered complete. The focus for the next phase of work is on frontend implementation, deployment, and documentation.

---

## High Priority - Core Frontend Functionality

These tasks are essential to make the application usable. The goal is to connect the existing UI components to the validated backend API.

### 1. Complete Frontend JavaScript Integration
- **Goal:** Wire up the main user interface to the backend API endpoints.
- **Tasks:**
    - [ ] **Connect API Client:** Implement a robust API client in JavaScript to handle all communication with the backend.
    - [ ] **Implement Form Submission:** Write handlers for all forms (e.g., scenario definition, optimization parameters) to gather user input and send it to the appropriate API endpoint (`/api/scenarios/run`).
    - [ ] **Handle API Responses:** Process successful responses from the backend and display the results (KPIs, charts, tables) in the UI.
    - [ ] **Implement Progress Tracking:** For long-running operations (like optimization), use the WebSocket endpoint (`/api/ws/sse/{client_id}`) to show real-time progress to the user.
    - [ ] **Error Handling:** Implement user-friendly error messages when the API returns an error.

### 2. Fix Frontend Strain Management
- **Goal:** Make the strain management modal fully functional.
- **Tasks:**
    - [ ] **CRUD Functionality:** Implement the "add", "edit", and "delete" functionality for strains, connecting them to the relevant backend endpoints.
    - [ ] **Strain Selection:** Allow users to select from a list of existing strains in the database when creating a new scenario.
    - [ ] **Dynamic Table Updates:** Ensure the strain table in the UI updates automatically after any changes.
    - [ ] **Form Validation:** Add client-side validation to the strain input forms to prevent invalid data from being sent to the backend.

### 3. Connect Charts and Dashboards to Real Data
- **Goal:** Replace placeholder data in charts with live data from the backend.
- **Tasks:**
    - [ ] **Wire up Chart Rendering:** Connect the existing Plotly.js chart functions in `charts.js` to the data returned by the API.
    - [ ] **Dashboard Layout:** Finalize the layout of the main results dashboard, ensuring all key charts (e.g., Pareto front, cash flow) and KPIs are displayed clearly.
    - [ ] **Chart Interactivity:** Enable chart interactivity features like zooming, panning, and exporting as PNG.
    - [ ] **Responsive Design:** Ensure charts and dashboards are responsive and display correctly on different screen sizes.

---

## Medium Priority - Deployment and DevOps

Once the frontend is functional, the next step is to prepare the application for deployment.

### 4. Docker Configuration
- **Goal:** Containerize the application for easy and reproducible deployments.
- **Tasks:**
    - [ ] **Create Dockerfile:** Write a `Dockerfile` for the main Python application.
    - [ ] **Setup docker-compose:** Create a `docker-compose.yml` file to manage the application and any related services (e.g., a web server, a potential Redis cache).
    - [ ] **Environment Variables:** Document and configure all necessary environment variables (e.g., `API_HOST`, `LOG_LEVEL`). Create a `.env.example` file.
    - [ ] **Volume Mounts:** Configure volume mounts for any data that needs to persist, such as saved configurations or a strain database file.

### 5. Production Deployment Setup
- **Goal:** Prepare the application to be served in a production environment.
- **Tasks:**
    - [ ] **Production Configuration:** Create a production-ready configuration for the application (e.g., disabling debug mode).
    - [ ] **Web Server/Reverse Proxy:** Set up a reverse proxy like Nginx to handle incoming traffic, serve static files, and forward API requests to the Uvicorn server.
    - [ ] **SSL/TLS:** Configure SSL/TLS certificates to enable HTTPS.
    - [ ] **Health Check Endpoint:** Add a health check endpoint to the API for monitoring.
    - [ ] **Deployment Scripts:** Create simple shell scripts to automate the deployment process (e.g., `deploy.sh`).

---

## Low Priority - Nice-to-Have Features and Polish

These tasks can be addressed after the core functionality is complete and the application is deployable.

### 6. Frontend Polish
- **Goal:** Improve the overall user experience.
- **Tasks:**
    - [ ] **Loading Spinners:** Add loading spinners and other visual cues to indicate when the application is busy processing a request.
    - [ ] **Error Toasts:** Implement non-blocking error notifications (e.g., toast messages) for a smoother user experience.
    - [ ] **Help Tooltips:** Add tooltips to explain complex input parameters and chart features.
    - [ ] **UI Consistency:** Perform a general review of the UI to ensure consistency in layout, fonts, and colors.

### 7. Advanced Features
- **Goal:** Implement additional features to enhance the application's capabilities.
- **Tasks:**
    - [ ] **Import from Excel:** Implement the frontend part of the "Import from Excel" feature.
    - [ ] **Export to PDF:** Add a feature to export key results or charts as a PDF report.
    - [ ] **Scenario Comparison:** Design and implement a UI to compare the results of two or more scenarios side-by-side.

---

## New - Documentation and Training

To ensure the application is maintainable and usable by others, documentation is critical.

### 8. User and Developer Documentation
- **Goal:** Create comprehensive documentation for end-users and future developers.
- **Tasks:**
    - [ ] **Create USER_GUIDE.md:** Write a user guide with screenshots that explains how to use the application, from defining a scenario to interpreting the results.
    - [ ] **Create DEPLOYMENT.md:** Write a guide that explains how to set up the development environment and deploy the application to production.
    - [ ] **API Documentation:** Review and update the auto-generated API documentation to ensure all endpoints are clearly explained.

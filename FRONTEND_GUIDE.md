# 🚀 Bioprocess Web Frontend - Quick Start Guide

## Access the Application

The backend server is already running! You can access the application at:

### 🌐 **Web Interface**: http://localhost:8000/app
### 📚 **API Documentation**: http://localhost:8000/docs

## Features You Can Test

### 1. **Scenario Configuration**
- **Facility Tab**: 
  - Adjust target TPA (tonnes per annum)
  - Configure number of reactors and downstream lines
  - Set allocation policies
  
- **Strains Tab**:
  - Add production strains with different properties
  - Set titer, productivity, conversion yield
  - Configure cycle times
  - Save strains to database

- **Economics Tab**:
  - Adjust financial parameters (discount rate, project lifetime)
  - Configure pricing assumptions
  - Set labor and operational costs

- **Equipment Tab**:
  - View/modify equipment costs
  - Adjust scaling factors
  - Configure equipment specifications

### 2. **Run Analysis**
Click the green "Run Analysis" button in the top navigation to:
- Execute the bioprocess simulation
- Calculate capacity and economics
- Generate equipment sizing
- View comprehensive results

### 3. **View Results**
After running analysis, you'll see:
- **KPI Dashboard**: Key metrics like NPV, IRR, payback period
- **Capacity Charts**: Utilization, production breakdown, waterfall analysis
- **Economics Charts**: Financial timeline, cost breakdown
- **Equipment Details**: Sized equipment list with costs
- **Sensitivity Analysis**: Parameter impact visualization

### 4. **Advanced Features**

#### Monte Carlo Simulation
1. Enable "Run Monte Carlo simulation" checkbox
2. Set number of iterations
3. Define parameter variations
4. View probability distributions

#### Sensitivity Analysis
1. Click "Run Sensitivity Analysis"
2. Select parameters to test
3. View tornado chart showing impact

#### Export Options
- **Save Scenario**: Download configuration as JSON
- **Export to Excel**: Generate comprehensive Excel report
- **Copy Charts**: Right-click on any chart to save as image

### 5. **Strain Database**
- Add custom strains with specific characteristics
- Save strains for future use
- Load saved strains into scenarios
- Compare multiple strain options

## Testing Workflow

### Quick Test:
1. Open http://localhost:8000/app
2. Leave default values
3. Click "Run Analysis" (green button)
4. Review results in all tabs

### Comprehensive Test:
1. **Configure Facility**:
   - Set target to 20 TPA
   - Change reactors to 6
   - Enable shared downstream

2. **Add Strains**:
   - Click "Add Strain"
   - Name: "High Titer Strain"
   - Titer: 150 g/L
   - Productivity: 2.5 g/L/h
   - Save to database

3. **Adjust Economics**:
   - Set discount rate to 15%
   - Modify product price to $8/kg
   - Update labor costs

4. **Run Analysis**:
   - Click "Run Analysis"
   - Wait for results
   - Navigate through result tabs

5. **Export Results**:
   - Click "Export to Excel"
   - Check the exports/ folder

## Troubleshooting

### If the page doesn't load:
```bash
# Check if backend is running
curl http://localhost:8000/

# Restart the backend
./start_app.sh
```

### If forms don't submit:
- Open browser console (F12)
- Check for JavaScript errors
- Verify API endpoints are responding

### If charts don't display:
- Ensure Plotly.js is loaded
- Check browser console for errors
- Try refreshing the page

## Browser Compatibility
- ✅ Chrome/Chromium (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Edge

## Development Tips

### Watch Console Logs:
Press F12 in browser to open developer tools and monitor:
- Network requests to API
- JavaScript console for errors
- Application state changes

### Test API Directly:
Open http://localhost:8000/docs to:
- Test individual endpoints
- View request/response schemas
- Debug API issues

### Real-time Updates:
The backend auto-reloads on code changes:
- Edit Python files → backend restarts
- Edit JavaScript/CSS → refresh browser

## Stop the Application

To stop the server:
1. Go to the terminal running the server
2. Press `Ctrl + C`

Or kill the process:
```bash
kill $(lsof -Pi :8000 -sTCP:LISTEN -t)
```

## Need Help?

- Check API docs: http://localhost:8000/docs
- View server logs in terminal
- Browser console for JavaScript errors
- The README.md for project overview

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess
import time

@pytest.fixture(scope="module")
def app():
    proc = subprocess.Popen(["./start_app.sh"])
    time.sleep(20) # Increased wait time for server to start
    yield
    proc.terminate()

def test_run_analysis_e2e(app, selenium):
    selenium.get("http://localhost:8000/app-pro")

    # Wait for the run analysis button to be clickable
    run_button = WebDriverWait(selenium, 30).until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Run Analysis')]"))
    )

    # Click the button
    run_button.click()

    # Wait for the results to appear
    results = WebDriverWait(selenium, 60).until(
        EC.presence_of_element_located((By.ID, "results-container"))
    )

    assert results.is_displayed()

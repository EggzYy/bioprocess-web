import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess
import time
import functools

def generate_bug_report(test_method):
    @functools.wraps(test_method)
    def wrapper(self, *args, **kwargs):
        try:
            test_method(self, *args, **kwargs)
        except Exception as e:
            with open("BUG_REPORT.txt", "a") as f:
                f.write(f"Test failed: {test_method.__name__}\n")
                f.write(f"Error: {e}\n\n")
            raise
    return wrapper

class E2ETest(unittest.TestCase):
    def setUp(self):
        self.proc = subprocess.Popen(["./start_app.sh"])
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/home/jules/.cache/selenium/chrome/linux64/139.0.7258.138/chrome"
        
        service = Service(executable_path="/home/jules/.cache/selenium/chromedriver/linux64/139.0.7258.138/chromedriver")
        
        # Wait for the server to be ready
        for _ in range(20):
            try:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.get("http://localhost:8000/app-pro")
                if "Bioprocess Facility Designer - Comprehensive" in self.driver.title:
                    return
            except Exception as e:
                print(f"Error connecting to server: {e}")
            time.sleep(1)
        
        self.fail("Server did not start in 20 seconds")

    def tearDown(self):
        self.driver.quit()
        self.proc.terminate()
        self.proc.wait()

    @generate_bug_report
    def test_home_page_title(self):
        self.assertEqual(self.driver.title, "Bioprocess Facility Designer - Comprehensive")

    @generate_bug_report
    def test_run_analysis_button_present(self):
        button = self.driver.find_element(By.ID, "runAnalysisBtn")
        self.assertIsNotNone(button)

    @generate_bug_report
    def test_capacity_chart_present(self):
        chart = self.driver.find_element(By.ID, "capacityChart")
        self.assertIsNotNone(chart)

    @generate_bug_report
    def test_utilization_chart_present(self):
        chart = self.driver.find_element(By.ID, "utilizationChart")
        self.assertIsNotNone(chart)

    @generate_bug_report
    def test_capex_chart_present(self):
        chart = self.driver.find_element(By.ID, "capexChart")
        self.assertIsNotNone(chart)

    @generate_bug_report
    def test_opex_chart_present(self):
        chart = self.driver.find_element(By.ID, "opexChart")
        self.assertIsNotNone(chart)

    @generate_bug_report
    def test_cash_flow_chart_present(self):
        chart = self.driver.find_element(By.ID, "cashFlowChart")
        self.assertIsNotNone(chart)

    @generate_bug_report
    def test_tornado_chart_present(self):
        chart = self.driver.find_element(By.ID, "tornadoChart")
        self.assertIsNotNone(chart)

    @generate_bug_report
    def test_run_analysis_button_click_shows_modal(self):
        button = self.driver.find_element(By.ID, "runAnalysisBtn")
        button.click()
        
        wait = WebDriverWait(self.driver, 10)
        modal = wait.until(EC.presence_of_element_located((By.ID, "progressModal")))
        self.assertTrue(modal.is_displayed())

if __name__ == "__main__":
    unittest.main()

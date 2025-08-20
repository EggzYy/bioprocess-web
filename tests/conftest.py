import pytest
from selenium.webdriver.chrome.options import Options

@pytest.fixture
def chrome_options(chrome_options):
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    return chrome_options

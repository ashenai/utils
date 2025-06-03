"""
Module for scraping web pages with JavaScript content using Selenium.
This is an optional module that can be used by the main scraper.py to handle
pages that load content dynamically through JavaScript.
"""
import time
import importlib.util

# Check if required packages are available
SELENIUM_AVAILABLE = importlib.util.find_spec("selenium") is not None
WEBDRIVER_MGR_AVAILABLE = importlib.util.find_spec("webdriver_manager") is not None

# Default user agent header
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def fetch_page_with_javascript(url, wait_for_selector=None, wait_time=10, user_agent=None):
    """
    Fetch a web page with JavaScript execution using Selenium if available.
    
    Args:
        url: URL to fetch
        wait_for_selector: CSS selector to wait for (optional)
        wait_time: Time to wait for the selector in seconds
        user_agent: User agent string to use (optional)
        
    Returns:
        HTML content of the page after JavaScript execution or None if Selenium is not available
    """
    if not SELENIUM_AVAILABLE:
        print("WARNING: Selenium is not installed. Cannot execute JavaScript.")
        print("To install required packages, run: pip install selenium webdriver-manager")
        return None
    
    try:
        # Only import if selenium is available
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.common.exceptions import TimeoutException, WebDriverException
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={user_agent or DEFAULT_USER_AGENT}")
        
        try:
            driver = None
            if WEBDRIVER_MGR_AVAILABLE:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Try to use locally installed ChromeDriver
                driver = webdriver.Chrome(options=chrome_options)
                
            if not driver:
                print("Failed to initialize Chrome WebDriver")
                return None
                
            print(f"Fetching page with JavaScript: {url}")
            driver.get(url)
            
            if wait_for_selector:
                try:
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                    print(f"Found element matching selector: {wait_for_selector}")
                except TimeoutException:
                    print(f"Timeout waiting for element with selector: {wait_for_selector}")
            else:
                # Wait for the page to load completely
                print(f"Waiting {wait_time} seconds for page to load...")
                time.sleep(wait_time)
                
            page_source = driver.page_source
            return page_source
        finally:
            if driver:
                driver.quit()
    except Exception as e:
        print(f"Error fetching page with JavaScript: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    test_url = "https://azure.microsoft.com/en-us/updates?id=495755"
    html = fetch_page_with_javascript(
        test_url,
        wait_for_selector="div.ocr-faq-item__body, div.content-area, article",
        wait_time=15
    )
    
    if html:
        print("Successfully fetched page with JavaScript")
        print(f"HTML length: {len(html)} bytes")
        
        # Save to a file for inspection
        with open("azure_test_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved HTML to azure_test_page.html")
    else:
        print("Failed to fetch page with JavaScript")

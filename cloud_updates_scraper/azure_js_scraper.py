# Modified Azure update scraper function to handle JavaScript-rendered content

def scrape_azure_update_with_js(url, rss_title, rss_pub_date, user_agent_header):
    """
    Scrapes an individual Azure update page for detailed information,
    including handling JavaScript-rendered content.
    
    This function requires Selenium and webdriver_manager to be installed:
    pip install selenium webdriver-manager
    
    Args:
        url: The URL to scrape
        rss_title: The title from the RSS feed
        rss_pub_date: The publication date from the RSS feed
        user_agent_header: User agent header to use for the request
        
    Returns:
        A dictionary with scraped data or None if scraping fails
    """
    try:
        import time
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        from webdriver_manager.chrome import ChromeDriverManager
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        import re
        import json
    except ImportError as e:
        print(f"Required modules not available: {e}")
        print("To install required packages: pip install selenium webdriver-manager")
        return None
        
    print(f"Scraping Azure update with JavaScript support: {url}")
    
    try:
        # Set up headless Chrome
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if user_agent_header:
            options.add_argument(f"user-agent={user_agent_header['User-Agent']}")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Load the page
        driver.get(url)
        
        # Wait for content to load
        try:
            # First try to wait for specific content selectors
            selectors = "div.ocr-faq-item__body, div.content-area, article, div[role='main']"
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selectors))
            )
            print("Found content using one of the selectors")
        except TimeoutException:
            # If specific content doesn't appear, wait a fixed time
            print("Timeout waiting for specific content, falling back to fixed wait")
            time.sleep(10)
        
        # Get the rendered HTML
        html_content = driver.page_source
        driver.quit()
        
        # Use BeautifulSoup to parse the content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process the content (you can reuse the same logic from your existing function)
        title = rss_title
        page_date_str = None
        meta_tag = soup.find('meta', property='article:published_time')
        if meta_tag and meta_tag.get('content'): 
            page_date_str = meta_tag['content']
        
        if not page_date_str:
            # Try to find date in the page (reuse your date extraction logic)
            date_element = soup.find(['time', 'span', 'p', 'div'], class_=re.compile(r"date|time|published|updated", re.I))
            if date_element:
                if date_element.name == 'time' and date_element.has_attr('datetime'):
                    page_date_str = date_element['datetime']
                else: 
                    page_date_str = date_element.get_text(strip=True)
                    
        # Continue with the rest of your processing logic...
        # This is just a skeleton - you would need to complete the implementation 
        # based on your existing scrape_azure_update function
        
        # When done, return the extracted data
        return {
            'title': title,
            'url': url,
            'date_posted': page_date_str or rss_pub_date,
            'description': "JavaScript rendered content",  # Replace with actual extraction
            'links': "JavaScript links",  # Replace with actual extraction
            'status': "JavaScript status",  # Replace with actual extraction
            'update_type': "JavaScript update type",  # Replace with actual extraction
            'product_list': "JavaScript product list",  # Replace with actual extraction
            'categories': "JavaScript categories"  # Replace with actual extraction
        }
        
    except Exception as e:
        print(f"Error scraping Azure page with JavaScript: {e}")
        return None

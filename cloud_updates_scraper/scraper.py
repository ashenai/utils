import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import re
import json # Ensure json is imported globally

# Try to import the JavaScript scraper module
try:
    import js_support
    from js_support import JS_SCRAPER_AVAILABLE
    if JS_SCRAPER_AVAILABLE:
        from js_scraper import fetch_page_with_javascript
except ImportError:
    JS_SCRAPER_AVAILABLE = False
import time
import importlib.util

# Check if Selenium is available
SELENIUM_AVAILABLE = importlib.util.find_spec("selenium") is not None
if SELENIUM_AVAILABLE:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    # ChromeDriverManager is in webdriver_manager which might not be installed
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

USER_AGENT_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_page_with_javascript(url: str, wait_for_selector: str = None, wait_time: int = 10) -> str:
    """
    Fetch a web page with JavaScript execution using Selenium if available.
    
    Args:
        url: URL to fetch
        wait_for_selector: CSS selector to wait for (optional)
        wait_time: Time to wait for the selector in seconds
        
    Returns:
        HTML content of the page after JavaScript execution or None if Selenium is not available
    """
    selenium_spec = importlib.util.find_spec("selenium")
    if selenium_spec is None:
        print("WARNING: Selenium is not installed. Cannot execute JavaScript. Run: pip install selenium webdriver-manager")
        return None
    
    try:
        # Only import if selenium is available
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        # Check for webdriver_manager
        webdriver_mgr_spec = importlib.util.find_spec("webdriver_manager")
        webdriver_mgr_available = webdriver_mgr_spec is not None
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={USER_AGENT_HEADER['User-Agent']}")
        
        try:
            if webdriver_mgr_available:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Try to use locally installed ChromeDriver
                driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Error initializing Chrome WebDriver: {e}")
            print("If you don't have ChromeDriver installed, run: pip install webdriver-manager")
            return None
            
        try:
            print(f"Fetching page with JavaScript: {url}")
            driver.get(url)
            
            if wait_for_selector:
                try:
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                except TimeoutException:
                    print(f"Timeout waiting for element with selector: {wait_for_selector}")
            else:
                # Wait for the page to load completely
                time.sleep(wait_time)
                
            page_source = driver.page_source
            return page_source
        finally:
            driver.quit()
    except Exception as e:
        print(f"Error fetching page with JavaScript: {e}")
        return None

def fetch_rss_feed(url: str) -> BeautifulSoup:
    """ Fetches the content from the given URL and parses it as XML. """
    try:
        response = requests.get(url, headers=USER_AGENT_HEADER, timeout=10)
        response.raise_for_status()
        try: soup = BeautifulSoup(response.content, 'lxml-xml')
        except Exception:
            try: soup = BeautifulSoup(response.content, 'xml')
            except Exception: soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"Error fetching RSS feed from {url}: {e}"); raise

def parse_aws_rss(feed_content: BeautifulSoup) -> list[dict]:
    """ Parses AWS RSS feed content to extract update details. """
    updates = []
    if not feed_content: return updates
    for item in feed_content.find_all('item'):
        date_str = item.find('pubDate').text.strip() if item.find('pubDate') else 'N/A'
        updates.append({
            'title': item.find('title').text.strip() if item.find('title') else 'N/A',
            'url': item.find('link').text.strip() if item.find('link') else 'N/A',
            'date_posted': format_date(date_str)  # Format the date consistently
        })
    return updates

def extract_azure_status_from_title(title):
    """
    Extract Azure status information from the title text.
    
    Args:
        title: The title text to analyze
        
    Returns:
        str: Status extracted from title or None if not found
    """
    # Common status phrases in titles
    status_patterns = [
        # Generally Available patterns
        (r'\bGenerally\s+Available\b', "Generally Available"),
        (r'\bGA\b', "Generally Available"),
        (r'\b(is\s+)?(now\s+)?available\s+(in|for)\b', "Generally Available"),
        (r'\b(is\s+)?(now\s+)?(generally\s+)available\b', "Generally Available"),
        
        # Preview patterns
        (r'\bPublic\s+Preview\b', "Public Preview"),
        (r'\bPrivate\s+Preview\b', "Private Preview"),
        (r'\bIn\s+Preview\b', "In Preview"),
        (r'\b(now\s+)?(in\s+)?preview\b', "In Preview"),
        (r'\b(now\s+)?(available\s+)?in\s+preview\b', "In Preview"),
        
        # Retirement patterns
        (r'\bRetirement\b', "Retirement"),
        (r'\bRetir(ing|ed|ement)\b', "Retirement"),
        (r'\bEnd(\s+of)?\s+Support\b', "Retirement"),
        (r'\bDeprecated?\b', "Retirement"),
        (r'\bSunset(ing|ted)?\b', "Retirement"),
        
        # Launch patterns
        (r'\b(now\s+)?Available\b', "Launched"),
        (r'\bLaunch(ing|ed)?\b', "Launched"),
        (r'\bIntroduc(ing|ed)\b', "Launched"),
        (r'\bReleas(ing|ed)\b', "Launched"),
        (r'\bAnnouncing\b', "In Development")
    ]
    
    if not title:
        return None
        
    for pattern, status in status_patterns:
        if re.search(pattern, title, re.IGNORECASE):
            # Normalize the status value for consistency
            return normalize_azure_status(status)
            
    return None

def classify_azure_category(category_text):
    """
    Classify an Azure category as status, update type, or product/category.
    
    Args:
        category_text: The category text to classify
        
    Returns:
        tuple: (category_type, category_text) where category_type is one of:
               'status', 'update_type', 'category', or 'product'
               
    Note:
        - 'status' is a single value in Azure updates
        - 'update_type', 'category', and 'product' can have multiple values
    """
    # Define the category classification rules
    status_values = {
        "Retirement", "In Development", "In Preview", "Launched", 
        "Generally Available", "Public Preview", "Private Preview",
        # Make sure lowercase versions are also included
        "In preview"
    }
    
    type_values = {
        "Compliance", "Features", "Gallery", "Management", "Microsoft Build", 
        "Microsoft Connect", "Microsoft Ignite", "Microsoft Inspire", 
        "Open Source", "Operating System", "Pricing & Offerings", 
        "Regions & Datacenters", "Retirements", "SDK and Tools", "Security", "Services"
    }
    
    # Additional Azure product categories that don't fall into status or type
    known_categories = {
        "AI + machine learning", "Analytics", "Compute", "Containers", "Databases", 
        "Developer tools", "DevOps", "Hybrid + multicloud", "Identity", "Integration", 
        "Internet of Things", "Management and governance", "Media", "Migration", 
        "Mixed reality", "Mobile", "Networking", "Security", "Storage", 
        "Virtual desktop infrastructure", "Web"
    }
    
    # First normalize any potential status values
    normalized_status = normalize_azure_status(category_text)
    
    # Check if the normalized text is in our status values
    if normalized_status in status_values:
        return ('status', normalized_status)
    elif category_text in type_values:
        return ('update_type', category_text)
    elif category_text in known_categories:
        return ('category', category_text)
    elif category_text.lower() == "in preview" or category_text.lower() == "preview":
        # Special case for catching any "In preview" variants that might be missed
        return ('status', "In Preview")
    else:
        return ('product', category_text)

def parse_azure_rss(feed_content: BeautifulSoup) -> list[dict]:
    """ Parses Azure RSS feed content to extract update details. """
    updates = []
    if not feed_content: return updates
    
    for item in feed_content.find_all('item'):
        title_text = item.find('title').text.strip() if item.find('title') else 'N/A'
        
        # Get the date - prioritize lastBuildDate (most accurate for updates), fall back to pubDate
        date_posted = 'N/A'
        if item.find('lastBuildDate'):
            date_posted = item.find('lastBuildDate').text.strip()
        elif item.find('pubDate'):
            date_posted = item.find('pubDate').text.strip()
        
        # Basic item details
        update_item = {
            'title': title_text,
            'url': item.find('link').text.strip() if item.find('link') else 'N/A',
            'date_posted': date_posted,
            'status': "N/A",  # Will set from categories or title below
            'update_type': [],  # Multiple update types possible
            'product_list': [],  # Multiple products possible 
            'categories': []     # Multiple categories possible
        }
        
        # Extract categories
        for category_tag in item.find_all('category'):
            if not category_tag.text: continue
            
            category_text = category_tag.text.strip()
            category_type, value = classify_azure_category(category_text)

            # Status is single-valued, others are multi-valued
            if category_type == 'status':
                update_item['status'] = value
            elif category_type == 'update_type':
                update_item['update_type'].append(value)
            elif category_type == 'category':
                update_item['categories'].append(value)
            elif category_type == 'product':
                update_item['product_list'].append(value)
        
        # If status wasn't found in categories, try to extract it from title
        if update_item['status'] == "N/A":
            title_status = extract_azure_status_from_title(title_text)
            if title_status:
                update_item['status'] = title_status
        
        # Apply normalization to ensure consistency
        update_item['status'] = normalize_azure_status(update_item['status'])
        
        # Convert lists to string format for consistency with existing code
        update_item['update_type'] = ", ".join(update_item['update_type']) if update_item['update_type'] else "N/A"
        update_item['product_list'] = ", ".join(update_item['product_list']) if update_item['product_list'] else "N/A"
        update_item['categories'] = ", ".join(update_item['categories']) if update_item['categories'] else "N/A"
        
        # Format the date consistently
        update_item['date_posted'] = format_date(update_item['date_posted'])
        
        updates.append(update_item)
    
    return updates

def format_date(date_string: str) -> str:
    """ Converts various date string formats to 'MM/DD/YYYY'. """
    if not date_string or date_string == 'N/A': return "N/A"
    formats_to_try = [ 
        "%a, %d %b %Y %H:%M:%S Z", "%a, %d %b %Y %H:%M:%S %z", 
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%B %d, %Y",
        "%d %b %Y %H:%M:%S %z", "%d %B %Y %H:%M:%S %z"  # Additional formats for lastBuildDate
    ]
    for fmt in formats_to_try:
        try:
            dt_obj = None
            if fmt == "%a, %d %b %Y %H:%M:%S Z" and date_string.endswith(" GMT"):
                dt_obj = datetime.strptime(date_string.replace(" GMT", " Z"), fmt)
            elif fmt == "%Y-%m-%dT%H:%M:%S%z":
                dt_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else: dt_obj = datetime.strptime(date_string, fmt)
            if dt_obj: return dt_obj.strftime("%m/%d/%Y")
        except ValueError: continue
    try: # Fallback for ISO 8601 without explicit timezone
        dt_obj = datetime.fromisoformat(date_string)
        return dt_obj.strftime("%m/%d/%Y")
    except ValueError: pass
    print(f"Warning: Could not parse date string: {date_string} with known formats."); return date_string

def extract_product_from_title(title: str) -> str:
    """ Extracts AWS product name from the RSS title. """
    if not title: return "N/A"
    match = re.search(r"(?:Amazon|AWS)\s+([\w\s.-]+?)(?:\s+now|\s+announces|\s+introduces|\s+adds|\s+launches|\s+supports|\s+is\s+now|,|\s+in\s+|\s+for\s+|$)", title, re.IGNORECASE)
    if match:
        product = match.group(1).strip().rstrip('.-,')
        if product.lower() not in ["aws", "amazon"] and len(product) > 2 : return product
    known_products = ["S3", "EC2", "RDS", "Lambda", "VPC", "CloudFormation", "CloudWatch", "DynamoDB", "Elastic Beanstalk", "EMR", "ECS", "EKS", "Fargate", "MWAA", "SageMaker", "Route 53", "App Runner", "Amplify" ]
    for prod in known_products:
        if re.search(r"\b" + re.escape(prod) + r"\b", title): return prod
    return "N/A"

def scrape_aws_update(url: str, rss_title: str, rss_pub_date: str) -> dict | None:
    """ Scrapes an individual AWS update page for detailed information. """
    try:
        response = requests.get(url, headers=USER_AGENT_HEADER, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}"); return None
    soup = BeautifulSoup(response.content, 'html.parser')
    title_val = rss_title # Renamed to avoid conflict
    page_date_str = None
    time_tag = soup.find('time'); date_posted = None
    if time_tag and time_tag.has_attr('datetime'): page_date_str = time_tag['datetime']
    if not page_date_str:
        wn_post_date_tag = soup.find('p', class_='wn-post-date')
        if wn_post_date_tag:
            date_text = wn_post_date_tag.get_text(strip=True)
            match = re.search(r"(\w+ \d{1,2}, \d{4})", date_text, re.IGNORECASE)
            if match: page_date_str = match.group(1)
    if not page_date_str:
        date_text_match_on_page = soup.find(string=re.compile(r"Posted On: \w+ \d{1,2}, \d{4}", re.IGNORECASE))
        if date_text_match_on_page:
            match = re.search(r"(\w+ \d{1,2}, \d{4})", date_text_match_on_page, re.IGNORECASE)
            if match: page_date_str = match.group(1)
    date_posted = format_date(page_date_str if page_date_str else rss_pub_date)
    description_text = "N/A"; links_list = []; content_html_source = None; processed_via_json = False
    json_script_tags = soup.find_all('script', type='application/json')
    for script_tag in json_script_tags:
        if script_tag.string and '"postBody":' in script_tag.string: 
            print("DEBUG: Found a JSON script tag potentially containing postBody.")
            try:
                json_data = json.loads(script_tag.string)
                if (json_data and isinstance(json_data, dict) and json_data.get('data') and isinstance(json_data['data'], dict) and json_data['data'].get('items') and isinstance(json_data['data']['items'], list) and len(json_data['data']['items']) > 0 and isinstance(json_data['data']['items'][0], dict) and json_data['data']['items'][0].get('fields') and isinstance(json_data['data']['items'][0]['fields'], dict) and json_data['data']['items'][0]['fields'].get('postBody')):
                    content_html_source = json_data['data']['items'][0]['fields']['postBody']
                    print("DEBUG: Successfully extracted postBody HTML from JSON.")
                    processed_via_json = True; break 
            except Exception as e: print(f"DEBUG: Error processing JSON for AWS: {e}")
    if processed_via_json and content_html_source:
        content_soup = BeautifulSoup(content_html_source, 'html.parser')
        paragraphs = content_soup.find_all(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        description_text = "\n".join([p.get_text(separator=' ', strip=True) for p in paragraphs]) if paragraphs else content_soup.get_text(separator='\n', strip=True)
        for a_tag in content_soup.find_all('a', href=True):
            href = a_tag['href']; absolute_url = urljoin(url, href)
            if absolute_url not in links_list: links_list.append(absolute_url)
    else:
        if not processed_via_json: print("DEBUG: AWS JSON script/postBody method failed. Falling back to CSS selectors.")
        content_selectors = ["div.wn-body", "div.aws-text-box", "article", "main#main-content"]
        description_html_element = next((soup.select_one(s) for s in content_selectors if soup.select_one(s)), None)
        if description_html_element:
            content_elements = description_html_element.find_all(['p', 'li'], recursive=True)
            description_text = "\n".join([el.get_text(separator=' ', strip=True) for el in content_elements]) if content_elements else description_html_element.get_text(separator='\n', strip=True)
            for a_tag in description_html_element.find_all('a', href=True):
                href = a_tag['href']; absolute_url = urljoin(url, href)
                if absolute_url not in links_list: links_list.append(absolute_url)
        else: print(f"Warning: AWS Fallback CSS selectors also failed on page {url}")
    description_text = re.sub(r'\n\s*\n+', '\n', description_text).strip()
    if description_text.lower().startswith("posted on:") and "\n" in description_text:
        lines = description_text.split("\n", 2)
        if len(lines) > 1 and re.match(r"^\s*\w+ \d{1,2}, \d{4}", lines[1].strip()): 
            description_text = lines[2].strip() if len(lines) > 2 else ""
    links_str = ",".join(links_list) if links_list else "N/A"
    product = extract_product_from_title(rss_title)
    return {'title': title_val, 'url': url, 'date_posted': date_posted, 'description': description_text, 'links': links_str, 'product': product}

def _extract_azure_metadata_item(metadata_section_soup: BeautifulSoup, heading_text: str) -> str | None:
    """ 
    Helper to find a heading in Azure metadata and extract related text or links.
    This is the fallback method used when metadata isn't available from the RSS feed.
    """
    # TODO: Verify/Refine heading tags (h3, h4, strong, etc.)
    heading_tag = metadata_section_soup.find(['h3', 'h4', 'strong'], string=re.compile(r"^\s*" + re.escape(heading_text) + r"\s*$", re.IGNORECASE))
    if not heading_tag: return None
    
    items = []
    # Strategy: Find the parent container of the heading, then look for lists/links within that container
    # or in the immediate next sibling of that container if it's structured as heading-column, value-column.
    current_element = heading_tag
    # Try to find a common ancestor that would also contain the values or be adjacent to value container
    # Limit upward traversal to avoid going too high in the DOM
    for _ in range(3): # Try up to 3 levels up for a container
        parent = current_element.parent
        if not parent: break
        
        # Option 1: Items are in a list (ul) or div that is a sibling to the heading or heading's direct wrapper
        # E.g. <div class="item"><div class="label"><h4>Products</h4></div> <div class="value"><ul><li>P1</li></ul></div></div>
        # Or   <div class="item"><h4>Products</h4> <ul><li>P1</li></ul> </div>
        value_container = parent.find_next_sibling(['ul', 'div'])
        if not value_container: # If heading is wrapped, check sibling of parent
             value_container = parent.parent.find_next_sibling(['ul', 'div']) if parent.parent else None
        if not value_container : # If items are children of the parent of the heading
            value_container = parent

        if value_container:
            links = value_container.find_all('a', href=True)
            if links:
                for link in links: items.append(link.get_text(strip=True))
                if items: break 
            
            list_items = value_container.find_all('li')
            if list_items:
                for li in list_items: items.append(li.get_text(strip=True))
                if items: break
            
            # If no links or list items, get text from spans or the container itself, avoiding heading
            spans = value_container.find_all('span')
            if spans:
                for span in spans: 
                    if span.find(['h3','h4','strong']): continue # Don't re-add heading
                    items.append(span.get_text(strip=True))
                if items: break
            
            # Fallback: get text of the value_container, if it's not too complex
            if not items and value_container.name in ['div', 'p'] and len(value_container.find_all(['div','ul','p','h3','h4','strong'])) == 0 :
                text = value_container.get_text(strip=True)
                if text and text.lower() != heading_text.lower(): items.append(text); break
        
        if items: break # Found items, stop upward traversal
        current_element = parent # Move up for next iteration
        if current_element.name == 'body': break # Stop if we reach body

    result = ", ".join(filter(None, items)) if items else None
    
    # Apply normalization for status values
    if heading_text.lower() == "status" and result:
        result = normalize_azure_status(result)
        
    return result


def fetch_page_with_javascript(url: str, wait_for_selector: str = None, wait_time: int = 10) -> str:
    """
    Fetch a web page with JavaScript execution using Selenium if available.
    
    Args:
        url: URL to fetch
        wait_for_selector: CSS selector to wait for (optional)
        wait_time: Time to wait for the selector in seconds
        
    Returns:
        HTML content of the page after JavaScript execution or None if Selenium is not available
    """
    selenium_spec = importlib.util.find_spec("selenium")
    if selenium_spec is None:
        print("WARNING: Selenium is not installed. Cannot execute JavaScript. Run: pip install selenium webdriver-manager")
        return None
    
    try:
        # Only import if selenium is available
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        
        # Check for webdriver_manager
        webdriver_mgr_spec = importlib.util.find_spec("webdriver_manager")
        webdriver_mgr_available = webdriver_mgr_spec is not None
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={USER_AGENT_HEADER['User-Agent']}")
        
        try:
            if webdriver_mgr_available:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Try to use locally installed ChromeDriver
                driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Error initializing Chrome WebDriver: {e}")
            print("If you don't have ChromeDriver installed, run: pip install webdriver-manager")
            return None
            
        try:
            print(f"Fetching page with JavaScript: {url}")
            driver.get(url)
            
            if wait_for_selector:
                try:
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                except TimeoutException:
                    print(f"Timeout waiting for element with selector: {wait_for_selector}")
            else:
                # Wait for the page to load completely
                time.sleep(wait_time)
                
            page_source = driver.page_source
            return page_source
        finally:
            driver.quit()
    except Exception as e:
        print(f"Error fetching page with JavaScript: {e}")
        return None

def scrape_azure_update(url: str, rss_title: str, rss_pub_date: str, rss_metadata: dict = None) -> dict | None:
    """ 
    Scrapes an individual Azure update page for detailed information.
    
    Args:
        url: The URL of the Azure update
        rss_title: Title from the RSS feed
        rss_pub_date: Publication date from the RSS feed
        rss_metadata: Optional metadata extracted from RSS feed (status, update_type, product_list, categories)
    """
    try:
        # First try to load the page with JavaScript execution
        if "azure.microsoft.com" in url and "/updates" in url:
            print(f"Attempting to fetch Azure page with JavaScript execution: {url}")
            # For Azure updates pages, first try with JavaScript execution
            html_content = fetch_page_with_javascript(
                url, 
                wait_for_selector="div.ocr-faq-item__body, div.content-area, article",
                wait_time=15
            )
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
            else:
                # Fall back to regular requests if JavaScript execution fails
                print("JavaScript execution failed, falling back to standard HTTP request")
                response = requests.get(url, headers=USER_AGENT_HEADER, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
        else:
            # For non-Azure updates pages, use standard requests
            response = requests.get(url, headers=USER_AGENT_HEADER, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching Azure page {url}: {e}")
        return None

    # Check for JSON-based content that might contain the data
    json_script_tags = soup.find_all('script', type='application/json') + soup.find_all('script', {'id': re.compile(r'__NEXT_DATA__')})
    content_html_source = None
    processed_via_json = False
    json_metadata = {}
    
    for script_tag in json_script_tags:
        if script_tag.string:
            try:
                json_data = json.loads(script_tag.string)
                # Look for key patterns that might contain update data
                if isinstance(json_data, dict):
                    # Handle common patterns in Azure JSON data
                    if json_data.get('props', {}).get('pageProps', {}).get('pageData'):
                        content_data = json_data['props']['pageProps']['pageData']
                        print("DEBUG: Found pageData in JSON script tag.")
                        processed_via_json = True
                        
                        # Try to extract metadata from the JSON
                        if isinstance(content_data, dict):
                            # Extract status if available
                            if content_data.get('status'):
                                json_metadata['status'] = content_data['status']
                            
                            # Extract update type
                            if content_data.get('updateType'):
                                json_metadata['update_type'] = content_data['updateType']
                                
                            # Extract products/services
                            if content_data.get('services') and isinstance(content_data['services'], list):
                                json_metadata['product_list'] = ', '.join(content_data['services'])
                                
                            # Extract categories
                            if content_data.get('categories') and isinstance(content_data['categories'], list):
                                json_metadata['categories'] = ', '.join(content_data['categories'])
                        
                        break
            except Exception as e:
                print(f"DEBUG: Error processing JSON for Azure: {e}")
                
    # print(f"\n--- HTML Snippet for Azure URL: {url} (first 150k chars) ---")
    # print(soup.prettify()[:150000]) 
    # print("--- End HTML Snippet ---\n")

    title = rss_title
    
    # Use the RSS feed date if available and properly formatted
    date_posted = rss_pub_date
    if date_posted == "N/A" or not date_posted:
        # Try to extract date from page if RSS date is not available
        page_date_str = None
        meta_tag = soup.find('meta', property='article:published_time')
        if meta_tag and meta_tag.get('content'): page_date_str = meta_tag['content']
        
        if not page_date_str: # Try other common date patterns
            date_element = soup.find(['time', 'span', 'p', 'div'], class_=re.compile(r"date|time|published|updated", re.I))
            if date_element:
                if date_element.name == 'time' and date_element.has_attr('datetime'):
                    page_date_str = date_element['datetime']
                else: page_date_str = date_element.get_text(strip=True)
        if not page_date_str: # Fallback text search
            date_text_parent = soup.find(lambda tag: tag.name in ['p', 'div', 'span'] and ("Published:" in tag.get_text() or "Updated:" in tag.get_text()) and len(tag.get_text()) < 100)
            if date_text_parent:
                match = re.search(r"(?:Published|Updated):\s*(\w+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})", date_text_parent.get_text(), re.IGNORECASE)
                if match: page_date_str = match.group(1)
        date_posted = format_date(page_date_str) if page_date_str else "N/A"

    description_text = "N/A"; links_list = []
    # TODO: Verify/Refine these selectors after analyzing full HTML from a typical Azure update page
    description_selectors = [
        "div.html-content", "section[aria-label='article body']", "div.article-details", 
        "div.content-area", "div.main-content", "article.content-body", "article",
        "div.row > div.column.medium-9", "div.row > div.col-md-9", "div.ocr-faq-item__body", "div.accordion-item.col-xl-8",
        "div[role='main']" 
    ]
    description_html_element = next((soup.select_one(s) for s in description_selectors if soup.select_one(s)), None)
    
    if description_html_element:
        for unwanted in description_html_element.find_all(['div', 'section'], class_=re.compile("social|share|rating|feedback|related")):
            unwanted.decompose()
        paragraphs = description_html_element.find_all(['p', 'li'], recursive=True)
        description_text = "\n".join([p.get_text(separator=' ', strip=True) for p in paragraphs]) if paragraphs else description_html_element.get_text(separator='\n', strip=True)
        description_text = re.sub(r'\n\s*\n+', '\n', description_text).strip()
        for a_tag in description_html_element.find_all('a', href=True):
            href = a_tag['href']; absolute_url = urljoin(url, href)
            if absolute_url not in links_list: links_list.append(absolute_url)
    else: print(f"Warning: Azure description element not found for {url}")
    links_str = ",".join(links_list) if links_list else "N/A"

    # TODO: Verify/Refine these selectors for metadata area
    metadata_container_selectors = [
        "div.row.metadata-tags", "div.pzl-aside-bg-grey", "aside[aria-label='article metadata']", 
        "div[data-bi-area='sidebar']", "div.column.medium-3", "div.col-md-3", "div.statusBoxes", "div.cloudInstance.section", "div.platforms.section"
    ]
    metadata_section_soup = next((soup.select_one(s) for s in metadata_container_selectors if soup.select_one(s)), soup) # Fallback to whole soup
    if metadata_section_soup == soup: print(f"DEBUG: Azure metadata section not specifically found for {url}, using whole soup.")

    status = _extract_azure_metadata_item(metadata_section_soup, "Status")
    update_type = _extract_azure_metadata_item(metadata_section_soup, "Update type")
    product_list = _extract_azure_metadata_item(metadata_section_soup, "Products") or \
                   _extract_azure_metadata_item(metadata_section_soup, "Services") or \
                   _extract_azure_metadata_item(metadata_section_soup, "Product")
    categories = _extract_azure_metadata_item(metadata_section_soup, "Categories") or \
                 _extract_azure_metadata_item(metadata_section_soup, "Category")

    # Merge metadata from different sources with priority: 
    # 1. RSS feed metadata (most reliable for structured data)
    # 2. JSON metadata from the page
    # 3. HTML metadata extracted from the page
    # 4. Default values
    
    # Get the best value for each metadata field
    final_status = "N/A"
    final_update_type = "N/A"
    final_product_list = "N/A"
    final_categories = "N/A"
    
    # Start with HTML-extracted metadata
    if status: final_status = status
    if update_type: final_update_type = update_type
    if product_list: final_product_list = product_list
    if categories: final_categories = categories
    
    # Override with JSON metadata if available
    if json_metadata.get('status'): final_status = json_metadata['status']
    if json_metadata.get('update_type'): final_update_type = json_metadata['update_type']
    if json_metadata.get('product_list'): final_product_list = json_metadata['product_list']
    if json_metadata.get('categories'): final_categories = json_metadata['categories']
    
    # Finally, use RSS metadata (highest priority) if available
    if rss_metadata:
        # Status is single-valued
        if rss_metadata.get('status') and rss_metadata.get('status') != "N/A": 
            final_status = rss_metadata['status']
        
        # For multi-valued fields, use RSS metadata if it exists
        if rss_metadata.get('update_type') and rss_metadata.get('update_type') != "N/A": 
            final_update_type = rss_metadata['update_type']
        if rss_metadata.get('product_list') and rss_metadata.get('product_list') != "N/A": 
            final_product_list = rss_metadata['product_list']
        if rss_metadata.get('categories') and rss_metadata.get('categories') != "N/A": 
            final_categories = rss_metadata['categories']
    
    # Final normalization of status for consistency
    final_status = normalize_azure_status(final_status)
    
    return {
        'title': title, 
        'url': url, 
        'date_posted': date_posted, 
        'description': description_text, 
        'links': links_str, 
        'status': final_status, 
        'update_type': final_update_type, 
        'product_list': final_product_list, 
        'categories': final_categories
    }

def normalize_azure_status(status):
    """
    Normalizes Azure status values for consistent handling.
    
    Args:
        status: The status string to normalize
        
    Returns:
        str: Normalized status value
    """
    status_mapping = {
        # Map all variants of status values to their canonical form
        "in preview": "In Preview",
        "in preview.": "In Preview",
        "preview": "In Preview",
        "public preview": "Public Preview",
        "private preview": "Private Preview",
        "generally available": "Generally Available",
        "ga": "Generally Available",
        "retirement": "Retirement",
        "retiring": "Retirement",
        "retired": "Retirement",
        "in development": "In Development",
        "launched": "Launched"
    }
    
    if not status or status == "N/A":
        return "N/A"
        
    # Case-insensitive lookup
    lower_status = status.lower().strip()
    if lower_status in status_mapping:
        return status_mapping[lower_status]
    
    # Return original if no mapping found
    return status

if __name__ == '__main__':
    aws_rss_url = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
    print(f"\n--- Fetching AWS RSS feed from {aws_rss_url} to get a live test URL ---")
    live_test_url_aws, live_rss_title_aws, live_rss_pub_date_aws = None, None, None
    try:
        aws_feed_content = fetch_rss_feed(aws_rss_url)
        if aws_feed_content:
            aws_updates = parse_aws_rss(aws_feed_content)
            if aws_updates:
                print(f"Found {len(aws_updates)} AWS updates in the feed.")
                json_page_test_url = "https://aws.amazon.com/about-aws/whats-new/2025/06/amazon-lex-aws-cloudformation-govcloud-us-west-advanced-features" 
                test_update = next((u for u in aws_updates if u['url'] == json_page_test_url), aws_updates[0])
                live_test_url_aws, live_rss_title_aws, live_rss_pub_date_aws = test_update['url'], test_update['title'], test_update['date_posted']
                print(f"Using AWS test URL: {live_test_url_aws}")
    except Exception as e: print(f"Error processing AWS RSS for test: {e}")

    if live_test_url_aws:
        print(f"\n--- Testing AWS Update Scraper for URL: {live_test_url_aws} ---")
        scraped_data_aws = scrape_aws_update(live_test_url_aws, live_rss_title_aws, live_rss_pub_date_aws)
        if scraped_data_aws:
            print("Scraped AWS Data:"); [print(f"  {k.capitalize()}: {v[:300] if isinstance(v, str) and (k == 'description' or k == 'links') else v}...") for k, v in scraped_data_aws.items()]
    else: print("Failed to get a live AWS URL for testing.")

    azure_rss_url = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss"
    print(f"\n--- Fetching Azure RSS feed from {azure_rss_url} to get a live test URL ---")
    live_test_url_azure, live_rss_title_azure, live_rss_pub_date_azure = None, None, None
    try:
        azure_feed_content = fetch_rss_feed(azure_rss_url)
        if azure_feed_content:
            azure_updates = parse_azure_rss(azure_feed_content)
            if azure_updates:
                print(f"Found {len(azure_updates)} Azure updates in the feed.")
                example_azure_url = "https://azure.microsoft.com/en-us/updates?id=495605" # From task description
                test_update = next((u for u in azure_updates if u['url'] == example_azure_url), azure_updates[0])
                live_test_url_azure, live_rss_title_azure, live_rss_pub_date_azure = test_update['url'], test_update['title'], test_update['date_posted']
                print(f"Using Azure test URL: {live_test_url_azure}")
    except Exception as e: print(f"Error processing Azure RSS for test: {e}")
    
    if live_test_url_azure:
        print(f"\n--- Testing Azure Update Scraper for URL: {live_test_url_azure} ---")
        
        # Extract metadata from the test update
        test_update_metadata = {
            'status': test_update.get('status', "N/A"),
            'update_type': test_update.get('update_type', "N/A"),
            'product_list': test_update.get('product_list', "N/A"),
            'categories': test_update.get('categories', "N/A")
        }
        print(f"RSS metadata: {test_update_metadata}")
        
        scraped_data_azure = scrape_azure_update(
            live_test_url_azure, 
            live_rss_title_azure, 
            live_rss_pub_date_azure,
            test_update_metadata
        )
        if scraped_data_azure:
            print("Scraped Azure Data:"); [print(f"  {k.capitalize()}: {v[:300] if isinstance(v, str) and (k == 'description' or k == 'links') else v}...") for k, v in scraped_data_azure.items()]
    else: print("Failed to get a live Azure URL for testing.")

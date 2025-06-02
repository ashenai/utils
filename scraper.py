import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import re
import json # Ensure json is imported globally

USER_AGENT_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

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
        updates.append({
            'title': item.find('title').text.strip() if item.find('title') else 'N/A',
            'url': item.find('link').text.strip() if item.find('link') else 'N/A',
            'date_posted': item.find('pubDate').text.strip() if item.find('pubDate') else 'N/A'
        })
    return updates

def parse_azure_rss(feed_content: BeautifulSoup) -> list[dict]:
    """ Parses Azure RSS feed content to extract update details. """
    updates = []
    if not feed_content: return updates
    for item in feed_content.find_all('item'):
        updates.append({
            'title': item.find('title').text.strip() if item.find('title') else 'N/A',
            'url': item.find('link').text.strip() if item.find('link') else 'N/A',
            'date_posted': item.find('pubDate').text.strip() if item.find('pubDate') else 'N/A'
        })
    return updates

def format_date(date_string: str) -> str:
    """ Converts various date string formats to 'MM/DD/YYYY'. """
    if not date_string: return "N/A"
    formats_to_try = [ 
        "%a, %d %b %Y %H:%M:%S Z", "%a, %d %b %Y %H:%M:%S %z", 
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%B %d, %Y"
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
    """ Helper to find a heading in Azure metadata and extract related text or links. """
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

    return ", ".join(filter(None, items)) if items else None


def scrape_azure_update(url: str, rss_title: str, rss_pub_date: str) -> dict | None:
    """ Scrapes an individual Azure update page for detailed information. """
    try:
        response = requests.get(url, headers=USER_AGENT_HEADER, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Azure page {url}: {e}"); return None

    soup = BeautifulSoup(response.content, 'html.parser')
    # print(f"\n--- HTML Snippet for Azure URL: {url} (first 150k chars) ---")
    # print(soup.prettify()[:150000]) 
    # print("--- End HTML Snippet ---\n")

    title = rss_title
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
    date_posted = format_date(page_date_str if page_date_str else rss_pub_date)

    description_text = "N/A"; links_list = []
    # TODO: Verify/Refine these selectors after analyzing full HTML from a typical Azure update page
    description_selectors = [
        "div.html-content", "section[aria-label='article body']", "div.article-details", 
        "div.content-area", "div.main-content", "article.content-body", "article",
        "div.row > div.column.medium-9", "div.row > div.col-md-9", 
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
        "div[data-bi-area='sidebar']", "div.column.medium-3", "div.col-md-3"
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

    return {
        'title': title, 'url': url, 'date_posted': date_posted, 'description': description_text, 
        'links': links_str, 'status': status or "N/A", 'update_type': update_type or "N/A", 
        'product_list': product_list or "N/A", 'categories': categories or "N/A"
    }

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
        scraped_data_azure = scrape_azure_update(live_test_url_azure, live_rss_title_azure, live_rss_pub_date_azure)
        if scraped_data_azure:
            print("Scraped Azure Data:"); [print(f"  {k.capitalize()}: {v[:300] if isinstance(v, str) and (k == 'description' or k == 'links') else v}...") for k, v in scraped_data_azure.items()]
    else: print("Failed to get a live Azure URL for testing.")

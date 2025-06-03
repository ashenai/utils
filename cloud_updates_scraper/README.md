# Cloud Provider Update Scraper

## Description

This tool scrapes software and service updates from AWS (Amazon Web Services) and Azure (Microsoft Azure) public RSS feeds. It then visits each update page to extract more detailed information. All collected data, including titles, URLs, publication dates, descriptions, and provider-specific metadata, is saved into an Excel workbook (`cloud_updates.xlsx`).

The project utilizes the following Python libraries:
- `requests` for fetching web content.
- `BeautifulSoup4` for parsing HTML and XML.
- `openpyxl` for creating and updating Excel files.

## Features

*   Fetches the latest updates from official AWS and Azure RSS feeds.
*   Scrapes detailed information from individual update announcement pages.
*   Stores structured data in a single Excel file (`cloud_updates.xlsx`) for easy viewing and analysis.
*   The AWS scraper can handle different page structures, including pages where content is embedded within JSON script tags.
*   Includes basic error handling for network issues and individual page scraping failures, allowing the process to continue for other items.
*   Organizes data with clear headers in the Excel sheet, distinguishing between AWS and Azure-specific fields.

## Setup and Installation

1.  **Prerequisites:**
    *   Python 3.7 or higher.

2.  **Clone the Repository:**
    ```bash
    # Replace with actual repository URL when available
    git clone https://example.com/your-repo-name.git
    cd your-repo-name
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the following content:
    ```
    requests
    beautifulsoup4
    openpyxl
    lxml 
    ```
    Then, install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `lxml` is recommended for robust XML/HTML parsing with BeautifulSoup and was used during development).*

## How to Run

1.  Navigate to the project's root directory in your terminal.
2.  Execute the main script:
    ```bash
    python main.py
    ```
3.  The script will process updates from both AWS and Azure. Progress and any issues will be logged to the console.
4.  Upon completion, the Excel file named `cloud_updates.xlsx` will be created or updated in the project root directory.

## Azure Scraper - Important Note

The scraper for Azure update pages (`scrape_azure_update` function in `scraper.py`) currently uses generalized CSS selectors to find the main content (description) and specific metadata (Status, Update type, Products, Categories). Due to the complexity and variability of Azure update page HTML structures, these selectors are best-guess placeholders and may not always extract all details accurately for every Azure update page. The AWS scraper is generally more robust due to more consistent page structures or available JSON data.

### Guidance for Improvement (Azure)

To improve Azure data extraction accuracy:

1.  **Obtain Full HTML:** For an Azure update page that isn't scraping well, temporarily add a line like `print(soup.prettify())` at the beginning of the `scrape_azure_update` function in `scraper.py`. Run `python main.py` (you might want to temporarily limit `main.py` to process only that one Azure URL for easier debugging) to output the full HTML of that page to your console.
2.  **Analyze HTML:** Save this HTML output to a file and open it in a browser or text editor. Use browser developer tools (Inspect Element) to understand the DOM structure and identify reliable CSS selectors for:
    *   The main content/description area (e.g., a specific `<div>`, `<article>`, or `<section>` that wraps the primary text).
    *   The container holding all metadata items (like Status, Update Type, Products, Categories). This is often a sidebar or a specific `div` section.
    *   The specific tags and classes for each metadata item's heading and its corresponding value(s).
3.  **Update `scraper.py`:**
    *   Modify the `description_selectors` list within the `scrape_azure_update` function with the more precise selector(s) you identified for the main description content.
    *   Update the `metadata_container_selectors` list with the selector for the section containing all metadata items.
    *   If necessary, adjust the logic within the `_extract_azure_metadata_item` helper function based on how metadata headings and their values are structured relative to each other on the page. Pay attention to comments like `# TODO: Verify/Refine this selector` in the code.

## Dependencies

The project relies on the following Python libraries (also listed in `requirements.txt`):

*   `requests`: For making HTTP requests to fetch RSS feeds and web pages.
*   `beautifulsoup4`: For parsing XML (RSS feeds) and HTML (update pages).
*   `openpyxl`: For reading from and writing to Excel (.xlsx) files.
*   `lxml`: (Recommended) An efficient XML and HTML parser that can be used by BeautifulSoup.

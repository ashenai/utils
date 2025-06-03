import logging
import argparse
import sys
from datetime import datetime

from scraper import (
    fetch_rss_feed,
    parse_aws_rss,
    parse_azure_rss,
    scrape_aws_update,
    scrape_azure_update
)
from excel_writer import ExcelUpdater

# Constants
AWS_RSS_URL = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
AZURE_RSS_URL = "https://www.microsoft.com/releasecommunications/api/v2/azure/rss" # Verified in previous Azure RSS subtask
EXCEL_FILENAME = "cloud_updates.xlsx"
TEST_LIMIT = 3  # Number of items to process in test mode

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Enable debug logging if needed
# Uncomment the next line to see more detailed logs
# logging.getLogger().setLevel(logging.DEBUG)

def parse_date_arg(date_str):
    """Parse a date string in MM/DD/YYYY format to a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%m/%d/%Y')
    except ValueError:
        logging.error(f"Invalid date format: {date_str}. Expected MM/DD/YYYY.")
        sys.exit(1)

def is_date_in_range(date_str, from_date=None, to_date=None):
    """Check if a date string is within the specified range.
    
    Args:
        date_str: Date string in MM/DD/YYYY format
        from_date: Start date (datetime object)
        to_date: End date (datetime object)
        
    Returns:
        True if the date is in range, False otherwise
    """
    if not date_str or date_str == 'N/A' or (not from_date and not to_date):
        return True  # No filter or no valid date to filter on
        
    try:
        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
        in_range = True
        
        if from_date:
            in_range = in_range and date_obj >= from_date
            if not in_range:
                logging.debug(f"Date {date_str} is before from_date {from_date.strftime('%m/%d/%Y')}")
        
        if to_date:
            compare_result = date_obj <= to_date
            in_range = in_range and compare_result
            if not compare_result:
                logging.debug(f"Date {date_str} is after to_date {to_date.strftime('%m/%d/%Y')}")
            
        return in_range
    except ValueError:
        # If we can't parse the date, better to include it than filter it out
        logging.warning(f"Could not parse date for filtering: {date_str}")
        return True

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Cloud Updates Scraper')
    parser.add_argument('--test', action='store_true', help='Run in test mode with limited items')
    parser.add_argument('--from', dest='from_date', help='Process updates from this date (MM/DD/YYYY format)')
    parser.add_argument('--to', dest='to_date', help='Process updates to this date (MM/DD/YYYY format)')
    return parser.parse_args()

def main():
    # Parse command-line arguments
    args = parse_args()
    test_mode = args.test
    from_date = parse_date_arg(args.from_date) if args.from_date else None
    to_date = parse_date_arg(args.to_date) if args.to_date else None
    
    # Validate date range if both are provided
    if from_date and to_date and from_date > to_date:
        logging.error(f"Invalid date range: --from ({args.from_date}) is after --to ({args.to_date})")
        sys.exit(1)
    
    # Log execution mode and date filters
    if test_mode:
        logging.info("Running in TEST MODE - Limited to processing only the first 3 items")
    else:
        logging.info("Running in PRODUCTION MODE - Processing all available items")
    
    if from_date:
        logging.info(f"Filtering updates from {args.from_date}")
    if to_date:
        logging.info(f"Filtering updates to {args.to_date}")
    
    logging.info("Initializing ExcelUpdater...")
    excel_updater = ExcelUpdater(EXCEL_FILENAME) # excel_writer.py handles file existence

    # --- AWS Processing ---
    logging.info("Starting AWS updates processing...")
    try:
        aws_feed_content = fetch_rss_feed(AWS_RSS_URL)
        if aws_feed_content:
            aws_items = parse_aws_rss(aws_feed_content)
            logging.info(f"Found {len(aws_items)} AWS items in the RSS feed.")
            for i, item in enumerate(aws_items):
                # Apply item limit only in test mode
                if test_mode and i >= TEST_LIMIT:
                    logging.info(f"AWS: Reached test mode limit ({TEST_LIMIT}), stopping AWS processing.")
                    break                # Check if date is in the specified range
                if not is_date_in_range(item['date_posted'], from_date, to_date):
                    logging.info(f"Skipping AWS item from {item['date_posted']}: outside of requested date range")
                    continue

                logging.info(f"Processing AWS item from {item['date_posted']}: {item.get('title', 'N/A')} - URL: {item.get('url', 'N/A')}")
                try:
                    scraped_data = scrape_aws_update(item['url'], item['title'], item['date_posted'])
                    if scraped_data:
                        scraped_data['provider'] = 'AWS'
                        excel_updater.add_update(scraped_data)
                        logging.info(f"Successfully scraped and added AWS item: {item.get('title')}")
                    else:
                        logging.warning(f"Scraping returned None for AWS item: {item.get('url')}")
                except Exception as e:
                    logging.error(f"Error scraping AWS item {item.get('url')}: {e}", exc_info=False) # exc_info=False to keep log cleaner
        else:
            logging.warning("Could not fetch AWS RSS feed content.")
    except Exception as e:
        logging.error(f"An error occurred during AWS RSS feed processing: {e}", exc_info=False)

    # --- Azure Processing ---
    logging.info("Starting Azure updates processing...")
    try:
        azure_feed_content = fetch_rss_feed(AZURE_RSS_URL)
        if azure_feed_content:
            azure_items = parse_azure_rss(azure_feed_content)
            logging.info(f"Found {len(azure_items)} Azure items in the RSS feed.")
            for i, item in enumerate(azure_items):
                # Apply item limit only in test mode
                if test_mode and i >= TEST_LIMIT:
                    logging.info(f"Azure: Reached test mode limit ({TEST_LIMIT}), stopping Azure processing.")
                    break
                  # Check if date is in the specified range
                if not is_date_in_range(item['date_posted'], from_date, to_date):
                    logging.info(f"Skipping Azure item from {item['date_posted']}: outside of requested date range")
                    continue
                
                logging.info(f"Processing Azure item from {item['date_posted']}: {item.get('title', 'N/A')} - URL: {item.get('url', 'N/A')}")
                try:
                    # Extract RSS metadata for the Azure item
                    metadata = {
                        'status': item.get('status'),
                        'update_type': item.get('update_type'),
                        'product_list': item.get('product_list'),
                        'categories': item.get('categories')
                    }
                    logging.info(f"RSS metadata: Status='{metadata['status']}', Type='{metadata['update_type']}', Products='{metadata['product_list']}'")
                    
                    # Pass the metadata to the scraper function
                    scraped_data = scrape_azure_update(item['url'], item['title'], item['date_posted'], metadata)
                    if scraped_data:
                        scraped_data['provider'] = 'Azure'
                        excel_updater.add_update(scraped_data)
                        logging.info(f"Successfully scraped and added Azure item: {item.get('title')}")
                    else:
                        logging.warning(f"Scraping returned None for Azure item: {item.get('url')}")
                except Exception as e:
                    logging.error(f"Error scraping Azure item {item.get('url')}: {e}", exc_info=False)
        else:
            logging.warning("Could not fetch Azure RSS feed content.")
    except Exception as e:
        logging.error(f"An error occurred during Azure RSS feed processing: {e}", exc_info=False)

    try:
        excel_updater.save_workbook()
    except Exception as e:
        logging.error(f"Failed to save the workbook: {e}", exc_info=False)
        
    logging.info("Processing complete.")

if __name__ == '__main__':
    main()

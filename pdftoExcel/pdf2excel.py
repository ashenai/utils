import re
import pandas as pd
import pdfplumber
import sys
import os

# Function to extract data from the PDF
def extract_data_from_pdf(pdf_path):
    print(f"Opening PDF file: {pdf_path}")
    extracted_data = []
    raw_lines = []  # Store all non-empty lines
    current_section = None
    found_first_section = False  # Flag to track if we've found the first section
    pending_item = None  # Store the current item being processed
    pending_description_lines = []  # Store all text lines between items
    
    # Patterns for header and footer to ignore
    header_patterns = [
        r"KB Home Lone Star Inc\., a Texas corporation",
        r"Salerno 45's 868290",
        r"All Plan Options with Prices",
        r"Options Available for Plan 7D \(134\.1655\) March 30, 2025",
        r"OPTION SELECTIONS Sales Office Option Cut-Off Unit Price"
    ]
    footer_patterns = [
        r"Prices and availability of option selections are subject to change\.",
        r"Page \d+ of 15"
    ]
    
    # Combine all patterns to ignore
    ignore_patterns = header_patterns + footer_patterns
    
    # Updated pattern to match item, cutoff, and price on the same line
    # Format: <item text> A $price
    item_line_pattern = r"^(.*?)\s+A\s+(\$[\d,]+(?:\.\d{2})?|Included|N/C|TBD)\s*$"
    
    def save_pending_item():
        """Helper function to save the pending item with any accumulated description"""
        nonlocal pending_item, pending_description_lines
        if pending_item:
            # If there are pending description lines, combine them
            if pending_description_lines:
                pending_item["Description"] = " ".join(pending_description_lines)
            extracted_data.append(pending_item)
            print(f"Saved item: {pending_item['Item']}")
            # Reset pending data
            pending_item = None
            pending_description_lines = []
    
    print("Starting to process pages...")
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"Processing page {page_num}/{len(pdf.pages)}")
            
            # Extract words with their formatting
            words = page.extract_words(keep_blank_chars=True)
            
            # Group words into lines
            current_line = []
            current_y = None
            lines = []
            
            for word in words:
                if current_y is None:
                    current_y = word['top']
                
                # If y position changes significantly, we're on a new line
                if abs(word['top'] - current_y) > 2:  # threshold for new line
                    if current_line:
                        line_text = ' '.join(word['text'] for word in current_line)
                        lines.append(line_text.strip())
                    current_line = [word]
                    current_y = word['top']
                else:
                    current_line.append(word)
            
            # Don't forget the last line
            if current_line:
                line_text = ' '.join(word['text'] for word in current_line)
                lines.append(line_text.strip())
            
            # Process lines
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Skip empty lines
                if not line.strip():
                    i += 1
                    continue
                
                # Store raw line
                raw_lines.append({"Page": page_num, "Line": line})
                
                # Skip header/footer lines
                should_skip = False
                for pattern in ignore_patterns:
                    if re.search(pattern, line):
                        should_skip = True
                        break
                if should_skip:
                    i += 1
                    continue
                
                # Check if this is a section heading (exclude 'A' and 'TBD')
                if line.isupper() and line not in ["A", "TBD", "OPTION SELECTIONS", "7D"]:
                    if not found_first_section and line == "APPLIANCES":
                        found_first_section = True
                        current_section = line
                        print(f"Found first section: {current_section}")
                    elif found_first_section:
                        # Save any pending item before starting new section
                        save_pending_item()
                        current_section = line
                        print(f"Found section: {current_section}")
                    i += 1
                    continue
                
                # Skip all lines before the first section
                if not found_first_section:
                    i += 1
                    continue
                
                # Check for item line pattern (item, cutoff, and price on same line)
                match = re.match(item_line_pattern, line)
                if match:
                    # Save any pending item before starting new one
                    save_pending_item()
                    
                    # Create new item from the matched components
                    item_text, price = match.groups()
                    pending_item = {
                        "Section": current_section,
                        "Item": item_text.strip(),
                        "Description": None,
                        "Unit Price": price.strip(),
                        "Cut-Off": "A"
                    }
                    i += 1
                    continue
                
                # If we get here, this is a text line between items
                # Add it to pending description lines
                pending_description_lines.append(line)
                i += 1
    
    # Don't forget to save the last pending item
    save_pending_item()
    
    print(f"Extraction complete. Found {len(extracted_data)} items total.")
    return extracted_data, raw_lines

# Function to save data to Excel
def save_to_excel(processed_data, raw_lines, output_path, debug_mode=False):
    print(f"Saving data to Excel file: {output_path}")
    
    # Create a pandas DataFrame from the processed data
    df = pd.DataFrame(processed_data)
    
    # Create Excel writer object
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Write processed data to the first sheet
        df.to_excel(writer, sheet_name='Processed Data', index=False)
        
        # If in debug mode, write raw lines to second sheet
        if debug_mode and raw_lines:
            df_raw = pd.DataFrame(raw_lines)
            df_raw.to_excel(writer, sheet_name='Raw Lines', index=False)
    
    print("Excel file saved successfully.")

def print_usage():
    print("Usage: python pdf2excel.py <pdf_filename> [-debug]")
    print("Example: python pdf2excel.py input.pdf")
    print("Example with debug: python pdf2excel.py input.pdf -debug")
    sys.exit(1)

# Main script execution
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
    
    pdf_path = sys.argv[1]
    debug_mode = len(sys.argv) > 2 and sys.argv[2] == "-debug"
    
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)
    
    print(f"\nStarting PDF to Excel conversion")
    print(f"Input file: {pdf_path}")
    if debug_mode:
        print("Debug mode enabled - will include raw data sheet")
    
    # Generate output filename based on input filename
    output_path = os.path.splitext(pdf_path)[0] + ".xlsx"
    print(f"Output will be saved to: {output_path}")
    
    # Extract data from PDF
    processed_data, raw_lines = extract_data_from_pdf(pdf_path)
    
    # Save extracted data to Excel
    save_to_excel(processed_data, raw_lines, output_path, debug_mode)
    
    print(f"\nProcess complete!")
    print(f"Data has been saved to {output_path}")

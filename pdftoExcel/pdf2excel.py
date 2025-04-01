import re
import pandas as pd
from PyPDF2 import PdfReader
import sys
import os

# Function to extract data from the PDF
def extract_data_from_pdf(pdf_path):
    print(f"Opening PDF file: {pdf_path}")
    reader = PdfReader(pdf_path)
    print(f"Successfully opened PDF. Number of pages: {len(reader.pages)}")
    
    extracted_data = []
    raw_lines = []  # Store all non-empty lines
    current_section = None
    found_first_section = False  # Flag to track if we've found the first section
    current_description = []
    
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
    
    # Regex patterns to identify cutoff and price lines
    cutoff_pattern = r"^A\s*$"
    price_pattern = r"^(\$[\d,]+(?:\.\d{2})?|Included|N/C|TBD)\s*$"
    
    print("Starting to process pages...")
    for page_num, page in enumerate(reader.pages, 1):
        print(f"Processing page {page_num}/{len(reader.pages)}")
        text = page.extract_text()
        lines = text.split("\n")
        print(f"Found {len(lines)} lines in page {page_num}")
        
        # Filter out empty lines and store raw lines
        non_empty_lines = []
        for line in lines:
            if line.strip():
                raw_lines.append({
                    "Page": page_num,
                    "Line": line.strip()
                })
                non_empty_lines.append(line.strip())
        
        # Process lines
        i = 0
        while i < len(non_empty_lines):
            line = non_empty_lines[i]
            
            # Skip header/footer lines
            should_skip = False
            for pattern in ignore_patterns:
                if re.search(pattern, line):
                    should_skip = True
                    break
            if should_skip:
                i += 1
                continue
            
            # Debug output
            print(f"\nProcessing line: {line}")
            
            # Check if this is a section heading (exclude 'A' and 'TBD')
            if line.isupper() and line not in ["A", "TBD", "OPTION SELECTIONS", "7D"]:
                if not found_first_section and line == "APPLIANCES":
                    found_first_section = True
                    current_section = line
                    print(f"Found first section: {current_section}")
                elif found_first_section:
                    current_section = line
                    print(f"Found section: {current_section}")
                i += 1
                continue
            
            # Skip all lines before the first section
            if not found_first_section:
                i += 1
                continue
            
            # Check for item/cutoff/price pattern (3-line structure)
            if i + 2 < len(non_empty_lines):
                next_line = non_empty_lines[i + 1]
                next_next_line = non_empty_lines[i + 2]
                
                if (re.match(cutoff_pattern, next_line) and 
                    re.match(price_pattern, next_next_line)):
                    # Found an item pattern
                    if current_description:  # Save any pending description
                        # Update the last item's description if it exists
                        if extracted_data:
                            extracted_data[-1]["Description"] = " ".join(current_description)
                        current_description = []
                    
                    # Add the new item
                    extracted_data.append({
                        "Section": current_section,
                        "Item": line,
                        "Description": None,  # Will be updated when we find description lines
                        "Unit Price": next_next_line,
                        "Cut-Off": next_line
                    })
                    print(f"Found item: {line} with price {next_next_line}")
                    i += 3  # Skip the cutoff and price lines
                    continue
            
            # If we get here and we're past the first section, this is a description line
            if found_first_section and not (line.isupper() and line not in ["A", "TBD"]):
                current_description.append(line)
                print(f"Added description line: {line}")
            
            i += 1
    
    # Don't forget to add any remaining description to the last item
    if current_description and extracted_data:
        extracted_data[-1]["Description"] = " ".join(current_description)
    
    print(f"Extraction complete. Found {len(extracted_data)} items total.")
    return extracted_data, raw_lines

# Function to save data to Excel
def save_to_excel(processed_data, raw_lines, output_path, debug_mode=False):
    print(f"\nSaving data to Excel file: {output_path}")
    
    # Create Excel writer
    with pd.ExcelWriter(output_path) as writer:
        # Save processed data
        if processed_data:
            df_processed = pd.DataFrame(processed_data)
            print("Processed DataFrame created successfully")
            print(f"Processed columns: {', '.join(df_processed.columns)}")
            df_processed.to_excel(writer, sheet_name='Processed Data', index=False)
            print("Processed data written to Excel file")
        else:
            print("WARNING: No processed data to save!")
        
        # Save raw lines only in debug mode
        if debug_mode and raw_lines:
            df_raw = pd.DataFrame(raw_lines)
            print("Raw lines DataFrame created successfully")
            print(f"Raw columns: {', '.join(df_raw.columns)}")
            df_raw.to_excel(writer, sheet_name='Raw Lines', index=False)
            print("Raw lines written to Excel file")

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

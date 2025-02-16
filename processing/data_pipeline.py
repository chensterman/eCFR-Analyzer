import os
import re
import requests
import textstat
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from io import BytesIO
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
from threading import Lock


# Load environment variables
load_dotenv()

# Set up Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Create a lock for Supabase client access
supabase_lock = Lock()

# For mandate count
RESTRICTIVE_WORDS = [
    "shall", "must", "require", "prohibited", "forbidden", "may not", "shall not",
    "must not", "is required", "is mandated", "restricted to", "obligated to",
    "subject to", "enforceable", "compliance with", "not allowed"
]


def is_connection_error(error: Exception) -> bool:
    """Check if the error is related to connection issues."""
    error_str = str(error).lower()
    connection_keywords = ['disconnect', 'connection', 'timeout', 'socket']
    return any(keyword in error_str for keyword in connection_keywords)


def is_rate_limited(error: Exception) -> bool:
    """Check if the error is related to rate limiting."""
    error_str = str(error).lower()
    rate_limit_keywords = ['rate limit', '429', 'too many requests']
    return any(keyword in error_str for keyword in rate_limit_keywords)


def insert_sections_batch(sections: List[Dict[str, Any]], batch_size: int = 50) -> bool:
    """Insert sections and their versions in batches."""
    try:
        # First, extract all unique section info
        section_infos = []
        for section in sections:
            # Skip sections missing required fields
            if not all(section.get(field) for field in ['title', 'chapter', 'part', 'section']):
                continue
                
            section_infos.append({
                "title": section["title"],
                "chapter": section["chapter"],
                "subchap": section.get("subchap"),
                "part": section["part"],
                "subpart": section.get("subpart"),
                "section": section["section"]
            })
        
        # Process sections in batches
        for i in range(0, len(section_infos), batch_size):
            batch = section_infos[i:i + batch_size]
            
            # Acquire lock before using Supabase client
            with supabase_lock:
                # Add small delay to prevent rapid sequential requests
                time.sleep(0.1)
                
                # Insert batch of sections and get their IDs
                sections_res = supabase.table("sections").upsert(
                    batch,
                    on_conflict="title,chapter,subchap,part,subpart,section"
                ).execute()
                
                # Map section identifiers to their IDs
                section_id_map = {
                    (s["title"], s["chapter"], s.get("subchap"), s["part"], s.get("subpart"), s["section"]): s["id"]
                    for s in sections_res.data
                }
                
                # Prepare version records for this batch
                version_records = []
                for section in sections[i:i + batch_size]:
                    key = (
                        section["title"],
                        section["chapter"],
                        section.get("subchap"),
                        section["part"],
                        section.get("subpart"),
                        section["section"]
                    )
                    if key in section_id_map:
                        version_records.append({
                            "section_id": section_id_map[key],
                            "issue_date": section["issue_date"],
                            "content": section["content"],
                            "word_count": section["word_count"],
                            "readability_score": section.get("readability_score"),
                            "mandate_count": section.get("mandate_count", 0)
                        })
                
                # Insert batch of versions
                if version_records:
                    # Add small delay between operations
                    time.sleep(0.1)
                    supabase.table("section_versions").insert(version_records).execute()
                
        return True
        
    except Exception as e:
        if is_connection_error(e):
            print(f"Connection error during batch insert: {e}")
        return False


def download_ecfr_xml(date: str, title_num: int) -> Optional[bytes]:
    """Download eCFR XML for a specific title and date."""
    url = f"https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title_num}.xml"
    
    try:
        # Make GET request
        response = requests.get(url)
        response.raise_for_status()
        return response.content
        
    except requests.RequestException as e:
        print(f"Error downloading XML for title {title_num}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading title {title_num}: {e}")
        return None


def process_section(issue_date: str, section: ET.Element, ancestors: Dict[str, str]) -> Dict[str, str]:
    """Process a section element and combine it with its ancestor information."""
    section_id = section.get("N", "")
    
    # Get the section content
    content = ""
    head = section.find("HEAD")
    if head is not None:
        content = extract_text(head) + " "
    
    # Add the rest of the section content
    for elem in section:
        if elem.tag != "HEAD":
            content += extract_text(elem) + " "
    
    content = content.strip()
    
    return {
        "issue_date": issue_date,
        "title": ancestors.get("title", ""),
        "chapter": ancestors.get("chapter", ""),
        "subchap": ancestors.get("subchap", ""),
        "part": ancestors.get("part", ""),
        "subpart": ancestors.get("subpart", ""),
        "section": section_id,
        "content": content,
        "word_count": len(content.split()),
        "readability_score": calculate_flesch_kincaid(content),
        "mandate_count": count_mandates(content),
    }


def extract_text(element: ET.Element) -> str:
    """Extract all text content from an element, including nested elements."""
    text = (element.text or "").strip()
    for child in element:
        text += " " + extract_text(child)
        if child.tail:
            text += " " + child.tail.strip()
    return " ".join(text.split())


def calculate_flesch_kincaid(text: str) -> float:
    """Calculate the Flesch-Kincaid Grade Level score for the given text."""
    return textstat.flesch_reading_ease(text)


def count_mandates(text: str) -> int:
    """Count the number of restrictive/mandatory words in the text."""
    text = text.lower()
    count = 0
    
    # First count single words
    words = text.split()
    single_word_terms = [w for w in RESTRICTIVE_WORDS if " " not in w]
    count += sum(words.count(word) for word in single_word_terms)
    
    # Then count phrases
    phrases = [w for w in RESTRICTIVE_WORDS if " " in w]
    for phrase in phrases:
        count += text.count(phrase)
    
    return count


def process_xml_content(issue_date: str, xml_content: bytes) -> Optional[Dict[str, List[Dict[str, str]]]]:
    """Process the XML content from memory and return structured data."""
    try:
        # Parse XML from memory using BytesIO
        tree = ET.parse(BytesIO(xml_content))
        root = tree.getroot()
        
        processed_sections = []
        ancestors = {}
        
        # Find the title number
        div1 = root.find(".//DIV1")
        if div1 is not None:
            ancestors["title"] = div1.get("N", "")
        
        # Process each level of the hierarchy
        for div3 in root.findall(".//DIV3"):  # Chapter
            ancestors["chapter"] = div3.get("N", "")
            ancestors["subchap"] = None  # Reset subchapter
            
            # Try to find subchapters (DIV4)
            div4s = div3.findall(".//DIV4")
            
            if div4s:  # If there are subchapters, process through them
                for div4 in div4s:
                    ancestors["subchap"] = div4.get("N", "")
                    process_parts(div4, ancestors, processed_sections, issue_date)
            else:  # No subchapters, process parts directly under chapter
                process_parts(div3, ancestors, processed_sections, issue_date)
        
        if not processed_sections:
            print(f"Warning: No sections found in XML content. Title structure might be different.")
            
        return {"processed": processed_sections}
    
    except Exception as e:
        print(f"Error processing XML content: {e}")
        return None


def process_parts(parent_elem: ET.Element, ancestors: Dict[str, str], processed_sections: List[Dict[str, str]], issue_date: str):
    """Process parts and their sections under a parent element."""
    for div5 in parent_elem.findall(".//DIV5"):
        ancestors["part"] = div5.get("N", "")
        
        # Process sections directly under the part
        for div8 in div5.findall("./DIV8"):
            section_data = process_section(issue_date, div8, ancestors.copy())
            if section_data:
                processed_sections.append(section_data)
        
        # Process sections within subparts
        for div6 in div5.findall("./DIV6"):
            if div6.get("TYPE") == "SUBPART":
                ancestors["subpart"] = div6.get("N", "")
                
                # Process sections within this subpart
                for div8 in div6.findall(".//DIV8"):
                    section_data = process_section(issue_date, div8, ancestors.copy())
                    if section_data:
                        processed_sections.append(section_data)
                
                # Clear subpart after processing its sections
                ancestors.pop("subpart", None)


def process_title(issue_date: str, title_num: int) -> bool:
    """Process a single title."""
    print(f"Processing title {title_num}")
    
    # Download the XML
    print(f"    Downloading XML file")
    xml_content = download_ecfr_xml(issue_date, title_num)
    if xml_content is None:
        print(f"Failed to download XML for title {title_num}")
        return False
    
    # Process the XML content
    print(f"    Processing XML content")
    result = process_xml_content(issue_date, xml_content)
    if result is None:
        print(f"Failed to process XML for title {title_num}")
        return False
    
    # Insert sections into Supabase using batch inserts
    print(f"    Inserting sections into Supabase")
    try:
        sections = result["processed"]
        if not sections:
            print(f"No sections found for title {title_num}")
            return True
            
        success = insert_sections_batch(sections)
        return success
        
    except Exception as e:
        if is_connection_error(e):
            print(f"Error processing sections for title {title_num}: {e}")
        return False


def title_exists_for_date(title: str, issue_date: str) -> bool:
    """Check if sections from a title already have versions for the given date."""
    try:
        # Query to check if any sections from this title have versions for this date
        result = supabase.from_('sections') \
            .select('id', count='exact') \
            .eq('title', title) \
            .execute()
            
        if not result.data or result.count == 0:
            return False
            
        section_ids = [section['id'] for section in result.data]
        
        # Check if any of these sections have versions for this date
        versions_result = supabase.from_('section_versions') \
            .select('id', count='exact') \
            .in_('section_id', section_ids) \
            .eq('issue_date', issue_date) \
            .execute()
            
        return versions_result.count > 0
        
    except Exception as e:
        print(f"Error checking title existence: {e}")
        return False  # Assume title doesn't exist if query fails


def process_date(date_index: int, total_dates: int, issue_date: str) -> tuple[list[int], list[int]]:
    """Process all titles for a specific date sequentially."""
    print(f"\nProcessing date {issue_date} ({date_index}/{total_dates})")
    successful_titles = []
    failed_titles = []
    skipped_titles = []
    
    # Process titles sequentially
    for title_num in range(1, 51):
        if title_num == 35:  # Skip title 35
            continue
            
        # Check if title already exists for this date
        if title_exists_for_date(str(title_num), issue_date):
            print(f"Title {title_num} already exists for {issue_date}, skipping...")
            skipped_titles.append(title_num)
            continue
            
        try:
            success = process_title(issue_date, title_num)
            if success:
                successful_titles.append(title_num)
            else:
                failed_titles.append(title_num)
            
        except Exception as e:
            if is_connection_error(e):
                print(f"Connection error processing title {title_num}: {e}")
            failed_titles.append(title_num)
        
        # Wait 5 seconds as for rate limit
        time.sleep(5)
    
    # Print summary for this date
    print(f"\nDate {issue_date} Complete!")
    print(f"Successfully processed {len(successful_titles)} titles")
    print(f"Failed to process {len(failed_titles)} titles")
    print(f"Skipped {len(skipped_titles)} existing titles")
    
    if failed_titles:
        print(f"Failed titles for {issue_date}:", failed_titles)
    
    return successful_titles, failed_titles


def generate_annual_dates(start_date: str, end_date: str) -> List[str]:
    """Generate a list of dates at 1-year intervals between start_date and end_date (YYYY-MM-DD format).
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    dates = []
    current = start
    
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current = current.replace(year=current.year + 1)
    
    return dates


def main():
    """Main pipeline function that processes titles 1-50 for all years between 2017-02-13 and 2025-02-13."""
    start_date = "2018-02-13"
    end_date = "2018-02-13"
    
    print("Starting eCFR data pipeline...")
    print(f"Processing data from {start_date} to {end_date}")
    
    # Generate all dates to process
    dates = generate_annual_dates(start_date, end_date)
    print(f"Found {len(dates)} dates to process")
    
    # Track overall statistics
    total_successful_titles = 0
    total_failed_titles = 0
    failed_attempts = []
    
    # Process each date
    for date_index, issue_date in enumerate(dates, 1):
        successful_titles, failed_titles = process_date(date_index, len(dates), issue_date)
        
        # Update statistics
        total_successful_titles += len(successful_titles)
        total_failed_titles += len(failed_titles)
        failed_attempts.extend((issue_date, title) for title in failed_titles)
    
    # Print overall summary
    print("\nPipeline Complete!")
    print(f"Processed {len(dates)} dates")
    print(f"Total successful title processes: {total_successful_titles}")
    print(f"Total failed title processes: {total_failed_titles}")
    
    if failed_attempts:
        print("\nAll failed attempts:")
        for date, title in failed_attempts:
            print(f"Date: {date}, Title: {title}")


if __name__ == "__main__":
    main()
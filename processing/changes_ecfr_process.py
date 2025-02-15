import requests
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from root_ecfr_process import calculate_flesch_kincaid, count_mandates
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from datetime import datetime

STARTING_ECFR_DATE = "2017-01-03"


class RateLimiter:
    """Token bucket rate limiter with thread safety."""
    def __init__(self, tokens_per_second: float, burst_size: int):
        self.tokens_per_second = tokens_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def _add_tokens(self):
        now = time.time()
        time_passed = now - self.last_update
        new_tokens = time_passed * self.tokens_per_second
        self.tokens = min(self.burst_size, self.tokens + new_tokens)
        self.last_update = now
    
    def acquire(self):
        """Acquire a token, blocking if none are available."""
        while True:
            with self.lock:
                self._add_tokens()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
            time.sleep(0.1)  # Sleep briefly before checking again

# Global rate limiter: 2 requests per second with burst capacity of 10
rate_limiter = RateLimiter(tokens_per_second=2, burst_size=10)


def get_versions(title: int) -> List[Dict[str, Any]]:
    """Fetch version data for a specific title."""
    url = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json?issue_date[gte]={STARTING_ECFR_DATE}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["content_versions"]
    return []


def get_ancestry(date: str, title: int, part: str, subpart: str, section: str) -> List[Dict[str, Any]]:
    """Fetch ancestry data for a specific title and date."""
    url = f"https://www.ecfr.gov/api/versioner/v1/ancestry/{date}/title-{title}.json?part={part}&subpart={subpart}&section={section}"
    response = requests.get(url)
    if response.status_code == 200:
        ancestry_list = response.json()
        return {
            "issue_date": date,
            "title": find_ancestor_by_type(ancestry_list, "title"),
            "chapter": find_ancestor_by_type(ancestry_list, "chapter"),
            "subchap": find_ancestor_by_type(ancestry_list, "subchapter"),
            "part": find_ancestor_by_type(ancestry_list, "part"),
            "subpart": find_ancestor_by_type(ancestry_list, "subpart"),
            "section": find_ancestor_by_type(ancestry_list, "section"),
        }
    return {}


def find_ancestor_by_type(ancestry: List[Dict[str, Any]], type_name: str) -> str:
    ancestors = ancestry["ancestors"]
    for item in ancestors:
        if item["type"] == type_name:
            return item.get("identifier", "")
    return ""


def extract_xml_content(xml_text: bytes) -> str:
    """Extract content from an XML section while preserving formatting."""

    # Decode bytes to string before parsing
    xml_str = xml_text.decode('utf-8')
    root = ET.fromstring(xml_str)
    
    # Extract the section header
    content = []
    head = root.find("HEAD")
    if head is not None:
        content.append(head.text.strip())
    
    # Process each paragraph
    for elem in root.findall(".//P"):
        # Get the text content
        text = ""
        
        # Handle italic markers
        italic = elem.find("I")
        if italic is not None:
            text += italic.text.strip() + " "
            if italic.tail:
                text += italic.tail.strip()
        else:
            text = elem.text.strip() if elem.text else ""
        
        # Get any remaining text
        for child in elem:
            if child.tail:
                text += " " + child.tail.strip()
        
        content.append(text.strip())
    
    # Add any citation information
    cita = root.find(".//CITA")
    if cita is not None:
        content.append(cita.text.strip())
    
    # Join all content with proper spacing
    return " ".join(content)


def download_with_retry(url: str, max_retries: int = 3, initial_delay: float = 1.0) -> bytes:
    """Download content with exponential backoff retry logic and rate limiting."""
    for attempt in range(max_retries):
        try:
            # Acquire token before making request
            rate_limiter.acquire()
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    delay = initial_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                    continue
            raise  # Re-raise the exception if it's not a 429 or we're out of retries


def process_version(version: Dict[str, Any], ancestry: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single version with its ancestry data."""
    params = {
        'chapter': ancestry.get("chapter", ""),
        'subchapter': ancestry.get("subchap", ""),
        'part': ancestry.get("part", ""),
        'subpart': ancestry.get("subpart", ""),
        'section': ancestry.get("section", ""),
    }
    
    # Filter out empty parameters
    query_params = {k: v for k, v in params.items() if v}
    
    # Build query string for non-empty parameters
    query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
    
    # Download the XML content
    base_url = f"https://www.ecfr.gov/api/versioner/v1/full/{version.get('issue_date', '')}/title-{ancestry.get('title', '')}.xml"
    url = f"{base_url}?{query_string}" if query_string else base_url
    
    try:
        xml_content = download_with_retry(url)
        content = extract_xml_content(xml_content).strip()
            
    except Exception as e:
        print(f"Error processing XML for section {version['identifier']}: {e}")
        # Fallback to just the name if there's an error
        content = version["name"]
    
    return {
        **ancestry,
        "content": content,
        "word_count": len(content.split()),
        "readability_score": calculate_flesch_kincaid(content),
        "mandate_count": count_mandates(content)
    }


def process_single_version(version):
    """Process a single version with its ancestry data."""
    ancestry = get_ancestry(version["issue_date"], int(version["title"]), 
                          version["part"], version["subpart"], version["identifier"])
    return process_version(version, ancestry)


def process_title(title_num: int):
    """Process all versions for a specific title."""
    versions = get_versions(title_num)
    processed_versions = []
    
    # Use fewer workers but still maintain some concurrency
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks and get future objects
        future_to_version = {executor.submit(process_single_version, version): version 
                           for version in versions}
        
        # Collect results as they complete
        for future in as_completed(future_to_version):
            try:
                processed_version = future.result()
                processed_versions.append(processed_version)
            except Exception as e:
                version = future_to_version[future]
                print(f"Error processing version {version['identifier']}: {str(e)}")
    
    # Save processed data
    output_path = f"processed/title-{title_num}-changes.json"
    with open(output_path, "w") as f:
        json.dump({"processed": processed_versions}, f, indent=2)
    print(f"Saved processed data for title {title_num}")


def ensure_directories():
    """Ensure necessary directories exist."""
    Path("processed").mkdir(parents=True, exist_ok=True)


def main():
    """Process titles with controlled concurrency."""
    # Process multiple titles concurrently, but with fewer workers
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit all titles for processing
        future_to_title = {executor.submit(process_title, title): title for title in range(1, 51)}
        
        # Process completed futures as they finish
        for future in as_completed(future_to_title):
            title = future_to_title[future]
            try:
                future.result()
                print(f"Completed processing title {title}")
            except Exception as e:
                print(f"Error processing title {title}: {e}")


if __name__ == "__main__":
    ensure_directories()
    main()
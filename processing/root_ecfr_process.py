import requests
import xml.etree.ElementTree as ET
import json
import os
import re
from typing import Dict, List, Optional
from pathlib import Path
from io import BytesIO
import textstat


LATEST_ECFR_DATE = "2025-02-13"
RESTRICTIVE_WORDS = [
    "shall", "must", "require", "prohibited", "forbidden", "may not", "shall not",
    "must not", "is required", "is mandated", "restricted to", "obligated to",
    "subject to", "enforceable", "compliance with", "not allowed"
]


def calculate_flesch_kincaid(text: str) -> float:
    """
    Calculate the Flesch-Kincaid Grade Level score for the given text.
    """
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


def extract_text(element: ET.Element) -> str:
    """Extract all text content from an element, including nested elements."""
    text = (element.text or "").strip()
    for child in element:
        text += " " + extract_text(child)
        if child.tail:
            text += " " + child.tail.strip()
    return " ".join(text.split())


def process_section(section: ET.Element, ancestors: Dict[str, str]) -> Dict[str, str]:
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
        "issue_date": LATEST_ECFR_DATE,
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


def process_xml_content(xml_content: bytes) -> Optional[Dict[str, List[Dict[str, str]]]]:
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
        for div3 in root.findall(".//DIV3"):
            ancestors["chapter"] = div3.get("N", "")
            
            for div4 in div3.findall(".//DIV4"):
                ancestors["subchap"] = div4.get("N", "")
                
                for div5 in div4.findall(".//DIV5"):
                    ancestors["part"] = div5.get("N", "")
                    
                    # Process sections directly under the part
                    for div8 in div5.findall("./DIV8"):
                        section_data = process_section(div8, ancestors)
                        processed_sections.append(section_data)
                    
                    # Process sections within subparts
                    for div6 in div5.findall("./DIV6"):
                        if div6.get("TYPE") == "SUBPART":
                            # Get subpart letter/number
                            ancestors["subpart"] = div6.get("N", "")
                            
                            # Process sections within this subpart
                            for div8 in div6.findall(".//DIV8"):
                                section_data = process_section(div8, ancestors)
                                processed_sections.append(section_data)
                            
                            # Clear subpart after processing its sections
                            ancestors.pop("subpart", None)
        
        return {"processed": processed_sections}
    
    except Exception as e:
        print(f"Error processing XML content: {e}")
        return None


def download_ecfr_xml(date: str, title_num: int) -> Optional[bytes]:
    """Download eCFR XML for a specific title and date."""
    url = f"https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title_num}.xml"
    
    try:
        # Make GET request
        response = requests.get(url)
        response.raise_for_status()
        
        print(f"Successfully downloaded XML for title {title_num}")
        return response.content
        
    except requests.RequestException as e:
        print(f"Error downloading XML for title {title_num}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error downloading title {title_num}: {e}")
        return None


def ensure_directories():
    """Ensure necessary directories exist."""
    Path("processed").mkdir(exist_ok=True)


def process_title(title_num: int) -> bool:
    """Download and process a single title."""
    print(f"\nProcessing Title {title_num}...")
    
    # Download the XML
    xml_content = download_ecfr_xml(LATEST_ECFR_DATE, title_num)
    if xml_content is None:
        return False
    
    # Process the XML content
    result = process_xml_content(xml_content)
    if result is None:
        return False
    
    # Save the JSON
    json_path = f"processed/title-{title_num}.json"
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4)
        print(f"Successfully processed and saved {json_path}")
        return True
    
    except Exception as e:
        print(f"Error saving JSON for title {title_num}: {e}")
        return False


def main():
    """Process all eCFR titles."""
    ensure_directories()
    
    successful_titles = []
    failed_titles = []
    
    for title_num in range(1, 51):
        if process_title(title_num):
            successful_titles.append(title_num)
        else:
            failed_titles.append(title_num)
    
    # Print summary
    print("\nProcessing Complete!")
    print(f"Successfully processed {len(successful_titles)} titles")
    if failed_titles:
        print(f"Failed to process {len(failed_titles)} titles: {failed_titles}")


if __name__ == "__main__":
    main()
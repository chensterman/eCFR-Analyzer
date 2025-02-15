import os
from supabase import create_client, Client
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Any
import glob

load_dotenv()

# Set your Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Create a Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def insert_section_with_version(data: Dict[str, Any]) -> None:
    """Insert a section and its version into Supabase.
    
    Skips sections that are missing required fields (title, chapter, part, or section).
    """
    # Check required fields
    required_fields = ['title', 'chapter', 'part', 'section']
    for field in required_fields:
        if not data.get(field):
            print(f"Skipping section: missing required field '{field}'")
            return

    # Unpack the static section info
    section_info = {
        "title": data["title"],
        "chapter": data["chapter"],
        "subchap": data.get("subchap"),
        "part": data["part"],
        "subpart": data.get("subpart"),
        "section": data["section"]
    }

    try:
        # Try to find an existing section
        res = supabase.table("sections") \
                    .select("id") \
                    .eq("title", section_info["title"]) \
                    .eq("chapter", section_info["chapter"]) \
                    .eq("subchap", section_info["subchap"]) \
                    .eq("part", section_info["part"]) \
                    .eq("subpart", section_info["subpart"]) \
                    .eq("section", section_info["section"]) \
                    .execute()

        if res.data and len(res.data) > 0:
            section_id = res.data[0]["id"]
        else:
            # Insert new section
            insert_res = supabase.table("sections").insert(section_info).execute()
            section_id = insert_res.data[0]["id"]

        # Insert the version record
        version_info = {
            "section_id": section_id,
            "issue_date": data["issue_date"],
            "content": data["content"],
            "word_count": data["word_count"],
            "readability_score": data.get("readability_score"),
            "mandate_count": data.get("mandate_count", 0)
        }

        version_res = supabase.table("section_versions").insert(version_info).execute()
        print(f"Inserted version for section {section_info['section']} from {data['issue_date']}")
    
    except Exception as e:
        print(f"Error processing section {section_info['section']}: {str(e)}")

def process_title_file(file_path: str) -> None:
    """Process a single title JSON file and insert its data into Supabase."""
    print(f"Processing {file_path}...")
    try:
        with open(file_path, 'r') as f:
            sections = json.load(f)["processed"]
            
        for section in sections:
            insert_section_with_version(section)
            
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")

def main():
    """Process all title JSON files in the processed directory."""
    processed_dir = os.path.join(os.path.dirname(__file__), "processed")
    
    # Find all JSON files in the processed directory, excluding those with 'changes' in the name
    all_files = glob.glob(os.path.join(processed_dir, "title-*.json"))
    json_files = [f for f in all_files if "changes" not in os.path.basename(f)]
    
    if not json_files:
        print("No JSON files found in the processed directory")
        return
    
    print(f"Found {len(json_files)} files to process")
    
    # Process each file
    for file_path in json_files:
        process_title_file(file_path)

if __name__ == "__main__":
    main()

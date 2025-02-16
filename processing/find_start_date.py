import requests
from datetime import datetime


def get_ecfr_date(title_num: int):
    """Get the oldest documented issue date for a given title number."""
    url = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title_num}.json"
    
    try:
        # Make GET request
        response = requests.get(url)
        response.raise_for_status()
        
        # Extract issue date from JSON
        date = response.json()["content_versions"][0]["issue_date"]

        # Convert YYYY-MM-DD to epoch seconds
        epoch_seconds = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
        print(epoch_seconds)
        return epoch_seconds

    except requests.RequestException as e:
        print(f"Error getting data: {e}")
        return False

    except:
        print("Unexpected error")
        return False


if __name__ == "__main__":
    # For every title, get the one with the most recent first issue date
    latest = 0
    for i in range(1, 51):
        epoch = get_ecfr_date(i)
        if not epoch:
            continue
        if epoch > latest:
            latest = epoch
    print(f"Latest Version: {latest}")
    # 1483419600 epoch seconds or 1/3/2017
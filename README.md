
# eCFR Analyzer

The goal of this project is to create a simple website to analyze Federal Regulations. The eCFR is available at https://www.ecfr.gov/. There is a public api for it.

This repo contains code for downloading the current eCFR plus historical changes, along with the processing and backend storage of the data. It also contains code for the frontend visualization and analysis of the data.

The analysis is done with the following metrics:

- Over time, query by agency or CFR title
	- Word count
	- Mandate count
	- Readability

## Key Assumptions

1. We rely on the eCFR public API to download all the necessary data. The documentation used for reference is [here](https://www.ecfr.gov/developers/documentation/api/v1#/).

2. `GET /api/versioner/v1/versions/title-{title}.json` is the endpoint that will serve as the source of truth for historical changes to the eCFR. The data returned by this endpoint seems to be consistent with the change information returned by the public eCFR search tool [here](https://www.ecfr.gov/recent-changes).

3. 1/3/2017 seems to be the earliest date where reliable change data is available for all eCFR titles (see `processing/find_start_date.py` for more details). Thus, this date will serve as the start for all historical change data to the eCFR.

4. We assume that downloading the entirety of the 1/3/2017 version eCFR and using the versioner endpoint mentioned above to follow changes made all the way to present day will lead us to the most recent version of the eCFR.

## Implementation

### File Structure

- The `processing` folder primarily contains Python scripts used for the following:
	- Download the necessary eCFR data
	- Pre-process the data by analyzing each section for metrics like word count and readability
	- Upload the resulting data for storage in a [TODO] database instance
- The `app` folder contains a [TODO] application with code to serve the frontend as well as query the necessary backend services.
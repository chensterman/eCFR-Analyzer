
# eCFR Analyzer

The goal of this project is to create a simple website to analyze Federal Regulations. The eCFR is available at [here](https://www.ecfr.gov/). There is a public api for it.

This repo contains code for downloading the current eCFR plus historical changes, along with the processing and backend storage of the data. It also contains code for the frontend visualization and analysis of the data.

The analysis is done with the following metrics:

- Over time, query by agency or CFR title
	- Word count
	- Mandate count (restrictive phrases like "prohibited", "forbidden", "compliance with", etc.)
	- Readability (calculated using the [Flesch-Kincaid](https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests) reading ease score)

Try out the demo [here](https://ecfr-analyzer-one.vercel.app/)!

## Key Assumptions

1. We will rely on the eCFR public API to download all the necessary data (all text and information about agencies). The documentation used for reference is [here](https://www.ecfr.gov/developers/documentation/api/v1#/).

2. 1/3/2017 seems to be the earliest date where reliable historical data is available for all eCFR titles (see `processing/find_start_date.py` for more details). Thus, this date will serve as the start for all historical change data to the eCFR.

3. For our visualization, we will download the entirety of the eCFR for every year from 2017-2025 on the day of 2/13, using the `/api/versioner/v1/full/{date}/title-{title}.xml` endpoint. This assumes that we will capture historical changes annually as we document every new version each year.

## Implementation

### File Structure

- The `processing` folder primarily contains Python scripts used for the following:
	- Download the necessary eCFR data
	- Pre-process the data by analyzing each section for metrics like word count and readability
	- Upload the resulting data for storage in a Supabase instance
- The `frontend` folder contains code for a Next.js application to serve as the frontend. Queries to other backend systems also are served here.

### Architecture

**Frontend**
A Next.js application using [Shadcn](https://ui.shadcn.com/) components to build out UI + visualizations, and the Next.js Supabase client to query the database. 

**Database**
A [Supabase](https://supabase.com/) instance hosting a PostgreSQL database of all eCFR text. Requests are made through RPC function calls to extract the necessary metrics for each query.

**Deployment**
[Vercel](https://vercel.com/) is used to host the frontend as a web application.
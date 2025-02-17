
# eCFR Analyzer

The goal of this project is to create a simple website to analyze Federal Regulations. The eCFR is available at [here](https://www.ecfr.gov/). There is a public api for it.

This repo contains code for downloading the current eCFR plus historical changes, along with the processing and backend storage of the data. It also contains code for the frontend visualization and analysis of the data.

The analysis is done with the following metrics:

- Over time, query by agency or CFR title
	- Word count
	- Mandate count (restrictive phrases like "prohibited", "forbidden", "compliance with", etc.)
	- Readability (calculated using the [Flesch-Kincaid](https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests) reading ease score)

Try out the demo [here](https://ecfr-analyzer-one.vercel.app/)!

##KNOWN ISSUES (discovered after submission)
1. [FIXED ~30 additional minutes] Some titles appear to show cumulative word/mandate count year over year for some reason - a script will run in the background to hopefully fix this since it seems to be an issue with the database. For such titles and agencies, to get the true word/mandate count for a specific year, subtract the amount from the previous year. Sincere apologies for this.
2. [FIXED ~1 additional hour] On rare occasions, a query will fail due to the load being too high on the Supabase instance. Chances increase when querying for more than one agency/title at a time. If you rerun the query, it's likely it will work again.
3. If you see sudden jumps in word/mandate count for certain agencies, this is likely because an associated title and chapter was not readily available to be scraped for certain years. Once the text became available to the scraper in other years, the additional text causes a jump in the count, either up or down.

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

Frontend - 
A Next.js application using [Shadcn](https://ui.shadcn.com/) components to build out UI + visualizations, and the Next.js Supabase client to query the database. 

Database - 
A [Supabase](https://supabase.com/) instance hosting a PostgreSQL database of all eCFR text. Requests are made through RPC function calls to extract the necessary metrics for each query.

Deployment -
[Vercel](https://vercel.com/) is used to host the frontend as a web application.

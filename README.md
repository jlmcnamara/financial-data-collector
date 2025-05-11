# Financial Data Collector

A Python-based system for collecting and processing financial data from Fortune 100 companies, including Investor Relations (IR) pages and SEC EDGAR filings.

## Features

- Scrapes Investor Relations (IR) pages for company information.
- Fetches SEC filings (10-K, 10-Q, 8-K) using SEC's free JSON API.
- Processes and summarizes financial documents using OpenAI (requires API key).
- Provides RESTful API endpoints to access the collected data.
- Scheduled daily runs to fetch new data.
- Stores raw documents and metadata in the local file system (`./data/raw`, `./data/processed`).
- Manages a list of Fortune 100 companies with their CIKs.

## Project Structure

financial-data-collector/
├── app/
│   ├── __init__.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── companies.py
│   │   ├── ir_scraper.py
│   │   └── sec_fetcher.py
│   ├── processors/
│   │   ├── __init__.py
│   │   └── summarizer.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── data_store.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   └── scheduler/
│       ├── __init__.py
│       └── tasks.py
├── data/
│   ├── companies/
│   │   └── fortune100.csv
│   ├── raw/            # Stores downloaded raw files
│   │   └── .gitkeep
│   └── processed/      # Stores summarized documents
│       └── .gitkeep
├── config.py           # Configuration settings
├── main.py             # Main application entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables file
├── .gitignore          # Specifies intentionally untracked files
├── README.md           # This file
├── SECURITY.md         # Security policy
└── CONTRIBUTING.md     # Contribution guidelines


## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jlmcnamara/financial-data-collector.git
    cd financial-data-collector
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browser drivers:**
    (Required for `ir_scraper.py`)
    ```bash
    playwright install chromium
    ```

5.  **Set up environment variables:**
    Copy the example environment file and fill in your details:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file with your actual `OPENAI_API_KEY` and `SEC_USER_AGENT` (your email).

## Usage

1.  **Run the application:**
    ```bash
    python main.py
    ```
    This will:
    - Initialize the Fortune 100 company list (`data/companies/fortune100.csv`).
    - Start the daily data collection scheduler.
    - Launch the Flask API server (default: `http://0.0.0.0:5000`).

2.  **Access the API endpoints:**
    Open your browser or API client (like Postman or Insomnia) to interact with the API. The root endpoint `http://0.0.0.0:5000/` provides a list of available endpoints.

    **Key Endpoints:**
    -   `GET /api/companies`: List all Fortune 100 companies.
    -   `GET /api/companies/{ticker}`: Get details for a specific company.
    -   `GET /api/companies/{ticker}/ir`: Get Investor Relations documents metadata for a company.
    -   `GET /api/companies/{ticker}/sec`: Get SEC filings metadata for a company.
    -   `GET /api/companies/{ticker}/summaries`: Get document summaries for a company.
    -   `POST /api/collect/ir/{ticker}`: Trigger collection of IR documents for a company.
    -   `POST /api/collect/sec/{ticker}`: Trigger collection of SEC filings for a company.
        -   Payload (optional): `{"form_types": ["10-K", "10-Q"], "count": 3}`
    -   `POST /api/collect/all/{ticker}`: Trigger collection of all documents for a company.
    -   `POST /api/summarize/{ticker}/{document_type}/{document_path}`: Generate a summary for a specific downloaded document. (`document_type` is 'ir' or 'sec', `document_path` is the relative path from `data/raw/{ticker}/{document_type}/`).
    -   `GET /api/status`: Get system status.

## Configuration

The application is configured using environment variables defined in the `.env` file:

-   `OPENAI_API_KEY`: Your OpenAI API key (required for summarization).
-   `SEC_USER_AGENT`: Your email address, used as the User-Agent for SEC API requests (as per SEC guidelines).
-   `API_HOST`: Host for the API server (default: `0.0.0.0`).
-   `API_PORT`: Port for the API server (default: `5000`).
-   `SCHEDULER_DAILY_TIME`: Time to run the daily collection job (e.g., `02:00` for 2 AM, default is `02:00`).

## Data Storage

-   **Company List**: `data/companies/fortune100.csv` contains the list of companies, their tickers, and CIKs.
-   **Raw Documents**: Downloaded files (HTML, PDFs, etc.) are stored in `data/raw/{TICKER}/{SOURCE}/{DOCUMENT_TYPE}/`. Metadata for each downloaded file is stored as a `.meta.json` file alongside it.
-   **Processed Summaries**: Summaries generated by OpenAI are stored in `data/processed/` as JSON files, mirroring the structure of the raw file path.
-   **In-memory Data Store**: The `DataStore` object keeps track of loaded documents and summaries in memory. This data is persisted to `data/data_store.json` by the scheduler and loaded on startup.

## Future Enhancements

-   Integration with PostgreSQL or S3 for more scalable and robust storage.
-   Vector embeddings of financial documents for semantic search and Q&A.
-   Advanced analytics dashboard with visualizations.
-   Webhook integration (e.g., Slack/Teams) for alerts on new filings.
-   More sophisticated error handling and retry mechanisms.
-   Comprehensive unit and integration tests.

## Security

Please refer to `SECURITY.md` for security best practices and information on reporting vulnerabilities.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

## License

This project is licensed under the MIT License.

# Financial Data Collector

## What is this?

This is a tool that automatically gathers financial information about big companies (the Fortune 100). Instead of manually visiting company websites and government databases, this tool does it for you. It collects earnings reports, financial statements, and other important documents that investors, analysts, and researchers might need.

## Why was this built?

Manually collecting financial data is:
- **Time-consuming**: Going to each company's website or SEC page takes hours
- **Inconsistent**: Different companies organize their information differently
- **Hard to analyze**: Raw financial documents can be hundreds of pages long

This tool solves these problems by automatically finding, downloading, and organizing all this information in one place. It even creates summaries of long documents so you can quickly understand what's important.

## What This Tool Does

### 1. Finds & Downloads Financial Documents
- **From company websites**: Automatically locates and downloads earnings reports, presentations, and transcripts from Investor Relations pages
- **From government sources**: Collects official SEC filings like 10-K (annual reports), 10-Q (quarterly reports), and 8-K (significant events) using the free SEC EDGAR database

### 2. Makes Documents Easier to Understand
- **Creates summaries**: Uses AI (OpenAI's GPT models) to generate plain-language summaries of complex financial documents
- **Highlights key information**: Identifies important financial metrics and business developments

### 3. Keeps Everything Organized
- **Central storage**: Saves all documents in a structured file system so you can easily find what you need
- **Metadata tracking**: Keeps track of what's been collected, when, and where it came from

### 4. Works Without You Having to Do Anything
- **Runs on schedule**: Automatically checks for new documents every day
- **Updates itself**: Maintains an up-to-date list of Fortune 100 companies and their identification numbers

### 5. Makes the Data Available Through an API
- **Simple access**: Provides easy ways to request information through a web API
- **Search capability**: Allows finding documents by company, date, or document type

## How It's Organized

The code is organized into different parts, each handling a specific job:

```
📁 financial-data-collector/
│
├── 📁 app/                 # Main application code
│   │
│   ├── 📁 collectors/      # Parts that gather information
│   │   ├── companies.py    # Tracks Fortune 100 companies
│   │   ├── ir_scraper.py   # Gets documents from company websites
│   │   └── sec_fetcher.py  # Gets documents from SEC database
│   │
│   ├── 📁 processors/      # Parts that analyze information
│   │   └── summarizer.py   # Creates easy-to-read summaries using AI
│   │
│   ├── 📁 storage/         # Parts that save information
│   │   └── data_store.py   # Keeps track of what we've collected
│   │
│   ├── 📁 api/             # Parts that share information
│   │   └── routes.py       # Creates web endpoints to access data
│   │
│   └── 📁 scheduler/       # Parts that automate everything
│       └── tasks.py        # Runs daily collection jobs
│
├── 📁 data/                # Where collected information is stored
│   ├── 📁 companies/       # List of companies we track
│   ├── 📁 raw/             # Original downloaded documents
│   └── 📁 processed/       # Summaries and analysis of documents
│
├── config.py               # Settings for the application
├── main.py                 # Starting point of the application
└── requirements.txt        # List of required software packages
```

Each component works together to form a complete system - from finding documents to analyzing them to making them accessible.

## Getting Started - Step by Step Guide

### What You'll Need
- A computer with Python 3.8 or newer installed
- Basic familiarity with running commands in a terminal
- An OpenAI API key (if you want the summarization features)

### Installation Instructions

1. **Get the code**
   ```bash
   # Download the code to your computer
   git clone https://github.com/jlmcnamara/financial-data-collector.git
   
   # Go into the project folder
   cd financial-data-collector
   ```

2. **Set up a Python environment**
   ```bash
   # Create an isolated environment for this project
   python -m venv venv
   
   # Activate the environment
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```
   This creates a special environment just for this project, so it won't interfere with other Python projects on your computer.

3. **Install the necessary packages**
   ```bash
   # Install all required software
   pip install -r requirements.txt
   ```
   This might take a few minutes as it installs several packages needed by the tool.

4. **Install the web browser automation tool**
   ```bash
   # Install the browser that will be used to scrape websites
   playwright install chromium
   ```
   This installs a special browser that can be controlled by the tool to navigate company websites.

5. **Set up your configuration**
   ```bash
   # Create your personal configuration file
   cp .env.example .env
   ```
   Now open the `.env` file in any text editor and add:
   - Your OpenAI API key (get one at https://platform.openai.com if you don't have one)
   - Your email address (required for SEC API access)

6. **Run the application**
   ```bash
   # Start everything up
   python main.py
   ```

7. **Check that it's working**
   Open your web browser and go to: http://localhost:5000/
   
   You should see a welcome message and a list of available API endpoints.

### Troubleshooting Common Issues

- **"ModuleNotFoundError"**: Make sure you've activated the virtual environment and installed dependencies
- **"Connection refused"**: Check that the API server is running on the correct port
- **"SEC API error"**: Ensure you've set a valid email in the `SEC_USER_AGENT` variable
- **"Summarization disabled"**: You need to set a valid `OPENAI_API_KEY` to use summary features

## Using the Tool

### Starting Everything Up

Just run this command to start the entire system:
```bash
python main.py
```

This does three important things:
1. Sets up the list of Fortune 100 companies to track
2. Starts the automatic daily data collection process
3. Launches a web server so you can access the data through an API

### Getting Information Out

The tool provides many ways to access the data through its API. You can use any web browser or tool like Postman to interact with it.

Here are some of the most useful API endpoints:

#### Getting Company Information
- **View all companies**: `GET http://localhost:5000/api/companies`
- **Get details about one company**: `GET http://localhost:5000/api/companies/AAPL` (replace AAPL with any company ticker)

#### Viewing Collected Documents
- **See all IR documents for a company**: `GET http://localhost:5000/api/companies/AAPL/ir`
- **See all SEC filings for a company**: `GET http://localhost:5000/api/companies/AAPL/sec`
- **View summaries for a company**: `GET http://localhost:5000/api/companies/AAPL/summaries`

#### Starting Manual Collection
- **Collect IR documents**: `POST http://localhost:5000/api/collect/ir/AAPL`
- **Collect SEC filings**: `POST http://localhost:5000/api/collect/sec/AAPL`
  - You can customize this with a JSON body: `{"form_types": ["10-K", "10-Q"], "count": 3}`

#### Creating Summaries
- **Generate a summary**: `POST http://localhost:5000/api/summarize/document`
  - With body: `{"relative_file_path": "AAPL/sec/10-K/file.html"}`

#### System Status
- **Check if everything is working**: `GET http://localhost:5000/api/status`

### Examples of What You Can Do

1. **Research a company quickly**:
   - Collect recent SEC filings for Apple: `POST /api/collect/sec/AAPL`
   - Get summaries of those filings: `GET /api/companies/AAPL/summaries`

2. **Compare quarterly results**:
   - Collect quarterly reports for multiple companies
   - Review the AI-generated summaries to quickly spot trends

3. **Set up automated monitoring**:
   - Let the system run daily to collect new documents
   - Build your own alert system that checks for new data through the API

## Setting Things Up

The application uses a `.env` file to store important settings. You'll need to create this file based on the `.env.example` template:

```
# Create your configuration file
cp .env.example .env
```

Then edit the `.env` file to include:

-   `OPENAI_API_KEY`: Your API key from OpenAI (needed to generate summaries)
    - If you don't add this, the tool will still collect documents but won't create summaries
    - Get this from: https://platform.openai.com/account/api-keys

-   `SEC_USER_AGENT`: Your email address
    - The SEC requires this when accessing their API so they can contact you if needed
    - Example: `yourname@example.com`

-   `API_HOST`: Where the API server will run (usually leave as `0.0.0.0`)

-   `API_PORT`: Which port to use for the API (usually leave as `5000`)

-   `SCHEDULER_DAILY_TIME`: When to run the automatic collection each day
    - Format is 24-hour time: `02:00` means 2:00 AM
    - Choose a time when your system will be running but not busy

## Where Everything Gets Stored

The tool organizes all the information it collects in a structured way:

### List of Companies
- **File**: `data/companies/fortune100.csv`
- **What it contains**: The Fortune 100 companies, their stock symbols (tickers), and their SEC identification numbers (CIKs)
- **How it's maintained**: Updated automatically to keep CIKs current

### Original Documents
- **Location**: `data/raw/{COMPANY_TICKER}/{SOURCE}/{DOCUMENT_TYPE}/`
  - Example: `data/raw/AAPL/sec/10-K/` would contain Apple's annual reports
- **File types**: HTML, PDF, DOCX, etc. (whatever format the document was in originally)
- **Extra information**: Each document has a companion `.meta.json` file with details about:
  - When it was downloaded
  - Where it came from (URL)
  - What type of document it is
  - A unique hash to identify the content

### Document Summaries
- **Location**: `data/processed/` with the same folder structure as raw documents
- **Format**: JSON files containing:
  - AI-generated summary text
  - Key points extracted from the document
  - Links back to the original document

### System Memory
- **File**: `data/data_store.json`
- **Purpose**: Helps the system remember what it's already collected and processed
- **When it's updated**: Continuously during operation, with a full save when scheduled tasks complete

## The Road Ahead: Future Plans

This tool is just getting started. Here's what we're planning to add:

### Better Storage Solutions
- **Database integration**: Move from file storage to PostgreSQL for better performance with large amounts of data
- **Cloud storage**: Add Amazon S3 support to store documents in the cloud instead of locally
- **Distributed architecture**: Split components into microservices that can run on multiple machines

### Smarter Document Understanding
- **AI-powered Q&A**: Allow asking specific questions about financial documents
- **Vector embeddings**: Create numerical representations of document content for semantic search
- **Entity recognition**: Automatically identify companies, people, and financial terms in documents
- **Trend detection**: Identify patterns across multiple reports and time periods

### Better User Experience
- **Web dashboard**: Create a user-friendly interface with visualizations of financial data
- **Company comparison tools**: Side-by-side analysis of different companies
- **Custom alerts**: Get notifications when specific events or metrics appear in new documents
- **Integration with analysis tools**: Export data to Excel, Tableau, or other analysis platforms

### Expanded Data Sources
- **Earnings call transcripts**: Specialized processing for quarterly earnings calls
- **News articles**: Collect relevant financial news alongside official documents
- **International filings**: Support for documents from non-US regulatory bodies
- **Alternative data**: Integration with other financial data sources

### Enhanced Reliability
- **Robust error handling**: Better recovery from network problems or site changes
- **Comprehensive testing**: Full test suite to ensure everything works correctly
- **Monitoring dashboard**: Real-time view of system health and collection progress

### Community Features
- **User annotations**: Allow adding notes and tags to documents
- **Collaborative analysis**: Share insights with team members
- **Plugin system**: Allow others to extend the tool with new capabilities

## Security

Please refer to `SECURITY.md` for security best practices and information on reporting vulnerabilities.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

## License

This project is licensed under the MIT License.

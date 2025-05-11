import os
import csv
import pandas as pd
import requests
from config import FORTUNE_100_CSV, COMPANIES_DIR, SEC_USER_AGENT

# Sample dataset with public Fortune companies data
# In production, you would fetch this from a reliable source or a more comprehensive list
SAMPLE_FORTUNE_COMPANIES = [
    {"rank": 1, "company": "Walmart", "ticker": "WMT", "cik": "0000104169"},
    {"rank": 2, "company": "Amazon", "ticker": "AMZN", "cik": "0001018724"},
    {"rank": 3, "company": "Apple", "ticker": "AAPL", "cik": "0000320193"},
    {"rank": 4, "company": "CVS Health", "ticker": "CVS", "cik": "0000064803"},
    {"rank": 5, "company": "UnitedHealth Group", "ticker": "UNH", "cik": "0000731766"},
    # Add more companies as needed for a more complete list.
    # For a full Fortune 100, this list would be much longer.
    # Consider using a more dynamic way to get this list for a production system.
]

def initialize_fortune_100():
    """Initialize or update the Fortune 100 companies CSV file."""
    os.makedirs(os.path.dirname(FORTUNE_100_CSV), exist_ok=True)
    
    if not os.path.exists(FORTUNE_100_CSV):
        # Create the initial CSV file
        df = pd.DataFrame(SAMPLE_FORTUNE_COMPANIES)
        df.to_csv(FORTUNE_100_CSV, index=False)
        print(f"Created Fortune 100 CSV file at {FORTUNE_100_CSV}")
    else:
        # Optionally, you could add logic here to update the existing file
        # For example, if you have a new source for SAMPLE_FORTUNE_COMPANIES
        print(f"Fortune 100 CSV file already exists at {FORTUNE_100_CSV}")

def get_fortune_100():
    """Get the list of Fortune 100 companies."""
    if not os.path.exists(FORTUNE_100_CSV):
        initialize_fortune_100()
    
    try:
        return pd.read_csv(FORTUNE_100_CSV)
    except pd.errors.EmptyDataError:
        print(f"Warning: {FORTUNE_100_CSV} is empty. Re-initializing.")
        initialize_fortune_100() # Attempt to re-initialize
        return pd.read_csv(FORTUNE_100_CSV)
    except Exception as e:
        print(f"Error reading {FORTUNE_100_CSV}: {e}")
        # Fallback to sample data if file is corrupt or unreadable
        return pd.DataFrame(SAMPLE_FORTUNE_COMPANIES)


def get_company_cik(ticker):
    """Get the CIK for a company by ticker symbol."""
    df = get_fortune_100()
    # Ensure CIK is treated as string, especially if it has leading zeros
    df['cik'] = df['cik'].astype(str).str.zfill(10) 
    company = df[df['ticker'].str.upper() == ticker.upper()]
    if not company.empty:
        return company.iloc[0]['cik']
    return None

def get_company_by_ticker(ticker):
    """Get company details by ticker symbol."""
    df = get_fortune_100()
    company = df[df['ticker'].str.upper() == ticker.upper()]
    if not company.empty:
        return company.iloc[0]
    return None

def fetch_sec_cik_mapping():
    """Fetch the SEC CIK to Ticker mapping from the official SEC website."""
    # SEC provides a JSON file mapping CIKs to tickers and company names
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": SEC_USER_AGENT or "FinancialDataCollector/1.0 your-email@example.com"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for HTTP errors
        
        data = response.json()
        # The data is a dictionary where keys are CIKs (as integers)
        # and values are dicts with 'ticker' and 'title' (company name)
        # We want a ticker -> CIK mapping
        mapping = {}
        for entry in data.values(): # Iterate through the values of the outer dictionary
            ticker = entry.get('ticker')
            cik = str(entry.get('cik_str')).zfill(10) # CIK is 'cik_str'
            if ticker and cik:
                mapping[ticker.upper()] = cik
        return mapping
    except requests.RequestException as e:
        print(f"Failed to fetch CIK mapping from SEC: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from SEC CIK mapping: {e}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred while fetching CIK mapping: {e}")
        return {}

def update_fortune_100_ciks():
    """Update CIKs in the Fortune 100 CSV file using the SEC mapping."""
    if not os.path.exists(FORTUNE_100_CSV):
        initialize_fortune_100()
        # If the file was just created, it might not have all tickers
        # or CIKs might be from the sample list.
    
    df = pd.read_csv(FORTUNE_100_CSV)
    
    print("Fetching SEC CIK mapping to update local list...")
    sec_cik_map = fetch_sec_cik_mapping()
    
    if not sec_cik_map:
        print("Could not fetch CIK mapping from SEC. CIKs will not be updated.")
        return

    updates_made = 0
    for index, row in df.iterrows():
        ticker = str(row['ticker']).upper()
        current_cik = str(row['cik']).zfill(10) if pd.notna(row['cik']) else None
        
        if ticker in sec_cik_map:
            sec_cik = sec_cik_map[ticker]
            if current_cik != sec_cik:
                df.loc[index, 'cik'] = sec_cik
                print(f"Updated CIK for {ticker}: {current_cik} -> {sec_cik}")
                updates_made += 1
        else:
            print(f"Ticker {ticker} not found in SEC CIK mapping. CIK not updated.")
            
    if updates_made > 0:
        df.to_csv(FORTUNE_100_CSV, index=False)
        print(f"Updated CIKs for {updates_made} companies in {FORTUNE_100_CSV}")
    else:
        print(f"No CIK updates were necessary for companies in {FORTUNE_100_CSV} based on SEC mapping.")

if __name__ == "__main__":
    # This allows running this script directly to initialize/update the company list
    print("Initializing company list...")
    initialize_fortune_100()
    print("\nAttempting to update CIKs from SEC data...")
    update_fortune_100_ciks()
    print("\nFetching company AAPL:")
    print(get_company_by_ticker("AAPL"))
    print("\nFetching CIK for AAPL:")
    print(get_company_cik("AAPL"))

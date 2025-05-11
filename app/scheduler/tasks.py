import asyncio
import time
from datetime import datetime
import os
from apscheduler.schedulers.background import BackgroundScheduler # For non-blocking scheduler

from app.collectors.companies import get_fortune_100
from app.collectors.ir_scraper import IRScraper
from app.collectors.sec_fetcher import SECFetcher
# DocumentSummarizer is not directly used by scheduler, but by API triggered actions
from app.storage.data_store import data_store 
from config import SCHEDULER_DAILY_TIME, DATA_DIR # DATA_DIR for saving data_store

# Create instances of collectors for the scheduler's use
# These are distinct from API instances if state matters, but here they are stateless
ir_scraper = IRScraper()
sec_fetcher = SECFetcher()

# Define when to run the daily collection jobs
# Default is 2 AM (format HH:MM)
# This is parsed from the SCHEDULER_DAILY_TIME env variable in config.py
def _parse_daily_time(daily_time_str):
    """Parse a time string in HH:MM format to hour and minute."""
    if not daily_time_str or ":" not in daily_time_str:
        return 2, 0  # Default to 2:00 AM if format is invalid
        
    try:
        hour, minute = daily_time_str.split(":")
        hour = int(hour)
        minute = int(minute)
        # Validate hour and minute
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            print(f"Warning: Invalid daily time format {daily_time_str}. Using default 02:00.")
            return 2, 0
        return hour, minute
    except ValueError:
        print(f"Warning: Invalid daily time format {daily_time_str}. Using default 02:00.")
        return 2, 0

# --- Scheduled Jobs ---
async def _collect_ir_for_company(ticker):
    """Collect IR documents for a single company."""
    print(f"Scheduled task: Collecting IR documents for {ticker}")
    results = await ir_scraper.process_company(ticker)
        
    # Store metadata for successfully downloaded documents
    successful_downloads = 0
    for res in results:
        if res.get("success") and res.get("status") == "downloaded":
            data_store.add_document_metadata(ticker, "ir", res["metadata"])
            successful_downloads += 1
    print(f"Completed IR collection for {ticker}. Successfully downloaded {successful_downloads}/{len(results)} documents.")

def _collect_sec_for_company(ticker):
    """Collect SEC filings for a single company."""
    print(f"Scheduled task: Collecting SEC filings for {ticker}")
    form_types = ["10-K", "10-Q", "8-K"]  # Default types of interest
    count = 2  # Just get the most recent 2 of each type for scheduled runs
    results = sec_fetcher.download_recent_filings_documents(
        ticker,
        form_types=form_types,
        count=count,
        download_all_docs_in_filing=False  # Just primary documents for scheduled runs
    )
    
    # Store metadata for successfully downloaded documents
    successful_downloads = 0
    for res in results:
        if res.get("success") and res.get("status") == "downloaded":
            data_store.add_document_metadata(ticker, "sec", res["metadata"])
            successful_downloads += 1
    print(f"Completed SEC collection for {ticker}. Successfully downloaded {successful_downloads}/{len(results)} documents.")

def daily_collection_job():
    """The daily collection job that runs for all companies."""
    start_time = datetime.now()
    print(f"\n--- Starting daily collection job at {start_time.isoformat()} ---")
    
    # Get the list of Fortune 100 companies to process
    companies_df = get_fortune_100()
    total_companies = len(companies_df)
    print(f"Found {total_companies} companies to process")
    
    # Process each company
    processed_count = 0
    for index, company in companies_df.iterrows():
        ticker = company['ticker']
        try:
            print(f"\nProcessing company {processed_count+1}/{total_companies}: {company['company']} ({ticker})")
            
            # Run IR collection
            try:
                # For async IR scraper, we need to set up event loop here
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_collect_ir_for_company(ticker))
                loop.close()
            except Exception as e:
                print(f"Error during IR collection for {ticker}: {e}")
                
            # Run SEC collection
            try:
                _collect_sec_for_company(ticker)
            except Exception as e:
                print(f"Error during SEC collection for {ticker}: {e}")
                
            processed_count += 1
            # Small delay between companies to be nice to servers
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing company {ticker}: {e}")
            continue
    
    # Save the updated data store at the end of the job
    try:
        data_store.save_to_json()
        print(f"Data store saved successfully to {data_store.storage_file_path}")
    except Exception as e:
        print(f"Error saving data store: {e}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60.0
    print(f"\n--- Daily collection job completed at {end_time.isoformat()} ---")
    print(f"--- Duration: {duration:.2f} minutes ---")
    print(f"--- Processed {processed_count}/{total_companies} companies ---\n")

# --- Update CIKs job ---
def update_ciks_job():
    """Update CIKs from SEC's mapping, weekly to ensure we have accurate CIKs."""
    print(f"\n--- Starting CIK update job at {datetime.now().isoformat()} ---")
    try:
        from app.collectors.companies import update_fortune_100_ciks
        update_fortune_100_ciks()
        print(f"CIK update job completed at {datetime.now().isoformat()}")
    except Exception as e:
        print(f"Error updating CIKs: {e}")

# --- Scheduler initialization ---
def init_scheduler():
    """Initialize and start the background scheduler."""
    scheduler = BackgroundScheduler()
    
    # Parse the daily time for scheduled runs
    hour, minute = _parse_daily_time(SCHEDULER_DAILY_TIME)
    print(f"Setting up daily collection job to run at {hour:02d}:{minute:02d}")
    
    # Add scheduled jobs
    scheduler.add_job(daily_collection_job, 'cron', hour=hour, minute=minute, id='daily_collection_job')
    # Add weekly job to update CIKs - Sunday at 1:00 AM
    scheduler.add_job(update_ciks_job, 'cron', day_of_week='sun', hour=1, minute=0, id='weekly_cik_update_job')
    
    # Start the scheduler
    scheduler.start()
    print(f"Scheduler started with {len(scheduler.get_jobs())} jobs")
    
    return scheduler

# If this file is run directly, run the daily collection job once
if __name__ == "__main__":
    print("Running daily collection job once for testing...")
    daily_collection_job()

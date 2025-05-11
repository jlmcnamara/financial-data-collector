import os
import sys
from flask import Flask
from app.api.routes import init_app
from app.scheduler.tasks import init_scheduler
from app.collectors.companies import initialize_fortune_100, update_fortune_100_ciks
from app.storage.data_store import data_store
from config import DATA_DIR, API_HOST, API_PORT, COMPANIES_DIR

def main():
    """Main entry point for the application."""
    print("Starting Financial Data Collector")
    
    # Check if necessary directories exist
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"Created data directory: {DATA_DIR}")
    if not os.path.exists(COMPANIES_DIR):
        os.makedirs(COMPANIES_DIR, exist_ok=True)
        print(f"Created companies directory: {COMPANIES_DIR}")

    # Initialize the Fortune 100 companies list
    print("Initializing Fortune 100 companies list...")
    initialize_fortune_100()
    # Optionally, update CIKs if needed (can be run less frequently)
    # print("Updating CIKs for Fortune 100 companies...")
    # update_fortune_100_ciks() 
    
    # Load the data store if it exists
    data_store_path = os.path.join(DATA_DIR, "data_store.json")
    if os.path.exists(data_store_path):
        print(f"Loading data store from {data_store_path}")
        data_store.load_from_json(data_store_path)
    
    # Initialize the Flask app
    print("Initializing API server...")
    app = init_app()
    
    # Initialize the scheduler
    print("Initializing scheduler...")
    scheduler = init_scheduler()
    
    # Run the Flask app
    print(f"Starting API server on {API_HOST}:{API_PORT}")
    print(f"Access API documentation at http://{API_HOST}:{API_PORT}/")
    app.run(host=API_HOST, port=API_PORT, debug=True)

if __name__ == "__main__":
    main()

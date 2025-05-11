import os
import json
from datetime import datetime
from config import DATA_DIR # For default save/load location

class DataStore:
    def __init__(self, storage_file_name="data_store.json"):
        # Stores metadata about companies, downloaded documents, and summaries.
        # Actual documents are on the filesystem. This store tracks their metadata.
        self.companies_info = {} # Key: ticker, Value: company details (rank, name, cik) from fortune100.csv
        self.document_metadata_store = {} # Key: ticker, Value: { "ir": [doc_meta1, ...], "sec": [doc_meta2, ...] }
        self.summary_metadata_store = {}  # Key: original_doc_filepath, Value: summary_metadata (path to summary, timestamp, etc.)
        
        self.storage_file_path = os.path.join(DATA_DIR, storage_file_name)
        self._load_from_json() # Load data on initialization

    def add_company_info(self, ticker, company_data):
        """Store basic info about a company (from fortune100.csv)."""
        self.companies_info[ticker.upper()] = company_data
        # No immediate save, rely on periodic save by scheduler or app shutdown

    def get_company_info(self, ticker):
        """Get stored basic info for a company."""
        return self.companies_info.get(ticker.upper())

    def get_all_companies_info(self):
        """Get all stored company basic info."""
        return self.companies_info

    def add_document_metadata(self, ticker, source_type, doc_metadata):
        """
        Add metadata for a downloaded document.
        source_type should be 'ir' or 'sec'.
        doc_metadata should be the dictionary created by the scraper/fetcher.
        The key for identifying a document could be its 'filepath_relative' or 'content_hash_sha256'.
        """
        ticker_upper = ticker.upper()
        if ticker_upper not in self.document_metadata_store:
            self.document_metadata_store[ticker_upper] = {"ir": [], "sec": []}
        
        if source_type not in ["ir", "sec"]:
            print(f"Warning: Invalid source_type '{source_type}' for document metadata. Use 'ir' or 'sec'.")
            return

        # Avoid duplicates based on content hash or URL
        doc_key = doc_metadata.get("content_hash_sha256") or doc_metadata.get("url")
        existing_docs = self.document_metadata_store[ticker_upper][source_type]
        
        is_duplicate = False
        if doc_key:
            for existing_doc in existing_docs:
                existing_key = existing_doc.get("content_hash_sha256") or existing_doc.get("url")
                if existing_key == doc_key:
                    is_duplicate = True
                    # Optionally update metadata if the new one is more recent or complete
                    # For now, just skip if considered a duplicate
                    break
        
        if not is_duplicate:
            self.document_metadata_store[ticker_upper][source_type].append(doc_metadata)
            print(f"Added document metadata for {ticker_upper}/{source_type}: {doc_metadata.get('filename') or doc_metadata.get('url')}")
        else:
            print(f"Skipped adding duplicate document metadata for {ticker_upper}/{source_type}: {doc_key}")


    def get_document_metadata(self, ticker, source_type=None, document_identifier=None):
        """
        Get document metadata.
        If source_type is None, returns all for ticker.
        If document_identifier (e.g. filename or hash) is provided, tries to find that specific doc.
        """
        ticker_upper = ticker.upper()
        if ticker_upper not in self.document_metadata_store:
            return [] if source_type else {} # Return empty list/dict if ticker not found

        if source_type:
            if source_type not in self.document_metadata_store[ticker_upper]:
                return []
            docs_list = self.document_metadata_store[ticker_upper][source_type]
            if document_identifier:
                for doc_meta in docs_list:
                    if document_identifier in (doc_meta.get("filename"), doc_meta.get("content_hash_sha256"), doc_meta.get("url")):
                        return doc_meta # Return single matching doc
                return None # Not found
            return docs_list # Return list for the source_type
        else: # No source_type specified, return all for ticker
            if document_identifier: # Search across all source types for this ticker
                for st in ["ir", "sec"]:
                    for doc_meta in self.document_metadata_store[ticker_upper].get(st, []):
                         if document_identifier in (doc_meta.get("filename"), doc_meta.get("content_hash_sha256"), doc_meta.get("url")):
                            return doc_meta
                return None # Not found
            return self.document_metadata_store[ticker_upper] 

    def add_summary_metadata(self, original_doc_filepath_relative, summary_metadata):
        """
        Add metadata for a generated summary.
        original_doc_filepath_relative is the key.
        summary_metadata typically includes path to summary file, model used, timestamp.
        """
        # Ensure the key is consistent (e.g. normalized path)
        key = os.path.normpath(original_doc_filepath_relative)
        self.summary_metadata_store[key] = summary_metadata
        print(f"Added summary metadata for document: {key}")

    def get_summary_metadata(self, original_doc_filepath_relative):
        """Get summary metadata for a given original document filepath."""
        key = os.path.normpath(original_doc_filepath_relative)
        return self.summary_metadata_store.get(key)

    def get_all_summaries_metadata(self, ticker=None):
        """Get all summary metadata, optionally filtered by ticker if original file path includes it."""
        if not ticker:
            return self.summary_metadata_store
        
        ticker_upper = ticker.upper()
        filtered_summaries = {}
        # Assuming original_doc_filepath_relative might start with TICKER/...
        # e.g., AAPL/sec/10-K/.../document.html.meta.json
        # This filtering is a bit heuristic based on path structure.
        for key, value in self.summary_metadata_store.items():
            # Check if the ticker is in the path of the original document
            # Path might be like 'data/raw/AAPL/sec/...'
            path_parts = os.path.normpath(key).split(os.sep)
            if len(path_parts) > 2 and path_parts[2].upper() == ticker_upper: # Crude check, assumes data/raw/TICKER structure
                 filtered_summaries[key] = value
            elif value.get("original_file_metadata", {}).get("ticker", "").upper() == ticker_upper: # Check metadata
                 filtered_summaries[key] = value

        return filtered_summaries

    def save_to_json(self):
        """Save the current state of the data store to a JSON file."""
        data_to_save = {
            "companies_info": self.companies_info,
            "document_metadata_store": self.document_metadata_store,
            "summary_metadata_store": self.summary_metadata_store,
            "last_saved_at": datetime.now().isoformat()
        }
        
        try:
            os.makedirs(os.path.dirname(self.storage_file_path), exist_ok=True)
            with open(self.storage_file_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            print(f"DataStore saved to {self.storage_file_path}")
        except Exception as e:
            print(f"Error saving DataStore to {self.storage_file_path}: {e}")

    def _load_from_json(self):
        """Load the data store state from a JSON file if it exists."""
        if os.path.exists(self.storage_file_path):
            try:
                with open(self.storage_file_path, 'r') as f:
                    loaded_data = json.load(f)
                
                self.companies_info = loaded_data.get("companies_info", {})
                self.document_metadata_store = loaded_data.get("document_metadata_store", {})
                self.summary_metadata_store = loaded_data.get("summary_metadata_store", {})
                print(f"DataStore loaded from {self.storage_file_path}. Last saved: {loaded_data.get('last_saved_at')}")
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {self.storage_file_path}. Initializing with empty store.")
                self._initialize_empty_store()
            except Exception as e:
                print(f"Error loading DataStore from {self.storage_file_path}: {e}. Initializing with empty store.")
                self._initialize_empty_store()
        else:
            print(f"DataStore file {self.storage_file_path} not found. Initializing with empty store.")
            self._initialize_empty_store()
            
    def _initialize_empty_store(self):
        self.companies_info = {}
        self.document_metadata_store = {}
        self.summary_metadata_store = {}

# Create a singleton instance of DataStore to be used across the application
data_store = DataStore()

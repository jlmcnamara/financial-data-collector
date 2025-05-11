import os
import requests
import json
import time
import hashlib
from datetime import datetime
import pandas as pd
from config import RAW_DATA_DIR, SEC_USER_AGENT, SEC_API_RATE_LIMIT, BASE_DIR
from app.collectors.companies import get_company_cik # get_company_by_ticker is not needed here

class SECFetcher:
    def __init__(self):
        if not SEC_USER_AGENT:
            raise ValueError("SEC_USER_AGENT must be set in .env or config.py")
        self.headers = {
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate", # Standard practice
            "Host": "data.sec.gov" # Specify host for data.sec.gov API
        }
        self.sec_archives_headers = { # Different host for www.sec.gov
            "User-Agent": SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }

    def _make_request(self, url, use_archives_headers=False):
        """Helper function to make requests with rate limiting and error handling."""
        headers_to_use = self.sec_archives_headers if use_archives_headers else self.headers
        try:
            time.sleep(SEC_API_RATE_LIMIT)  # Respect SEC rate limits (10 req/sec max)
            response = requests.get(url, headers=headers_to_use)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - URL: {url} - Status: {response.status_code} - Response: {response.text[:200]}")
            return {"error": str(http_err), "status_code": response.status_code, "response_text": response.text[:200]}
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err} - URL: {url}")
            return {"error": f"Connection error: {conn_err}"}
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err} - URL: {url}")
            return {"error": f"Timeout error: {timeout_err}"}
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred during the request: {req_err} - URL: {url}")
            return {"error": f"Request exception: {req_err}"}
        except json.JSONDecodeError as json_err:
            # This can happen if the response is not JSON (e.g., an HTML error page)
            print(f"JSON decode error: {json_err} - URL: {url} - Response was not valid JSON.")
            # Try to get some text from the response if possible, for debugging
            try:
                error_text = response.text[:200] # Get first 200 chars
            except: # response object might not exist if request failed early
                error_text = "Response content unavailable."
            return {"error": f"JSON decode error: {json_err}", "response_text": error_text}


    def get_company_submissions(self, ticker):
        """Get company submissions metadata from SEC EDGAR (data.sec.gov)."""
        cik_str = get_company_cik(ticker)
        if not cik_str:
            return {"error": f"CIK not found for ticker {ticker}"}
        
        # CIK must be 10 digits, zero-padded. get_company_cik should already provide this.
        # cik_padded = cik_str.zfill(10) # Ensured by get_company_cik if it uses zfill
        url = f"https://data.sec.gov/submissions/CIK{cik_str}.json" # cik_str should be padded already
        print(f"Fetching submissions for {ticker} (CIK: {cik_str}) from {url}")
        return self._make_request(url)

    def get_company_facts(self, ticker):
        """Get company facts (XBRL taxonomy data) from SEC EDGAR."""
        cik_str = get_company_cik(ticker)
        if not cik_str:
            return {"error": f"CIK not found for ticker {ticker}"}
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_str}.json"
        print(f"Fetching company facts for {ticker} (CIK: {cik_str}) from {url}")
        return self._make_request(url)

    def get_company_concept(self, ticker, concept_name, taxonomy="us-gaap"):
        """Get a specific concept (e.g., Revenues) for a company from SEC EDGAR."""
        cik_str = get_company_cik(ticker)
        if not cik_str:
            return {"error": f"CIK not found for ticker {ticker}"}
        url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_str}/{taxonomy}/{concept_name}.json"
        print(f"Fetching concept '{concept_name}' for {ticker} (CIK: {cik_str}) from {url}")
        return self._make_request(url)

    def get_filing_index(self, ticker, accession_number):
        """Get the index of files for a specific filing from www.sec.gov."""
        cik_str = get_company_cik(ticker)
        if not cik_str:
            return {"error": f"CIK not found for ticker {ticker}"}
        
        # The CIK for www.sec.gov URLs should NOT be zero-padded according to some examples
        # but data.sec.gov CIKs are. Let's use the unpadded CIK (lstrip '0') for archives.
        cik_for_archive = cik_str.lstrip('0') 
        accession_number_clean = accession_number.replace('-', '') # Remove dashes
        
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_for_archive}/{accession_number_clean}/index.json"
        print(f"Fetching filing index for {ticker} (Acc#: {accession_number}) from {url}")
        return self._make_request(url, use_archives_headers=True)

    def download_filing_document(self, ticker, accession_number, document_filename, form_type="UnknownForm"):
        """Download a specific document from a filing."""
        cik_str = get_company_cik(ticker)
        if not cik_str:
            print(f"Cannot download, CIK not found for {ticker}")
            return {"success": False, "error": f"CIK not found for ticker {ticker}"}

        cik_for_archive = cik_str.lstrip('0')
        accession_number_clean = accession_number.replace('-', '')
        
        # Construct download URL
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_for_archive}/{accession_number_clean}/{document_filename}"
        
        # Create directory structure: RAW_DATA_DIR/TICKER/sec/FORM_TYPE/ACCESSION_NUMBER/
        safe_form_type = form_type.replace("/", "_") # Sanitize form type for dir name
        filing_dir = os.path.join(RAW_DATA_DIR, ticker.upper(), "sec", safe_form_type, accession_number_clean)
        os.makedirs(filing_dir, exist_ok=True)
        
        filepath = os.path.join(filing_dir, document_filename)

        # Skip re-download if file already exists
        if os.path.exists(filepath):
            print(f"File already exists, skipping download: {filepath}")
            metadata_filepath = f"{filepath}.meta.json"
            if os.path.exists(metadata_filepath):
                 with open(metadata_filepath, "r") as f_meta:
                    existing_metadata = json.load(f_meta)
                 return {
                    "success": True, 
                    "filepath": filepath,
                    "metadata": existing_metadata,
                    "status": "skipped_exists"
                }

        print(f"Downloading SEC document for {ticker}: {doc_url} to {filepath}")
        try:
            time.sleep(SEC_API_RATE_LIMIT)
            response = requests.get(doc_url, headers=self.sec_archives_headers, stream=True)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            with open(filepath, "rb") as f_for_hash:
                content_hash = hashlib.sha256(f_for_hash.read()).hexdigest()
            
            metadata = {
                "url": doc_url,
                "ticker": ticker,
                "cik": cik_str,
                "accession_number": accession_number, # Original with dashes
                "document_filename": document_filename,
                "form_type": form_type,
                "downloaded_at": datetime.now().isoformat(),
                "content_hash_sha256": content_hash,
                "filepath_relative": os.path.relpath(filepath, BASE_DIR)
            }
            
            metadata_filepath = f"{filepath}.meta.json"
            with open(metadata_filepath, "w") as f_meta:
                json.dump(metadata, f_meta, indent=4)
            
            return {"success": True, "filepath": filepath, "metadata": metadata, "status": "downloaded"}
        
        except requests.RequestException as e:
            print(f"Failed to download SEC document {doc_url} for {ticker}: {e}")
            return {"success": False, "error": str(e), "url": doc_url, "status": "failed_download"}
        except Exception as e:
            print(f"Unexpected error downloading {doc_url} for {ticker}: {e}")
            return {"success": False, "error": str(e), "url": doc_url, "status": "failed_unexpected"}

    def get_recent_filings_metadata(self, ticker, form_types=None, count=10):
        """Get metadata for recent filings of specified types."""
        if form_types is None:
            form_types = ["10-K", "10-Q", "8-K"] # Default forms
        
        submissions_data = self.get_company_submissions(ticker)
        if "error" in submissions_data:
            print(f"Could not get submissions for {ticker}: {submissions_data['error']}")
            return []
        
        recent_filings_list = []
        if "filings" in submissions_data and "recent" in submissions_data["filings"]:
            recent = submissions_data["filings"]["recent"]
            
            # Iterate through all available recent filings
            # The fields are parallel arrays, so ensure indices are valid
            num_filings = len(recent.get("accessionNumber", []))
            for i in range(num_filings):
                try:
                    form = recent["form"][i]
                    if form in form_types:
                        filing_info = {
                            "accessionNumber": recent["accessionNumber"][i],
                            "filingDate": recent["filingDate"][i],
                            "reportDate": recent.get("reportDate", [""])[i], # May not always exist
                            "form": form,
                            "primaryDocument": recent["primaryDocument"][i],
                            "primaryDocDescription": recent.get("primaryDocDescription", [""])[i], # May not exist
                            "size": recent.get("size", [None])[i] # File size if available
                        }
                        recent_filings_list.append(filing_info)
                        if len(recent_filings_list) >= count:
                            break 
                except IndexError:
                    print(f"Index error while processing recent filings for {ticker}. Data might be inconsistent.")
                    break # Stop processing if data structure is unexpected
        else:
            print(f"No 'filings' or 'recent' section in submissions data for {ticker}.")
            
        return recent_filings_list

    def download_recent_filings_documents(self, ticker, form_types=None, count=5, download_all_docs_in_filing=False):
        """Download documents for recent filings of specified types."""
        if form_types is None:
            form_types = ["10-K", "10-Q", "8-K"]
        
        filings_metadata = self.get_recent_filings_metadata(ticker, form_types, count)
        if not filings_metadata:
            print(f"No recent filings metadata found for {ticker} matching criteria.")
            return []

        download_results = []
        for filing_meta in filings_metadata:
            acc_no = filing_meta["accessionNumber"]
            primary_doc_name = filing_meta["primaryDocument"]
            form = filing_meta["form"]
            
            # Download the primary document
            print(f"Processing primary document {primary_doc_name} for filing {acc_no} ({form}) for {ticker}")
            result = self.download_filing_document(ticker, acc_no, primary_doc_name, form_type=form)
            download_results.append(result)

            if download_all_docs_in_filing and result.get("success"):
                # If primary doc downloaded, get index and download other docs (e.g., exhibits)
                filing_index_data = self.get_filing_index(ticker, acc_no)
                if "error" not in filing_index_data and "directory" in filing_index_data:
                    for item in filing_index_data["directory"].get("item", []):
                        doc_name_in_index = item.get("name")
                        # Skip if it's the primary document (already downloaded) or not a downloadable type
                        if doc_name_in_index and doc_name_in_index != primary_doc_name and \
                           not doc_name_in_index.endswith((".xml", ".xsd", ".jpg", ".gif")): # Add more non-doc extensions
                            print(f"Processing additional document {doc_name_in_index} for filing {acc_no} for {ticker}")
                            exhibit_result = self.download_filing_document(ticker, acc_no, doc_name_in_index, form_type=f"{form}_Exhibit")
                            download_results.append(exhibit_result)
                else:
                    print(f"Could not get filing index for {acc_no} or index malformed.")
        
        successful_downloads = sum(1 for r in download_results if r.get("status") == "downloaded")
        skipped_downloads = sum(1 for r in download_results if r.get("status") == "skipped_exists")
        print(f"SEC Filings for {ticker}: {successful_downloads} downloaded, {skipped_downloads} skipped (existed).")
        return download_results

# Example usage
def main_test_sec():
    # Ensure SEC_USER_AGENT is set in .env
    if not SEC_USER_AGENT:
        print("SEC_USER_AGENT not set. Please set it in your .env file.")
        return
        
    fetcher = SECFetcher()
    test_ticker = "AAPL"

    # print(f"\n--- Getting submissions for {test_ticker} ---")
    # submissions = fetcher.get_company_submissions(test_ticker)
    # if "error" not in submissions:
    #     print(f"Filings entity name: {submissions.get('entityName')}")
    #     if "filings" in submissions and "recent" in submissions["filings"]:
    #         print(f"Recent forms: {submissions['filings']['recent']['form'][:5]}") # Print first 5 forms
    # else:
    #     print(f"Error fetching submissions: {submissions['error']}")

    # print(f"\n--- Getting recent filings metadata for {test_ticker} (10-K, 10-Q, up to 3) ---")
    # recent_meta = fetcher.get_recent_filings_metadata(test_ticker, form_types=["10-K", "10-Q"], count=3)
    # for meta_item in recent_meta:
    #     print(f"  Form: {meta_item['form']}, Date: {meta_item['filingDate']}, Acc#: {meta_item['accessionNumber']}, Doc: {meta_item['primaryDocument']}")
    
    # if recent_meta:
    #     acc_num_test = recent_meta[0]['accessionNumber']
    #     print(f"\n--- Getting filing index for {test_ticker}, Acc#: {acc_num_test} ---")
    #     filing_idx = fetcher.get_filing_index(test_ticker, acc_num_test)
    #     if "error" not in filing_idx and "directory" in filing_idx:
    #         print(f"  Filing directory name: {filing_idx['directory']['name']}")
    #         print(f"  Items in filing: {len(filing_idx['directory'].get('item',[]))}")
    #     else:
    #         print(f"  Error fetching filing index: {filing_idx.get('error', 'Unknown error')}")


    print(f"\n--- Downloading recent 10-K, 10-Q, 8-K for {test_ticker} (primary docs only, up to 2 of each type effectively) ---")
    # This will download primary documents for up to 'count' total filings matching the types.
    download_results = fetcher.download_recent_filings_documents(test_ticker, form_types=["10-K", "10-Q", "8-K"], count=2, download_all_docs_in_filing=False)
    # for res in download_results:
    #     if res.get("success"):
    #         print(f"  Downloaded/Skipped: {res['filepath']} (Status: {res['status']})")
    #     else:
    #         print(f"  Failed: {res.get('url', 'N/A')} - {res.get('error', 'Unknown error')}")
            
if __name__ == "__main__":
    main_test_sec()

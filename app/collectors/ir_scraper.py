import os
import asyncio
from urllib.parse import urljoin
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import requests
import hashlib
from datetime import datetime
import json
import time
from config import RAW_DATA_DIR, SEC_USER_AGENT, BASE_DIR # Use SEC_USER_AGENT for consistency
from app.collectors.companies import get_company_by_ticker
import pandas as pd

class IRScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": SEC_USER_AGENT or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    async def get_ir_page_url(self, ticker):
        """Get the Investor Relations page URL for a company."""
        company_details = get_company_by_ticker(ticker)
        if company_details is None or pd.isna(company_details['company']):
            print(f"Company details not found for ticker {ticker}")
            # Fallback to a ticker-based general search if company name is missing
            return f"https://www.{ticker.lower()}.com"


        company_name_raw = company_details['company']
        # Basic cleaning for URL generation
        company_name = company_name_raw.lower().replace('&', 'and').replace(' ', '').replace('.', '').replace(',', '')
        
        # Common IR page patterns
        potential_urls = [
            f"https://ir.{company_name}.com",
            f"https://investor.{company_name}.com",
            f"https://investors.{company_name}.com",
            f"https://{company_name}.com/investor-relations",
            f"https://{company_name}.com/investors",
            f"https://www.{company_name}.com/investor-relations",
            f"https://www.{company_name}.com/investors",
            # Ticker based URLs
            f"https://ir.{ticker.lower()}.com",
            f"https://investor.{ticker.lower()}.com",
            f"https://investors.{ticker.lower()}.com",
            f"https://www.{ticker.lower()}.com/investor-relations", # From original user prompt
            f"https://www.{ticker.lower()}.com/investors",
        ]
        
        # Try each URL pattern with a HEAD request first
        for url in potential_urls:
            try:
                # Use requests for simple HEAD check to avoid Playwright overhead
                response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    print(f"Found IR page for {ticker} at {url}")
                    return url
            except requests.RequestException:
                continue # Try next URL
        
        print(f"Could not quickly find IR page for {ticker} using common patterns. Falling back to {potential_urls[-2]}.")
        # Fallback to a general ticker-based URL if specific patterns fail
        return potential_urls[-2] # f"https://www.{ticker.lower()}.com/investor-relations"
    
    async def grab_ir_links(self, ticker):
        """Scrape IR page for relevant links."""
        base_url_guess = await self.get_ir_page_url(ticker)
        if not base_url_guess:
            print(f"Could not determine a base IR page URL for {ticker}")
            return []
        
        print(f"Attempting to scrape IR page for {ticker} starting with: {base_url_guess}")
        
        links_found = []
        actual_page_url = base_url_guess # Will be updated after page.goto if redirects occur

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch() # Consider headless=False for debugging
                page = await browser.new_page()
                
                # Increase timeout and handle potential navigation errors
                try:
                    await page.goto(base_url_guess, timeout=60000, wait_until="domcontentloaded")
                    actual_page_url = page.url # Get the final URL after redirects
                    print(f"Successfully navigated to {actual_page_url} for {ticker}")
                except PlaywrightTimeoutError:
                    print(f"Timeout loading IR page {base_url_guess} for {ticker}. Trying to get content anyway.")
                except Exception as nav_exc:
                    print(f"Navigation error for {base_url_guess} for {ticker}: {nav_exc}. Page content might be unavailable.")
                    await browser.close()
                    return []

                html_content = await page.content()
                await browser.close()

            except Exception as e: # Catch broader Playwright errors during setup/teardown
                print(f"Playwright setup/teardown error for {ticker}: {e}")
                return []

        soup = BeautifulSoup(html_content, "lxml")
        
        # Keywords for identifying relevant financial documents
        # From original user prompt: ["10-k", "10-q", "earnings", "slide", "transcript"]
        # Expanded list:
        keywords_doc_type = {
            "10-K": ["10-k", "annual report"],
            "10-Q": ["10-q", "quarterly report"],
            "8-K": ["8-k", "current report"], # Added 8-K
            "Earnings Release": ["earnings release", "results announcement"],
            "Presentation": ["presentation", "slide deck", "investor deck", "webcast slides"],
            "Transcript": ["transcript", "earnings call transcript"],
            "SEC Filings": ["sec filings", "edgar filings"], # General link to SEC page
        }

        for a_tag in soup.find_all("a", href=True):
            link_text = a_tag.text.strip().lower()
            href = a_tag["href"]

            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            matched_doc_type = "Other" # Default
            for doc_type, type_keywords in keywords_doc_type.items():
                if any(kw in link_text for kw in type_keywords):
                    matched_doc_type = doc_type
                    break 
            
            # Also check href for keywords if text is not descriptive (e.g. "PDF Download")
            if matched_doc_type == "Other":
                 for doc_type, type_keywords in keywords_doc_type.items():
                    if any(kw.replace(" ","") in href.lower() for kw in type_keywords): # check href too
                        matched_doc_type = doc_type
                        break
            
            # If any keyword (even if not mapped to a specific type yet) is present, consider it
            generic_keywords = ["financials", "report", "filing", "investor", "quarterly", "annual"]
            if matched_doc_type == "Other" and any(gk in link_text or gk in href.lower() for gk in generic_keywords):
                 # If it has a common file extension, it's likely a document
                if any(href.lower().endswith(ext) for ext in ['.pdf', '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx']):
                    # Try to be more specific based on original user prompt keywords
                    if any(tag in link_text for tag in ["10-k", "10-q", "earnings", "slide", "transcript"]):
                         # Re-evaluate based on user prompt specific tags
                        if "10-k" in link_text: matched_doc_type = "10-K"
                        elif "10-q" in link_text: matched_doc_type = "10-Q"
                        elif "earnings" in link_text: matched_doc_type = "Earnings Release"
                        elif "slide" in link_text: matched_doc_type = "Presentation"
                        elif "transcript" in link_text: matched_doc_type = "Transcript"
                    else:
                        matched_doc_type = "Financial Document" # Generic if still "Other"

            if matched_doc_type != "Other":
                full_url = urljoin(actual_page_url, href) # Use actual_page_url as base
                links_found.append({
                    "url": full_url,
                    "text": a_tag.text.strip(),
                    "type": matched_doc_type,
                    "source_page": actual_page_url
                })
        
        print(f"Found {len(links_found)} potential IR links for {ticker} from {actual_page_url}")
        return links_found
    
    def _determine_document_type(self, text_content, href_content): # Modified from original
        """Determine the document type based on its text and href."""
        # This is a simplified helper, the main logic is in grab_ir_links
        text = text_content.lower()
        href = href_content.lower()
        if "10-k" in text or "10k" in href: return "10-K"
        if "10-q" in text or "10q" in href: return "10-Q"
        if "8-k" in text or "8k" in href: return "8-K"
        if "earnings" in text: return "Earnings Release"
        if "presentation" in text or "slide" in text or "deck" in text: return "Presentation"
        if "transcript" in text: return "Transcript"
        if "annual report" in text and "10-k" not in text : return "Annual Report (Non-SEC)"
        if "sec filings" in text: return "SEC Filings Page"
        return "Other IR Document"

    async def download_document(self, ticker, doc_info):
        """Download a document from the IR page."""
        url = doc_info["url"]
        doc_type_from_link = doc_info.get("type", "Other IR Document")
        
        # Create directory structure
        # Standardize doc_type for directory naming (e.g., replace spaces with underscores)
        safe_doc_type_dir = doc_type_from_link.replace(" ", "_")
        company_dir = os.path.join(RAW_DATA_DIR, ticker.upper(), "ir", safe_doc_type_dir)
        os.makedirs(company_dir, exist_ok=True)
        
        # Generate a filename based on URL hash and date, preserve extension
        file_extension = os.path.splitext(url.split('?')[0])[-1].lower() # Get ext before query params
        if not file_extension or len(file_extension) > 5: # if no ext or too long (likely not an ext)
            file_extension = ".html" # Default to .html if no clear extension

        url_hash = hashlib.md5(url.encode()).hexdigest()
        filename_base = f"{datetime.now().strftime('%Y%m%d')}_{url_hash}"
        filename = f"{filename_base}{file_extension}"
        filepath = os.path.join(company_dir, filename)
        
        # Skip re-download if file already exists (basic check, could use hash from metadata)
        if os.path.exists(filepath):
            print(f"File already exists, skipping download: {filepath}")
            # Optionally, read existing metadata
            metadata_filepath = f"{filepath}.meta.json"
            if os.path.exists(metadata_filepath):
                 with open(metadata_filepath, "r") as f_meta:
                    existing_metadata = json.load(f_meta)
                 return {
                    "success": True, # Or mark as skipped
                    "filepath": filepath,
                    "metadata": existing_metadata,
                    "status": "skipped_exists"
                }
            # If metadata doesn't exist but file does, it's an incomplete download - proceed to download
            
        print(f"Downloading IR document for {ticker}: {url} to {filepath}")
        try:
            response = requests.get(url, headers=self.headers, timeout=60, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            # Refine extension based on Content-Type if initial extension was a guess (e.g. .html)
            if file_extension == ".html": # Or if no extension was found initially
                if 'pdf' in content_type: new_ext = ".pdf"
                elif 'excel' in content_type or 'spreadsheetml' in content_type: new_ext = ".xlsx"
                elif 'powerpoint' in content_type or 'presentationml' in content_type: new_ext = ".pptx"
                elif 'msword' in content_type or 'wordprocessingml' in content_type: new_ext = ".docx"
                elif 'text/plain' in content_type: new_ext = ".txt"
                else: new_ext = file_extension # keep original if no better mapping

                if new_ext != file_extension:
                    filename = f"{filename_base}{new_ext}"
                    filepath = os.path.join(company_dir, filename)
                    print(f"Refined filename based on Content-Type: {filepath}")


            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Calculate hash of downloaded content
            with open(filepath, "rb") as f_for_hash:
                content_hash = hashlib.sha256(f_for_hash.read()).hexdigest()

            metadata = {
                "url": url,
                "original_link_text": doc_info["text"],
                "detected_document_type": doc_type_from_link, # Type detected from link text/href
                "content_type_header": content_type,
                "downloaded_at": datetime.now().isoformat(),
                "source_page": doc_info.get("source_page"),
                "content_hash_sha256": content_hash,
                "filename": filename,
                "filepath_relative": os.path.relpath(filepath, BASE_DIR) # Relative to project root
            }
            
            metadata_filepath = f"{filepath}.meta.json"
            with open(metadata_filepath, "w") as f_meta:
                json.dump(metadata, f_meta, indent=4)
            
            return {
                "success": True,
                "filepath": filepath,
                "metadata": metadata,
                "status": "downloaded"
            }
        except requests.RequestException as e:
            print(f"Failed to download IR document {url} for {ticker}: {e}")
            return {"success": False, "error": str(e), "url": url, "status": "failed_download"}
        except Exception as e:
            print(f"An unexpected error occurred while downloading IR document {url} for {ticker}: {e}")
            return {"success": False, "error": str(e), "url": url, "status": "failed_unexpected"}
    
    async def process_company(self, ticker):
        """Process a company's IR page: find links and download documents."""
        print(f"Processing Investor Relations for {ticker.upper()}")
        ir_links = await self.grab_ir_links(ticker)
        
        download_results = []
        if not ir_links:
            print(f"No relevant IR links found for {ticker}")
            return download_results

        for link_info in ir_links:
            # Filter out links that are clearly just pages to other SEC filings lists, unless explicitly desired
            if link_info["type"] == "SEC Filings Page" and "sec.gov" not in link_info["url"]:
                # If it's an internal page listing SEC docs, we might want to scrape it too, or ignore
                print(f"Skipping generic SEC filings page link for {ticker}: {link_info['url']}")
                continue

            # Add a small delay to be polite to servers
            await asyncio.sleep(0.5) # Use asyncio.sleep in async function
            result = await self.download_document(ticker, link_info)
            download_results.append(result)
        
        successful_downloads = sum(1 for r in download_results if r.get("success"))
        print(f"Completed IR processing for {ticker}. Successful downloads: {successful_downloads}/{len(ir_links)}")
        return download_results

# Example usage for testing this module directly
async def main_test():
    # Test with a known ticker, e.g., AAPL
    # Ensure you have playwright browsers installed: playwright install chromium
    test_ticker = "AAPL" 
    scraper = IRScraper()
    
    # Test getting IR page URL
    ir_page_url = await scraper.get_ir_page_url(test_ticker)
    print(f"Suggested IR Page URL for {test_ticker}: {ir_page_url}")

    # Test grabbing links
    links = await scraper.grab_ir_links(test_ticker)
    print(f"\nFound links for {test_ticker}:")
    for link_data in links:
        print(f"  - Text: {link_data['text']}, Type: {link_data['type']}, URL: {link_data['url']}")

    # Test processing company (finds links and downloads)
    results = await scraper.process_company(test_ticker)
    print(f"\nDownload results for {test_ticker}:")
    for res in results:
        if res.get("success"):
            print(f"  SUCCESS: {res['filepath']}")
            print(f"    Metadata: {res['metadata']}")
        else:
            print(f"  FAILURE: {res.get('url', 'N/A')}, Error: {res.get('error', 'Unknown')}")
            
if __name__ == "__main__":
    # This part allows you to run `python ir_scraper.py` to test
    # Make sure to set SEC_USER_AGENT in your .env or config for headers
    
    # Check if SEC_USER_AGENT is set, otherwise provide a default for testing
    if not SEC_USER_AGENT:
        print("Warning: SEC_USER_AGENT not set in .env. Using a default for testing.")
        # This is just for direct script execution, app will use configured one.
        os.environ['SEC_USER_AGENT'] = "IRScraperTest/1.0 youremail@example.com" 
        from config import SEC_USER_AGENT # Re-evaluate after setting
    
    print("Running IR Scraper Test...")
    asyncio.run(main_test())

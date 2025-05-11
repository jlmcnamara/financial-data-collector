from flask import Flask, jsonify, request, Blueprint
from datetime import datetime
import asyncio
import os # For path manipulation in summarize endpoint

from app.storage.data_store import data_store
from app.collectors.companies import get_fortune_100, get_company_by_ticker, update_fortune_100_ciks
from app.collectors.ir_scraper import IRScraper
from app.collectors.sec_fetcher import SECFetcher
from app.processors.summarizer import DocumentSummarizer
from config import RAW_DATA_DIR, BASE_DIR # For constructing document paths

# Create a Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Create instances of our collectors and processors
# These will be used by the API endpoints.
# For a larger app, these might be managed by dependency injection or an app context.
ir_scraper = IRScraper()
sec_fetcher = SECFetcher()
summarizer = DocumentSummarizer()

# --- Company Information Endpoints ---
@api_bp.route('/companies', methods=['GET'])
def get_companies_route():
    """Get all companies from the Fortune 100 list."""
    companies_df = get_fortune_100()
    return jsonify(companies_df.to_dict(orient='records'))

@api_bp.route('/companies/<ticker>', methods=['GET'])
def get_company_route(ticker):
    """Get company details by ticker."""
    company_details = get_company_by_ticker(ticker.upper())
    if company_details is None: # pandas Series can be None if row not found
        return jsonify({"error": f"Company with ticker {ticker} not found"}), 404
    return jsonify(company_details.to_dict())

@api_bp.route('/companies/update-ciks', methods=['POST'])
def update_ciks_route():
    """Trigger an update of CIKs from the SEC mapping."""
    try:
        update_fortune_100_ciks()
        return jsonify({"message": "CIK update process initiated. Check server logs for details."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update CIKs: {str(e)}"}), 500

# --- Document Metadata Endpoints ---
@api_bp.route('/documents/<ticker>', methods=['GET'])
def get_all_documents_for_ticker_route(ticker):
    """Get all stored document metadata (IR and SEC) for a company."""
    doc_metadata = data_store.get_document_metadata(ticker.upper())
    if not doc_metadata:
        return jsonify({"message": f"No document metadata found for ticker {ticker}"}), 404
    return jsonify(doc_metadata)

@api_bp.route('/documents/<ticker>/ir', methods=['GET'])
def get_ir_documents_route(ticker):
    """Get Investor Relations document metadata for a company."""
    ir_docs_metadata = data_store.get_document_metadata(ticker.upper(), source_type="ir")
    if not ir_docs_metadata:
        return jsonify({"message": f"No IR document metadata found for ticker {ticker}"}), 404
    return jsonify(ir_docs_metadata)

@api_bp.route('/documents/<ticker>/sec', methods=['GET'])
def get_sec_documents_route(ticker):
    """Get SEC filings metadata for a company."""
    sec_docs_metadata = data_store.get_document_metadata(ticker.upper(), source_type="sec")
    if not sec_docs_metadata:
         return jsonify({"message": f"No SEC document metadata found for ticker {ticker}"}), 404
    return jsonify(sec_docs_metadata)

# --- Data Collection Trigger Endpoints ---
@api_bp.route('/collect/ir/<ticker>', methods=['POST'])
def collect_ir_route(ticker):
    """Collect (scrape and download) IR documents for a company."""
    # This runs asynchronously in the Flask context.
    # For long-running tasks, consider a task queue like Celery.
    async def _collect_ir_async():
        return await ir_scraper.process_company(ticker.upper())

    try:
        # Create a new event loop for this async task if not running in an async framework
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(_collect_ir_async())
        loop.close()

        # Store metadata for successfully downloaded documents
        successful_downloads = 0
        for res in results:
            if res.get("success") and res.get("status") == "downloaded":
                data_store.add_document_metadata(ticker.upper(), "ir", res["metadata"])
                successful_downloads +=1
        data_store.save_to_json() # Persist datastore changes
        
        return jsonify({
            "message": f"IR collection for {ticker} completed. {successful_downloads} new documents processed.",
            "results_summary": f"{len(results)} links processed. See details.",
            "details": results # Full results from scraper
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to collect IR data for {ticker}: {str(e)}"}), 500

@api_bp.route('/collect/sec/<ticker>', methods=['POST'])
def collect_sec_route(ticker):
    """Collect (fetch and download) SEC filings for a company."""
    data = request.json or {}
    form_types = data.get("form_types", ["10-K", "10-Q", "8-K"]) # Default types
    count = data.get("count", 5) # Default count
    download_all = data.get("download_all_docs_in_filing", False)

    try:
        results = sec_fetcher.download_recent_filings_documents(
            ticker.upper(), 
            form_types=form_types, 
            count=count,
            download_all_docs_in_filing=download_all
        )
        # Store metadata for successfully downloaded documents
        successful_downloads = 0
        for res in results:
            if res.get("success") and res.get("status") == "downloaded":
                data_store.add_document_metadata(ticker.upper(), "sec", res["metadata"])
                successful_downloads += 1
        data_store.save_to_json()

        return jsonify({
            "message": f"SEC collection for {ticker} completed. {successful_downloads} new documents processed.",
            "results_summary": f"{len(results)} documents/exhibits processed. See details.",
            "details": results
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to collect SEC data for {ticker}: {str(e)}"}), 500

# --- Summarization Endpoints ---
@api_bp.route('/summarize/document', methods=['POST'])
def summarize_document_route():
    """
    Generate a summary for a specific downloaded document.
    Expects JSON payload: {"relative_file_path": "TICKER/SOURCE/FORM_TYPE/.../filename.ext"}
    'relative_file_path' should be relative to the 'data/raw/' directory.
    """
    data = request.json
    if not data or "relative_file_path" not in data:
        return jsonify({"error": "Missing 'relative_file_path' in request JSON body"}), 400

    relative_file_path = data["relative_file_path"]
    # Construct the full path from the project's perspective
    # Assumes relative_file_path starts from within data/raw, e.g., "AAPL/sec/10-K/000.../aapl-10k.htm"
    # BASE_DIR/data/raw/ + relative_file_path
    full_document_path = os.path.join(BASE_DIR, 'data', 'raw', relative_file_path)
    # Normalize path for consistency
    full_document_path = os.path.normpath(full_document_path)


    if not os.path.exists(full_document_path) or not full_document_path.startswith(os.path.normpath(os.path.join(BASE_DIR, 'data', 'raw'))):
        # Security check: ensure the path is within the expected raw data directory
        return jsonify({"error": f"Document not found or invalid path: {relative_file_path}"}), 404
    
    if not summarizer.can_summarize: # Check if OpenAI key is available
         return jsonify({"error": "Summarization service is not available (OpenAI API key missing or invalid)."}), 503

    try:
        summary_result = summarizer.summarize_document(full_document_path)
        
        if summary_result.get("success"):
            # Store summary metadata, using the relative path of the original doc as a key
            data_store.add_summary_metadata(relative_file_path, summary_result["details"])
            data_store.save_to_json()
            return jsonify(summary_result), 200
        else:
            return jsonify(summary_result), 500 # If summarizer itself reports an error
            
    except Exception as e:
        return jsonify({"error": f"Error summarizing document {relative_file_path}: {str(e)}"}), 500

@api_bp.route('/summaries/<ticker>', methods=['GET'])
def get_summaries_for_ticker_route(ticker):
    """Get all stored summary metadata for a company."""
    # This is a bit heuristic as summaries are keyed by file paths.
    # We filter by checking if the ticker is in the original document's path.
    summaries = data_store.get_all_summaries_metadata(ticker=ticker.upper())
    if not summaries:
        return jsonify({"message": f"No summaries found for ticker {ticker}"}), 404
    return jsonify(summaries)


# --- System Status Endpoint ---
@api_bp.route('/status', methods=['GET'])
def get_status_route():
    """Get system status, including counts from the data store."""
    num_companies_info = len(data_store.get_all_companies_info())
    
    total_doc_metadata_count = 0
    for ticker_data in data_store.document_metadata_store.values():
        total_doc_metadata_count += len(ticker_data.get("ir", []))
        total_doc_metadata_count += len(ticker_data.get("sec", []))
        
    total_summary_metadata_count = len(data_store.summary_metadata_store)
    
    return jsonify({
        "status": "API Running",
        "timestamp": datetime.now().isoformat(),
        "data_store_info": {
            "tracked_companies_count": num_companies_info,
            "total_document_metadata_count": total_doc_metadata_count,
            "total_summary_metadata_count": total_summary_metadata_count,
            "data_store_file": data_store.storage_file_path
        }
    })

# --- Root endpoint for the Flask App (not part of Blueprint) ---
def create_flask_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp) # Register the API blueprint

    @app.route('/')
    def index():
        """Root endpoint - provides basic API documentation links or info."""
        # Create a list of available API endpoints from the blueprint
        endpoints = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith(api_bp.name + '.'): # Filter for API blueprint endpoints
                 # Exclude 'static' and other default Flask rules
                if rule.endpoint != 'static':
                    methods = ','.join(sorted(list(m for m in rule.methods if m not in ('HEAD', 'OPTIONS'))))
                    endpoints.append({
                        "path": str(rule), 
                        "methods": methods,
                        # Try to get docstring from the view function
                        "description": app.view_functions[rule.endpoint].__doc__.strip().split('\n')[0] if app.view_functions[rule.endpoint].__doc__ else "No description."
                    })
        
        return jsonify({
            "message": "Welcome to the Financial Data Collector API!",
            "documentation_note": "Explore the endpoints listed below.",
            "api_base_path": api_bp.url_prefix,
            "available_api_endpoints": sorted(endpoints, key=lambda e: e["path"])
        })
    return app

# --- App Initialization Function (used by main.py) ---
def init_app():
    """Initializes and returns the Flask application."""
    app = create_flask_app()
    # Add any other app configurations here if needed
    # e.g., app.config.from_object('config_module.ProductionConfig')
    return app

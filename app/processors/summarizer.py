import os
import json
import time
import openai # Make sure this matches your requirements.txt (openai vs openai-python)
from bs4 import BeautifulSoup
from datetime import datetime
from config import OPENAI_API_KEY, PROCESSED_DATA_DIR, BASE_DIR

# Set up OpenAI API key
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    print("Warning: OPENAI_API_KEY is not set. Summarization will not work.")

class DocumentSummarizer:
    def __init__(self, model_name="gpt-3.5-turbo-instruct"): # Using a more common completion model
        if not OPENAI_API_KEY:
            print("Summarizer Error: OPENAI_API_KEY is not available.")
            self.can_summarize = False
        else:
            self.can_summarize = True
        self.model_name = model_name # Or use "text-davinci-003" if preferred and available
                                     # Note: "text-davinci-003" is a legacy model.
                                     # Consider "gpt-3.5-turbo" for chat completions or
                                     # "gpt-3.5-turbo-instruct" for completions if using older SDK.

    def _extract_text_from_html(self, html_content_bytes):
        """Extract text content from HTML bytes."""
        try:
            # Try decoding with utf-8, then fallback to others if needed
            html_content = html_content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                html_content = html_content_bytes.decode('latin-1') # Common fallback
            except UnicodeDecodeError:
                html_content = html_content_bytes.decode('ascii', errors='ignore') # Last resort

        soup = BeautifulSoup(html_content, 'lxml') # Changed from 'html.parser' to 'lxml' for robustness
        
        # Remove script, style, head, nav, footer elements as they usually don't contain main content
        for element_type in ["script", "style", "head", "title", "meta", "link", "nav", "footer", "header", "aside"]:
            for element in soup.find_all(element_type):
                element.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True) # Use newline as separator and strip whitespace
        
        # Further clean-up: remove excessive newlines
        text = '\n'.join(line for line in text.splitlines() if line.strip())
        
        return text

    def _extract_text_from_file(self, file_path):
        """Extract text from a file based on its extension."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        try:
            with open(file_path, 'rb') as f: # Open in binary mode
                content_bytes = f.read()
            
            if ext in ['.html', '.htm', '.xhtml']:
                return self._extract_text_from_html(content_bytes)
            elif ext in ['.txt', '.md', '.rst']:
                # Try common encodings for text files
                try: return content_bytes.decode('utf-8')
                except UnicodeDecodeError: 
                    try: return content_bytes.decode('latin-1')
                    except UnicodeDecodeError: return content_bytes.decode('ascii', errors='ignore')
            elif ext == '.json': # If it's a JSON file, maybe just return its content as string or summarize specific fields
                try:
                    data = json.loads(content_bytes.decode('utf-8'))
                    return json.dumps(data, indent=2) # Pretty print JSON content for summarization
                except Exception as e:
                    print(f"Could not parse JSON file {file_path}: {e}")
                    return "Could not extract text: Malformed JSON."
            # Add handling for PDF, DOCX etc. if libraries like PyPDF2, python-docx are added
            # elif ext == '.pdf':
            #    # Requires PyPDF2 or similar: pip install PyPDF2
            #    # from PyPDF2 import PdfReader
            #    # reader = PdfReader(file_path)
            #    # text = "".join(page.extract_text() for page in reader.pages)
            #    # return text
            #    return "PDF text extraction not implemented yet."
            else:
                # For other file types, attempt a generic decode, but this is unlikely to be useful
                print(f"Warning: Attempting generic text extraction for unsupported file type {ext} at {file_path}")
                try: return content_bytes.decode('utf-8', errors='ignore')
                except: return f"Could not extract meaningful text from this file format ({ext})."
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return "Could not extract text: File not found."
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return f"Could not extract text: Error reading file ({str(e)})."

    def _chunk_text(self, text, max_tokens_per_chunk=3000): # Max tokens for gpt-3.5-turbo is ~4096 (prompt+completion)
        """Split text into manageable chunks based on approximate token count."""
        # A rough estimate: 1 token ~ 4 chars in English.
        # Or, more simply, split by words if preferred.
        # This method aims for token limits for LLMs.
        # Max tokens for gpt-3.5-turbo-instruct is 4096.
        # Leaving some room for the prompt itself.
        
        # Simple word-based chunking, could be improved with tokenizers like tiktoken
        words = text.split()
        chunks = []
        current_chunk_words = []
        # Estimate words per chunk: max_tokens_per_chunk * (3/4) (avg 0.75 words per token)
        # Or simpler: max_chars = max_tokens_per_chunk * 3 (avg 3 chars per token for safety)
        max_chars_per_chunk = max_tokens_per_chunk * 3 
        
        current_char_count = 0
        for word in words:
            word_len = len(word)
            if current_char_count + word_len + (1 if current_chunk_words else 0) > max_chars_per_chunk:
                if current_chunk_words: # Avoid creating empty chunks
                    chunks.append(' '.join(current_chunk_words))
                current_chunk_words = [word]
                current_char_count = word_len
            else:
                current_chunk_words.append(word)
                current_char_count += word_len + (1 if len(current_chunk_words) > 1 else 0)
        
        if current_chunk_words: # Add the last chunk
            chunks.append(' '.join(current_chunk_words))
        
        if not chunks and text: # If text is very short but not empty
            chunks.append(text)
            
        return chunks

    def _summarize_single_chunk(self, chunk_text, max_summary_tokens=150):
        """Generate a summary for a single text chunk using OpenAI."""
        if not self.can_summarize:
            return "Summarization disabled: OpenAI API key not set or invalid."

        prompt = (
            f"Please provide a concise summary of the following financial document excerpt. "
            f"Focus on key financial metrics, significant events, risks, and forward-looking statements. "
            f"If the text is too short or irrelevant, indicate that.\n\n"
            f"Document Excerpt:\n\"\"\"\n{chunk_text}\n\"\"\"\n\n"
            f"Concise Summary:"
        )
        
        try:
            # Using openai.Completion for models like "text-davinci-003" or "gpt-3.5-turbo-instruct"
            # For chat models like "gpt-3.5-turbo", use openai.ChatCompletion.create
            if "instruct" in self.model_name or "davinci" in self.model_name:
                 response = openai.Completion.create(
                    engine=self.model_name, # or "text-davinci-003"
                    prompt=prompt,
                    max_tokens=max_summary_tokens, # Max tokens for the summary itself
                    temperature=0.3, # Lower for more factual summaries
                    top_p=1.0,
                    frequency_penalty=0.1, # Slight penalty for repeating words
                    presence_penalty=0.1   # Slight penalty for repeating concepts
                )
                 summary = response.choices[0].text.strip()
            elif "turbo" in self.model_name and not "instruct" in self.model_name : # Likely a chat model
                response = openai.ChatCompletion.create(
                    model=self.model_name, # e.g., "gpt-3.5-turbo"
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes financial document excerpts."},
                        {"role": "user", "content": prompt} # The prompt constructed above is the user message
                    ],
                    max_tokens=max_summary_tokens,
                    temperature=0.3,
                    top_p=1.0,
                    frequency_penalty=0.1,
                    presence_penalty=0.1
                )
                summary = response.choices[0].message.content.strip()
            else:
                return f"Unsupported OpenAI model for summarization: {self.model_name}"

            return summary if summary else "Summary could not be generated for this chunk."
        
        except openai.error.OpenAIError as e: # Catch specific OpenAI errors
            print(f"OpenAI API error while summarizing chunk: {e}")
            return f"Error generating summary due to OpenAI API issue: {str(e)}"
        except Exception as e:
            print(f"Unexpected error generating summary for chunk: {e}")
            return f"Error generating summary: {str(e)}"

    def summarize_document(self, file_path):
        """Extract text from a document, chunk it, and generate a summary for each chunk, then an overall summary."""
        if not self.can_summarize:
            return {"success": False, "error": "Summarization disabled: OpenAI API key not set or invalid."}

        print(f"Starting summarization for document: {file_path}")
        
        # Ensure PROCESSED_DATA_DIR exists
        os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
        
        # Create an output path for the summary JSON file
        # It should mirror the structure of RAW_DATA_DIR within PROCESSED_DATA_DIR
        try:
            relative_path_from_raw = os.path.relpath(file_path, os.path.join(BASE_DIR, 'data', 'raw'))
            summary_output_dir = os.path.join(PROCESSED_DATA_DIR, os.path.dirname(relative_path_from_raw))
            os.makedirs(summary_output_dir, exist_ok=True)
            base_name = os.path.basename(file_path)
            summary_filename = f"{base_name}.summary.json"
            summary_output_path = os.path.join(summary_output_dir, summary_filename)
        except ValueError as ve: # relpath might fail if file_path is not under data/raw
            print(f"Path error for {file_path}: {ve}. Using default processed dir.")
            base_name = os.path.basename(file_path)
            summary_output_path = os.path.join(PROCESSED_DATA_DIR, f"{base_name}.summary.json")


        # Check if metadata file exists for the original document
        original_doc_metadata_path = f"{file_path}.meta.json"
        original_metadata = {}
        if os.path.exists(original_doc_metadata_path):
            try:
                with open(original_doc_metadata_path, 'r') as f_meta:
                    original_metadata = json.load(f_meta)
            except Exception as e:
                print(f"Could not read metadata for {file_path}: {e}")
        
        # Extract text from the document
        extracted_text = self._extract_text_from_file(file_path)
        if not extracted_text or "Could not extract text" in extracted_text or "not implemented yet" in extracted_text:
            error_msg = f"No text extracted or extraction failed for {file_path}. Details: {extracted_text}"
            print(error_msg)
            return {"success": False, "error": error_msg, "original_file": file_path}
        
        # Chunk the extracted text
        text_chunks = self._chunk_text(extracted_text)
        if not text_chunks:
            print(f"No text chunks generated for {file_path}. The document might be empty or very short.")
            return {"success": False, "error": "No text chunks to summarize.", "original_file": file_path}
        
        print(f"Generated {len(text_chunks)} chunks for summarization from {file_path}.")

        chunk_summaries = []
        for i, chunk in enumerate(text_chunks):
            print(f"Summarizing chunk {i+1} of {len(text_chunks)}...")
            chunk_summary = self._summarize_single_chunk(chunk)
            chunk_summaries.append(chunk_summary)
            time.sleep(0.5) # Small delay between API calls if needed, though OpenAI SDK might handle rate limits for some plans.

        # Combine chunk summaries to create a preliminary combined summary
        combined_preliminary_summary = "\n\n---\n\n".join(
            f"Summary of Chunk {i+1}:\n{s}" for i, s in enumerate(chunk_summaries) if s and "Error" not in s and "disabled" not in s
        )

        # Generate a final, high-level summary from the combined preliminary summary if there are multiple chunks
        final_summary_text = ""
        if len(text_chunks) > 1 and combined_preliminary_summary:
            print("Generating final high-level summary...")
            # Chunk the combined summaries if they are too long for a single final pass
            final_summary_chunks = self._chunk_text(combined_preliminary_summary, max_tokens_per_chunk=3500) # Slightly larger for final pass
            
            if len(final_summary_chunks) > 1:
                print(f"Combined chunk summaries are too long, summarizing the combined summaries in {len(final_summary_chunks)} parts.")
                final_summary_parts = []
                for i, f_chunk in enumerate(final_summary_chunks):
                    part_summary = self._summarize_single_chunk(f"This is part {i+1} of combined summaries. Summarize it: {f_chunk}", max_summary_tokens=250)
                    final_summary_parts.append(part_summary)
                final_summary_text = "\n\n---\n\n".join(final_summary_parts)
            else: # If combined summaries fit in one go
                 final_summary_text = self._summarize_single_chunk(
                    f"Please provide a coherent high-level summary of the following combined chunk summaries from a financial document:\n\n{combined_preliminary_summary}",
                    max_summary_tokens=400 # Allow more tokens for final summary
                )
        elif chunk_summaries: # Only one chunk, or only one valid chunk summary
            final_summary_text = chunk_summaries[0] if chunk_summaries[0] and "Error" not in chunk_summaries[0] and "disabled" not in chunk_summaries[0] else "No valid summary generated for the single chunk."
        else:
            final_summary_text = "No valid chunk summaries were generated to create a final summary."

        # Save the detailed summarization result
        summary_result_data = {
            "original_file_path": file_path,
            "original_file_metadata": original_metadata,
            "model_used": self.model_name,
            "summarization_timestamp": datetime.now().isoformat(),
            "final_summary": final_summary_text,
            "number_of_chunks": len(text_chunks),
            "chunk_summaries": chunk_summaries, # List of summaries for each chunk
            "summary_output_file": summary_output_path
        }
        
        try:
            with open(summary_output_path, 'w') as f_out:
                json.dump(summary_result_data, f_out, indent=4)
            print(f"Successfully generated and saved summary to: {summary_output_path}")
            return {
                "success": True,
                "summary": final_summary_text, # For quick access
                "output_path": summary_output_path,
                "details": summary_result_data # Contains all info
            }
        except Exception as e:
            print(f"Error saving summary JSON to {summary_output_path}: {e}")
            return {
                "success": False,
                "error": f"Failed to save summary JSON: {str(e)}",
                "summary_generated": final_summary_text, # Still return summary if generated
                "original_file": file_path
            }

# Example usage (for testing this module directly)
def main_test_summarizer():
    # Create a dummy file for testing if it doesn't exist
    dummy_file_dir = os.path.join(BASE_DIR, "data", "raw", "TESTTICKER", "sec", "10-K", "00000TEST-00-000000")
    os.makedirs(dummy_file_dir, exist_ok=True)
    dummy_file_path = os.path.join(dummy_file_dir, "test_document.html")
    
    if not os.path.exists(dummy_file_path):
        with open(dummy_file_path, "w", encoding="utf-8") as f:
            f.write("""
            <html><head><title>Test Document</title></head>
            <body>
                <h1>Financial Report Q4 2023</h1>
                <p>This is a test document for summarization. Revenue was $100 million, an increase of 10% year-over-year. 
                Net income was $10 million. The company launched a new product, the SuperWidget, which is expected to 
                drive future growth. Risks include supply chain disruptions and increased competition.</p>
                <section>
                    <h2>Outlook</h2>
                    <p>The company expects revenue to grow by 15% in the next fiscal year. We are optimistic about the future.
                    However, economic uncertainty remains a concern for overall market conditions.
                    Key initiatives include expanding into new markets and investing in R&D.</p>
                </section>
                <footer>Contact us at info@example.com</footer>
            </body></html>
            """)
        print(f"Created dummy test file: {dummy_file_path}")

    # Create dummy metadata for the dummy file
    dummy_metadata_path = f"{dummy_file_path}.meta.json"
    if not os.path.exists(dummy_metadata_path):
        dummy_meta = {
            "url": "http://example.com/test_document.html",
            "ticker": "TESTTICKER",
            "form_type": "10-K",
            "downloaded_at": datetime.now().isoformat(),
            "content_hash_sha256": "dummyhash123",
            "filepath_relative": os.path.relpath(dummy_file_path, BASE_DIR)
        }
        with open(dummy_metadata_path, "w") as f_meta:
            json.dump(dummy_meta, f_meta, indent=4)
        print(f"Created dummy metadata file: {dummy_metadata_path}")

    summarizer = DocumentSummarizer()
    if not summarizer.can_summarize:
        print("Cannot run summarizer test: OpenAI API key missing.")
        return

    print(f"\n--- Summarizing test document: {dummy_file_path} ---")
    result = summarizer.summarize_document(dummy_file_path)
    
    if result.get("success"):
        print("\n--- Summary Result ---")
        print(f"Final Summary: {result.get('summary')}")
        print(f"Output saved to: {result.get('output_path')}")
        # print("\nFull Details:")
        # print(json.dumps(result.get('details'), indent=2))
    else:
        print("\n--- Summarization Failed ---")
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    # Ensure OPENAI_API_KEY is set in your .env file to run this test
    main_test_summarizer()

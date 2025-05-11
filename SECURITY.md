# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to [your-email@example.com] (replace with your actual contact email). All security vulnerabilities will be promptly addressed.

Please do not disclose security vulnerabilities publicly until they have been addressed by the maintainers.

## Security Considerations

This application:
1.  Handles financial data which, while publicly sourced, should be processed responsibly.
2.  Makes API calls to external services (SEC EDGAR, OpenAI) requiring proper usage and potentially authentication (OpenAI).
3.  Requires an OpenAI API key that must be kept secure and should **never** be committed to the repository.

### Security Best Practices

-   **API Keys**:
    -   Always use environment variables (via a `.env` file) to store API keys and other sensitive credentials.
    -   Ensure the `.env` file is listed in `.gitignore` to prevent it from being committed to version control.
    -   The `OPENAI_API_KEY` is critical. Protect it like a password.
-   **SEC User Agent**:
    -   The `SEC_USER_AGENT` should be a valid email address as per SEC guidelines for making requests to their APIs. This helps them contact you if there are issues with your requests.
-   **Dependencies**:
    -   Keep dependencies updated to their latest secure versions. Regularly review and update packages listed in `requirements.txt`.
    -   You can use tools like `pip-audit` to check for known vulnerabilities in your dependencies:
        ```bash
        pip install pip-audit
        pip-audit
        ```
-   **Input Validation**:
    -   While this MVP has basic input handling, a production system should have robust validation for all API inputs, especially file paths and parameters used in external calls.
-   **Rate Limiting**:
    -   The application includes a basic rate limit for the SEC API (`SEC_API_RATE_LIMIT` in `config.py`). Respect the terms of service for all external APIs used.
-   **Error Handling**:
    -   Ensure sensitive information is not leaked in error messages or logs.
-   **Principle of Least Privilege**:
    -   If deploying, ensure the application runs with the minimum necessary permissions.

## Dependencies

Security vulnerabilities in dependencies should be addressed promptly by updating to a patched version.

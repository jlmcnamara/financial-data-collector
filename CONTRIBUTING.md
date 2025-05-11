# Contributing Guidelines

Thank you for considering contributing to the Financial Data Collector project! We welcome contributions that improve the functionality, reliability, and usability of this tool.

## How to Contribute

1.  **Fork the Repository**: Start by forking the main repository to your own GitHub account.
2.  **Clone Your Fork**: Clone your forked repository to your local machine.
    ```bash
    git clone https://github.com/YOUR_USERNAME/financial-data-collector.git
    cd financial-data-collector
    ```
3.  **Create a Branch**: Create a new branch for your feature or bug fix.
    ```bash
    git checkout -b feature/your-awesome-feature  # or fix/issue-description
    ```
4.  **Set Up Your Environment**:
    -   Create and activate a virtual environment.
    -   Install dependencies: `pip install -r requirements.txt`
    -   Set up your `.env` file as described in `README.md`.
5.  **Make Your Changes**: Implement your feature or fix the bug.
    -   Follow the coding style (PEP 8 for Python).
    -   Write clear, concise, and well-documented code.
    -   Add comments where necessary to explain complex logic.
6.  **Test Your Changes**:
    -   Ensure your changes work as expected.
    -   If you add new functionality, consider adding tests (future goal to implement a test suite).
    -   Make sure the application runs without errors after your changes.
7.  **Commit Your Changes**: Write meaningful commit messages.
    ```bash
    git add .
    git commit -m "feat: Add awesome feature"  # or "fix: Resolve specific bug"
    ```
    (Consider using [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.)
8.  **Push to Your Fork**:
    ```bash
    git push origin feature/your-awesome-feature
    ```
9.  **Open a Pull Request (PR)**:
    -   Go to the original repository on GitHub.
    -   Click on "Pull Requests" and then "New Pull Request".
    -   Choose your fork and branch to compare with the main branch of the original repository.
    -   Provide a clear title and description for your PR, explaining the changes and why they are being made.
    -   If your PR addresses an existing issue, link to it (e.g., "Closes #123").

## Code Review

-   Once a PR is submitted, maintainers will review your code.
-   Be prepared to discuss your changes and make adjustments based on feedback.
-   All PRs must pass any automated checks (linters, tests - to be implemented) before being merged.

## Security Practices

When contributing, please adhere to the security practices outlined in `SECURITY.md`:
-   **Never commit sensitive information** (API keys, passwords, etc.).
-   Be mindful of how your changes might impact the security of the application.

## Coding Standards

-   **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines. Use a linter like Flake8 or Black if possible.
-   **Documentation**: Document new functions, classes, and complex logic. Update `README.md` if your changes affect usage or setup.
-   **Clarity**: Write code that is easy to understand and maintain.

## Reporting Bugs

If you find a bug, please open an issue on GitHub with the following information:
-   A clear and descriptive title.
-   Steps to reproduce the bug.
-   Expected behavior.
-   Actual behavior.
-   Your environment (OS, Python version).
-   Any relevant error messages or logs.

Thank you for contributing!

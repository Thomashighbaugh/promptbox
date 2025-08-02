# Project: PromptBox

This project is a Streamlit application for managing prompts and interacting with LLMs.

## How to run the application:

1.  **Install dependencies:**
    ```bash
    pip install -e .
    ```
2.  **Run the Streamlit application:**
    ```bash
    streamlit run src/promptbox/app.py
    ```

## Agent-specific instructions:

-   **Linting:** Use `ruff check .`
-   **Type Checking:** Use `mypy src/promptbox/`
-   **Testing:** This project does not currently have a dedicated test suite. If changes are made, consider adding tests in a `tests/` directory at the project root, mirroring the `src/` structure.

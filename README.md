# `promptbox` - Streamlit Edition

**A user-friendly Streamlit application for creating, managing, testing, and interacting with Large Language Model (LLM) prompts, characters, and chat sessions.**

`promptbox` provides a local-first, web-based UI to streamline your workflow with LLMs. It helps you organize your prompt library, define reusable character/scenario cards, test them in an interactive chat interface, and save your valuable chat sessions for later review or continuation.

![promptbox_streamlit_screenshot_placeholder](https://via.placeholder.com/800x450.png?text=Promptbox+Streamlit+UI+Screenshot)
_(Screenshot placeholder - to be updated with actual UI)_

---

## Core Features

- **🗃️ Prompt & Character Library:**
  - Create, store, and manage your prompts and character/scenario cards in a local SQLite database.
  - Organize items with names, descriptions, and nested folders (e.g., `creative/story-starters/fantasy`).
  - Visually browse your library through an intuitive folder structure.
- **⚡️ Interactive Chat Interface:**
  - Test any prompt or character card in an interactive chat session.
  - Dynamically select LLM providers and models for each chat.
  - Support for template variables `[[variable_name]]` in prompts and cards, filled in before starting a chat.
  - Markdown rendering for chat messages (excluding within code fences).
  - Edit your user messages after sending, and the LLM will regenerate responses from that point.
- **💾 Chat Session Management:**
  - Save your chat sessions, including the messages, provider/model used, and originating prompt/card.
  - Browse saved sessions and reload them to continue the conversation or review past interactions.
  - "Save on Exit" prompt: If you navigate away from an active chat, you'll be asked if you want to save the session.
- **🌐 Multi-Provider Support:**
  - Seamlessly switch between different LLM providers and models. `promptbox` dynamically fetches available models.
  - Supported Providers (configure with your API keys):
    - Ollama (for local models)
    - Mistral
    - Groq
    - Google (Gemini)
    - Cerebras
- **🤖 AI-Powered Prompt Improvement:**
  - Select a prompt and use an LLM to analyze and suggest improvements to its wording for clarity, effectiveness, and robustness. Apply suggestions with a click.
- **🔍 Full-Text Search (Prompts):**
  - Quickly find prompts by searching through their name, description, folder, and instruction content.
- **📦 Backup & Export:**
  - **Database Backup:** Create a timestamped backup of your entire SQLite database file.
  - **Markdown Export:**
    - Export all prompts or all character cards to structured `.tar.gz` archives of Markdown files.
    - Export individual saved chat sessions to Markdown files.
- **💻 Local-First Philosophy:**
  - Your data is yours. The prompt database, configuration, and backups are stored locally on your machine in a dedicated `~/.promptbox` directory.

## Installation

`promptbox` requires **Python 3.11** or newer.

1.  **Check your Python version:**

    ```bash
    python --version
    # or
    python3 --version
    ```

2.  **Clone the repository (or download the source code):**

    ```bash
    git clone https://github.com/your-username/promptbox.git # Replace with the actual repository URL
    cd promptbox
    ```

3.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

4.  **Install the application and its dependencies:**
    This command uses `pip` to install the project and all its dependencies from `pyproject.toml`.
    ```bash
    pip install .
    ```
    _For developers who want to modify the code, install in editable mode:_
    ```bash
    pip install -e .
    ```

## Configuration

Before running the application, you need to configure your API keys for the LLM providers you intend to use.

1.  **Create a `.env` file:** In the root of the `promptbox` project directory (where `pyproject.toml` is located), create a file named `.env`.

2.  **Add your API Keys:** Copy the template below into your `.env` file and add the API keys for the services you wish to use. You only need to provide keys for the providers you have access to or plan to use.

    ```dotenv
    # .env file for promptbox

    # --- Cloud Provider API Keys (only fill in the ones you use) ---
    MISTRAL_API_KEY="your-mistral-api-key"
    GROQ_API_KEY="your-groq-api-key"
    GOOGLE_API_KEY="your-google-api-key" # For Gemini models
    CEREBRAS_API_KEY="your-cerebras-api-key"

    # --- (Optional) Override for local Ollama server address ---
    # The application defaults to http://127.0.0.1:11434 if this is not set.
    # Make sure your Ollama server is running and accessible at this address.
    # OLLAMA_API_BASE="http://127.0.0.1:11434"

    # --- (Optional) Override for the main database file path ---
    # Defaults to ~/.promptbox/data/promptbox.db
    # DATABASE_PATH="/custom/path/to/your/promptbox.db"
    ```

The application will automatically load these keys and settings when it starts.

## Usage

To run the `promptbox` Streamlit application:

1.  Make sure you are in the root directory of the project (where you cloned/downloaded it).
2.  Ensure your virtual environment is activated (if you created one).
3.  Run the following command in your terminal:

    ```bash
    streamlit run src/promptbox/app.py
    ```

This will start the Streamlit server, and the application should open in your default web browser.

### Navigating the Application

The application features a sidebar for navigation:

- **🏠 Home:** Displays a welcome message and general information.
- **📝 Prompts:** Manage your prompt templates.
  - View prompts organized by folders.
  - Create new prompts with system, user, and assistant instructions.
  - Edit existing prompts.
  - Use AI to improve prompts.
  - Start a chat session using a selected prompt.
  - Search and filter prompts.
- **🎭 Characters/Scenarios:** Manage reusable character personas or scenario setups.
  - Similar organization and management features as Prompts.
  - Start a chat session using a selected character/scenario card.
- **💬 Chat Sessions:** View your saved chat conversations.
  - Browse a list of past sessions.
  - Load a session to continue chatting or review its contents.
  - Delete old sessions.
- **💾 Backups:** Manage application data backups.
  - Backup the entire database.
  - Export prompts or cards to Markdown archives.

### Chat Interface Features

- **Model Selection:** Choose your LLM provider and model before starting or during a chat (by changing model).
- **Variable Substitution:** If a prompt/card uses `[[variables]]`, you'll be asked to fill them in.
- **Message Editing:** Click the pencil icon next to one of your messages to edit it. The chat history will truncate to that point, and the LLM will generate a new response.
- **Saving:**
  - Explicitly save a session using the "Save Session" button.
  - If you navigate away or try to change models mid-chat, a dialog will ask if you wish to save your current progress.
- **Export to Markdown:** Save the current chat (even if not a fully saved session) to a Markdown file.

## Project Structure

The project is organized within the `src/promptbox` directory:

```
promptbox/
├── src/
│   ├── promptbox/
│   │   ├── core/         # Core application logic (e.g., config.py).
│   │   ├── db/           # Database setup, SQLAlchemy models (models.py), session management (database.py).
│   │   ├── models/       # Pydantic data models (data_models.py) for validation and data transfer.
│   │   ├── services/     # Business logic layer (e.g., prompt_service.py, chat_service.py).
│   │   ├── ui/           # Streamlit UI view modules (e.g., prompt_view.py, chat_view.py).
│   │   ├── utils/        # Standalone utility functions (e.g., file_handler.py, prompt_parser.py).
│   │   ├── __init__.py
│   │   └── app.py        # Main Streamlit application entry point.
│   ├── __init__.py
├── README.md             # This file.
└── pyproject.toml        # Project metadata and dependencies.
```

### Key Technologies

- **[Streamlit](https://streamlit.io/):** For building the interactive web-based user interface.
- **[SQLAlchemy](https://www.sqlalchemy.org/):** For the database Object-Relational Mapper (ORM), managing the SQLite database.
- **[Pydantic](https://docs.pydantic.dev/):** For data validation and settings management.
- **[Langchain](https://github.com/langchain-ai/langchain):** For abstracting and simplifying interactions with various LLM providers.
- **Python-dotenv:** For managing API keys and environment variables.

## Contributing

Contributions are welcome! If you have suggestions for improvements, new features, or have found a bug, please feel free to open an issue or submit a pull request to the project repository.

1.  Fork the repository.
2.  Create a new feature branch (e.g., `git checkout -b feature/awesome-new-feature`).
3.  Make your changes and commit them (`git commit -m 'Add awesome new feature'`).
4.  Push to the branch (`git push origin feature/awesome-new-feature`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License. See the `LICENSE` file (if included in the repository) for details.

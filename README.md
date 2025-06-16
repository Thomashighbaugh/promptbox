# `promptbox`

**A powerful, terminal-based toolkit for creating, managing, and interacting with Large Language Model (LLM) prompts.**

`promptbox` is a local-first TUI (Text-based User Interface) designed for developers, writers, and prompt engineers who want a fast, efficient, and keyboard-driven workflow for their prompts. It helps you organize your prompt library, test prompts against multiple LLM providers, and maintain a history of your interactions.

I have wanted an application like this, using my Dropbox to nest prompts in folders but even this was not enough as I couldn't just run prompts there from the editor.

![promptbox_screenshot](https://user-images.githubusercontent.com/12345/some-image-url.png) <!-- Placeholder for a future screenshot -->

---

## Core Features

- **🗃️ Prompt Library:** Create, store, and manage your prompts in a local SQLite database. Organize them with names, descriptions, folders, and tags.
- **⚡️ Interactive Chat:** Test any prompt in an interactive chat session. The UI is clean, responsive, and designed for conversation.
- **🌐 Multi-Provider Support:** Seamlessly switch between different LLM providers (with free tiers that I use, you can PR openai if you are willing to support it or tell me about other free providers as you wish) and models for any chat session. `promptbox` dynamically fetches the available models from each provider's API.
  - Ollama (for local models)
  - Mistral
  - Groq
  - Google (Gemini)
  - Cerebras
- **🤖 AI-Powered Improvement:** Use one LLM to analyze and improve a prompt you've written. Get suggestions for clarity, effectiveness, and robustness.
- **🔍 Full-Text Search:** Quickly find any prompt by searching through its name, description, tags, and instruction content.
- **📦 Backup & Export:**
  - Create a timestamped backup of your entire prompt database.
  - Export all your prompts to a structured `.tar.gz` archive of Markdown files.
- **💻 Local-First Philosophy:** Your data is yours. The prompt database and configuration are stored locally on your machine in a dedicated `~/.promptbox` directory.

## Installation

`promptbox` requires **Python 3.11** or newer.

1.  **Check your Python version:**

    ```bash
    python --version
    ```

2.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/promptbox.git
    cd promptbox
    ```

3.  **Install the application:**
    This command uses `pip` to install the project and all its dependencies, making the `promptbox` command available in your terminal.
    ```bash
    pip install .
    ```
    _For developers who want to modify the code, install in editable mode:_
    ```bash
    pip install -e .
    ```

## Configuration

Before running the application, you must configure your API keys.

1.  **Create a `.env` file:** In the root of the `promptbox` project directory, create a file named `.env`.

2.  **Add your API Keys:** Copy the template below into your `.env` file and add the API keys for the services you wish to use. You only need to provide keys for the providers you have access to.

    ```dotenv
    # .env file

    # --- Cloud Provider API Keys (only fill in the ones you use) ---
    MISTRAL_API_KEY="your-mistral-api-key"
    GROQ_API_KEY="your-groq-api-key"
    GOOGLE_API_KEY="your-google-api-key"
    CEREBRAS_API_KEY="your-cerebras-api-key"

    # --- (Optional) Override for local Ollama server address ---
    # The application defaults to http://127.0.0.1:11434 if this is not set.
    # OLLAMA_API_BASE="http://127.0.0.1:11434"
    ```

The application will automatically load these keys when it starts.

## Usage

To run the application, simply execute the command in your terminal:

```bash
promptbox
```

You will be greeted by the main menu, which is the central hub for all actions.

### Main Menu Navigation

- **(L)ist & Manage Prompts:** The core of the application. This takes you to a scrollable list of all your saved prompts.

  - From the list, enter a prompt's ID to view its details and access the **Actions Menu**.
  - **Actions Menu:**
    - **(c) Chat:** Start a new interactive chat session using this prompt as the template.
    - **(e) Edit:** (Not yet implemented) Modify the selected prompt.
    - **(d) Delete:** Permanently remove the prompt from your database.
    - **(i) Improve:** Use another LLM to suggest improvements to your prompt's text.
    - **(b) Back:** Return to the prompt list.

- **(N)ew Prompt:** Launch a step-by-step wizard to create and save a new prompt. You'll be asked for a name, folder, tags, and the system, user, and assistant instructions.

  - For multi-line input (like prompt instructions), use `Ctrl+D` (on Linux/macOS) or `Ctrl+Z` then `Enter` (on Windows) on a new line to finish typing.

- **(S)earch Prompts:** Perform a case-insensitive, full-text search across all fields of your prompts.

- **(B)ackup Options:** Create backups of your data.

- **(Q)uit:** Exit the application.

### The Chat Interface

When you start a chat, you first select the provider and model you wish to use. The chat session then begins.

- If your prompt template ends with a `User Instruction`, the AI will generate the first response automatically.
- Type your message and press `Enter`.
- Use the following special commands in the input box:
  - `/save`: Saves the full conversation log to the database, associated with the original prompt.
  - `/exit`: Ends the chat session and returns you to the previous menu.

## Project Structure

The project is organized into logical components within the `src/promptbox` directory.

```
src/promptbox/
├── core/         # Core application logic, like configuration (config.py).
├── db/           # Database setup, session management, and SQLAlchemy models.
├── models/       # Pydantic data models for data validation and transfer.
├── services/     # Business logic (LLM integrations, prompt management, chat).
├── tui/          # All Text-based User Interface code (menus, components, chat UI).
└── utils/        # Standalone utility functions (e.g., file handlers).
```

### Key Technologies

- **[Rich](https://github.com/Textualize/rich):** For all TUI rendering, including panels, tables, styled text, and live updates.
- **[SQLAlchemy](https://www.sqlalchemy.org/):** For the database Object-Relational Mapper (ORM), managing the SQLite database.
- **[Langchain](https://github.com/langchain-ai/langchain):** For abstracting and simplifying interactions with the various LLM providers.

## Contributing

Contributions are welcome! If you have a suggestion for an improvement or have found a bug, please feel free to open an issue or submit a pull request.

1.  Fork the repository.
2.  Create a new feature branch (`git checkout -b feature/your-amazing-feature`).
3.  Commit your changes (`git commit -m 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/your-amazing-feature`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

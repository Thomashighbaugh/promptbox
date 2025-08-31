# Promptbox Agent Guidelines

## Build/Run Commands
- **Run app**: `streamlit run src/promptbox/app.py`
- **Install**: `pip install -e .` (editable install from pyproject.toml)
- **No tests**: Project currently has no test suite configured

## Code Style & Conventions
- **Language**: Python 3.11+ (as specified in pyproject.toml)
- **Imports**: Group stdlib, third-party, local imports with line breaks between groups
- **Type hints**: Use type annotations with `|` union syntax (e.g., `str | None`)
- **Docstrings**: Triple-quoted strings for modules/functions describing purpose
- **Naming**: Snake_case for variables/functions, PascalCase for classes
- **Error handling**: Use try/except with specific error types, display errors via `st.error()`
- **Services**: Use dependency injection pattern via Streamlit cache_resource decorators
- **Database**: SQLAlchemy models in `db/` directory, separate engines per database

## Project Structure
- **Entry point**: `src/promptbox/app.py` - Main Streamlit application
- **Services**: Business logic in `src/promptbox/services/`
- **UI**: Streamlit views in `src/promptbox/ui/`
- **Config**: Settings management in `src/promptbox/core/config.py`
- **Database**: Models and connection management in `src/promptbox/db/`

## Dependencies
- **Core**: Streamlit, SQLAlchemy, Pydantic, PyYAML
- **LLM**: LangChain ecosystem (mistralai, groq, google-genai, openai, ollama)
- **Utils**: Requests, Pillow, python-dotenv, Jinja2
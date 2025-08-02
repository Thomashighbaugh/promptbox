# Architecture

This document provides an overview of the project's architecture.

## Directory Structure

The project is organized into the following directories:

- **`.github`**: Contains GitHub-specific files, such as workflows and documentation.
- **`src/promptbox`**: Contains the main source code for the application.
  - **`core`**: Core application settings and configuration.
  - **`db`**: Database models, connection management, and data access layer.
  - **`models`**: Pydantic data models.
  - **`services`**: Business logic for the application.
  - **`ui`**: Streamlit views for the user interface.
  - **`utils`**: Utility functions.
- **`.venv`**: The virtual environment for the project.

## UI Layer

The UI is built using Streamlit. The code for the UI is located in the `src/promptbox/ui` directory. Each view (e.g., `prompt_view.py`, `character_view.py`) is responsible for rendering a specific part of the application.

## Service Layer

The business logic for the application is located in the `src/promptbox/services` directory. Each service (e.g., `prompt_service.py`, `character_service.py`) is responsible for a specific domain of the application.

## Data Layer

The data layer is responsible for interacting with the database. The code for the data layer is located in the `src/promptbox/db` directory. It uses SQLAlchemy for the ORM and SQLite for the database.

## Configuration

The application's configuration is managed by the `src/promptbox/core/config.py` file. It uses Pydantic to define the settings and reads them from a `.env` file.

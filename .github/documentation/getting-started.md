# Getting Started

This guide will walk you through the process of setting up and running Promptbox on your local machine.

## Prerequisites

- Python 3.9+
- pip

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/promptbox.git
    cd promptbox
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file** in the root of the project. You can copy the `.env.example` file if it exists.

2.  **Set the required environment variables** in the `.env` file. The most important one is `APP_HOME`, which specifies the directory where Promptbox will store its data.

    ```
    APP_HOME=/path/to/your/promptbox/data
    ```

## Running the Application

Once you have completed the installation and configuration steps, you can run the application using the following command:

```bash
streamlit run src/promptbox/app.py
```

The application will be available at `http://localhost:8501`.

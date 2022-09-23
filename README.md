# CHSLD scraper

Scrape CHSLD information from bottinsante.ca and indexsante.ca and export it to CSV and Excel files.

## Setup

1. Download and install python on your machine: https://www.python.org/downloads/

2. (Optional) Create a new virtual environment and activate it.
    This makes the project self-contained, with all dependencies, avoiding version conflicts between different projects. Otherwise, the packages will be installed globally.

    ```
    python -m venv .venv

    (On Windows)
    .venv\Scripts\activate

    (On Linux or Mac)
    source .venv/bin/activate
    ```

3. Install project dependencies.
    ```
    pip install -r requirements.txt
    ```

4. Run the scraper.
    ```
    python scrape.py
    ```

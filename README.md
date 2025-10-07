# YouTube ELT Pipeline

This project is a YouTube ELT (Extract, Load, Transform) pipeline for analyzing YouTube data. It uses Apache Airflow for orchestration, PostgreSQL as a data warehouse, and Soda Core for data quality validation.

## Project Structure

```
.
├── .github/workflows/
├── dags/
│   ├── dag_data_quality.py
│   ├── dag_produce_json.py
│   └── dag_update_db.py
├── data/json/
├── include/
│   ├── scripts/
│   │   └── youtube_elt.py
│   └── soda/
│       └── checks/
├── tests/
├── .dockerignore
├── Dockerfile
├── packages.txt
├── README.md
└── requirements.txt
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/youtube-elt-pipeline.git
    cd youtube-elt-pipeline
    ```

2.  **Set up the environment:**
    - Create a `.env` file and add your YouTube API key:
      ```
      YOUTUBE_API_KEY=your_api_key
      ```

3.  **Build and run the Docker containers:**
    ```bash
    docker-compose up --build
    ```

## Usage

1.  **Access the Airflow UI:**
    - Open your web browser and go to `http://localhost:8080`.
    - The default username and password are `admin`.

2.  **Enable the DAGs:**
    - In the Airflow UI, enable the following DAGs in order:
      1. `produce_json`
      2. `update_db`
      3. `data_quality`

3.  **Monitor the pipeline:**
    - You can monitor the progress of the DAGs in the Airflow UI.
    - The extracted data will be stored in the `data/json` directory.
    - The transformed data will be loaded into the PostgreSQL database.

## Data Warehouse

- **Schema:** `staging`, `core`
- **Tables:**
  - `staging.videos`
  - `core.videos`

## Data Quality

- Data quality checks are performed using Soda Core.
- The checks are defined in the `include/soda/checks` directory.

## CI/CD

- The CI/CD pipeline is configured using GitHub Actions.
- The workflow is defined in the `.github/workflows` directory.
# YouTube ELT Pipeline - Step-by-Step Tutorial

This document provides a detailed, step-by-step walkthrough of the YouTube ELT Pipeline project. It covers the entire process, from setting up the initial project structure to running the complete data pipeline.

---

### Introduction

This project is designed to build an automated ELT (Extract, Load, Transform) pipeline for analyzing YouTube data. We will use Apache Airflow to orchestrate the pipeline, PostgreSQL as our data warehouse, and Soda Core to ensure data quality. The entire environment will be containerized using Docker for portability and ease of use.

### Prerequisites

Before you begin, make sure you have the following installed:

*   Docker and Docker Compose
*   A YouTube API Key

---

### Step 1: Project Structure ✓ [COMPLETED]

The first step is to set up a clean and organized project structure. This helps in maintaining the codebase and makes it easier to navigate.

Here is the structure we have created:

```
.
├── .github/workflows/  # For CI/CD pipelines
├── dags/               # Airflow DAGs
├── data/json/          # To store extracted JSON data
├── include/            # For scripts and other resources
│   ├── scripts/        # Python scripts used by Airflow
│   └── soda/           # Soda Core configurations and checks
├── tests/              # For unit and integration tests
├── .dockerignore       # To exclude files from the Docker build
├── Dockerfile          # To build the Docker image
├── packages.txt        # For OS-level packages
├── README.md           # Project documentation
└── requirements.txt    # Python dependencies
```

This structure separates the different components of the project, making it modular and scalable.

---

### Step 2: Docker and Airflow Configuration ✓ [COMPLETED]

We use Docker to create a reproducible environment for our pipeline. The `Dockerfile` is based on an official Astronomer image, which comes with Airflow pre-installed.

**`Dockerfile`**

```dockerfile
FROM quay.io/astronomer/astro-runtime:8.8.0
```

**`requirements.txt`**

This file lists the Python packages required for the project. These packages are installed when the Docker image is built.

```
apache-airflow-providers-postgres
apache-airflow-providers-docker
soda-core-scientific
soda-core-postgres
google-api-python-client
```

---

### Step 3: Extracting Data (`dag_produce_json.py`) ✓ [PARTIALLY COMPLETED]

This is the first stage of our pipeline, where we extract data from the YouTube API. The YouTube data extraction script is working successfully, but the DAG integration is pending.

**The Script: `include/scripts/youtube_elt.py`**

This Python script is responsible for:

1.  **Connecting to the YouTube API:** It uses the `googleapiclient` library to create a client for the YouTube v3 API.
2.  **Fetching Video IDs:** It retrieves the IDs of all videos in a given playlist (in our case, MrBeast's channel).
3.  **Fetching Video Details:** It gets detailed information for each video, including title, publication date, duration, and statistics (views, likes, comments).
4.  **Handling Pagination and Quotas:** The script is designed to handle API pagination and includes basic error handling and retry logic to manage API quotas.
5.  **Saving Data:** The extracted data is saved as a timestamped JSON file in the `data/json/` directory.

**The DAG: `dags/dag_produce_json.py`**

This Airflow DAG orchestrates the execution of the `youtube_elt.py` script. It uses a `BashOperator` to run the script inside the Airflow container.

```python
from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="produce_json",
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["youtube", "elt", "json"],
) as dag:
    BashOperator(
        task_id="run_elt_script",
        bash_command="python /usr/local/airflow/include/scripts/youtube_elt.py",
    )
```

---

### Step 4: Storing and Transforming Data (`dag_update_db.py`) ✓ [DATABASE SETUP COMPLETED]

Once the data is extracted, we load it into our PostgreSQL data warehouse. The database setup has been completed with the required schemas and tables.

**The DAG: `dags/dag_update_db.py`**

This DAG is responsible for:

1.  **Creating Tables:** It first ensures that the `staging.videos` and `core.videos` tables exist in the database.
2.  **Loading to Staging:** It uses a `PythonOperator` to call a function that reads the JSON file and loads the data into the `staging.videos` table. This table holds the raw data.
3.  **Transforming and Loading to Core:** It then executes an SQL query to transfer the data from the staging table to the `core.videos` table. During this process, it handles duplicates and updates existing records.

---

### Step 5: Ensuring Data Quality (`dag_data_quality.py`)

To ensure the data is reliable, we use Soda Core to perform automated data quality checks.

**Soda Core Configuration:**

*   **`include/soda/configuration.yml`:** This file configures the connection to our PostgreSQL database.
*   **`include/soda/checks/videos.yml`:** This file defines the data quality checks to be performed on the `core.videos` table. For example, we check for row counts, missing values, and duplicates.

**The DAG: `dags/dag_data_quality.py`**

This DAG uses a `BashOperator` to run the Soda scan. If any of the data quality checks fail, the task will fail, and an alert can be configured.

---

### Step 6: Automating with CI/CD

We use GitHub Actions to create a Continuous Integration/Continuous Deployment (CI/CD) pipeline.

**The Workflow: `.github/workflows/main.yml`**

This workflow is triggered on every push to the `main` branch. It performs the following steps:

1.  **Checks out the code.**
2.  **Sets up a Python environment.**
3.  **Installs the dependencies.**
4.  **Runs the unit tests.**

This ensures that the code is always in a deployable state.

---

### Step 7: Running the Pipeline

To run the pipeline, you will need to:

1.  **Set up your environment:** Create a `.env` file with your `YOUTUBE_API_KEY`.
2.  **Build and run the Docker containers:** Use `docker-compose up --build`.
3.  **Access the Airflow UI:** Open `http://localhost:8080` in your browser.
4.  **Enable and trigger the DAGs:** Enable the `produce_json`, `update_db`, and `data_quality` DAGs in the Airflow UI.

---

### Conclusion

This project provides a solid foundation for building a production-ready ELT pipeline. By following this guide, you can understand the key components and how they work together to create a robust and automated data workflow.
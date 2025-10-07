# YouTube ELT Pipeline - Project Plan

This document outlines the epics, user stories, and tasks for the YouTube ELT Pipeline project. This can be used to populate a Kanban board in a tool like Jira.

---

### Epic 1: Data Extraction and Orchestration

**Description:** Build a robust and automated pipeline to extract data from the YouTube API and orchestrate the workflow using Airflow.

**User Stories:**

*   **As a Data Engineer, I can orchestrate the daily extraction of YouTube data via Airflow DAGs.**
    *   **Task:** Create an Airflow DAG (`produce_json`) to trigger the extraction process.
    *   **Task:** Implement a Python script to connect to the YouTube v3 API.
    *   **Task:** Fetch video data for the specified channel (MrBeast).
    *   **Task:** Implement pagination to retrieve all videos from the channel's playlist.
    *   **Task:** Handle API quota limits (10,000 units/day) to avoid errors.
    *   **Task:** Implement error handling and retry logic for API calls.
    *   **Task:** Save the extracted data into timestamped JSON files.

---

### Epic 2: Data Warehousing and Transformation

**Description:** Load the extracted data into a PostgreSQL data warehouse and transform it for analysis.

**User Stories:**

*   **As a Data Analyst, I can access structured data in PostgreSQL.**
    *   **Task:** Design a Data Warehouse architecture with `staging` and `core` schemas.
    *   **Task:** Create an Airflow DAG (`update_db`) to manage the database update process.
    *   **Task:** Create a `staging.videos` table for raw data.
    *   **Task:** Create a `core.videos` table for cleaned and transformed data.
    *   **Task:** Implement a process to load data from JSON files into the `staging.videos` table.
    *   **Task:** Implement a transformation process to clean and standardize the data.
    *   **Task:** Load the transformed data from the `staging` schema to the `core` schema.
    *   **Task:** Handle data duplication and maintain a history of changes.

---

### Epic 3: Data Quality and Validation

**Description:** Ensure the integrity and reliability of the data through automated data quality checks.

**User Stories:**

*   **As a Data Quality Manager, I can automatically validate the quality of the data.**
    *   **Task:** Integrate Soda Core into the project.
    *   **Task:** Create an Airflow DAG (`data_quality`) to run data quality scans.
    *   **Task:** Configure Soda Core to connect to the PostgreSQL database.
    *   **Task:** Define data quality checks (e.g., completeness, coherence, format) in a Soda YAML file.
    *   **Task:** Implement alerting for data quality issues.

---

### Epic 4: Deployment and Infrastructure

**Description:** Containerize the application and automate the deployment process for portability and scalability.

**User Stories:**

*   **As a DevOps, I can deploy and monitor the pipeline via Docker and Astro CLI.**
    *   **Task:** Create a `Dockerfile` to containerize the Airflow environment.
    *   **Task:** Use Astro CLI to manage the local development environment.
    *   **Task:** Configure Docker volumes to persist data between the container and the host machine.

*   **As a Developer, I can launch the pipeline locally and deploy it with GitHub Actions.**
    *   **Task:** Set up a CI/CD pipeline using GitHub Actions.
    *   **Task:** Create a workflow to build and test the project on every push to the `main` branch.
    *   **Task:** Implement unit and integration tests for the codebase (minimum 20 tests).

---

### Epic 5: (Bonus) Data Visualization

**Description:** Create a simple dashboard to visualize the analyzed data.

**User Stories:**

*   **As a Business Analyst, I can visualize the data via a simple dashboard.**
    *   **Task:** (Bonus) Create a Streamlit dashboard to display key metrics.
    *   **Task:** (Bonus) Connect the dashboard to the PostgreSQL data warehouse.
    *   **Task:** (Bonus) Visualize metrics such as views, likes, and comments over time.
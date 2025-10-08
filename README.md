# 📊 YouTube ELT Pipeline - Automated Data Analysis

## 🎯 Overview

This project implements a complete YouTube ELT (Extract, Load, Transform) pipeline for automated analysis of YouTube performance data. Built with Apache Airflow, PostgreSQL, and Soda Core for data quality validation.

**Target Channel:** MrBeast (@MrBeast)  
**Architecture:** Docker + Astro CLI + PostgreSQL + Soda Core  
**Data Extracted:** Video ID, title, publication date, duration, views, likes, comments

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YouTube API   │───▶│   Airflow DAGs   │───▶│   PostgreSQL    │
│                 │    │                 │    │                 │
│ - Video Data    │    │ - produce_json  │    │ - Staging       │
│ - Metadata      │    │ - update_db     │    │ - Core          │
│ - Statistics    │    │ - data_quality  │    │ - Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   JSON Files    │    │   Soda Checks   │    │   Airflow UI    │
│ - Timestamped   │    │ - Quality Rules │    │ - Monitoring    │
│ - Raw Storage   │    │ - Validation    │    │ - Management    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Astro CLI (recommended)
- YouTube API Key
- 8GB+ RAM recommended

### 1. Clone & Setup
```bash
git clone <repository-url>
cd "Youtube ELT Pipeline"
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your credentials
nano .env
```

**Required Configuration:**
```env
YOUTUBE_API_KEY=your-actual-api-key-here
POSTGRES_PASSWORD=your-secure-password
AIRFLOW_PASSWORD=your-admin-password
```

### 3. Start with Docker Compose
```bash
# Start the complete pipeline
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Start with Astro CLI (Recommended)
```bash
# Initialize Astro (if not already done)
astro dev init

# Start development environment
astro dev start

# View Airflow UI: http://localhost:8080
# Username: admin
# Password: admin (or your configured password)
```

## 📋 DAG Workflows

### 1. **produce_json** (Daily 00:00 UTC)
- Extracts latest 100 videos from MrBeast channel
- Handles API rate limits (10,000 units/day)
- Saves timestamped JSON files
- Implements retry logic and error handling

### 2. **update_db** (Daily 00:05 UTC)  
- Loads JSON data to PostgreSQL staging
- Transforms and cleanses data
- Transfers to core schema with UPSERT
- Maintains historical versions

### 3. **data_quality** (Daily 00:10 UTC)
- Runs comprehensive Soda Core validation
- Checks completeness, consistency, format
- Generates quality reports
- Triggers alerts on failures

## 🗄️ Database Schema

### Staging Schema (`staging.videos`)
```sql
CREATE TABLE staging.videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    published_at TIMESTAMP,
    duration TEXT,
    view_count BIGINT,
    like_count BIGINT,
    comment_count BIGINT
);
```

### Core Schema (`core.videos`)
```sql
CREATE TABLE core.videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    published_at TIMESTAMP,
    duration TEXT,
    view_count BIGINT,
    like_count BIGINT,
    comment_count BIGINT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_category TEXT,
    performance_score DECIMAL,
    is_trending BOOLEAN
);
```

## 📊 Data Access

### Via Airflow UI
- Navigate to http://localhost:8080
- Use Admin → Connections to query data
- View task logs and execution history

### Via pgAdmin (localhost:5050)
```
Host: postgres
Port: 5432
Database: postgres
Username: postgres
Password: password
```

### Via DBeaver/Local Tools
```
Connection: PostgreSQL
Host: localhost
Port: 5432
Database: postgres
Schema: core
```

## 🧪 Testing

### Run All Tests
```bash
# In project directory
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=include --cov-report=html
```

### Test Categories
- **Unit Tests**: Core functions (13+ tests)
- **Integration Tests**: Database operations
- **DAG Tests**: Airflow workflow validation
- **Data Quality Tests**: Soda Core rules

## 🔍 Data Quality Validation

### Soda Core Checks
```yaml
checks for core.videos:
  # Completeness
  - row_count > 0
  - missing_count(video_id) = 0
  - missing_count(title) = 0
  
  # Consistency  
  - duplicate_count(video_id) = 0
  - invalid_count(view_count) = 0
  
  # Format Validation
  - invalid_format(published_at, 'yyyy-MM-dd') = 0
  - invalid_regex(video_id, '^[A-Za-z0-9_-]{11}$') = 0
  
  # Business Rules
  - view_count >= 0
  - like_count >= 0
  - comment_count >= 0
```

## 📈 Monitoring & Alerting

### Airflow UI Features
- **DAG Status**: Real-time execution monitoring
- **Task Logs**: Detailed execution traces  
- **Data Lineage**: Visual workflow dependencies
- **Alerting**: Email notifications on failures

### Log Locations
```
logs/dag_id=produce_json/    # JSON extraction logs
logs/dag_id=update_db/       # Database operation logs  
logs/dag_id=data_quality/    # Quality validation logs
```

## 🚀 Production Deployment

### Docker Production
```bash
# Use production compose file
docker-compose -f docker-compose-production.yml up -d

# Scale workers if needed
docker-compose up -d --scale airflow-worker=3
```

### Environment Variables
```env
# Production settings
AIRFLOW__CORE__EXECUTOR=CeleryExecutor
AIRFLOW__CELERY__BROKER_URL=redis://redis:6379/0
AIRFLOW__CELERY__RESULT_BACKEND=db+postgresql://user:pass@postgres/airflow

# Security
AIRFLOW__CORE__FERNET_KEY=your-production-fernet-key
AIRFLOW__WEBSERVER__SECRET_KEY=your-production-secret
```

### CI/CD Pipeline
GitHub Actions automatically:
- Runs tests on push to main
- Validates DAG syntax
- Checks data quality rules
- Deploys to production (manual approval)

## 🔒 Security Best Practices

### API Key Management
```bash
# Set via Airflow Variables (recommended)
AIRFLOW_VAR_YOUTUBE_API_KEY=your-key

# Or via environment variables
YOUTUBE_API_KEY=your-key
```

### Database Security
- Use strong passwords
- Enable SSL connections in production
- Regular backups with encryption
- Network isolation via Docker networks

## 🛠️ Troubleshooting

### Common Issues

#### 1. API Quota Exceeded
```
Error: quotaExceeded
Solution: Wait 24h or use different API key
Monitoring: Check quota usage in Google Cloud Console
```

#### 2. Database Connection Failed
```
Error: could not connect to server
Solution: Ensure PostgreSQL container is running
Check: docker-compose logs postgres
```

#### 3. Soda Checks Failing
```
Error: Check failed: row_count > 0
Solution: Verify data extraction completed
Debug: Check produce_json DAG logs
```

### Debug Commands
```bash
# Check container status
docker-compose ps

# View specific service logs
docker-compose logs airflow

# Access Airflow container
docker-compose exec airflow bash

# Test database connection
docker-compose exec postgres psql -U postgres -d postgres
```

## 📝 Development

### Adding New Data Sources
1. Create new extraction function in `include/scripts/`
2. Add DAG in `dags/`  
3. Update database schema
4. Add Soda quality checks
5. Write tests

### Extending Data Quality
1. Add checks in `include/soda/checks/`
2. Update configuration in `include/soda/configuration.yml`
3. Test with `soda scan` command

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)  
5. Open Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Add docstrings to all functions
- Write tests for new features
- Update documentation

## 📞 Support

### Documentation
- [Complete Code Documentation](COMPLETE_CODE_AND_WORKFLOW_DOCUMENTATION.md)
- [Component Functions Guide](COMPONENT_FUNCTIONS_GUIDE.html)

### Issues
- Check existing issues in repository
- Provide detailed error logs
- Include system information

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for automated YouTube analytics**
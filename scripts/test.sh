#!/bin/bash

# YouTube ELT Pipeline Test Runner Script
# Comprehensive testing script for the pipeline

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_RESULTS_DIR="$PROJECT_DIR/test-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    info "Running test: $test_name"
    
    if eval "$test_command" > "$TEST_RESULTS_DIR/${test_name}.log" 2>&1; then
        log "✓ PASSED: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        error "✗ FAILED: $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        error "Check log file: $TEST_RESULTS_DIR/${test_name}.log"
        return 1
    fi
}

# Setup test environment
setup_test_environment() {
    log "Setting up test environment..."
    
    # Create test results directory
    mkdir -p "$TEST_RESULTS_DIR"
    
    # Setup Python environment
    cd "$PROJECT_DIR"
    
    # Install test dependencies
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt > "$TEST_RESULTS_DIR/install.log" 2>&1 || warn "Failed to install requirements"
    fi
    
    # Install additional test packages
    pip install pytest pytest-cov pytest-mock bandit safety black isort flake8 > "$TEST_RESULTS_DIR/test-deps.log" 2>&1
    
    # Setup environment variables
    export AIRFLOW_HOME="$PROJECT_DIR"
    export YOUTUBE_API_KEY="test_api_key_placeholder"
    export POSTGRES_HOST="localhost"
    export POSTGRES_PORT="5432"
    export POSTGRES_USER="postgres"
    export POSTGRES_PASSWORD="password"
    export POSTGRES_DB="postgres"
    
    # Create necessary directories
    mkdir -p data/json
    mkdir -p logs
    
    log "Test environment setup completed"
}

# Run unit tests
run_unit_tests() {
    log "Running unit tests..."
    
    run_test "unit_tests" "python -m pytest tests/ -v --cov=include --cov-report=html:$TEST_RESULTS_DIR/coverage --cov-report=xml:$TEST_RESULTS_DIR/coverage.xml"
    
    # Count individual test functions
    if command -v pytest > /dev/null 2>&1; then
        TEST_COUNT=$(python -m pytest tests/ --collect-only -q 2>/dev/null | grep "test session starts" -A 999 | grep -c "::test_" || echo "0")
        info "Total individual test functions: $TEST_COUNT"
    fi
}

# Test code quality
run_code_quality_tests() {
    log "Running code quality tests..."
    
    run_test "black_format_check" "black --check --diff ."
    run_test "isort_import_check" "isort --check-only --diff ."
    run_test "flake8_linting" "flake8 --max-line-length=88 --extend-ignore=E203,W503 ."
    run_test "bandit_security_scan" "bandit -r . -f json -o $TEST_RESULTS_DIR/bandit-report.json"
    run_test "safety_vulnerability_check" "safety check --json --output $TEST_RESULTS_DIR/safety-report.json"
}

# Test DAG integrity
run_dag_tests() {
    log "Running DAG integrity tests..."
    
    run_test "dag_loading" "python -c 'import sys; sys.path.append(\"dags\"); from airflow.models import DagBag; dagbag = DagBag(); exit(1 if dagbag.import_errors else 0)'"
    
    # Test individual DAGs
    for dag_file in dags/*.py; do
        if [ -f "$dag_file" ]; then
            dag_name=$(basename "$dag_file" .py)
            run_test "dag_syntax_$dag_name" "python -m py_compile $dag_file"
        fi
    done
}

# Test database operations
run_database_tests() {
    log "Running database tests..."
    
    # Test database connectivity (requires running PostgreSQL)
    run_test "postgres_connectivity" "python -c '
import psycopg2
try:
    conn = psycopg2.connect(host=\"localhost\", port=5432, user=\"postgres\", password=\"password\", database=\"postgres\")
    conn.close()
    print(\"Database connection successful\")
except Exception as e:
    print(f\"Database connection failed: {e}\")
    exit(1)
'" || warn "Database tests skipped - PostgreSQL not available"
}

# Test Soda Core configuration
run_soda_tests() {
    log "Running Soda Core tests..."
    
    if pip list | grep -q soda-core; then
        run_test "soda_config_validation" "soda test-connection -d postgres_db -c include/soda/configuration.yml"
        run_test "soda_checks_syntax" "soda scan -d postgres_db -c include/soda/configuration.yml include/soda/checks/videos.yml --dry-run"
    else
        warn "Soda Core not installed - skipping Soda tests"
    fi
}

# Test Docker configuration
run_docker_tests() {
    log "Running Docker tests..."
    
    if command -v docker > /dev/null 2>&1; then
        run_test "dockerfile_syntax" "docker build -t youtube-elt-test --dry-run ."
        run_test "docker_compose_config" "docker-compose config"
        
        # Test different compose files
        for compose_file in docker-compose*.yml; do
            if [ -f "$compose_file" ]; then
                compose_name=$(basename "$compose_file" .yml)
                run_test "compose_config_$compose_name" "docker-compose -f $compose_file config"
            fi
        done
    else
        warn "Docker not available - skipping Docker tests"
    fi
}

# Test API integration (mock)
run_api_tests() {
    log "Running API integration tests..."
    
    # Test API client creation (with mock)
    run_test "youtube_api_client" "python -c '
import sys
sys.path.append(\"include/scripts\")
try:
    from unittest.mock import patch
    with patch(\"os.getenv\", return_value=\"test_key\"):
        from youtube_elt import create_youtube_client
        print(\"API client creation test passed\")
except Exception as e:
    print(f\"API client test failed: {e}\")
    sys.exit(1)
'"
}

# Test file operations
run_file_tests() {
    log "Running file operation tests..."
    
    # Test directory structure
    run_test "directory_structure" "python -c '
import os
required_dirs = [\"dags\", \"include\", \"include/scripts\", \"include/soda\", \"tests\", \"data\"]
missing = [d for d in required_dirs if not os.path.exists(d)]
if missing:
    print(f\"Missing directories: {missing}\")
    exit(1)
print(\"All required directories exist\")
'"
    
    # Test required files
    run_test "required_files" "python -c '
import os
required_files = [\"requirements.txt\", \"Dockerfile\", \"docker-compose.yml\", \".env.example\"]
missing = [f for f in required_files if not os.path.exists(f)]
if missing:
    print(f\"Missing files: {missing}\")
    exit(1)
print(\"All required files exist\")
'"
}

# Test environment configuration
run_env_tests() {
    log "Running environment tests..."
    
    run_test "env_file_format" "python -c '
import os
if os.path.exists(\".env.example\"):
    with open(\".env.example\", \"r\") as f:
        content = f.read()
        required_vars = [\"YOUTUBE_API_KEY\", \"POSTGRES_HOST\", \"POSTGRES_PASSWORD\"]
        missing = [var for var in required_vars if var not in content]
        if missing:
            print(f\"Missing environment variables in .env.example: {missing}\")
            exit(1)
        print(\"Environment file format is correct\")
else:
    print(\"No .env.example file found\")
    exit(1)
'"
}

# Generate test report
generate_report() {
    log "Generating test report..."
    
    REPORT_FILE="$TEST_RESULTS_DIR/test-report.html"
    
    cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>YouTube ELT Pipeline Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .summary { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .passed { color: #27ae60; }
        .failed { color: #e74c3c; }
        .test-section { margin: 20px 0; }
        .test-logs { background-color: #f8f9fa; padding: 10px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>YouTube ELT Pipeline Test Report</h1>
        <p>Generated on: $(date)</p>
    </div>
    
    <div class="summary">
        <h2>Test Summary</h2>
        <p><strong>Total Tests:</strong> $TOTAL_TESTS</p>
        <p class="passed"><strong>Passed:</strong> $PASSED_TESTS</p>
        <p class="failed"><strong>Failed:</strong> $FAILED_TESTS</p>
        <p><strong>Success Rate:</strong> $(( TOTAL_TESTS > 0 ? (PASSED_TESTS * 100) / TOTAL_TESTS : 0 ))%</p>
    </div>
    
    <div class="test-section">
        <h2>Test Logs</h2>
EOF
    
    # Add individual test logs
    for log_file in "$TEST_RESULTS_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            test_name=$(basename "$log_file" .log)
            echo "<h3>$test_name</h3><div class='test-logs'><pre>$(cat "$log_file" | head -50)</pre></div>" >> "$REPORT_FILE"
        fi
    done
    
    echo "</div></body></html>" >> "$REPORT_FILE"
    
    log "Test report generated: $REPORT_FILE"
}

# Main test runner
main() {
    log "Starting YouTube ELT Pipeline comprehensive testing"
    
    setup_test_environment
    
    # Run all test suites
    run_unit_tests
    run_code_quality_tests
    run_dag_tests
    run_database_tests
    run_soda_tests
    run_docker_tests
    run_api_tests
    run_file_tests
    run_env_tests
    
    # Generate report
    generate_report
    
    # Print summary
    log "Test execution completed"
    log "Total Tests: $TOTAL_TESTS"
    log "Passed: $PASSED_TESTS"
    log "Failed: $FAILED_TESTS"
    
    if [ $FAILED_TESTS -gt 0 ]; then
        error "Some tests failed. Check logs in $TEST_RESULTS_DIR"
        exit 1
    else
        log "All tests passed successfully!"
        exit 0
    fi
}

# Print usage
usage() {
    echo "Usage: $0 [options]"
    echo "  -h, --help     Show this help message"
    echo "  --unit         Run only unit tests"
    echo "  --quality      Run only code quality tests"
    echo "  --dag          Run only DAG tests"
    echo "  --docker       Run only Docker tests"
    echo ""
    echo "Examples:"
    echo "  $0             # Run all tests"
    echo "  $0 --unit      # Run only unit tests"
    echo "  $0 --quality   # Run only code quality tests"
}

# Handle command line arguments
case "${1:-all}" in
    -h|--help)
        usage
        exit 0
        ;;
    --unit)
        setup_test_environment
        run_unit_tests
        generate_report
        ;;
    --quality)
        setup_test_environment  
        run_code_quality_tests
        generate_report
        ;;
    --dag)
        setup_test_environment
        run_dag_tests
        generate_report
        ;;
    --docker)
        setup_test_environment
        run_docker_tests
        generate_report
        ;;
    all|*)
        main
        ;;
esac
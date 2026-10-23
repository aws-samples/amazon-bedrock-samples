#!/bin/bash

# BDA Blueprint Optimizer Test Runner
# This script runs the complete test suite with various options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_COVERAGE=true
PARALLEL=false
VERBOSE=false
HTML_REPORT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            shift
            ;;
        --no-coverage)
            RUN_COVERAGE=false
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit-only       Run only unit tests"
            echo "  --integration-only Run only integration tests"
            echo "  --no-coverage     Skip coverage reporting"
            echo "  --parallel        Run tests in parallel"
            echo "  --verbose         Verbose output"
            echo "  --html            Generate HTML report"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest is not installed. Please install test requirements:"
    echo "pip install -r requirements-test.txt"
    exit 1
fi

# Create test results directory
mkdir -p test-results

print_status "Starting BDA Blueprint Optimizer Test Suite"
echo "=============================================="

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

if [ "$RUN_COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-report=xml:test-results/coverage.xml"
fi

if [ "$HTML_REPORT" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --html=test-results/report.html --self-contained-html"
fi

# Add JUnit XML for CI/CD
PYTEST_CMD="$PYTEST_CMD --junitxml=test-results/junit.xml"

# Run tests based on selection
if [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = true ]; then
    print_status "Running all tests..."
    $PYTEST_CMD tests/
elif [ "$RUN_UNIT" = true ]; then
    print_status "Running unit tests only..."
    $PYTEST_CMD tests/ -m "not integration"
elif [ "$RUN_INTEGRATION" = true ]; then
    print_status "Running integration tests only..."
    $PYTEST_CMD tests/ -m "integration"
fi

# Check test results
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Generate coverage badge if coverage was run
if [ "$RUN_COVERAGE" = true ] && [ $TEST_EXIT_CODE -eq 0 ]; then
    if command -v coverage-badge &> /dev/null; then
        print_status "Generating coverage badge..."
        coverage-badge -o test-results/coverage-badge.svg
        print_success "Coverage badge generated: test-results/coverage-badge.svg"
    fi
fi

# Display test results summary
echo ""
echo "=============================================="
print_status "Test Results Summary"
echo "=============================================="

if [ -f "test-results/junit.xml" ]; then
    # Parse JUnit XML for summary (basic parsing)
    if command -v xmllint &> /dev/null; then
        TOTAL_TESTS=$(xmllint --xpath "string(//testsuite/@tests)" test-results/junit.xml 2>/dev/null || echo "N/A")
        FAILED_TESTS=$(xmllint --xpath "string(//testsuite/@failures)" test-results/junit.xml 2>/dev/null || echo "0")
        ERROR_TESTS=$(xmllint --xpath "string(//testsuite/@errors)" test-results/junit.xml 2>/dev/null || echo "0")
        
        echo "Total Tests: $TOTAL_TESTS"
        echo "Failed Tests: $FAILED_TESTS"
        echo "Error Tests: $ERROR_TESTS"
    fi
fi

if [ "$RUN_COVERAGE" = true ] && [ -f "test-results/coverage.xml" ]; then
    if command -v xmllint &> /dev/null; then
        COVERAGE=$(xmllint --xpath "string(//coverage/@line-rate)" test-results/coverage.xml 2>/dev/null || echo "N/A")
        if [ "$COVERAGE" != "N/A" ]; then
            COVERAGE_PERCENT=$(echo "$COVERAGE * 100" | bc -l 2>/dev/null | cut -d. -f1 2>/dev/null || echo "N/A")
            echo "Code Coverage: ${COVERAGE_PERCENT}%"
        fi
    fi
fi

echo "=============================================="

# Display available reports
if [ -f "test-results/report.html" ]; then
    print_status "HTML report available: test-results/report.html"
fi

if [ -f "test-results/coverage.xml" ]; then
    print_status "Coverage report available: test-results/coverage.xml"
fi

# Exit with the same code as pytest
exit $TEST_EXIT_CODE

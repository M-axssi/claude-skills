#!/bin/bash
# Environment verification script
# Verifies that the Docker environment is properly set up

set -e

PROJECT_TYPE="$1"
CONTAINER_NAME="${2:-academic-project-test}"

echo "===== Environment Verification ====="
echo "Project Type: $PROJECT_TYPE"
echo ""

# Function to run command in container
run_in_container() {
    docker exec "$CONTAINER_NAME" bash -c "$1"
}

# Verify Python environment
verify_python() {
    echo "Verifying Python environment..."

    # Check Python version
    echo -n "Python version: "
    run_in_container "python --version" || echo "Warning: Python not found"

    # Check pip
    echo -n "pip version: "
    run_in_container "pip --version" || echo "Warning: pip not found"

    # List installed packages
    echo ""
    echo "Installed packages:"
    run_in_container "pip list" || echo "Warning: Cannot list packages"

    # Try importing common packages
    echo ""
    echo "Testing imports..."
    run_in_container "python -c 'import sys; print(\"sys module OK\")'" || echo "Warning: Import test failed"
}

# Verify C++ environment
verify_cpp() {
    echo "Verifying C++ environment..."

    # Check compiler
    echo -n "GCC version: "
    run_in_container "gcc --version | head -n1" || echo "Warning: GCC not found"

    echo -n "G++ version: "
    run_in_container "g++ --version | head -n1" || echo "Warning: G++ not found"

    # Check cmake
    echo -n "CMake version: "
    run_in_container "cmake --version | head -n1" || echo "Warning: CMake not found"

    # Check make
    echo -n "Make version: "
    run_in_container "make --version | head -n1" || echo "Warning: Make not found"

    # List compiled binaries
    echo ""
    echo "Compiled binaries:"
    run_in_container "find /app -type f -executable 2>/dev/null | head -20" || echo "Warning: No binaries found"
}

# Verify Node.js environment
verify_nodejs() {
    echo "Verifying Node.js environment..."

    # Check Node version
    echo -n "Node version: "
    run_in_container "node --version" || echo "Warning: Node not found"

    # Check npm
    echo -n "npm version: "
    run_in_container "npm --version" || echo "Warning: npm not found"

    # List installed packages
    echo ""
    echo "Installed packages:"
    run_in_container "npm list --depth=0" || echo "Warning: Cannot list packages"
}

# Main verification logic
main() {
    # Check if container is running
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        echo "Error: Container '$CONTAINER_NAME' is not running" >&2
        echo "Please start the container first with:" >&2
        echo "  docker run -d --name $CONTAINER_NAME academic-project:latest tail -f /dev/null" >&2
        exit 1
    fi

    case "$PROJECT_TYPE" in
        python)
            verify_python
            ;;
        cpp)
            verify_cpp
            ;;
        nodejs)
            verify_nodejs
            ;;
        *)
            echo "Error: Unsupported project type: $PROJECT_TYPE" >&2
            exit 1
            ;;
    esac

    echo ""
    echo "===== Verification Complete ====="
}

# Check arguments
if [ -z "$PROJECT_TYPE" ]; then
    echo "Usage: $0 <project-type> [container-name]" >&2
    echo "Supported types: python, cpp, nodejs" >&2
    exit 1
fi

main "$@"

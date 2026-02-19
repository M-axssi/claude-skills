#!/bin/bash
# Project type detection script
# Detects Python, C++, and Node.js projects
# Priority: Python > C++ > Node.js

set -e

PROJECT_DIR="${1:-.}"

# Function to check if a file exists in the project
file_exists() {
    [ -f "$PROJECT_DIR/$1" ]
}

# Detect Python project
detect_python() {
    if file_exists "requirements.txt" || \
       file_exists "pyproject.toml" || \
       file_exists "setup.py" || \
       file_exists "environment.yml" || \
       file_exists "Pipfile"; then
        echo "python"
        return 0
    fi
    return 1
}

# Detect C/C++ project
detect_cpp() {
    if file_exists "CMakeLists.txt" || \
       file_exists "Makefile" || \
       file_exists "makefile" || \
       file_exists "conanfile.txt" || \
       file_exists "vcpkg.json"; then
        echo "cpp"
        return 0
    fi
    return 1
}

# Detect Node.js project
detect_nodejs() {
    if file_exists "package.json"; then
        echo "nodejs"
        return 0
    fi
    return 1
}

# Main detection logic with priority
main() {
    # Priority 1: Python
    if detect_python; then
        exit 0
    fi

    # Priority 2: C++
    if detect_cpp; then
        exit 0
    fi

    # Priority 3: Node.js
    if detect_nodejs; then
        exit 0
    fi

    # Unknown project type
    echo "unknown"
    exit 1
}

main "$@"

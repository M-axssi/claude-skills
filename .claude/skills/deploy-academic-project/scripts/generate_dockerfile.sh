#!/bin/bash
# Dockerfile generation script
# Generates optimized Dockerfile based on project type

set -e

PROJECT_TYPE="$1"
PROJECT_DIR="${2:-.}"
OUTPUT_FILE="${3:-Dockerfile}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(dirname "$SCRIPT_DIR")/templates"

# Function to copy template
generate_from_template() {
    local template_name="$1"
    local template_path="$TEMPLATE_DIR/Dockerfile.$template_name"

    if [ ! -f "$template_path" ]; then
        echo "Error: Template not found: $template_path" >&2
        exit 1
    fi

    # Copy template to output file
    cp "$template_path" "$PROJECT_DIR/$OUTPUT_FILE"

    # Also copy corresponding .dockerignore if exists
    local dockerignore_path="$TEMPLATE_DIR/.dockerignore.$template_name"
    if [ -f "$dockerignore_path" ]; then
        cp "$dockerignore_path" "$PROJECT_DIR/.dockerignore"
    fi
}

# Main generation logic
main() {
    case "$PROJECT_TYPE" in
        python)
            echo "Generating Python Dockerfile..."
            generate_from_template "python"
            ;;
        cpp)
            echo "Generating C++ Dockerfile..."
            generate_from_template "cpp"
            ;;
        nodejs)
            echo "Generating Node.js Dockerfile..."
            generate_from_template "nodejs"
            ;;
        *)
            echo "Error: Unsupported project type: $PROJECT_TYPE" >&2
            exit 1
            ;;
    esac

    echo "Dockerfile generated successfully: $PROJECT_DIR/$OUTPUT_FILE"
}

# Check arguments
if [ -z "$PROJECT_TYPE" ]; then
    echo "Usage: $0 <project-type> [project-dir] [output-file]" >&2
    echo "Supported types: python, cpp, nodejs" >&2
    exit 1
fi

main "$@"

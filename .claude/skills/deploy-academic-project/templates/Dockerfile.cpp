# Multi-stage Dockerfile for C/C++ projects
# Supports CMake and Makefile-based builds

# ===== BUILD STAGE =====
FROM gcc:latest AS builder

WORKDIR /app

# Install build tools and common dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    make \
    g++ \
    git \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy build configuration files (layer caching optimization)
COPY CMakeLists.txt* Makefile* makefile* conanfile.txt* vcpkg.json* ./

# Copy source code directories
COPY src* ./src/ 2>/dev/null || true
COPY include* ./include/ 2>/dev/null || true
COPY lib* ./lib/ 2>/dev/null || true
COPY cmake* ./cmake/ 2>/dev/null || true

# Copy everything else (fallback)
COPY . .

# Build the project
RUN if [ -f "CMakeLists.txt" ]; then \
        echo "Building with CMake..." && \
        mkdir -p build && \
        cd build && \
        cmake .. && \
        make -j$(nproc); \
    elif [ -f "Makefile" ] || [ -f "makefile" ]; then \
        echo "Building with Make..." && \
        make -j$(nproc); \
    else \
        echo "No build system detected. Trying to compile all .cpp files..." && \
        find . -name "*.cpp" -type f | while read file; do \
            g++ -o "$(basename "$file" .cpp).out" "$file" 2>/dev/null || true; \
        done; \
    fi

# ===== RUNTIME STAGE =====
FROM ubuntu:22.04

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled binaries from builder
COPY --from=builder /app/build/ ./build/ 2>/dev/null || true
COPY --from=builder /app/*.out ./ 2>/dev/null || true
COPY --from=builder /app/bin/ ./bin/ 2>/dev/null || true

# Copy any shared libraries or data files
COPY --from=builder /app/lib/ ./lib/ 2>/dev/null || true
COPY --from=builder /app/data/ ./data/ 2>/dev/null || true

# Update library path
ENV LD_LIBRARY_PATH=/app/lib:$LD_LIBRARY_PATH
ENV PATH=/app/build:/app/bin:/app:$PATH

# Default command: bash (for interactive use)
CMD ["/bin/bash"]

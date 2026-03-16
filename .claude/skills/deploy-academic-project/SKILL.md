---
name: deploy-academic-project
description: Automatically clone, analyze, and deploy academic project environments from GitHub URLs or local paths. Supports Python, C++, and Node.js projects with Docker containerization. Use when setting up research code, reproducing academic work, or deploying computational environments.
argument-hint: [github-url-or-path]
disable-model-invocation: false
context: fork
agent: Explore
allowed-tools: Bash(*), Read, Write, Glob, Grep
---

# Academic Project Auto-Deployment

Automatically setup and containerize academic projects with optimized Docker environments.

## What this skill does

1. **Clone repository** (if URL provided) or use local directory
2. **Detect project type** - Python, C++, Node.js
3. **Generate optimized Dockerfile** - Multi-stage build with caching
4. **Build Docker image** - Isolated, reproducible environment
5. **Verify installation** - Test imports, binaries, packages
6. **Provide usage instructions** - Docker commands and next steps

## Supported project types

- **Python** (Priority HIGH): requirements.txt, pyproject.toml, environment.yml, setup.py
- **C/C++** (Priority HIGH): CMakeLists.txt, Makefile, conanfile.txt
- **Node.js** (Priority MEDIUM): package.json

## Usage

Invoke this skill with a GitHub URL or local directory path:

```bash
/deploy-academic-project https://github.com/username/research-project
/deploy-academic-project /path/to/local/project
```

---

## Implementation Workflow

### Step 1: Parse Input and Setup

```bash
INPUT="$ARGUMENTS"

# Parse optional target directory from arguments (second argument)
# Usage: /deploy-academic-project <url-or-path> [target-dir]
URL_OR_PATH=$(echo "$INPUT" | awk '{print $1}')
TARGET_PARENT=$(echo "$INPUT" | awk '{print $2}')

# Determine if input is URL or local path
if [[ "$URL_OR_PATH" =~ ^https?:// ]]; then
    REPO_NAME=$(basename "$URL_OR_PATH" .git)
    if [ -n "$TARGET_PARENT" ]; then
        PROJECT_DIR="$TARGET_PARENT/$REPO_NAME"
    else
        PROJECT_DIR="$(pwd)/$REPO_NAME"
    fi
    # IMPORTANT: Always use --recursive to fetch git submodules (e.g. libigl, Eigen)
    # Without --recursive, submodule directories will be empty and build will fail silently
    echo "Cloning repository: $URL_OR_PATH -> $PROJECT_DIR"
    git clone --recursive "$URL_OR_PATH" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
elif [ -d "$URL_OR_PATH" ]; then
    PROJECT_DIR="$(cd "$URL_OR_PATH" && pwd)"
    echo "Using local directory: $PROJECT_DIR"
    cd "$PROJECT_DIR"
    # Initialize submodules if present in local repo
    if [ -f ".gitmodules" ]; then
        echo "Found .gitmodules - initializing submodules..."
        git submodule update --init --recursive
    fi
else
    echo "Error: Invalid input. Provide a GitHub URL or local directory path."
    exit 1
fi

WORK_DIR="$PROJECT_DIR"
```

### Step 2: Detect Project Type

```bash
# Get the absolute path to the skills directory
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect project type using our script
PROJECT_TYPE=$("$SKILL_DIR/scripts/detect_project.sh" .)

if [ "$PROJECT_TYPE" == "unknown" ]; then
    echo "Error: Could not detect project type."
    echo "Supported types: Python, C++, Node.js"
    echo "Please ensure your project has one of these files:"
    echo "  - Python: requirements.txt, pyproject.toml, environment.yml"
    echo "  - C++: CMakeLists.txt, Makefile"
    echo "  - Node.js: package.json"
    exit 1
fi

echo "Detected project type: $PROJECT_TYPE"
```

### Step 3: Analyze Project Structure

Read README and identify key files:

```bash
# Find and read README
README=$(find . -maxdepth 1 -iname "README*" -type f | head -1)
if [ -n "$README" ]; then
    echo "Found README: $README"
    echo "Reading documentation..."
    head -50 "$README"
fi

# Identify main entry points
case "$PROJECT_TYPE" in
    python)
        echo "Looking for Python entry points..."
        find . -name "main.py" -o -name "app.py" -o -name "run.py" -o -name "__main__.py" | head -5
        ;;
    cpp)
        echo "Looking for C++ source files..."
        find . -name "main.cpp" -o -name "main.c" -o -name "*.cpp" | head -5
        ;;
    nodejs)
        echo "Looking for Node.js entry points..."
        cat package.json | grep -E '"main"|"start"'
        ;;
esac
```

### Step 4: Generate Dockerfile

```bash
echo "Generating Dockerfile for $PROJECT_TYPE project..."

# Use our generation script
"$SKILL_DIR/scripts/generate_dockerfile.sh" "$PROJECT_TYPE" .

if [ ! -f "Dockerfile" ]; then
    echo "Error: Dockerfile generation failed"
    exit 1
fi

echo "Dockerfile generated successfully"
echo "---"
cat Dockerfile
echo "---"
```

### Step 5: Build Docker Image

```bash
IMAGE_NAME="academic-project-$(basename "$WORK_DIR")"

echo "Building Docker image: $IMAGE_NAME"
echo "This may take several minutes depending on dependencies..."

# IMPORTANT: For C++ projects with large dependencies (e.g. libigl, OpenCV),
# use DOCKER_BUILDKIT=0 (legacy builder).
#
# Why: BuildKit streams build output over a gRPC connection that can timeout
# during long compilations, producing:
#   "rpc error: code = Unavailable desc = error reading from server: EOF"
# The legacy builder commits each completed RUN step as a cached layer
# immediately, so interrupted builds resume from the last successful layer.
#
# Also: --progress=plain is NOT compatible with DOCKER_BUILDKIT=0.
# Only use --progress=plain when BuildKit is enabled.

if [ "$PROJECT_TYPE" = "cpp" ]; then
    echo "C++ project detected: using legacy builder (DOCKER_BUILDKIT=0) to avoid timeout"
    DOCKER_BUILDKIT=0 docker build -t "$IMAGE_NAME:latest" .
else
    DOCKER_BUILDKIT=1 docker build -t "$IMAGE_NAME:latest" .
fi

if [ $? -ne 0 ]; then
    echo "Error: Docker build failed"
    echo "Please check the build logs above for details"
    exit 1
fi

echo "Docker image built successfully: $IMAGE_NAME:latest"
```

### Step 6: Verify Environment

```bash
echo "Verifying environment..."

# Start a temporary container for testing
CONTAINER_NAME="test-$IMAGE_NAME"
docker run -d --name "$CONTAINER_NAME" "$IMAGE_NAME:latest" tail -f /dev/null

# Wait for container to be ready
sleep 2

# Run verification script
"$SKILL_DIR/scripts/verify_env.sh" "$PROJECT_TYPE" "$CONTAINER_NAME"

# Cleanup test container
docker rm -f "$CONTAINER_NAME"
```

### Step 7: Generate Usage Instructions

```bash
echo ""
echo "========================================="
echo "   DEPLOYMENT SUCCESSFUL"
echo "========================================="
echo ""
echo "Docker image: $IMAGE_NAME:latest"
echo ""
echo "RECOMMENDED: Mount source code and results directory for full sync:"
echo "  Source code changes take effect immediately (no rebuild needed)"
echo "  Results are saved directly to your local project directory"
echo ""
echo "To run interactively with full sync:"
echo "  docker run -it --rm --gpus all -v $PROJECT_DIR:/app $IMAGE_NAME:latest"
echo ""
echo "NOTE: -v $PROJECT_DIR:/app mounts your entire project into the container."
echo "      Code edits on host are immediately visible inside the container."
echo "      All output files written to /app (e.g. /app/results) appear on host."
echo ""

case "$PROJECT_TYPE" in
    python)
        echo "To run a Python script with full sync:"
        echo "  docker run --rm --gpus all -v $PROJECT_DIR:/app $IMAGE_NAME:latest python your_script.py"
        echo ""
        echo "To start Jupyter Notebook:"
        echo "  docker run -it --rm --gpus all -p 8888:8888 -v $PROJECT_DIR:/app $IMAGE_NAME:latest jupyter notebook --ip=0.0.0.0 --allow-root"
        ;;
    cpp)
        echo "Compiled binaries are in: /app/build/ or per-example subdirectories"
        echo ""
        # Check if the project uses OpenGL/GLFW (needs display)
        if grep -r "opengl\|glfw\|Viewer" . --include="*.cpp" -l -q 2>/dev/null; then
            echo "OpenGL/GUI detected in this project."
            echo ""
            echo "RECOMMENDED: X11 forwarding via XLaunch (VcXsrv) — lower latency than noVNC"
            echo ""
            echo "  Linux:"
            echo "    xhost +local:docker"
            echo "    docker run -d -e DISPLAY=\$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \\"
            echo "      $IMAGE_NAME:latest tail -f /dev/null"
            echo "    docker exec -it <container_id> bash"
            echo ""
            echo "  Windows (requires VcXsrv with 'Disable access control' checked):"
            echo "    1. Start XLaunch: Multiple Windows -> Start no client -> Disable access control"
            echo "    2. Run container in background:"
            echo "       docker run -d -e DISPLAY=host.docker.internal:0.0 \\"
            echo "         $IMAGE_NAME:latest tail -f /dev/null"
            echo "    3. Enter shell via Windows Terminal (NOT Git Bash/mintty):"
            echo "       docker exec -it <container_id> bash"
            echo "    4. Verify DISPLAY: echo \$DISPLAY  (should be host.docker.internal:0.0)"
            echo "       If DISPLAY is wrong: export DISPLAY=host.docker.internal:0.0"
            echo ""
            echo "FALLBACK: noVNC (browser-based, no extra software, but higher latency):"
            echo "  docker run -d -p 6080:6080 $IMAGE_NAME:latest"
            echo "  Then open: http://localhost:6080/vnc.html"
        else
            echo "To run your compiled program:"
            echo "  docker run -it --rm $IMAGE_NAME:latest ./build/your_program"
        fi
        ;;
    nodejs)
        echo "To run your Node.js application:"
        echo "  docker run -it --rm $IMAGE_NAME:latest npm start"
        echo ""
        echo "To run specific script:"
        echo "  docker run -it --rm $IMAGE_NAME:latest npm run your_script"
        ;;
esac

echo ""
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test the environment with: docker run -it --rm $IMAGE_NAME:latest"
echo "2. Review the Dockerfile at: $WORK_DIR/Dockerfile"
echo "3. Customize if needed and rebuild"
echo ""
echo "Project location: $WORK_DIR"
echo "========================================="
```

---

## Cross-Platform Compatibility

This skill is designed to work on both **Windows** and **Linux**:

- **Shell**: Uses bash (Git Bash on Windows, native bash on Linux)
- **Paths**: Uses Unix-style paths (`/`) - Docker handles conversion
- **Line endings**: `.gitattributes` ensures LF line endings for scripts
- **Docker**: Same commands work on Docker Desktop (Windows) and Docker Engine (Linux)

## Troubleshooting

### [C++] Git submodules are empty after clone

**Symptom**: CMake fails with `Could not find LIBIGL` or similar; `libigl/` or other dependency directories are empty.

**Cause**: Repository was cloned without `--recursive`, so submodules were not fetched.

**Fix**:
```bash
# Option A: Re-clone with --recursive (preferred)
git clone --recursive https://github.com/...

# Option B: Initialize submodules in existing clone
git submodule update --init --recursive
```

**In Dockerfile**: Always use `git clone --recursive` for C++ projects.

---

### [C++] Docker build fails with "rpc error: EOF" or connection reset

**Symptom**: Build stops mid-compilation with:
```
ERROR: failed to build: failed to receive status: rpc error: code = Unavailable desc = error reading from server: EOF
```

**Cause**: BuildKit streams output over a gRPC connection. Long C++ compilations (e.g. libigl header-only library) exceed the connection timeout.

**Fix**: Disable BuildKit for C++ projects:
```bash
DOCKER_BUILDKIT=0 docker build -t myimage:latest .
```

The legacy builder commits each completed `RUN` step as a cached Docker layer immediately. If the build is interrupted again, it will resume from the last successful step — not from scratch.

---

### [C++] `--progress=plain` flag not recognized

**Symptom**:
```
unknown flag: --progress
```

**Cause**: `--progress` is a BuildKit-only flag and is not supported by the legacy builder (`DOCKER_BUILDKIT=0`).

**Fix**: Remove `--progress=plain` when using `DOCKER_BUILDKIT=0`. Use them separately:
```bash
# Legacy builder (no --progress):
DOCKER_BUILDKIT=0 docker build -t myimage .

# OR BuildKit with verbose output (no timeout issues for short builds):
DOCKER_BUILDKIT=1 docker build --progress=plain -t myimage .
```

---

### [C++/OpenGL] "cannot open display" when running GUI programs

**Symptom**: Program starts but crashes with `cannot open display :0` or similar.

**Cause**: Docker containers have no display by default. OpenGL/GLFW requires a display server.

**Fix A (Recommended): noVNC** — browser-based, no extra software on host:
```dockerfile
# Add to Dockerfile:
RUN apt-get install -y xvfb x11vnc novnc websockify openbox supervisor
```
Then expose port 6080 and open `http://localhost:6080/vnc.html`.

**Fix B: X11 forwarding on Linux**:
```bash
xhost +local:docker
docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix myimage
```

**Fix C: X11 forwarding on Windows** (requires VcXsrv):
1. Install and start VcXsrv with "Disable access control" checked
2. `docker run -it --rm -e DISPLAY=HOST_IP:0.0 myimage`

---

### [Windows] "stdin is not a tty" when entering container shell

**Symptom**: `docker run -it` or `winpty docker run -it` fails with:
```
stdin is not a tty
```
or
```
the input device is not a TTY. If you are using mintty, try prefixing the command with 'winpty'
```

**Cause**: Git Bash / mintty does not provide a real TTY. `winpty` only works when called **directly** in a terminal, not from inside a bash script.

**Fix**: Use a two-step approach — start the container detached, then exec into it from **Windows Terminal** (not Git Bash):
```bash
# Step 1: Start container in background (no TTY needed)
docker run -d -e DISPLAY=host.docker.internal:0.0 myimage:latest tail -f /dev/null

# Step 2: Open Windows Terminal and exec in (Windows Terminal has real TTY)
docker exec -it <container_id> bash
```

**Note**: Docker Desktop's built-in `>_` terminal also works, but lacks readline auto-completion. Windows Terminal is preferred for a full shell experience.

---

### [Windows/X11] VcXsrv shows "0 clients" — GUI windows don't appear

**Symptom**: Container runs, programs launch without error, but no window appears on the host. VcXsrv tray shows "0 clients connected".

**Cause**: Windows Firewall is blocking port 6000 (X11) for VcXsrv, especially on virtual/Docker networks classified as "Public".

**Diagnosis** (run inside container):
```bash
bash -c 'echo >/dev/tcp/host.docker.internal/6000' && echo "OPEN" || echo "BLOCKED"
```

**Fix**:
```powershell
# Run in PowerShell (Administrator)
netsh advfirewall firewall add rule name="VcXsrv" dir=in action=allow `
  program="C:\Program Files\VcXsrv\vcxsrv.exe" enable=yes
```
Or: Windows Defender Firewall → Allow an app → VcXsrv → check both Private and Public.

---

### [Windows/X11] DISPLAY env var is wrong inside container

**Symptom**: `echo $DISPLAY` inside container returns `:1` (or another local value) instead of `host.docker.internal:0.0`, causing X11 programs to fail.

**Cause**: If the Dockerfile contains `ENV DISPLAY=:1` (e.g. from noVNC setup), it becomes the default. The `-e` flag overrides it at runtime, but only if the container was started with `-e DISPLAY=host.docker.internal:0.0`.

**Fix**: Verify and override manually in the container shell:
```bash
echo $DISPLAY                          # check current value
export DISPLAY=host.docker.internal:0.0  # override if wrong
```
Or ensure container is always started with the explicit flag:
```bash
docker run -d -e DISPLAY=host.docker.internal:0.0 myimage:latest tail -f /dev/null
```

---

### [Windows] Container shell has no auto-completion or history

**Symptom**: Tab completion, arrow-key history, and readline shortcuts don't work after entering container shell.

**Cause**: Docker Desktop's built-in terminal is a web-based xterm.js with limited readline support. Also, `bash-completion` may not be sourced by default in non-login shells.

**Fix A (Preferred)**: Use **Windows Terminal** instead of Docker Desktop's terminal:
```powershell
docker exec -it <container_id> bash
```
Windows Terminal provides full readline/TTY support.

**Fix B**: Enable bash-completion inside the container:
```bash
source /etc/bash_completion        # enable for current session
echo 'source /etc/bash_completion 2>/dev/null' >> ~/.bashrc  # persist
```

---

### Build fails due to missing system dependencies

Check the Dockerfile and add system dependencies:

```dockerfile
RUN apt-get update && apt-get install -y \
    your-missing-package \
    && rm -rf /var/lib/apt/lists/*
```

### Python packages fail to install

- For packages requiring compilation: Already included in builder stage
- For Conda packages: Use `environment.yml` instead of `requirements.txt`

### [CUDA] PyTorch CUDA extension build fails with "No module named 'torch'"

pip's build isolation creates a clean env without torch. Fix:
```bash
pip install --no-build-isolation /path/to/extension
```
Applies to: nvdiffrast, diffoctreerast, diff-gaussian-rasterization, and any `setup.py` that `import torch`.

### [CUDA] conda install torch fails with "undefined symbol: iJIT_NotifyEvent"

Intel MKL version conflict. Use pip instead:
```bash
pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118
```

### [CUDA] Multiple packages install conflicting nvidia-*-cuXX versions

torch, flash-attn, xformers each pull in `nvidia-*-cu11/12` packages at different versions, causing symbol errors like `undefined symbol: __nvJitLinkAddData_12_1`. Fix: pin all packages to the same CUDA version family (all cu118 or all cu121), and reinstall conflicting packages explicitly.

### [CUDA] setup.sh case matching fails silently for PyTorch version strings

`$PYTORCH_VERSION` may be `2.4.0+cu118` (with suffix), but case branches match only `2.4.0`. Check the actual string before running setup.sh:
```bash
python -c "import torch; print(torch.__version__)"
```

### [CUDA] wget-downloaded wheel rejected by pip as invalid

pip validates wheel filenames — they must follow `name-ver-pytag-abitag-platformtag.whl`. Downloading with `-O short-name.whl` strips required tags. Fix: preserve the original filename or rename to the full format before `pip install`.

### C++ compilation fails

- Ensure source code is in `src/` or `include/` directories
- Check that CMakeLists.txt or Makefile is at project root
- Add required libraries to Dockerfile

### Container data is lost after removal

Use volume mounts to persist output:
```bash
docker run -it --rm -v $(pwd)/output:/app/output myimage
```
Data written to `/app/output` inside the container is saved to `./output` on the host.

## Features

✅ **Automatic language detection** - Python, C++, Node.js
✅ **Multi-stage Docker builds** - Minimal final image size
✅ **Layer caching optimization** - Fast rebuilds
✅ **Cross-platform support** - Windows & Linux
✅ **Scientific computing ready** - NumPy, SciPy compatible
✅ **Multiple dependency formats** - pip, conda, cmake, npm
✅ **Environment verification** - Automated testing
✅ **Production-ready** - Debian-based stable images

## Limitations

- **GPU support**: Not included by default (can be added manually with nvidia-docker)
- **Large datasets**: Should be mounted as volumes, not copied into image
- **Proprietary dependencies**: Cannot download licensed software automatically
- **Interactive setup**: Cannot handle projects requiring manual configuration steps

## Future Enhancements

- Add R and Julia support
- Integrate with Jupyter for interactive notebooks
- Support for GPU/CUDA environments
- Automatic dataset download from Zenodo/Figshare
- CI/CD integration templates

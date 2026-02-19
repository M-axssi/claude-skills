# C/C++ .dockerignore

# Version control
.git
.gitignore
.gitattributes

# Build directories
build/
Build/
BUILD/
out/
bin/
obj/
Debug/
Release/

# Compiled Object files
*.o
*.obj
*.ko
*.elf
*.slo
*.lo

# Compiled Dynamic libraries
*.so
*.so.*
*.dylib
*.dll

# Compiled Static libraries
*.a
*.lib
*.la

# Executables
*.exe
*.out
*.app
*.i*86
*.x86_64
*.hex

# CMake
CMakeCache.txt
CMakeFiles/
cmake_install.cmake
cmake-build-*/
*.cmake
!CMakeLists.txt

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
*.cbp
*.depend
*.layout

# Documentation
docs/
*.md
README*
LICENSE
CONTRIBUTING*
doxygen/

# CI/CD
.github/
.gitlab-ci.yml
.travis.yml

# Testing
test/
tests/
Testing/
*.test
*.testresult

# Logs
*.log
logs/

# Conan
conan.lock
conanbuildinfo.*
conaninfo.txt

# vcpkg
vcpkg_installed/
.vcpkg/

# Data files
data/
datasets/
*.dat
*.bin

# Temporary files
tmp/
temp/
*.tmp
*.temp
*.bak
*.swp

# Package manager
node_modules/
.npm/

@echo off
setlocal

set CASCLIB_REPO=https://github.com/ladislav-zezula/CascLib.git
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set BUILD_DIR=%TEMP%\casclib-build-%RANDOM%
set OUTPUT_DIR=%PROJECT_DIR%\src\d2rhelper

echo === Building CascLib shared library (Windows native) ===
echo Build dir: %BUILD_DIR%
echo Output dir: %OUTPUT_DIR%

git clone --depth 1 %CASCLIB_REPO% %BUILD_DIR%

cd /d %BUILD_DIR%

cmake -DCMAKE_BUILD_TYPE=Release -B build
if %errorlevel% neq 0 (
    echo cmake configure failed
    cd /d %PROJECT_DIR%
    rmdir /s /q %BUILD_DIR%
    exit /b 1
)

cmake --build build --config Release
if %errorlevel% neq 0 (
    echo cmake build failed
    cd /d %PROJECT_DIR%
    rmdir /s /q %BUILD_DIR%
    exit /b 1
)

if exist build\Release\CascLib.dll (
    copy /y build\Release\CascLib.dll %OUTPUT_DIR%\
) else if exist build\CascLib.dll (
    copy /y build\CascLib.dll %OUTPUT_DIR%\
) else if exist build\libCascLib.dll (
    copy /y build\libCascLib.dll %OUTPUT_DIR%\Casclib.dll
)

cd /d %PROJECT_DIR%
rmdir /s /q %BUILD_DIR%
echo === Build complete ===
echo Built: %OUTPUT_DIR%\Casclib.dll

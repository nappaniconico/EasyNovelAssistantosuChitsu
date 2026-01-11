@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem =========================================================
rem  Settings
rem =========================================================
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "TEMP_GIT=%SCRIPT_DIR%\temp_git"
set "PORTABLE_GIT_EXE=PortableGit-2.52.0-64-bit.7z.exe"
set "PORTABLE_GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.52.0.windows.1/PortableGit-2.52.0-64-bit.7z.exe"
set "PORTABLE_GIT_HOME=%TEMP_GIT%\PortableGit"
set "GIT_CMD=%PORTABLE_GIT_HOME%\cmd\git.exe"

set "REPO_URL=https://github.com/nappaniconico/EasyNovelAssistantosuChitsu.git"
set "REPO_DIR=%SCRIPT_DIR%\EasyNovelAssistantosuChitsu"

echo.
echo === Start setup ===
echo Script dir: "%SCRIPT_DIR%"

rem =========================================================
rem  1) Prepare temp_git and download PortableGit
rem =========================================================
if not exist "%TEMP_GIT%" (
  echo [1/7] Creating "%TEMP_GIT%"
  mkdir "%TEMP_GIT%"
)

if not exist "%TEMP_GIT%\%PORTABLE_GIT_EXE%" (
  echo [1/7] Downloading PortableGit
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "Invoke-WebRequest '%PORTABLE_GIT_URL%' -OutFile '%TEMP_GIT%\%PORTABLE_GIT_EXE%'" || (
      echo ERROR: Failed to download PortableGit.
      exit /b 1
    )
) else (
  echo [1/7] PortableGit already downloaded.
)

rem =========================================================
rem  2) Extract PortableGit
rem =========================================================
if not exist "%GIT_CMD%" (
  echo [2/7] Extracting PortableGit
  if exist "%PORTABLE_GIT_HOME%" rmdir /s /q "%PORTABLE_GIT_HOME%"
  mkdir "%PORTABLE_GIT_HOME%"

  "%TEMP_GIT%\%PORTABLE_GIT_EXE%" -y -o"%PORTABLE_GIT_HOME%" >nul || (
    echo ERROR: Failed to extract PortableGit.
    exit /b 1
  )
) else (
  echo [2/7] PortableGit already extracted.
)

if not exist "%GIT_CMD%" (
  echo ERROR: git.exe not found.
  exit /b 1
)

set "PATH=%PORTABLE_GIT_HOME%\cmd;%PORTABLE_GIT_HOME%\usr\bin;%PATH%"

rem =========================================================
rem  3) Clone or pull repository
rem =========================================================
echo [3/7] Sync repository
if exist "%REPO_DIR%\.git" (
  echo - repo exists, pulling
  "%GIT_CMD%" -C "%REPO_DIR%" pull --rebase || (
    echo ERROR: git pull failed.
    exit /b 1
  )
) else (
  echo - cloning
  "%GIT_CMD%" clone "%REPO_URL%" "%REPO_DIR%" || (
    echo ERROR: git clone failed.
    exit /b 1
  )
)

rem =========================================================
rem  4) Install uv via official PowerShell installer
rem =========================================================
echo [4/7] Ensure uv is installed

where uv >nul 2>&1
if %ERRORLEVEL%==0 (
  echo - uv already available
) else (
  echo - Installing uv using official installer
  powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" || (
    echo ERROR: uv installation failed.
    exit /b 1
  )

  rem uv is typically installed into %USERPROFILE%\.cargo\bin
  if exist "%USERPROFILE%\.cargo\bin" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
  )
)

where uv >nul 2>&1
if not %ERRORLEVEL%==0 (
  echo ERROR: uv not found after installation.
  echo Try opening a new terminal or ensure PATH contains:
  echo   %USERPROFILE%\.cargo\bin
  exit /b 1
)

rem =========================================================
rem  5) Move temp_git into EasyNovelAssistantosuChitsu
rem =========================================================
echo [5/7] Moving temp_git into repository

set "DEST_TEMP_GIT=%REPO_DIR%\temp_git"

if exist "%DEST_TEMP_GIT%" (
  echo - Removing existing "%DEST_TEMP_GIT%"
  rmdir /s /q "%DEST_TEMP_GIT%"
)

move "%TEMP_GIT%" "%DEST_TEMP_GIT%" >nul || (
  echo ERROR: Failed to move temp_git.
  exit /b 1
)

echo - temp_git moved successfully


rem =========================================================
rem  6) Run uv sync
rem =========================================================
echo [6/7] Running uv sync
pushd "%REPO_DIR%"
uv sync || (
  popd
  echo ERROR: uv sync failed.
  exit /b 1
)
popd

echo.
echo === Done! ===

rem =========================================================
rem  7) Download koboldcpp.exe into EasyNovelAssistantosuChitsu
rem =========================================================
echo [7/7] Ensure koboldcpp.exe exists

set "KOBOLD_URL=https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe"
set "KOBOLD_EXE=%REPO_DIR%\koboldcpp.exe"

if exist "%KOBOLD_EXE%" (
  echo - koboldcpp.exe already exists
) else (
  echo - Downloading koboldcpp.exe
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "Invoke-WebRequest '%KOBOLD_URL%' -OutFile '%KOBOLD_EXE%'" || (
      echo ERROR: Failed to download koboldcpp.exe
      exit /b 1
    )
)

exit /b 0
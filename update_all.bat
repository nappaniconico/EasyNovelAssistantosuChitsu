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


echo.
echo === Start setup ===
echo Script dir: "%SCRIPT_DIR%"

rem =========================================================
rem  1) Prepare temp_git and download PortableGit
rem =========================================================
if not exist "%TEMP_GIT%" (
  echo [1/4] Creating "%TEMP_GIT%"
  mkdir "%TEMP_GIT%"
)

if not exist "%TEMP_GIT%\%PORTABLE_GIT_EXE%" (
  echo [1/4] Downloading PortableGit
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "Invoke-WebRequest '%PORTABLE_GIT_URL%' -OutFile '%TEMP_GIT%\%PORTABLE_GIT_EXE%'" || (
      echo ERROR: Failed to download PortableGit.
      exit /b 1
    )
) else (
  echo [1/4] PortableGit already downloaded.
)

rem =========================================================
rem  2) Extract PortableGit
rem =========================================================
if not exist "%GIT_CMD%" (
  echo [2/4] Extracting PortableGit
  if exist "%PORTABLE_GIT_HOME%" rmdir /s /q "%PORTABLE_GIT_HOME%"
  mkdir "%PORTABLE_GIT_HOME%"

  "%TEMP_GIT%\%PORTABLE_GIT_EXE%" -y -o"%PORTABLE_GIT_HOME%" >nul || (
    echo ERROR: Failed to extract PortableGit.
    exit /b 1
  )
) else (
  echo [2/4] PortableGit already extracted.
)

if not exist "%GIT_CMD%" (
  echo ERROR: git.exe not found.
  exit /b 1
)

set "PATH=%PORTABLE_GIT_HOME%\cmd;%PORTABLE_GIT_HOME%\usr\bin;%PATH%"

rem =========================================================
rem  3) Clone or pull repository
rem =========================================================
echo [3/4] Sync repository
if exist ".git" (
  echo - repo exists, pulling
  "%GIT_CMD%" pull --rebase || (
    echo ERROR: git pull failed.
    exit /b 1
  )
) else (
  echo - repo not exists
)

rem =========================================================
rem  4) Download koboldcpp.exe into EasyNovelAssistantosuChitsu
rem =========================================================
echo [4/4] Ensure koboldcpp.exe exists

set "KOBOLD_URL=https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe"
set "KOBOLD_EXE=koboldcpp.exe"

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
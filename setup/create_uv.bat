pushd %~dp0
pushd ..
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
uv sync
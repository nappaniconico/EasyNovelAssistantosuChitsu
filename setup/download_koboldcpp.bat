@echo off
chcp 65001 > NUL
set CURL_CMD=C:\Windows\System32\curl.exe
set KOBOLD_CPP_EXE=koboldcpp.exe

pushd %~dp0
pushd ..

echo %CURL_CMD% -Lo %KOBOLD_CPP_EXE% https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe
%CURL_CMD% -Lo %KOBOLD_CPP_EXE% https://github.com/LostRuins/koboldcpp/releases/latest/download/koboldcpp.exe
if %errorlevel% neq 0 ( pause & popd & exit /b 1 )

popd
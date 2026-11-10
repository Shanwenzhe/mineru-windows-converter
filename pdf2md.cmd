@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pdf2md.ps1" %*

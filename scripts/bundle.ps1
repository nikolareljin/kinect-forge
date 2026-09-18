$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $Root "..")

python -m PyInstaller `
  --noconfirm `
  --windowed `
  --name kinect-forge `
  --add-data "docs;docs" `
  --collect-submodules open3d `
  --hidden-import tkinter `
  --hidden-import tkinter.ttk `
  src/kinect_forge/__main__.py

Write-Host "Built package under dist/"

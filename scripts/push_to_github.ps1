param(
  [Parameter(Mandatory=$true)][string]$RemoteUrl,
  [string]$Branch = "main",
  [switch]$Force
)

# Usage:
#   .\scripts\push_to_github.ps1 -RemoteUrl "git@github.com:Aionmizu/meow-meow-3000.git"
# or
#   .\scripts\push_to_github.ps1 -RemoteUrl "https://<TOKEN>@github.com/Aionmizu/meow-meow-3000.git"

$ErrorActionPreference = 'Stop'

# Ensure git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "git is not installed or not in PATH" -ForegroundColor Red
  exit 1
}

# Ensure we are at repo root (contains pyproject.toml)
if (-not (Test-Path -Path "pyproject.toml")) {
  Write-Host "Run this from the project root (pyproject.toml not found)." -ForegroundColor Red
  exit 1
}

# Initialize git if needed
if (-not (Test-Path -Path ".git")) {
  git init
}

# Add all files
git add -A

# Commit
$commitMsg = "chore: add deploy_kali.sh and docs; automation scripts"
try {
  git commit -m $commitMsg
} catch {
  Write-Host "Nothing to commit or commit failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Set branch
if ($Force) {
  git branch -M $Branch
} else {
  try { git rev-parse --verify $Branch *> $null } catch { git branch -M $Branch }
}

# Set remote
$remoteExists = git remote | Select-String -Pattern '^origin$' -Quiet
if ($remoteExists) {
  if ($Force) {
    git remote remove origin
    git remote add origin $RemoteUrl
  } else {
    Write-Host "Remote 'origin' already exists. Use -Force to overwrite." -ForegroundColor Yellow
  }
} else {
  git remote add origin $RemoteUrl
}

# Push
if ($Force) {
  git push -u origin $Branch --force
} else {
  git push -u origin $Branch
}

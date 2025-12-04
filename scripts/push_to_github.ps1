#!/usr/bin/env pwsh
param(
  [Parameter(Mandatory=$true)][string]$RemoteUrl,
  [string]$Branch = "main",
  [switch]$Force,
  [string]$Username,
  [string]$Password,
  [switch]$UseCredentialManager
)

# Usage:
#   .\scripts\push_to_github.ps1 -RemoteUrl "https://github.com/Aionmizu/meow-meow-3000.git" -Branch main -UseCredentialManager
# or (optional SSH)
#   .\scripts\push_to_github.ps1 -RemoteUrl "git@github.com:Aionmizu/meow-meow-3000.git" -Branch main
# or (HTTPS with embedded token, not recommended)
#   .\scripts\push_to_github.ps1 -RemoteUrl "https://<TOKEN>@github.com/Aionmizu/meow-meow-3000.git" -Branch main
# Note: GitHub disables password auth for Git over HTTPS. Use interactive prompts or a Personal Access Token (PAT).

$ErrorActionPreference = 'Stop'

function Build-RemoteUrlWithCreds([string]$url, [string]$user, [string]$pass) {
  try {
    $uri = [System.Uri]$url
  } catch {
    return $url
  }
  if ($uri.Scheme -notin @('http','https')) { return $url }
  $u = [System.Uri]::EscapeDataString($user)
  $p = [System.Uri]::EscapeDataString($pass)
  $hostAndPath = $uri.Host + $uri.PathAndQuery
  if ($uri.Port -and $uri.IsDefaultPort -eq $false) { $hostAndPath = $uri.Host + ':' + $uri.Port + $uri.PathAndQuery }
  return "$($uri.Scheme)://$u`:$p@$hostAndPath"
}

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
$commitMsg = "chore: initial push"
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

# Auto-enable Credential Manager for HTTPS if no creds provided
if ($RemoteUrl -match '^(http|https)://' -and -not $Username -and -not $Password -and -not $UseCredentialManager) {
  $UseCredentialManager = $true
  Write-Host "Using Git Credential Manager for interactive HTTPS auth (prompts)." -ForegroundColor Cyan
}

# Optionally configure Git Credential Manager for interactive auth
if ($UseCredentialManager) {
  try { git config --global credential.helper manager-core } catch { try { git config --global credential.helper manager } catch {} }
}

# Prepare remote URL (inject creds for HTTPS if provided)
$effectiveRemote = $RemoteUrl
if ($Username -and $Password -and $RemoteUrl -match '^(http|https)://') {
  $effectiveRemote = Build-RemoteUrlWithCreds -url $RemoteUrl -user $Username -pass $Password
}

# Warn about using plain password with GitHub
if ($Username -and $Password -and $RemoteUrl -match 'github.com') {
  Write-Host "Note: GitHub requires a Personal Access Token (PAT). Use -Password <PAT> (your GitHub account password will not work)." -ForegroundColor Yellow
}

# If using SSH to GitHub, perform a quick auth check and guide the user
if ($effectiveRemote -match '^git@github.com:') {
  try {
    Write-Host "Checking SSH connectivity to GitHub (ssh -T git@github.com)..." -ForegroundColor Cyan
    $sshTest = & ssh -T git@github.com 2>&1
    if ($LASTEXITCODE -ne 1 -and $LASTEXITCODE -ne 255) {
      # GitHub returns 1 on success for 'Hi USERNAME!' without shell access
      Write-Host "SSH check returned exit code $LASTEXITCODE. Output:" -ForegroundColor Yellow
      Write-Host $sshTest
    } else {
      Write-Host $sshTest
    }
  } catch {
    Write-Host "SSH check could not be performed. If you see 'Permission denied (publickey)', use HTTPS with Credential Manager (recommended):`n  .\\scripts\\push_to_github.ps1 -RemoteUrl 'https://github.com/Aionmizu/meow-meow-3000.git' -Branch $Branch -UseCredentialManager" -ForegroundColor Yellow
  }
}

# Set remote
$remoteExists = git remote | Select-String -Pattern '^origin$' -Quiet
if ($remoteExists) {
  if ($Force) {
    git remote remove origin
    git remote add origin $effectiveRemote
  } else {
    Write-Host "Remote 'origin' already exists. Use -Force to overwrite." -ForegroundColor Yellow
  }
} else {
  git remote add origin $effectiveRemote
}

# Push
try {
  if ($Force) {
    git push -u origin $Branch --force
  } else {
    git push -u origin $Branch
  }
} catch {
  Write-Host "Push failed: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Troubleshooting: Prefer HTTPS with interactive prompts (-UseCredentialManager). Alternatively, use a PAT with -Username/-Password." -ForegroundColor Yellow
  exit 1
}

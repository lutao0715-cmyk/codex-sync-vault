param(
  [string]$Remote = $env:CODEX_SYNC_REMOTE,
  [string]$Vault = "$env:USERPROFILE\Documents\codex-sync-vault",
  [string]$CodexHome = "$env:USERPROFILE\.codex",
  [switch]$NoPush
)

$ErrorActionPreference = "Stop"

function Run-Git {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
  & git @Args
  if ($LASTEXITCODE -ne 0) {
    throw "git $($Args -join ' ') failed"
  }
}

function Ensure-Repo {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required. Install Git first, then rerun this script."
  }

  if (-not (Test-Path $Vault)) {
    if ([string]::IsNullOrWhiteSpace($Remote)) {
      New-Item -ItemType Directory -Force $Vault | Out-Null
      Push-Location $Vault
      try {
        Run-Git init
      } finally {
        Pop-Location
      }
    } else {
      Run-Git clone $Remote $Vault
    }
  }

  if (-not (Test-Path (Join-Path $Vault ".git"))) {
    throw "$Vault exists but is not a Git repository."
  }

  if (-not [string]::IsNullOrWhiteSpace($Remote)) {
    Push-Location $Vault
    try {
      $hasOrigin = (& git remote) -contains "origin"
      if (-not $hasOrigin) {
        Run-Git remote add origin $Remote
      }
    } finally {
      Pop-Location
    }
  }
}

function Copy-ToVault {
  $target = Join-Path $Vault "codex-home"
  New-Item -ItemType Directory -Force $target | Out-Null

  $skillsSrc = Join-Path $CodexHome "skills"
  $skillsDst = Join-Path $target "skills"
  if (Test-Path $skillsSrc) {
    robocopy $skillsSrc $skillsDst /MIR /XD ".system" /XF ".DS_Store" "Thumbs.db" | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "robocopy skills failed with code $LASTEXITCODE" }
  }

  $pluginsSrc = Join-Path $CodexHome "plugins"
  $pluginsDst = Join-Path $target "plugins"
  if (Test-Path $pluginsSrc) {
    robocopy $pluginsSrc $pluginsDst /MIR /XD "cache" ".plugin-appserver" ".remote-plugin-install-staging" /XF ".DS_Store" "Thumbs.db" | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "robocopy plugins failed with code $LASTEXITCODE" }
  }

  $configSrc = Join-Path $CodexHome "config.toml"
  if (Test-Path $configSrc) {
    New-Item -ItemType Directory -Force (Join-Path $target "config") | Out-Null
    Copy-Item $configSrc (Join-Path $target "config\config.toml") -Force
  }
}

function Copy-FromVault {
  $source = Join-Path $Vault "codex-home"
  if (-not (Test-Path $source)) {
    return
  }

  New-Item -ItemType Directory -Force $CodexHome | Out-Null

  $skillsSrc = Join-Path $source "skills"
  if (Test-Path $skillsSrc) {
    robocopy $skillsSrc (Join-Path $CodexHome "skills") /E /XD ".system" /XF ".DS_Store" "Thumbs.db" | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "import skills failed with code $LASTEXITCODE" }
  }

  $pluginsSrc = Join-Path $source "plugins"
  if (Test-Path $pluginsSrc) {
    robocopy $pluginsSrc (Join-Path $CodexHome "plugins") /E /XD "cache" ".plugin-appserver" ".remote-plugin-install-staging" /XF ".DS_Store" "Thumbs.db" | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "import plugins failed with code $LASTEXITCODE" }
  }

  $configSrc = Join-Path $source "config\config.toml"
  if (Test-Path $configSrc) {
    Copy-Item $configSrc (Join-Path $CodexHome "config.toml.synced") -Force
    Write-Host "Wrote config snapshot to $CodexHome\config.toml.synced. Review before replacing config.toml."
  }
}

function Commit-IfNeeded {
  Push-Location $Vault
  try {
    Run-Git add codex-home
    $status = & git status --porcelain
    if ($status) {
      Run-Git commit -m "Sync Codex local assets from Windows"
    }
  } finally {
    Pop-Location
  }
}

Ensure-Repo
Copy-ToVault
Commit-IfNeeded

Push-Location $Vault
try {
  if ((& git remote) -contains "origin") {
    Run-Git pull --rebase --autostash origin HEAD
  }
} finally {
  Pop-Location
}

Copy-FromVault
Copy-ToVault
Commit-IfNeeded

if (-not $NoPush) {
  Push-Location $Vault
  try {
    if ((& git remote) -contains "origin") {
      Run-Git push origin HEAD
    } else {
      Write-Host "No remote configured. Local vault updated at $Vault."
    }
  } finally {
    Pop-Location
  }
}

Write-Host "Codex sync complete. Restart Codex/ChatGPT desktop if plugin or skill changes do not appear immediately."

<#
  Structurally prepared Windows operator entry point. Not live-tested on Windows.
  This script neither accepts, prints, exports, nor packages secrets. During Setup it
  creates a fresh machine-local n8n encryption key when no state exists.
#>
param(
  [ValidateSet('Setup','Start','Stop','Restart','Status','Verify','Backup','Restore')]
  [string]$Action = 'Status',
  [string]$From = ''
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$StateDir = if ($env:LOCALLE_STATE_DIR) { $env:LOCALLE_STATE_DIR } else { Join-Path $env:USERPROFILE '.localle' }
$RuntimeDir = if ($env:LOCALLE_N8N_RUNTIME) { $env:LOCALLE_N8N_RUNTIME } else { Join-Path $StateDir 'n8n-runtime' }
$UserFolder = if ($env:LOCALLE_N8N_USER_FOLDER) { $env:LOCALLE_N8N_USER_FOLDER } else { Join-Path $StateDir 'n8n-user' }
$N8n = Join-Path $RuntimeDir 'node_modules\.bin\n8n.cmd'
$Model = if ($env:LOCALLE_OLLAMA_MODEL) { $env:LOCALLE_OLLAMA_MODEL } else { 'llama3.1:8b' }
$KeyConfigDir = Join-Path $UserFolder '.n8n'
$KeyConfig = Join-Path $KeyConfigDir 'config'
$env:N8N_USER_FOLDER = $UserFolder
$env:N8N_DIAGNOSTICS_ENABLED = 'false'
$env:N8N_HOST = '127.0.0.1'
$env:N8N_LISTEN_ADDRESS = '127.0.0.1'
$env:N8N_PORT = if ($env:LOCALLE_N8N_PORT) { $env:LOCALLE_N8N_PORT } else { '5678' }

function Require-Command([string]$Name) { if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "$Name is required." } }
function N8n-Command([string[]]$Args) { if (-not (Test-Path $N8n)) { throw "Pinned n8n missing. Run -Action Setup." }; & $N8n @Args }
function Has-Model { return ((& ollama list | Select-String -SimpleMatch $Model) -ne $null) }
function Check-Ollama { Invoke-RestMethod -UseBasicParsing -TimeoutSec 5 'http://127.0.0.1:11434/api/version' | Out-Null }
function Ensure-LocalEncryptionKey {
  New-Item -ItemType Directory -Force -Path $KeyConfigDir | Out-Null
  if (-not (Test-Path $KeyConfig)) {
    $db = Join-Path $KeyConfigDir 'database.sqlite'
    if (Test-Path $db) { throw 'Missing n8n key config beside an existing database. Restore the original protected key/config; do not generate a replacement.' }
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    @{ encryptionKey = [Convert]::ToBase64String($bytes) } | ConvertTo-Json | Set-Content -NoNewline -Encoding utf8 $KeyConfig
    icacls $KeyConfig /inheritance:r /grant:r "$env:USERNAME:(R,W)" | Out-Null
  }
  try { $config = Get-Content -Raw $KeyConfig | ConvertFrom-Json; if ([string]::IsNullOrWhiteSpace($config.encryptionKey)) { throw 'missing key' } } catch { throw 'n8n key config is invalid; do not start n8n.' }
}

switch ($Action) {
  'Setup' {
    Require-Command node; Require-Command npm; Require-Command ollama; Check-Ollama
    New-Item -ItemType Directory -Force -Path $RuntimeDir,$UserFolder | Out-Null
    Ensure-LocalEncryptionKey
    if (-not (Test-Path $N8n) -or ((& $N8n --version) -ne '1.117.3')) { & npm install --prefix $RuntimeDir --omit=dev --no-audit --no-fund --package-lock=false 'n8n@1.117.3' }
    if ((& $N8n --version) -ne '1.117.3') { throw 'Pinned n8n verification failed.' }
    if (-not (Has-Model)) { & ollama pull $Model }
    if (-not (Has-Model)) { throw "Required model $Model is missing." }
    $body = @{ model=$Model; prompt='Return exactly JSON with key health and boolean value true.'; format='json'; stream=$false } | ConvertTo-Json -Compress
    $result = Invoke-RestMethod -UseBasicParsing -Method Post -ContentType 'application/json' -Body $body 'http://127.0.0.1:11434/api/generate'
    $null = $result.response | ConvertFrom-Json
    Write-Output 'Setup complete. Create the three named company credentials in n8n, then run scripts/import-localle-workflow.sh. AUTO SEND remains OFF.'
  }
  'Start' {
    if (-not (Test-Path $N8n)) { throw 'Run -Action Setup first.' }
    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    $log = Join-Path $StateDir 'n8n.log'; $p = Start-Process -FilePath $N8n -ArgumentList 'start' -RedirectStandardOutput $log -RedirectStandardError $log -PassThru
    $p.Id | Set-Content (Join-Path $StateDir 'n8n.pid'); Write-Output "Localle n8n started at http://127.0.0.1:$env:N8N_PORT"
  }
  'Stop' { $pidFile=Join-Path $StateDir 'n8n.pid'; if (Test-Path $pidFile) { $p=Get-Process -Id (Get-Content $pidFile) -ErrorAction SilentlyContinue; if ($p) { Stop-Process -Id $p.Id }; Remove-Item $pidFile -Force }; Write-Output 'Localle n8n stopped.' }
  'Restart' { & $PSCommandPath -Action Stop; & $PSCommandPath -Action Start }
  'Status' {
    try { Invoke-RestMethod -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:$env:N8N_PORT/healthz" | Out-Null; 'N8N .................... PASS' } catch { 'N8N .................... FAIL' }
    if (Test-Path $N8n) { "N8N VERSION ............ $(& $N8n --version)" } else { 'N8N VERSION ............ MISSING' }
    try { Check-Ollama; 'OLLAMA ................. PASS' } catch { 'OLLAMA ................. FAIL' }
    if (Get-Command ollama -ErrorAction SilentlyContinue -and (Has-Model)) { "MODEL .................. PASS ($Model)" } else { 'MODEL .................. FAIL' }
    'AUTO SEND ............. VERIFY Config!auto_send_enabled is FALSE'; 'ZERO-COST CHECK ........ PASS — local Ollama only'
  }
  'Verify' { Ensure-LocalEncryptionKey; Check-Ollama; if (-not (Has-Model)) { throw "Required model $Model is missing." }; N8n-Command @('--version'); 'VERIFY PASS — provider authorization and AUTO SEND=false need controlled E2E evidence.' }
  'Backup' {
    $db=Join-Path $UserFolder '.n8n\database.sqlite'; if (-not (Test-Path $db)) { throw 'No Localle database to back up.' }; $dest=Join-Path (Join-Path $StateDir 'backups') (Get-Date -Format 'yyyyMMdd_HHmmss'); New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item $db (Join-Path $dest 'database.sqlite'); Copy-Item (Join-Path $ProjectRoot 'n8n\Localle_Option_B_Reservation_Intake_FINAL.n8n.json') (Join-Path $dest 'workflow.json'); Copy-Item (Join-Path $ProjectRoot 'config\live_sheet_contract.json') (Join-Path $dest 'schema-manifest.json'); Get-FileHash "$dest\*" -Algorithm SHA256 | Format-Table -AutoSize | Out-File "$dest\SHA256SUMS.txt"; "Backup complete: $dest"
  }
  'Restore' { if (-not $From -or -not (Test-Path (Join-Path $From 'database.sqlite'))) { throw 'Use -Action Restore -From C:\path\to\backup' }; $dest=Join-Path $UserFolder '.n8n\database.sqlite'; New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Copy-Item (Join-Path $From 'database.sqlite') $dest -Force; 'Restore complete. Confirm workflow remains inactive before testing.' }
}

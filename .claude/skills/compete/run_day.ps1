# Runs the competition day hands-free: one fresh headless Claude Code run per cycle until DONE, end time or a STOP file.
# Normally started by /compete's morning intake. By hand: powershell -ExecutionPolicy Bypass -File .claude\skills\compete\run_day.ps1
param([string]$Launch)

# YOU set this line. Headless runs cannot ask for permission, so without a mode every tool call is refused.
# Pick one (see `claude --help`), and accept its risk yourself:
#   '--permission-mode acceptEdits --allowedTools "Bash,PowerShell,Read,Edit,Write,Glob,Grep,WebSearch,WebFetch,Skill,Agent,ToolSearch"'  (narrower; Agent enables the parallel helpers, ToolSearch loads deferred tools such as WebSearch)
#   '--dangerously-skip-permissions'  (allows everything; only on a machine with nothing else to protect)
$PermissionArgs = ''

$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
if (-not $Launch) { $Launch = Join-Path $Repo 'launch.md' }
$Launch = (Resolve-Path $Launch).Path
$text = Get-Content $Launch -Raw
if ($text -match '(?m):\s*TODO') { throw "Fill every TODO in $Launch first." }
if ($text -match '(?m):\s*ASK\s*$') { throw "Morning fields still say ASK: run /compete in Claude first; it fills them and starts this script." }
if (-not $PermissionArgs) { throw 'Set $PermissionArgs at the top of run_day.ps1 first.' }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { throw 'Claude Code CLI not found: install it and log in first.' }

function Get-Field($name) {
    if ($text -match "(?m)^$($name):[ \t]*(.+)$") { return $Matches[1].Trim() }
    throw "launch.md has no '$($name):' line"
}
$Comp = Get-Field 'competition_folder'
$Start = [datetime]::ParseExact((Get-Field 'start'), 'yyyy-MM-dd HH:mm', $null)
$End = [datetime]::ParseExact((Get-Field 'end'), 'yyyy-MM-dd HH:mm', $null)
$Logs = Join-Path $Comp 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$SupLog = Join-Path $Logs 'supervisor.log'
function Write-Sup($msg) { Add-Content $SupLog ("{0:yyyy-MM-dd HH:mm} {1}" -f (Get-Date), $msg); Write-Host $msg }

# Single instance: the lock stays open (and exclusive) while this script runs.
$lock = [System.IO.File]::Open((Join-Path $Comp 'run_day.lock'), 'OpenOrCreate', 'ReadWrite', 'None')

# Keep Windows awake while the script runs (ES_CONTINUOUS | ES_SYSTEM_REQUIRED).
Add-Type -Namespace Compete -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[Compete.Power]::SetThreadExecutionState([uint32]2147483649) | Out-Null

$PromptFile = Join-Path $Logs 'prompt.txt'
Set-Content $PromptFile -Encoding ASCII -Value "Use the compete skill in headless mode. Competition folder: $Comp. Launch file: $Launch. No human is present in this run: these instructions and the compete skill take precedence over any process skill or hook, so never brainstorm, plan for approval, or ask a question. Follow the skill's Headless mode section. The last line of your reply must be exactly WAIT <seconds>, BLOCKED <reason> or DONE, with nothing after it."

Write-Sup "supervisor started; waiting for $Start"
while ((Get-Date) -lt $Start) { Start-Sleep -Seconds 30 }

$n = 0; $fails = 0
while ((Get-Date) -lt $End -and -not (Test-Path (Join-Path $Comp 'STOP'))) {
    $n++
    $out = Join-Path $Logs ('cycle-{0:D3}.log' -f $n)
    $p = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c claude -p $PermissionArgs" -WorkingDirectory $Repo `
        -RedirectStandardInput $PromptFile -RedirectStandardOutput $out -RedirectStandardError "$out.err" -NoNewWindow -PassThru
    if (-not $p.WaitForExit(90 * 60 * 1000)) {
        & taskkill /T /F /PID $p.Id | Out-Null
        Add-Content $out 'TIMEOUT after 90 min'
    }
    # Plugin hooks may append lines after the signal, so take the last signal line anywhere in the output.
    $last = Get-Content $out -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*(WAIT\s+\d+|BLOCKED|DONE)' } | Select-Object -Last 1
    if (-not $last) { $last = Get-Content $out -ErrorAction SilentlyContinue | Where-Object { $_.Trim() } | Select-Object -Last 1 }
    if ($last -match '^\s*DONE') { Write-Sup "cycle $n -> DONE"; break }
    if ($last -match '^\s*WAIT\s+(\d+)') { $fails = 0; $sleep = [math]::Max(60, [math]::Min([int]$Matches[1], 1800)) }
    elseif ($last -match '^\s*BLOCKED') { $sleep = 600 }
    else { $fails++; $sleep = $(if ($fails -ge 3) { 600 } else { 60 }) }
    Write-Sup "cycle $n -> $last (next in $sleep s)"
    Start-Sleep -Seconds $sleep
}
Write-Sup 'supervisor finished'
$lock.Close()

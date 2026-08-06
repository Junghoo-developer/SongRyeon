[CmdletBinding()]
param(
    [ValidateSet("verify", "demo")]
    [string]$Mode = "demo",

    [string]$Model = "gemma4:26b",

    [switch]$SkipTests,

    [switch]$AllowDirty,

    [switch]$NoClear
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Keep this PowerShell source ASCII-only so Windows PowerShell 5.1 can load it
# without a UTF-8 BOM. The Korean demo question is decoded from UTF-8 Base64.
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONUTF8 = "1"

if (-not $NoClear) {
    Clear-Host
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$fixtureRoot = Join-Path $repoRoot "evals\model_ceiling_cases\project"
$declarationPath = Join-Path $fixtureRoot "declaration_only.py"
$enforcedPath = Join-Path $fixtureRoot "enforced_limit.py"

function Assert-NativeSuccess {
    param(
        [int]$ExitCode,
        [string]$Message
    )

    if ($ExitCode -ne 0) {
        throw $Message
    }
}

function Get-MeaningfulLines {
    param([object[]]$Lines)

    return @($Lines | Where-Object {
        -not [string]::IsNullOrWhiteSpace([string]$_)
    })
}

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " SongRyeon Core v1 - submission video preflight" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Missing .venv Python. Create .venv and install project dependencies first."
}

foreach ($requiredPath in @($declarationPath, $enforcedPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Missing public video fixture: $([IO.Path]::GetFileName($requiredPath))"
    }
}

$declarationSource = Get-Content -Raw -Encoding utf8 -LiteralPath $declarationPath
$enforcedSource = Get-Content -Raw -Encoding utf8 -LiteralPath $enforcedPath
if (-not $declarationSource.Contains("MAX_PAYLOAD_CHARACTERS = 128")) {
    throw "The declaration_only.py video contract changed."
}
if ($declarationSource.Contains("if len(payload) > MAX_PAYLOAD_CHARACTERS:")) {
    throw "declaration_only.py is no longer a declaration-only negative control."
}
if (-not $enforcedSource.Contains("if len(payload) > MAX_PAYLOAD_CHARACTERS:")) {
    throw "enforced_limit.py no longer contains the enforcement condition."
}
if (-not $enforcedSource.Contains('raise ValueError("payload is too long")')) {
    throw "enforced_limit.py no longer contains the enforcement exception."
}

$gitShaLines = @(& git -C $repoRoot rev-parse HEAD 2>&1)
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Message "Could not read the Git SHA."
$gitSha = ([string]$gitShaLines[-1]).Trim()

$rawDirtyLines = @(& git -C $repoRoot status --porcelain 2>&1)
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Message "Could not inspect the Git worktree."
$dirtyLines = @(Get-MeaningfulLines -Lines $rawDirtyLines)
if (($dirtyLines.Count -gt 0) -and (-not $AllowDirty)) {
    throw "Worktree is not clean ($($dirtyLines.Count) changed paths). Commit or remove changes before recording."
}

$helpOutput = @(& $pythonPath -m demo --help 2>&1)
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Message "The demo CLI help command failed."
$helpText = $helpOutput -join "`n"
foreach ($requiredOption in @("--model", "--memory", "--project-root")) {
    if (-not $helpText.Contains($requiredOption)) {
        throw "The demo CLI is missing required option: $requiredOption"
    }
}

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($null -eq $ollamaCommand) {
    throw "The ollama command is not available."
}
$ollamaRows = @(& ollama list 2>&1)
Assert-NativeSuccess -ExitCode $LASTEXITCODE -Message "Could not read the Ollama model list."
$modelPattern = "^\s*$([regex]::Escape($Model))\s"
$modelRow = @($ollamaRows | Where-Object { ([string]$_) -match $modelPattern })
if ($modelRow.Count -eq 0) {
    throw "Ollama model not found: $Model. Run: ollama pull $Model"
}

Write-Host "Git SHA: $gitSha"
if ($dirtyLines.Count -eq 0) {
    Write-Host "Git worktree: clean" -ForegroundColor Green
} else {
    Write-Host "Git worktree: $($dirtyLines.Count) changed paths (AllowDirty development mode)" -ForegroundColor Yellow
}
Write-Host "Public fixture contract: OK" -ForegroundColor Green
Write-Host "Ollama model: $Model found" -ForegroundColor Green
Write-Host "Memory boundary: memory/memory.jsonl will not be used" -ForegroundColor Green

if ($Mode -eq "verify") {
    $testOutput = @()
    $testLines = @()
    if (-not $SkipTests) {
        Write-Host "Running full test suite..."
        $testOutput = @(& $pythonPath -m pytest -q 2>&1)
        $testExitCode = $LASTEXITCODE
        $testLines = @(Get-MeaningfulLines -Lines $testOutput)
        if ($testLines.Count -gt 0) {
            Write-Host "pytest final line: $($testLines[-1])"
        }
        if ($testExitCode -ne 0) {
            $tail = @($testLines | Select-Object -Last 12)
            foreach ($line in $tail) {
                Write-Host $line -ForegroundColor Red
            }
            throw "Full tests failed. Do not record the submission video."
        }
    } else {
        Write-Host "Full tests: skipped by -SkipTests" -ForegroundColor Yellow
    }

    $publicEvidenceRoot = Join-Path $repoRoot "evals\contest_holdout_v1\frozen\contest-20260806-v2"
    $auditPath = Join-Path $publicEvidenceRoot "HUMAN_AUDIT.json"
    $decisionPath = Join-Path $publicEvidenceRoot "PUBLICATION_DECISION.json"
    if ((Test-Path -LiteralPath $auditPath) -and (Test-Path -LiteralPath $decisionPath)) {
        $audit = Get-Content -Raw -Encoding utf8 -LiteralPath $auditPath | ConvertFrom-Json
        $decision = Get-Content -Raw -Encoding utf8 -LiteralPath $decisionPath | ConvertFrom-Json
        $auditItems = @($audit.items)
        $parseCount = @($auditItems | Where-Object {
            $_.verdict_parse_matches_answer -eq $true
        }).Count
        $groundingCount = @($auditItems | Where-Object {
            $_.explanation_supported_by_fixture -eq $true
        }).Count
        $authorityCount = @($auditItems | Where-Object {
            $_.ar_authority_labeling_accurate -eq $true
        }).Count

        if ($audit.audit_status -ne "completed_human_review") {
            throw "Human audit is not marked completed_human_review."
        }
        if (($decision.decision_status -ne "publication_integrity_gate_passed") -or
            ($decision.publishable -ne $true)) {
            throw "The publication integrity gate is not in a passed state."
        }
        if (($auditItems.Count -ne 19) -or ($parseCount -ne 19) -or
            ($groundingCount -ne 18) -or ($authorityCount -ne 18)) {
            throw "Human-audit counts differ from the approved public claim."
        }

        Write-Host "Publication integrity gate: PASSED" -ForegroundColor Green
        Write-Host "Human audit: parse 19/19 | grounding 18/19 | A/R authority 18/19"
        Write-Host "Boundary: integrity passed does not prove performance superiority." -ForegroundColor Yellow
    } else {
        throw "Public human-audit or publication-decision evidence is missing."
    }

    Write-Host "Pre-recording verification complete." -ForegroundColor Green
    exit 0
}

$sessionName = "{0}-{1}" -f (Get-Date -Format "yyyyMMdd-HHmmss"), ([guid]::NewGuid().ToString("N").Substring(0, 8))
$relativeSession = ".tmp\video-capture\$sessionName"
$sessionRoot = Join-Path $repoRoot $relativeSession
$memoryPath = Join-Path $sessionRoot "memory.jsonl"
New-Item -ItemType Directory -Path $sessionRoot | Out-Null

if (Test-Path -LiteralPath $memoryPath) {
    throw "The fresh isolated JSONL path already exists."
}

$questionBase64 = "ZGVjbGFyYXRpb25fb25seS5weeyZgCBlbmZvcmNlZF9saW1pdC5weeulvCDrqqjrkZAg7J297Ja06528LiDrkZAg7YyM7J287JeQIOqwmeydgCBNQVhfUEFZTE9BRF9DSEFSQUNURVJTID0gMTI4IOyDgeyImOqwgCDsnojsnLzrr4DroZwg65GYIOuLpCAxMjjsnpAg7KCc7ZWc7J2EIOyLpOygnOuhnCDsp5HtlontlZzri6Tqs6Ag64uo7KCV7ZW0IOyEpOuqhe2VtOudvC4="
$question = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($questionBase64))

Write-Host ""
Write-Host "=== ISOLATED DEMO START ===" -ForegroundColor Cyan
Write-Host "Model: $Model"
Write-Host "Project: two public synthetic fixture files"
Write-Host "Memory: fresh JSONL for this run only"
Write-Host "External API: disabled"
Write-Host "Question: $question"
Write-Host ""

$previousLocation = Get-Location
$demoExitCode = -1
try {
    Set-Location $repoRoot
    & $pythonPath -m demo `
        --model $Model `
        --num-ctx 16384 `
        --timeout-seconds 180 `
        --keep-alive 10m `
        --memory $memoryPath `
        --project-root $fixtureRoot `
        $question
    $demoExitCode = $LASTEXITCODE
} finally {
    Set-Location $previousLocation
}

Assert-NativeSuccess -ExitCode $demoExitCode -Message "The isolated demo failed. Do not present this as a success."
if (-not (Test-Path -LiteralPath $memoryPath -PathType Leaf)) {
    throw "The demo exited successfully but did not create the isolated JSONL."
}

Write-Host ""
Write-Host "Fresh isolated JSONL created: YES" -ForegroundColor Green
Write-Host "Existing memory/memory.jsonl accessed: NO" -ForegroundColor Green
Write-Host "Do not open raw JSONL on video; it may contain model thinking." -ForegroundColor Yellow
Write-Host "=== ISOLATED DEMO END ===" -ForegroundColor Cyan

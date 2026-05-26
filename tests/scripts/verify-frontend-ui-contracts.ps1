# Static checks for frontend UI contracts that are hard to cover without a
# browser test runner in this project.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$FrontendSrc = Join-Path $ProjectRoot "frontend/src"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Contains {
    param(
        [string]$Content,
        [string]$Pattern,
        [string]$Message
    )

    Assert-True ($Content -match $Pattern) $Message
}

$Helpers = Get-Content -Path (Join-Path $FrontendSrc "utils/helpers.ts") -Raw
Assert-Contains $Helpers "extractBackendErrorMessage" "helpers.ts must extract backend structured error messages"
Assert-Contains $Helpers "payload\.error\.message" "helpers.ts must read FastAPI error.message envelopes"

$TerminalStore = Get-Content -Path (Join-Path $FrontendSrc "stores/terminal.ts") -Raw
Assert-Contains $TerminalStore "extractErrorMessage\(error\)" "terminal store must surface structured backend errors"

$NetworkTerminal = Get-Content -Path (Join-Path $FrontendSrc "components/terminal/NetworkTerminal.vue") -Raw
Assert-True (-not $NetworkTerminal.Contains("admin@")) "terminal prompt must not hard-code admin username"
Assert-Contains $NetworkTerminal "store\.username\.trim\(\) \|\| 'admin'" "terminal prompt must use entered username with admin fallback"

$AIAssistant = Get-Content -Path (Join-Path $FrontendSrc "components/ai-assistant/AIAssistant.vue") -Raw
Assert-Contains $AIAssistant "!store\.isModelConnected" "AI input must be disabled when the selected model is disconnected"
Assert-Contains $AIAssistant "modelUnavailableStatusText" "AI input must explain why sending is unavailable"

$Messaging = Get-Content -Path (Join-Path $FrontendSrc "stores/ai-assistant/actions/messaging.ts") -Raw
Assert-Contains $Messaging "markStreamAborted" "stream aborts must be marked without surfacing low-level read errors"
Assert-Contains $Messaging "用户主动停止生成，忽略流读取中断" "stream reader abort errors must be treated as intentional stops"
Assert-Contains $Messaging "assistantMessage\.aborted === true" "stream completion must skip error handling for manually aborted messages"

Write-Host "Frontend UI contract verification passed" -ForegroundColor Green

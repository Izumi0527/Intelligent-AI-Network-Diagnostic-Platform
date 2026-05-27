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
Assert-True (-not $AIAssistant.Contains("<stream-toggle")) "AI assistant must not render the stream response toggle"
Assert-True (-not $AIAssistant.Contains("SEARCH_TOGGLE_STORAGE_KEY")) "web search must default off on each page load instead of restoring a persisted enabled state"

$Messaging = Get-Content -Path (Join-Path $FrontendSrc "stores/ai-assistant/actions/messaging.ts") -Raw
Assert-Contains $Messaging "markStreamAborted" "stream aborts must be marked without surfacing low-level read errors"
Assert-Contains $Messaging "用户主动停止生成，忽略流读取中断" "stream reader abort errors must be treated as intentional stops"
Assert-Contains $Messaging "assistantMessage\.aborted === true" "stream completion must skip error handling for manually aborted messages"
Assert-True (-not $Messaging.Contains("sendMessageRegular")) "AI messaging store must not keep the non-streaming send path"
Assert-True (-not $Messaging.Contains("state.streamingEnabled")) "AI messaging store must always use streaming and not branch on stream mode"

$AiService = Get-Content -Path (Join-Path $FrontendSrc "utils/aiService.ts") -Raw
Assert-Contains $AiService "fetch\('/api/ai/chat/stream'" "AI service must send chat messages to the streaming endpoint"
Assert-True (-not $AiService.Contains("sendMessageWithRetry")) "AI service must not expose the non-streaming retry sender"
Assert-True (-not $AiService.Contains("'/ai/chat'")) "AI service must not call the non-streaming chat endpoint"

$AiState = Get-Content -Path (Join-Path $FrontendSrc "stores/ai-assistant/state.ts") -Raw
Assert-Contains $AiState "searchEnabled: false" "web search must be disabled by default"
Assert-True (-not $AiState.Contains("streamingEnabled")) "AI state must not expose a user-controlled stream mode"

Write-Host "Frontend UI contract verification passed" -ForegroundColor Green

#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Stop RAG Server and Qdrant

.DESCRIPTION
    Stops the RAG server process and Qdrant if it was started by the RAG server.

.NOTES
    Called by Continue or manually
#>

$ErrorActionPreference = "Stop"

function Write-Status {
    param(
        [string]$Message,
        [string]$Status = "Info"
    )
    
    $colors = @{
        "Success" = "Green"
        "Error"   = "Red"
        "Warning" = "Yellow"
        "Info"    = "Cyan"
    }
    
    Write-Host "[$Status] " -ForegroundColor $colors[$Status] -NoNewline
    Write-Host $Message
}

Write-Status "=== RAG Server Shutdown ===" "Info"

# Stop RAG Server
Write-Status "Stopping RAG Server..." "Info"
$ragProcs = Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    $proc = $_
    try {
        $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
        if ($cmdline -like '*rag_server*' -or $cmdline -like '*rag_server.py*') {
            [PSCustomObject]@{Process = $proc; CommandLine = $cmdline}
        }
    } catch {}
} | Where-Object { $_ -ne $null }

if ($ragProcs.Count -gt 0) {
    foreach ($p in $ragProcs) {
        try {
            Write-Status "  Stopping RAG Server PID $($p.Process.Id)..." "Info"
            $p.Process | Stop-Process -Force -ErrorAction Stop
            Write-Status "  RAG Server PID $($p.Process.Id) stopped" "Success"
        } catch {
            Write-Status "  Failed to stop RAG Server PID $($p.Process.Id): $_" "Error"
        }
    }
} else {
    Write-Status "RAG Server not running" "Warning"
}

# Stop Qdrant
Write-Status "Stopping Qdrant..." "Info"
$qdrantProcs = Get-Process qdrant -ErrorAction SilentlyContinue

if ($qdrantProcs) {
    try {
        Write-Status "  Stopping Qdrant (PID $($qdrantProcs.Id))..." "Info"
        $qdrantProcs | Stop-Process -Force -ErrorAction Stop
        Start-Sleep -Seconds 1
        Write-Status "  Qdrant stopped" "Success"
    } catch {
        Write-Status "  Failed to stop Qdrant: $_" "Error"
    }
} else {
    Write-Status "Qdrant not running" "Warning"
}

Write-Status "=== RAG Server and Qdrant Shutdown Complete ===" "Info"
exit 0

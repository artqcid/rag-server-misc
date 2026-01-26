#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start RAG Server

.DESCRIPTION
    Launches the RAG server with Qdrant vector database.
    Requires:
    - Qdrant running on port 6333
    - Embedding server on port 8001
    - LLM server on port 8080

.PARAMETER Port
    Port for RAG server (default: 8002)

.PARAMETER QdrantUrl
    Qdrant server URL (default: http://localhost:6333)

.PARAMETER Collection
    Default collection name (default: documents)

.NOTES
    Called by Continue or manually
#>

param(
    [int]$Port = 8002,
    [string]$QdrantUrl = "http://localhost:6333",
    [string]$Collection = "documents"
)

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

function Test-ServiceRunning {
    param(
        [string]$ServiceName,
        [int]$Port
    )
    
    $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    return $connection.TcpTestSucceeded
}

function Stop-DuplicateRAGProcesses {
    $processes = Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
        $proc = $_
        try {
            $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmdline -like '*rag_server*') {
                [PSCustomObject]@{Process = $proc; CommandLine = $cmdline}
            }
        } catch {}
    } | Where-Object { $_ -ne $null }
    
    if ($processes.Count -gt 0) {
        Write-Status "Found $($processes.Count) existing rag_server process(es)" "Warning"
        foreach ($p in $processes) {
            Write-Status "  Stopping PID $($p.Process.Id)..." "Warning"
            try {
                $p.Process | Stop-Process -Force -ErrorAction Stop
                Start-Sleep -Milliseconds 500
                Write-Status "  Stopped PID $($p.Process.Id)" "Success"
            } catch {
                Write-Status "  Failed to stop PID $($p.Process.Id): $_" "Error"
            }
        }
        # Wait for port to be released
        Start-Sleep -Seconds 2
    }
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Status "=== RAG Server Startup ===" "Info"
Write-Status "Port: $Port" "Info"
Write-Status "Qdrant: $QdrantUrl" "Info"
Write-Status "Collection: $Collection" "Info"

# Check if Qdrant is running
Write-Status "Checking Qdrant..." "Info"
if (-not (Test-ServiceRunning -ServiceName "Qdrant" -Port 6333)) {
    Write-Status "Qdrant not running on port 6333!" "Warning"
    Write-Status "Starting Qdrant automatically..." "Info"
    
    $QdrantPath = "C:\qdrant\qdrant.exe"
    if (Test-Path $QdrantPath) {
        try {
            Start-Process -FilePath $QdrantPath -NoNewWindow -RedirectStandardOutput "C:\qdrant\qdrant.log" -RedirectStandardError "C:\qdrant\qdrant-error.log"
            Write-Status "Qdrant process started" "Info"
            Write-Status "Waiting for Qdrant to start..." "Info"
            
            # Wait for Qdrant to be ready
            $maxRetries = 30
            $retries = 0
            while (-not (Test-ServiceRunning -ServiceName "Qdrant" -Port 6333) -and $retries -lt $maxRetries) {
                Start-Sleep -Seconds 1
                $retries++
            }
            
            if (Test-ServiceRunning -ServiceName "Qdrant" -Port 6333) {
                Write-Status "Qdrant is running" "Success"
            } else {
                Write-Status "Qdrant failed to start within 30 seconds!" "Error"
                Write-Status "Check logs: C:\qdrant\qdrant.log" "Warning"
                exit 1
            }
        } catch {
            Write-Status "Failed to start Qdrant: $_" "Error"
            exit 1
        }
    } else {
        Write-Status "Qdrant executable not found at $QdrantPath!" "Error"
        exit 1
    }
} else {
    Write-Status "Qdrant is running" "Success"
}

# Check if Embedding server is running
Write-Status "Checking Embedding server..." "Info"
if (-not (Test-ServiceRunning -ServiceName "Embedding" -Port 8001)) {
    Write-Status "Embedding server not running on port 8001!" "Error"
    Write-Status "Start: .\embedding-server-misc\start.ps1" "Warning"
    exit 1
}
Write-Status "Embedding server is running" "Success"

# Check if LLM server is running
Write-Status "Checking LLM server..." "Info"
if (-not (Test-ServiceRunning -ServiceName "LLM" -Port 8080)) {
    Write-Status "LLM server not running on port 8080!" "Warning"
    Write-Status "Warning: RAG will start but queries will fail without LLM" "Warning"
}
else {
    Write-Status "LLM server is running" "Success"
}

# Check if port is available
if (Test-ServiceRunning -ServiceName "RAG" -Port $Port) {
    Write-Status "Port $Port is in use - checking for duplicate processes..." "Warning"
    Stop-DuplicateRAGProcesses
    
    # Re-check if port is still in use
    if (Test-ServiceRunning -ServiceName "RAG" -Port $Port) {
        Write-Status "Port $Port is still in use by another process!" "Error"
        Write-Status "Check: netstat -ano | findstr :$Port" "Warning"
        exit 1
    }
    Write-Status "Port $Port is now available" "Success"
}

# Check for virtual environment
if (-not (Test-Path "$ScriptDir\.venv")) {
    Write-Status "Creating virtual environment..." "Info"
    python -m venv "$ScriptDir\.venv"
    
    Write-Status "Installing dependencies..." "Info"
    & "$ScriptDir\.venv\Scripts\Activate.ps1"
    pip install -r "$ScriptDir\requirements.txt"
}

# Activate virtual environment
Write-Status "Activating virtual environment..." "Info"
& "$ScriptDir\.venv\Scripts\Activate.ps1"

# Set environment variables
$env:RAG_PORT = $Port
$env:RAG_QDRANT_URL = $QdrantUrl
$env:RAG_QDRANT_COLLECTION = $Collection
$env:PYTHONUNBUFFERED = "1"

# Start server
Write-Status "Starting RAG server on port $Port..." "Info"
Write-Status "Press Ctrl+C to stop" "Info"
Write-Status "=======================" "Info"

try {
    python -m rag_server
}
catch {
    Write-Status "Server stopped: $_" "Error"
    exit 1
}

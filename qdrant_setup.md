# Qdrant Setup Guide (Windows)

This guide covers setting up Qdrant as a portable Windows binary.

## Download Qdrant

1. Visit the [Qdrant Releases Page](https://github.com/qdrant/qdrant/releases)
2. Download the latest Windows binary: `qdrant-x86_64-pc-windows-msvc.zip`
3. Extract to `C:\qdrant\`

Your structure should look like:
```
C:\qdrant\
├── qdrant.exe
├── config/
│   └── config.yaml
└── storage/  (created automatically)
```

## Configuration

Create `C:\qdrant\config\config.yaml`:

```yaml
service:
  # HTTP API port
  http_port: 6333
  
  # gRPC port (optional)
  grpc_port: 6334
  
  # Enable CORS for local development
  enable_cors: true

storage:
  # Where to store vector data
  storage_path: ./storage
  
  # Performance settings
  optimizers_config:
    indexing_threshold: 10000

log_level: INFO
```

## Start Qdrant

### Option 1: Command Line (Foreground)

```powershell
cd C:\qdrant
.\qdrant.exe
```

### Option 2: Background Process

```powershell
cd C:\qdrant
Start-Process -FilePath ".\qdrant.exe" -WindowStyle Hidden
```

### Option 3: Windows Service (Advanced)

Use [NSSM](https://nssm.cc/) to install Qdrant as a Windows service:

```powershell
# Download NSSM
# Install service
nssm install Qdrant "C:\qdrant\qdrant.exe"
nssm set Qdrant AppDirectory "C:\qdrant"
nssm start Qdrant
```

## Verify Installation

Open browser or use curl:

```powershell
# Check health
curl http://localhost:6333/health

# Check collections
curl http://localhost:6333/collections
```

Expected response:
```json
{
  "title": "qdrant - vector search engine",
  "version": "1.x.x"
}
```

## Create Collection (Manual)

If auto-creation doesn't work, create manually:

```powershell
$body = @{
    vectors = @{
        size = 768
        distance = "Cosine"
    }
} | ConvertTo-Json

Invoke-RestMethod -Method Put `
    -Uri "http://localhost:6333/collections/documents" `
    -Body $body `
    -ContentType "application/json"
```

## Troubleshooting

### Port Already in Use

```powershell
# Find process using port 6333
Get-NetTCPConnection -LocalPort 6333 | Select-Object OwningProcess
Get-Process -Id <PID>

# Kill process if needed
Stop-Process -Id <PID> -Force
```

### Storage Permissions

Ensure `C:\qdrant\storage\` is writable:

```powershell
# Set permissions
icacls "C:\qdrant\storage" /grant Users:F
```

### Firewall Issues

Add firewall rule:

```powershell
New-NetFirewallRule -DisplayName "Qdrant" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 6333 `
    -Action Allow
```

## Performance Tips

1. **SSD Storage**: Place `storage/` on SSD for better performance
2. **Memory**: Allocate sufficient RAM (4GB+ recommended)
3. **Indexing**: Adjust `indexing_threshold` based on dataset size

## RAG Server Integration

The RAG server will automatically:
1. Check if Qdrant is running on port 6333
2. Create collections if they don't exist
3. Set vector dimensions to 768 (nomic-embed-text-v1.5)

## Alternative: Qdrant Cloud

If you prefer cloud hosting:

1. Sign up at [Qdrant Cloud](https://cloud.qdrant.io)
2. Create a cluster
3. Get API key and URL
4. Configure RAG server:

```powershell
$env:RAG_QDRANT_URL = "https://xyz.aws.cloud.qdrant.io:6333"
$env:RAG_QDRANT_API_KEY = "your-api-key"
```

## Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant GitHub](https://github.com/qdrant/qdrant)
- [Python Client Docs](https://github.com/qdrant/qdrant-client)

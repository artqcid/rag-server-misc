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
  # Enable the Web UI Dashboard at /dashboard
  enable_static_content: true
  
  # HTTP API port
  http_port: 6333
  
  # gRPC port (optional)
  grpc_port: 6334

storage:
  # WICHTIG: Absoluter Pfad um Datenverlust zu verhindern!
  # Relativer Pfad (./storage) hängt vom Arbeitsverzeichnis ab
  storage_path: C:/qdrant/storage
  
  # Snapshots path (absolut)
  snapshots_path: C:/qdrant/snapshots

log_level: INFO
```

> ⚠️ **WICHTIG**: Verwenden Sie **absolute Pfade** für `storage_path`!  
> Bei relativen Pfaden (`./storage`) kann Qdrant je nach Arbeitsverzeichnis  
> beim Start einen anderen Storage-Ordner verwenden und Daten "verschwinden".

## Web UI Dashboard

Das Dashboard erfordert die statischen Dateien:

```powershell
# Download Web UI
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri "https://github.com/qdrant/qdrant-web-ui/releases/download/v0.1.32/dist-qdrant.zip" -OutFile "C:\qdrant\dist-qdrant.zip"

# Extrahieren
Expand-Archive -Path "C:\qdrant\dist-qdrant.zip" -DestinationPath "C:\qdrant" -Force

# Struktur sollte sein:
# C:\qdrant\
# ├── static\
# │   ├── index.html
# │   ├── assets\
# │   └── ...
```

Nach dem Start ist das Dashboard unter **http://localhost:6333/dashboard** erreichbar.

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

---

## Collection Management

### Collection erstellen

```powershell
$body = '{"vectors":{"size":768,"distance":"Cosine"}}'
Invoke-RestMethod -Uri "http://localhost:6333/collections/juce-docs" -Method PUT -Body $body -ContentType "application/json"
```

### Collections auflisten

```powershell
Invoke-RestMethod -Uri "http://localhost:6333/collections"
```

### Alle Punkte in einer Collection löschen

```powershell
Invoke-RestMethod -Uri "http://localhost:6333/collections/juce-docs/points/delete" -Method POST -Body '{"filter":{}}' -ContentType "application/json"
```

### Collection komplett löschen

```powershell
Invoke-RestMethod -Uri "http://localhost:6333/collections/juce-docs" -Method DELETE
```

### Punkte zählen

```powershell
(Invoke-RestMethod -Uri "http://localhost:6333/collections/juce-docs").result.points_count
```

---

## n8n Workflow Integration

Für die JUCE-Dokumentations-Ingestion wird n8n mit 3 Tiers verwendet.

### Metadaten-Schema

Der RAG Server erwartet folgendes Format:

```json
{
  "documents": [
    {
      "content": "Der eigentliche Text...",
      "metadata": {
        "source": "web",
        "url": "https://juce.com/tutorials/...",
        "title": "Tutorial Title",
        "doc_type": "tutorial",
        "library": "JUCE",
        "module": "tutorial_name",
        "symbol": null,
        "symbol_type": null,
        "chunk": 1
      }
    }
  ],
  "collection": "juce-docs"
}
```

### Tier 1: Overview Pages (Code Node)

```javascript
const results = [];

for (const item of $input.all()) {
  const text = item.json.content || '';
  const url = item.json.url || '';
  
  // Bestimme Typ basierend auf URL
  let docType = 'overview';
  if (url.includes('modules')) docType = 'modules';
  if (url.includes('classes')) docType = 'class-index';
  if (url.includes('annotated')) docType = 'annotated';
  if (url.includes('hierarchy')) docType = 'hierarchy';
  
  // Titel aus URL ableiten
  const pageName = url.split('/').pop().replace('.html', '').replace(/_/g, ' ');
  const title = `JUCE ${docType} - ${pageName}`;
  
  // Content bereinigen
  const cleanContent = text
    .replace(/\s+/g, ' ')
    .replace(/Loading\.\.\..*?No Matches/g, '')
    .trim();
  
  if (cleanContent.length > 100) {
    const chunkSize = 4000;
    for (let i = 0; i < cleanContent.length; i += chunkSize) {
      const chunk = cleanContent.slice(i, i + chunkSize);
      results.push({
        json: {
          content: chunk,
          metadata: {
            source: "web",
            url: url,
            title: title,
            doc_type: docType,
            library: "JUCE",
            module: docType,
            chunk: Math.floor(i / chunkSize) + 1
          }
        }
      });
    }
  }
}

return results;
```

### Tier 2: Tutorials (Code Node)

```javascript
const results = [];

for (const item of $input.all()) {
  const text = item.json.content || '';
  const title = item.json.title || 'JUCE Tutorial';
  const url = item.json.url || '';
  
  // Tutorial-Name aus URL extrahieren
  const tutorialName = url.split('/').pop().replace('.html', '').replace('tutorial_', '').replace(/_/g, ' ');
  
  // Content bereinigen
  const cleanContent = text
    .replace(/\s+/g, ' ')
    .replace(/Loading\.\.\..*?No Matches/g, '')
    .trim();
  
  if (cleanContent.length > 100) {
    const chunkSize = 4000;
    for (let i = 0; i < cleanContent.length; i += chunkSize) {
      const chunk = cleanContent.slice(i, i + chunkSize);
      results.push({
        json: {
          content: chunk,
          metadata: {
            source: "web",
            url: url,
            title: title || tutorialName,
            doc_type: "tutorial",
            library: "JUCE",
            module: tutorialName,
            chunk: Math.floor(i / chunkSize) + 1
          }
        }
      });
    }
  }
}

return results;
```

### Tier 3: Class References (Code Node)

```javascript
const results = [];

for (const item of $input.all()) {
  const text = item.json.content || '';
  const className = item.json.className || '';
  const url = item.json.url || '';
  
  const classNameFromUrl = url.split('/').pop().replace('.html', '').replace('class', '');
  const displayName = className || classNameFromUrl;
  
  const cleanContent = text
    .replace(/\s+/g, ' ')
    .replace(/Loading\.\.\..*?No Matches/g, '')
    .trim();
  
  let module = 'juce_core';
  if (classNameFromUrl.includes('Audio')) module = 'juce_audio_basics';
  if (classNameFromUrl.includes('Midi')) module = 'juce_audio_basics';
  if (classNameFromUrl.includes('Synth')) module = 'juce_audio_basics';
  if (classNameFromUrl.includes('Component') || classNameFromUrl.includes('Button') || classNameFromUrl.includes('Slider')) module = 'juce_gui_basics';
  if (classNameFromUrl.includes('dsp')) module = 'juce_dsp';
  
  if (cleanContent.length > 100) {
    const chunkSize = 4000;
    for (let i = 0; i < cleanContent.length; i += chunkSize) {
      const chunk = cleanContent.slice(i, i + chunkSize);
      results.push({
        json: {
          content: chunk,
          metadata: {
            source: "web",
            url: url,
            title: displayName,
            doc_type: "class-reference",
            library: "JUCE",
            module: module,
            symbol: displayName,
            symbol_type: "class",
            chunk: Math.floor(i / chunkSize) + 1
          }
        }
      });
    }
  }
}

return results;
```

### Prepare Request (Code Node - alle Tiers)

```javascript
return [{
  json: {
    documents: $input.all().map(item => ({
      content: item.json.content,
      metadata: {
        source: item.json.metadata.source,
        url: item.json.metadata.url,
        title: item.json.metadata.title || item.json.metadata.module,
        doc_type: item.json.metadata.doc_type,
        library: item.json.metadata.library || "JUCE",
        module: item.json.metadata.module,
        symbol: item.json.metadata.symbol || null,
        symbol_type: item.json.metadata.symbol_type || null,
        chunk: item.json.metadata.chunk || 1
      }
    })),
    collection: "juce-docs"
  }
}];
```

### Batching für große Requests

Bei vielen Dokumenten (>50) sollte ein **Loop Over Items** Node verwendet werden:
- Batch Size: **30**
- Timeout im HTTP Request Node: **180000** (3 Minuten)

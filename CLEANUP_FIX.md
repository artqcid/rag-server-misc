# RAG Server Cleanup Fix

## Problem
Der RAG Server (und andere Server wie Embedding, MCP) liefen weiter, wenn VS Code beendet wurde.

## Ursache
Die Start-Skripte haben Python-Prozesse direkt mit `&` aufgerufen, ohne sie als Subprozesse zu verwalten. Dies führte dazu, dass bei Beendigung des PowerShell-Tasks die Python-Prozesse nicht sauber beendet wurden.

## Lösung

### 1. Primäre Lösung (Implementiert)
Die Start-Skripte wurden aktualisiert, um Prozesse mit `Start-Process -PassThru` zu starten und mit `WaitForExit()` auf die Beendigung zu warten. Dies ermöglicht:
- Saubere Beendigung bei Ctrl+C
- Automatische Bereinigung beim Beenden des Tasks
- Ordnungsgemäße Ressourcenfreigabe

**Betroffene Dateien:**
- `rag-server-misc/start.ps1` ✅
- `embedding-server-misc/start.ps1` ✅
- `mcp-server-misc/start-sse.ps1` ✅

### 2. Zusätzliche Cleanup-Skripte
Falls noch Prozesse laufen:
- `~/.continue/cleanup-on-exit.ps1` - Manueller Cleanup aller Server
- `~/.continue/vscode-autostart-manager.ps1` - Monitort VS Code und beendet Server beim Schließen

### Verwendung
```powershell
# Manueller Cleanup
& "C:\Users\marku\.continue\cleanup-on-exit.ps1"
```

## Testen
Nach den Änderungen:
1. Starten Sie die RAG-Server: `Start Rag Server` Task
2. Beenden Sie VS Code (oder drücken Sie Ctrl+C im Terminal)
3. Prüfen Sie, ob die Python-Prozesse beendet wurden:
   ```powershell
   Get-Process python | Where-Object { $_.CommandLine -like '*rag*' }
   ```

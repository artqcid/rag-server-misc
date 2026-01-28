# PowerShell-Skript: Prüft alle URLs in allen RAG-Kontexten
# Ausführen im Verzeichnis: rag-server-misc

$contextDir = "rag_server/indexing/contexts"
$contextFiles = Get-ChildItem -Name "$contextDir/*.json"
foreach ($file in $contextFiles) {
    $ctx = $file -replace ".json$", ""
    Write-Host "==== Prüfe Kontext: $ctx ===="
    python -m rag_server.indexing.cli verify $ctx
}

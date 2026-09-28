$env:PATH = "$env:LOCALAPPDATA\Programs\node24;$env:PATH"
$env:N8N_DIAGNOSTICS_ENABLED = "false"
$env:N8N_HIRING_BANNER_ENABLED = "false"
$nodeExe = "$env:LOCALAPPDATA\Programs\node24\node.exe"
$n8nBin = "$env:LOCALAPPDATA\Programs\node24\node_modules\n8n\bin\n8n"
& $nodeExe $n8nBin start

# Script tự động đọc dữ liệu từ Google Sheets và phát tin nhắn nhắc việc qua OpenClaw
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $currentDir) { $currentDir = Get-Location }
$groupId = "group:2327925421752384731"

Push-Location $currentDir
try {
    # 1. Đọc dữ liệu từ Google Sheets
    $tasksMsg = (python test_workflow.py | Out-String).Trim()
    
    # 2. Gửi vào nhóm Zalo qua OpenClaw
    if ($tasksMsg -and $tasksMsg.Length -gt 10) {
        Write-Host "Đang gửi báo cáo nhiệm vụ vào nhóm Zalo..."
        openclaw message send --channel zalouser --target $groupId --message "$tasksMsg"
        Write-Host "✅ ĐÃ GỬI BÁO CÁO NHIỆM VỤ THÀNH CÔNG TỪ GOOGLE SHEETS VÀO NHÓM ZALO!"
    } else {
        Write-Host "❌ Không lấy được dữ liệu nhiệm vụ từ Google Sheets."
    }
} finally {
    Pop-Location
}

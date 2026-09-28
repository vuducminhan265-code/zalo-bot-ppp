# Function department/zalo_service/setup_zalo_service_startup.ps1
# Creates Windows Task Scheduler Tasks for Auto-booting Zalo Bot & Scheduler on Windows Login

$actionBot = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "-m Function_department.zalo_service.zalo_bot_service" -WorkingDirectory "D:\Personal\Công việc\PPP - Sở Tài Chính\Self-Study\Zalo Bot"
$actionSched = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "-m Function_department.zalo_service.auto_scheduler" -WorkingDirectory "D:\Personal\Công việc\PPP - Sở Tài Chính\Self-Study\Zalo Bot"

$trigger = New-ScheduledTaskTrigger -AtLogOn

Register-ScheduledTask -TaskName "ZaloBot_Service_AutoStart" -Action $actionBot -Trigger $trigger -Description "Auto-starts Zalo Bot Service on Windows Login" -Force | Out-Null
Register-ScheduledTask -TaskName "ZaloBot_Scheduler_AutoStart" -Action $actionSched -Trigger $trigger -Description "Auto-starts Zalo Automated Task Scheduler on Windows Login" -Force | Out-Null

Write-Output "Successfully registered Windows Task Scheduler tasks for Zalo Bot & Auto Scheduler!"

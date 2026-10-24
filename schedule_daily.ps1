# Run collect.py every day with the Windows Task Scheduler.
#
#   .\schedule_daily.ps1               every day at 08:00
#   .\schedule_daily.ps1 -At 21:30     every day at 21:30
#   .\schedule_daily.ps1 -Remove       stop the daily collection
#
# The task runs for the current user only. If the computer is off at that time,
# it runs as soon as possible afterwards. Logs: logs\collect.log

param(
    [string]$At = "08:00",
    [switch]$Remove
)

$TaskName = "EcomCheck daily collect"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Removed the task '$TaskName'."
    return
}

$Root = $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "Python not found at $Python. Create the virtual environment first (see README)."
    return
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument "collect.py" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Collect Tiki prices for the keywords in keywords.txt (EcomCheck)" -Force | Out-Null
Write-Output "Registered '$TaskName': every day at $At. Logs: $Root\logs\collect.log"

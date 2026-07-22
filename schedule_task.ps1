$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "$PSScriptRoot\master_workflow.py"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 7:00am
$Settings = New-ScheduledTaskSettingsSet
$Principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

Register-ScheduledTask -TaskName "DailyMarketReport" -InputObject $Task -Force

Write-Host "Task 'DailyMarketReport' scheduled successfully for Mon-Fri at 7:00 AM."

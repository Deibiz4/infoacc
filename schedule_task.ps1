$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "d:\Docker\infoacc\daily_workflow.py"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 8:30am
$Settings = New-ScheduledTaskSettingsSet
$Principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

Register-ScheduledTask -TaskName "DailyMarketReport" -InputObject $Task

Write-Host "Task 'DailyMarketReport' scheduled successfully for Mon-Fri at 8:30 AM."

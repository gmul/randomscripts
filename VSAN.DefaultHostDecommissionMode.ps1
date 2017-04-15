
########################################
# Synopsis: Set the Host Decommission Mode on all hosts in a cluster
# Author: Greg Mulholland
# Version: 1.0

# Disclaimer: This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY


$message = write-host "This script will set the Host Decommission Mode to be used when entering Maintenance Mode." -fore cyan
$vcenter = Read-Host "Please provide vCenter Server (FQDN or IP) to connect to"
Connect-VIServer $vcenter -credential ( Get-Credential ) -WarningAction Silentlycontinue | Out-Null

$cluster = Read-Host "Please provide the vSAN cluster name"
$vmhosts = Get-VMHost -Location $cluster


$question     = "Which Host Decommission Mode would you like to configure?"
                   $choices = New-Object Collections.ObjectModel.Collection[Management.Automation.Host.ChoiceDescription]
                   $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList '&EnsureAccessibility'))
                   $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList '&FullDataMigration'))
                   $choices.Add((New-Object Management.Automation.Host.ChoiceDescription -ArgumentList '&None'))
                   $decision     = $Host.UI.PromptForChoice($message, $question, $choices, 0)

ForEach ($vmhost in $vmhosts)
  {
    Get-AdvancedSetting -Entity (Get-VMHost) -Name "VSAN.DefaultHostDecommissionMode" | Set-AdvancedSetting -Value $decision -Confirm:$false | Out-Null
  }

Write-host "Setting Host Decommission Mode on all hosts in @cluster .. Please wait"
sleep 3
Write-Host "Successfully set VSAN.DefaultHostDecommissionMode on all hosts"
sleep 2
Write-Host "Disconnecting from vCenter Server $vcenter"
Disconnect-VIServer $vCenter -Confirm:$false
Write-Host "Script Complete"

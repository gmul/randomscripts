
#$message = write-host "This script will set the Host Decommission Mode to be used when entering Maintenance Mode." -fore cyan
#$vcenter = Read-Host "Please provide vCenter Server (FQDN or IP) to connect to"
#Connect-VIServer -server 10.192.104.232

#$cluster = Read-Host "Please provide the vSAN cluster name"
#$cluster = get-cluster -name "VSAN"
#$vmhosts = Get-VMHost -Location $cluster$RuleSet = "GoldRuleSet"
$Rule = (New-SpbmRule -Capability VSAN.hostFailuresToTolerate 1)
$RuleSetRules = (New-SpbmRuleSet -Name $RuleSet -AllOfRules @(($Rule)))
New-SpbmStoragePolicy -Name $StoragePolicy -RuleSet $RuleSet
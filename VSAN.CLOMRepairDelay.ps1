# Synopsis: Set ClomRepairDelay on all hosts in cluster
#Rename to .ps1
# Download plink and put it in c:\temp http://the.earth.li/~sgtatham/putty/latest/x86/plink.exe

Write-host "Checked for VMware PowerCLI Powershell plugin, already loaded."
}
$vCenter = Read-Host "Provide vCenter Server"
Connect-VIServer $vCenter -credential ( Get-Credential ) -WarningAction Silentlycontinue | Out-Null
$cluster = Read-Host "Enter VSAN Cluster name"
$clomdelay = Read-Host "Enter the delay time (in minutes)"
Get-VMHost | Get-AdvancedSetting -name "VSAN.ClomRepairDelay" | Out-Null
Get-AdvancedSetting -Entity (Get-VMHost) -Name "VSAN.ClomRepairDelay" | Set-AdvancedSetting -Value $clomdelay -Confirm:$false | Out-Null 
Write-Host "Setting VSAN.ClomRepairDelay to $clomdelay minutes on each host"
#
$hostpass = Read-Host "Please enter root password for the ESXi hosts"
$str1=’ECHO Y | c:\temp\plink.exe -pw $hostpass -l root ‘
$str2=’ /etc/init.d/clomd restart 2>&1’
$outfile=’c:\temp\report.txt'
    foreach($esxentry in (Get-VMHost|?{$_.Powerstate -eq “PoweredOn”})){
    $esxhost=”‘”+$esxentry.name+”‘”
    $command=$str1+$esxhost+$str2
    $esxentry.name >> $outfile
    $result=Invoke-Expression -Command $command
     foreach($resultline in 1..$result.length){
        $result[$resultline] >> $outfile
          }
      }
#
Write-host "Restarting clomd service on all hosts.. Please wait"
sleep 10
Write-Host "VSAN.ClomRepairDelay set to $clomdelay"
sleep 3
Write-Host "Disconnected from $vcenter"
Disconnect-VIServer $vCenter -Confirm:$false
Write-Host "Script Complete"

#Set the VSAN Host autoclaim mode for VSAN. (This script disables autoclaim)
# Reference: http://www.virtuallyghetto.com/2013/09/additional-steps-required-to-completely.html
$hosts = Get-Cluster VSAN-Cluster | Get-VMHost
foreach($vihost in $hosts)
     {$esxcli = get-vmhost $vihost | Get-EsxCli
     $esxcli.vsan.storage.automode.set($true) | out-null}
Write-Host "Setting VSAN Disk AutoClaim Mode to 'False'"
sleep 5
Write-Host "Done"


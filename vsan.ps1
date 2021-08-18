import-module VMware.VimAutomation.Extensions
Connect-VIServer 172.16.78.191 -User root -Password vmware
$Datacenter = "DC01"
$Cluster = "VSAN Cluster"
$ESXHosts = "172.16.78.129", "172.16.78.130"
$ESXUser = "root"
$ESXPWD = "vmware"
$VMKNetforVSAN = "Management Network"

# If doesnt exist create the datacenter
If (-Not ($NewDatacenter = Get-Datacenter $Datacenter -ErrorAction SilentlyContinue)){
   Write-Host "Adding $Datacenter"
   $NewDatacenter = New-Datacenter -Name $Datacenter -Location (Get-Folder Datacenters)
}

# Create the initial cluster
if (-Not ($NewCluster = Get-Cluster $Cluster -ErrorAction SilentlyContinue)) {
   Write-Host "Adding $Cluster"
   $NewCluster = New-Cluster -Name $Cluster -Location $NewDatacenter
}

# For each of our hosts
$ESXHosts | Foreach {
   Write-Host "Adding $($_) to $($NewCluster)"
   # Add them to the cluster
   $AddedHost = Add-VMHost -Name $_ -Location $NewCluster -User $ESXUser -Password $ESXPWD -Force
   # Check to see if they have a VSAN enabled VMKernel
   $VMKernel = $AddedHost | Get-VMHostNetworkAdapter -VMKernel | Where {$_.PortGroupName -eq $VMKNetforVSAN }
   $IsVSANEnabled = $VMKernel | Where { $_.VsanTrafficEnabled}
   # If it isnt Enabled then Enable it
   If (-not $IsVSANEnabled) {
      Write-Host "Enabling VSAN Kernel on $VMKernel"
      $VMKernel | Set-VMHostNetworkAdapter -VsanTrafficEnabled $true -Confirm:$false | Out-Null
   } Else {
      Write-Host "VSAN Kernel already enabled on $VmKernel"
      $IsVSANEnabled | Select VMhost, DeviceName, IP, PortGroupName, VSANTrafficEnabled
   }
}
# Enable VSAN on the cluster and set to Automatic Disk Claim Mode
Write-Host "Enabling VSAN on $NewCluster"
$VSANCluster = $NewCluster | Set-Cluster -VsanEnabled:$true -VsanDiskClaimMode Automatic -Confirm:$false -ErrorAction SilentlyContinue
If ($VSANCluster.VSANEnabled){
   Write-Host "VSAN cluster $($VSANCLuster.Name) created in $($VSANCluster.VSANDiskClaimMode) configuration"
   Write-Host "The following Hosts and Disk Groups now exist:"
   Get-VsanDiskGroup | Select VMHost, Name | FT -AutoSize
   Write-Host "The following VSAN Datastore now exists:"
   Get-Datastore | Where {$_.Type -eq "vsan"} | Select Name, Type, FreeSpaceGB, CapacityGB
} Else {
   Write-Host "Something went wrong, VSAN not enabled"
}

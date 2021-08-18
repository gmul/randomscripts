#=================================================================================================================
# AUTHOR:  	Greg Mulholland
# DATE:    	13/07/2016
# Version: 	1.0
# COMMENT: 	This script connects to vCenter and will return all WWN's for ESX(i) hosts
# USAGE:    Enter the hostnsames or IPs for Each FD in $FD1hosts etc.
#=================================================================================================================

#$vcenter = Read-Host "Please provide vCenter Server (FQDN or IP) to connect to"
#Connect-VIServer -server 10.192.104.232


$FD1Hosts = “10.192.100.98”, "10.192.102.249”
$FD2Hosts = “10.192.117.135”, "10.192.121.192"
$FD3Hosts = "10.192.124.191", "10.192.97.1"

write-host -foregroundcolor cyan "Creating new Fault Domains and moving hosts."
  
Foreach ($fdhost in $fd1hosts){
                New-VsanFaultDomain –vmhost $fdhost –name "Rack1" 
}
 
Foreach ($fdhost in $fd2hosts){
                New-VsanFaultDomain –vmhost $fdhost –name "Rack2" 
}

Foreach ($fdhost in $fd1hosts){
                New-VsanFaultDomain –vmhost $fdhost –name "Rack" 
}

write-host -foregroundcolor yellow "Hosts moved into Fault Domains"
#Get-VsanFaultDomain | ft -AutoSize
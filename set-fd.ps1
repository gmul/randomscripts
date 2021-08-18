
#$message = write-host "This script will set the Host Decommission Mode to be used when entering Maintenance Mode." -fore cyan
#$vcenter = Read-Host "Please provide vCenter Server (FQDN or IP) to connect to"
#Connect-VIServer -server 10.192.104.232

#$cluster = Read-Host "Please provide the vSAN cluster name"
#$cluster = get-cluster -name "VSAN"
#$vmhosts = Get-VMHost -Location $cluster



#function vmcreation {

#    $vmcreationtest = Test-vsanvmcreation -cluster $cluster
#    $vmcreationresult = $vmcreationtest | ft CLuster, Status
#}

#write-host -foregroundcolor cyan ">>> Running Network Performance Test"
#get-cluster $cluster | network
#write-host -foregroundcolor yellow ">>> Network Performance Test Results"
#write-output $networkresultcon



$MyHosts = Get-VMHost 

ForEach ($VMHost in $MyHosts) 	
	{    
		New-VsanFaultDomain -VMHost $MyHosts[0], $MyHosts[1] -Name "FD1";
        New-VsanFaultDomain -VMHost $MyHosts[2], $MyHosts[3] -Name "FD2";
        New-VsanFaultDomain -VMHost $MyHosts[4], $MyHosts[5] -Name "FD3";#

	}


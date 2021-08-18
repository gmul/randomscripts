
#$message = write-host "This script will set the Host Decommission Mode to be used when entering Maintenance Mode." -fore cyan
#$vcenter = Read-Host "Please provide vCenter Server (FQDN or IP) to connect to"
#Connect-VIServer $vcenter -credential ( Get-Credential ) -WarningAction Silentlycontinue | Out-Null

#$cluster = Read-Host "Please provide the vSAN cluster name"
$cluster = get-cluster -name "VSAN"
#$vmhosts = Get-VMHost -Location $cluster

#Step Function

function network {

    $networktest = Test-VsanNetworkPerformance -cluster $cluster
    $networkresult = $networktest | ft CLuster, Status, TimeOfTest, CauseOfFailure
   

}


function vmcreation {

    $vmcreationtest = Test-vsanvmcreation -cluster $cluster
    $vmcreationresult = $vmcreationtest | ft CLuster, Status
}

write-host -foregroundcolor cyan ">>> Running Network Performance Test"
get-cluster $cluster | network
write-host -foregroundcolor yellow ">>> Network Performance Test Results"
write-output $networkresult

#write-host -foregroundcolor cyan ">>> Running VM Creation Tests"
#get-cluster $cluster | vmcreation
#write-host -foregroundcolor yellow ">>> VM Creation Test Results"
#write-output $vmcreactionresult

if($networkresult.status -eq "Failed")
    write-host "One of more tests failed. View the Health Service for further details"
else
 write-host "All tests passed"
 

#function ShowResults {
# 
        #Show me first
 #       write-host -foregroundcolor yellow ">>> Running "

  #      write-host "Press a key to run the command..."
        #wait for a keypress to continue
   #     $junk = [console]::ReadKey($true)

        #execute (dot source) me in global scope
 #       . $step
    #}
#}

#$vmcreationtest = Test-VsanVMCreation  -cluster $cluster
 #   $vmcreationresult = $vmcreationtest | ft Cluster, HostResult, Status, CauseOfFailure
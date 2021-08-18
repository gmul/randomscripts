Function Get-VsanClusterObjectUtilization {
    param(
        [Parameter(
            Mandatory=$true)
        ]
        [String]$ClusterName
    )

    Function Get-VSANDiskMapping {
        param(
            [Parameter(Mandatory=$true)]$vmhost
        )
        $vsanSystem = Get-View ($vmhost.ExtensionData.ConfigManager.VsanSystem)
        $vsanDiskMappings = $vsanSystem.config.storageInfo.diskMapping

        $diskGroupCount = 1
        $diskGroupObjectCount = 0
        $diskGroupObjectSize = 0
        $diskGroups = @{}
        foreach ($disk in $vsanDiskMappings) {
            #Write-Host "`tDiskGroup $diskGroupCount"
            $hdds = $disk.nonSsd
            foreach ($hdd in $hdds) {
                $diskHDD = $hdd.VsanDiskInfo.VsanUuid
                if($global:diskInfo[$diskHDD]) {
                    $diskGroupObjectCount += $global:diskInfo[$diskHDD].totalComponents
                    $diskGroupObjectSize += $global:diskInfo[$diskHDD].used
                    $global:clusterTotalObjects += $global:diskInfo[$diskHDD].totalComponents
                    $global:clusterTotalObjectSize += $global:diskInfo[$diskHDD].used
                }
                #Write-Host "`t`tHDD: $diskHDD"
            }
            #Write-Host "`t`tNumObjects: $diskGroupObjectCount"
            #Write-Host "`t`tObjectSize: $size GB"

            $diskGroupData = [pscustomobject] @{
                numObjects = $diskGroupObjectCount
                used = $diskGroupObjectSize
            }
            $diskGroups.add($diskGroupCount,$diskGroupData)

            $diskGroupObjectCount = 0
            $diskGroupObjectSize = 0
            $diskGroupCount+=1
        }
        $global:clusterResults.add($vmhost.name,$diskGroups)
    }

    Function BuildDiskInfo {
        $randomVmhost = Get-Cluster -Name $ClusterName | Get-VMHost | Select -First 1
        $vsanIntSys = Get-View ($randomVmhost.ExtensionData.ConfigManager.VsanInternalSystem)
        $results = $vsanIntSys.QueryPhysicalVsanDisks($null)
        $json = $results | ConvertFrom-Json


        foreach ($line in $json | Get-Member -MemberType NoteProperty) {
            $tmpObj = [pscustomobject] @{
                totalComponents = $json.$($line.Name).numTotalComponents
                dataComponents = $json.$($line.Name).numDataComponents
                witnessComponents = ($json.$($line.Name).numTotalComponents - $json.$($line.Name).numDataComponents)
                capacity = $json.$($line.Name).capacity
                used = $json.$($line.Name).physCapacityUsed
            }
            $global:diskInfo.Add($json.$($line.Name).uuid,$tmpObj)
        }
    }

    $cluster = Get-Cluster -Name $ClusterName -ErrorAction SilentlyContinue
    if($cluster -eq $null) {
        Write-Host -ForegroundColor Red "Error: Unable to find vSAN Cluster $ClusterName ..."
        break 
    }

    $global:clusterResults = @{}
    $global:clusterTotalObjects =  0
    $global:clusterTotalObjectSize = 0
    $global:diskInfo = @{}
    BuildDiskInfo

    foreach ($vmhost in $cluster | Get-VMHost) {
        #Write-Host "`n"$vmhost.name
        Get-VSANDiskMapping -vmhost $vmhost
    }

    Write-Host "`nTotal vSAN Components: $global:clusterTotalObjects"
    $size = [math]::Round(($global:clusterTotalObjectSize / 1GB),2)
    Write-Host "Total vSAN Components Used Space: $size GB"

    foreach ($vmhost in $global:clusterResults.keys | Sort-Object) {
        Write-Host "`n"$vmhost
        foreach ($diskgroup in $global:clusterResults[$vmhost].keys | Sort-Object) {
            Write-Host "`tDiskgroup $diskgroup"

            $numbOfObjects = $clusterResults[$vmhost][$diskgroup].numObjects
            $objPercentage = [math]::Round(($numbOfObjects / $global:clusterTotalObjects) * 100,2)
            Write-host "`t`tComponents: $numbOfObjects ($objPercentage%)"

            $objectsUsed = $clusterResults[$vmhost][$diskgroup].used
            $objectsUsedRounded = [math]::Round(($clusterResults[$vmhost][$diskgroup].used / 1GB),2)
            $usedPertcentage =[math]::Round(($objectsUsed / $global:clusterTotalObjectSize) * 100,2) 
            Write-host "`t`tUsedSpace: $objectsUsedRounded GB ($usedPertcentage%)"
        }
    }
    Write-Host
}

#Connect-VIServer -Server vcenter65-1.primp-industries.com -User administrator@vsphere.local -Password VMware1!
#Connect-VIServer -Server mgmt01vc01.sfo01.rainpole.local -User administrator@vsphere.local -Password VMware1!

#$ClusterName = "SFO01-Mgmt01"
$ClusterName = "VSAN-Cluster"
Get-VsanClusterObjectUtilization -ClusterName $ClusterName
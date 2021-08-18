
#lamw example
PS C:\Users\lamw> $cluster = "VSAN-Cluster"
$cluster_view = (Get-Cluster -Name $cluster).ExtensionData.MoRef

$vpm = Get-VSANView -Id "VsanPerformanceManager-vsan-performance-manager"

$spec = New-Object VMware.Vsan.Views.VsanPerfQuerySpec
$spec.EntityRefId = "disk-group:52803424-642d-9efc-44eb-48feeea13c18"
$spec.Labels = @("com.vmware.vsan.perf.graph.disk-group.latResync")
$vpm.VsanPerfQueryPerf(@($spec),$cluster_view


############################################################################################## 

##VsanSpaceReportSystem
#VsanQuerySpaceUsage
#spaceDetail



PS C:\Users\lamw> $cluster = "VSAN-Cluster"
$cluster_view = (Get-Cluster -Name $cluster).ExtensionData.MoRef

$vpm = Get-VSANView -Id "VsanPerformanceManager-vsan-performance-manager"

$spec = New-Object VMware.Vsan.Views.VsanPerfQuerySpec
$spec.EntityRefId = "disk-group:52803424-642d-9efc-44eb-48feeea13c18"
$spec.Labels = @("com.vmware.vsan.perf.graph.disk-group.latResync")
$vpm.VsanPerfQueryPerf(@($spec),$cluster_view)



#####get-spaceusage

#Methods
#VsanSpaceReportSystem
#VsanQuerySpaceUsage
#spaceDetail

$cluster = "VSAN-Cluster"
$cluster_view = (Get-Cluster -Name $cluster).ExtensionData.MoRef
$vrs = Get-VSANView -Id "VsanSpaceReportSystem-vsan-cluster-space-report-system"
#$spec = New-Object VMware.Vsan.Views.VsanQuerySpaceUsage
$spacereport=$vrs.vsanqueryspaceusage($Cluster.ExtensionData.MoRef).totalCapacityB


########get-objecthealth

#mo - VsanObjectSystem
#Data Object -VsanObjectInformation
#Properties   - vsanHealth
#type  spbmComplianceResult

$cluster = "VSAN-Cluster"
$cluster_view = (Get-Cluster -Name $cluster).ExtensionData.MoRef
$voi = Get-VSANView -Id "VsanObjectInformation-vsan-cluster-object-information"
$objectinfo = $voi.vsanHealth




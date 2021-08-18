#get disk group info



$cluster = "VSAN-Cluster"
$cluster_view = (Get-Cluster -Name $cluster).ExtensionData.MoRef

$vpm = Get-VSANView -Id "VsanPerformanceManager-vsan-performance-manager"

$spec = New-Object VMware.Vsan.Views.VsanPerfQuerySpec
$spec.EntityRefId = "disk-group:52803424-642d-9efc-44eb-48feeea13c18"
$spec.Labels = @("com.vmware.vsan.perf.graph.disk-group.latResync")
$vpm.VsanPerfQueryPerf(@($spec),$cluster_view)
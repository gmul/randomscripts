########################################
# Synopsis: Sample script to move hosts into fault domain
# Author: Greg Mulholland
# Version: 1.0

# Disclaimer: This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY
# Usage: Enter hosts names or IPs beloww also replace FD1 etc with Fault Domain Host name.

$FD1Hosts = “10.192.100.98”, "10.192.102.249”
$FD2Hosts = “10.192.117.135”, "10.192.121.192"
$FD3Hosts = "10.192.124.191", "10.192.97.1"
  
Foreach ($fdhost in $fd1hosts){
                New-VsanFaultDomain –vmhost $fdhost –FD1
}
 
Foreach ($fdhost in $fd2hosts){
                New-VsanFaultDomain –vmhost $fdhost –FD2
}

Foreach ($fdhost in $fd1hosts){
                New-VsanFaultDomain –vmhost $fdhost –FD3
}


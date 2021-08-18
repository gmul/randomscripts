#!/bin/bash
# This script needs bash shell, it does not work with other shell like ksh, zsh, dash, etc.

esxBranch="$1"
vcBranch="$1"
esxBuildNum="$2"
vcBuildNum="$3"

if [[ -z "$esxBuildNum" ]]; then
    esxBuildNum="ob-latest"
fi

if [[ -z "$vcBuildNum" ]]; then
    vcBuildNum="ob-latest"
fi

# default root is the path of this script, change it to your real root
SCRIPT="$(readlink -f $0)"
ROOT_DIR="`dirname $SCRIPT`"

if [[ -z "$esxBranch" ]]; then
    esxBranch="vsphere60u2"
fi
if [[ -z "$vcBranch" ]]; then
    vcBranch="vsphere60u2"
fi

if [[ "$esxBuildNum" == ob-* ]]; then
    esxBuildType="release"
else
    #echo "if occur error, please try other buildtype, like obj"
    esxBuildType="beta"
fi

if [[ "$vcBuildNum" == ob-* ]]; then
    vcBuildType="release"
else
    #echo "if occur error, please try other buildtype, like obj"
    vcBuildType="beta"
fi

esxBuild="--build server:$esxBuildType:$esxBuildNum:$esxBranch"
vcBuild="--build cloudvm:$vcBuildType:$vcBuildNum:$vcBranch"

VMID=`LC_CTYPE=C tr -dc a-z0-9 < /dev/urandom | fold -w 6 | head -n 1`
WORKDIR="/tmp/nimbus-$USER/vsan-`date +%Y%m%d-%H%M%S`-$VMID"
mkdir -p $WORKDIR

NIMBUSCTL=/mts/git/bin/nimbus-ctl

cat << 'EOD' > $WORKDIR/deploy-spec.rb
oneGB = 1 * 1024 * 1024 # in KB
$testbed = Proc.new do
  testbed = {
    'name' => 'vsan-3esx-fullInstall',
    'esx' => (0..2).map do
      {
        'style' => 'fullInstall',
        'numMem' => 16 * 1024,
        'disks' => [ 80 * oneGB, 80 * oneGB, 80 * oneGB, 80 * oneGB ],
        'ssds' => [ 50 * oneGB ],
        'nics' => 4,
        'staf' => false,
        'desiredPassword' => 'ca$hc0w',
        'vmotionNics' => ['vmk0'],
        'freeLocalLuns' => 4,
      }
    end,

    'vc' => {
      'type' => 'vcva',
      'numMem' => 32 * 1024,
      'dbType' => 'embedded',
      'dcName' => 'VSAN-DC',
      'clusterName' => 'VSAN-Cluster',
      'addHosts' => 'allInSameCluster',
    },

    'nfs' => [
      {
        'name' => "nfs.0"
      },
    ],

    'vsan' => true,
  }

  testbed
end

testbedSpec = $testbed.call()
Nimbus::TestbedRegistry.registerTestbed testbedSpec
EOD

echo "`date +%Y-%m-%dT%H:%M:%S` Deploy vsan test bed, log files are in $WORKDIR ..."
echo "                    It may take 20 ~ 30 minutes to finish, please be patient"
/mts/git/bin/nimbus-testbeddeploy --testbedSpecRubyFile $WORKDIR/deploy-spec.rb \
    --lease 16 --runName "vsan2016-$VMID" $esxBuild $vcBuild --resultsDir $WORKDIR \
    --keepVMsOnFailure > $WORKDIR/vsandeploy.log 2>&1

# get IP addresses for deployed ESX and VC
vcip=""
nfsip=""
esxs=()

OIFS=$IFS
IFS=': '
while read pod vm ip ; do
    case $vm in
    *vsan2016-$VMID.vcva* )
        vcip=$ip
        ;;
    *vsan2016-$VMID.esx* )
        esxs+=($ip)
        ;;
    *vsan2016-$VMID.nfs* )
        nfsip=$ip
        ;;
    esac
done < <($NIMBUSCTL ip *vsan2016-$VMID*)
IFS=$OIFS

allesx=$(IFS=, ; echo "${esxs[*]}")

echo "`date +%Y-%m-%dT%H:%M:%S` ESX: $allesx VC: $vcip NFS: $nfsip"


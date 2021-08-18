#!/usr/bin/env python

#- * -coding: utf - 8 - * -
# python vsanhealth.py--host 10.160 .83 .91--user 'administrator@vsphere.local'--password 'Admin!23'


__author__ = 'VMware, Inc'
from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass
if sys.version[0] < '3':
       input = raw_input
import vsanmgmtObjects
import vsanapiutils

def GetArgs():

 parser = argparse.ArgumentParser(
  description = 'Process args for VSAN SDK sample application') 
 parser.add_argument('-s', '--host', required = True, action = 'store',
  help = 'Remote host to connect to')
 parser.add_argument('-o', '--port', type = int,
  default = 443, action = 'store',
  help = 'Port to connect on')
 parser.add_argument('-u', '--user', required = True, action = 'store',
  help = 'User name to use when connecting to host')
 parser.add_argument('-p', '--password', required = True, action = 'store',
  help = 'Password to use when connecting to host')
 parser.add_argument('-c', '--cluster', dest = 'clusterName', required=True, metavar="CLUSTER",
  action = 'store')
 args = parser.parse_args()
 return args

def getClusterInstance(clusterName, serviceInstance):
  content = serviceInstance.RetrieveContent()
  searchIndex = content.searchIndex
  datacenters = content.rootFolder.childEntity
  for datacenter in datacenters:
      cluster = searchIndex.FindChild(datacenter.hostFolder, clusterName)
  if cluster is not None:
   return cluster
  return None

# Start program
#def main():
args = GetArgs()
if args.password:
 password = args.password
else:
 password = getpass.getpass(prompt = 'Enter password for host %s and '
 'user %s: ' % (args.host, args.user))


# For python 2.7 .9 and later, the defaul SSL conext has more strict# connection handshaking rule.We may need turn of the hostname checking# and client side cert verification
context = None
if sys.version_info[: 3] > (2, 7, 8):
  context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

si = SmartConnect(host = args.host,
  user = args.user,
  pwd = password,
  port = int(args.port),
  sslContext = context)

atexit.register(Disconnect, si)

#
#for detecting whether the host is VC or ESXi
#if aboutInfo.apiType == 'VirtualCenter':
#majorApiVersion = aboutInfo.apiVersion.split('.')[0]
 #if int(majorApiVersion) < 6:
  #print('The Virtual Center with version %s (lower than 6.0) is not supported.' % aboutInfo.apiVersion)
#return -1

# Here is an example of how to access VC side VSAN Health Service API
vcMos = vsanapiutils.GetVsanVcMos(si._stub, context = context)
# Get vsan health system
vhs = vcMos['vsan-cluster-health-system']

cluster = getClusterInstance(args.clusterName, si)
if cluster is None:
  print("Cluster %s is not found for %s" % (args.clusterName, args.host))
else:
  print("Cluster not found, script failed")

health = vhs.VsanQueryVcClusterHealthSummary(
  cluster = cluster)
clusterStatus = health

print("vSAN Overall Health is: %s" %
  (args.clusterName, clusterStatus))

# Start program
if __name__ == "__main__":
  main()
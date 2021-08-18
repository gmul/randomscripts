#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright 2016 VMware, Inc.  All rights reserved.

This file includes sample codes for VC and ESXi sides VSAN API accessing.

To provide an exmple of VC side VSAN API access, it shows how to get VSAN cluster health
status by invoking the QueryClusterHealthSummary API of the
VsanVcClusterHealthSystem MO.

To provide an exmple of ESXi side VSAN API access, it shows how to get performance
server related host information by invoking the VsanPerfQueryNodeInformation API
of the VsanPerformanceManager MO.

"""

__author__ = 'VMware, Inc'

from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass
#import the VSAN API python bindings
import vsanmgmtObjects
import vsanapiutils

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(
       description='Process args for VSAN SDK sample application')
   parser.add_argument('-s', '--host', required=True, action='store',
                       help='Remote host to connect to')
   parser.add_argument('-o', '--port', type=int, default=443, action='store',
                       help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store',
                       help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=False, action='store',
                       help='Password to use when connecting to host')
   parser.add_argument('--cluster', dest='clusterName', metavar="CLUSTER",
                      default='VSAN-Cluster')
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

#Start program
def main():
   args = GetArgs()
   if args.password:
      password = args.password
   else:
      password = getpass.getpass(prompt='Enter password for host %s and '
                                        'user %s: ' % (args.host,args.user))

   #For python 2.7.9 and later, the defaul SSL conext has more strict
   #connection handshaking rule. We may need turn of the hostname checking
   #and client side cert verification
   context = None
   if sys.version_info[:3] > (2,7,8):
      context = ssl.create_default_context()
      context.check_hostname = False
      context.verify_mode = ssl.CERT_NONE

   si = SmartConnect(host=args.host,
                     user=args.user,
                     pwd=password,
                     port=int(args.port),
                     sslContext=context)

   atexit.register(Disconnect, si)

   #for detecting whether the host is VC or ESXi
   aboutInfo = si.content.about

   if aboutInfo.apiType == 'VirtualCenter':
      majorApiVersion = aboutInfo.apiVersion.split('.')[0]
      if int(majorApiVersion) < 6:
         print('The Virtual Center with version %s (lower than 6.0) is not supported.'
               % aboutInfo.apiVersion)
         return -1

      #Here is an example of how to access VC side VSAN Health Service API
      vcMos = vsanapiutils.GetVsanVcMos(si._stub, context=context)
      # Get vsan health system
      vhs = vcMos['vsan-cluster-health-system']

      cluster = getClusterInstance(args.clusterName, si)

      if cluster is None:
         print("Cluster %s is not found for %s" % (args.clusterName, args.host))
         return -1
      #VSAN cluster health summary can be cached at VC.
      fetchFromCache = True
      fetchFromCacheAnswer = raw_input(
         'Do you want to fetch the cluster health from cache if exists?(y/n):')
      if fetchFromCacheAnswer.lower() == 'n':
         fetchFromCache = False
      print('Fetching cluster health from cached state: %s' %
             ('Yes' if fetchFromCache else 'No'))
      healthSummary = vhs.QueryClusterHealthSummary(
         cluster=cluster, includeObjUuids=True, fetchFromCache=fetchFromCache)
      clusterStatus = healthSummary.clusterStatus

      print("Cluster %s Status: %s" % (args.clusterName, clusterStatus.status))
      for hostStatus in clusterStatus.trackedHostsStatus:
         print("Host %s Status: %s" % (hostStatus.hostname, hostStatus.status))

      #Here is an example of how to track a task retruned by the VSAN API
      vsanTask = vhs.RepairClusterObjectsImmediate(cluster);
      #need covert to vcTask to bind the MO with vc session
      vcTask = vsanapiutils.ConvertVsanTaskToVcTask(vsanTask, si._stub)
      vsanapiutils.WaitForTasks([vcTask], si)
      print('Repairing cluster objects task completed with state: %s'
            % vcTask.info.state)


   if aboutInfo.apiType == 'HostAgent':
      majorApiVersion = aboutInfo.apiVersion.split('.')[0]
      if int(majorApiVersion) < 6:
         print('The ESXi with version %s (lower than 6.0) is not supported.'
               % aboutInfo.apiVersion)
         return -1

      #Here is an example of how to access ESXi side VSAN Performance Service API
      esxMos = vsanapiutils.GetVsanEsxMos(si._stub, context=context)
      # Get vsan health system
      vpm = esxMos['vsan-performance-manager']

      nodeInfo = vpm.VsanPerfQueryNodeInformation()[0]

      print('Hostname: %s' % args.host)
      print('  version: %s' % nodeInfo.version)
      print('  isCmmdsMaster: %s' % nodeInfo.isCmmdsMaster)
      print('  isStatsMaster: %s' % nodeInfo.isStatsMaster)
      print('  vsanMasterUuid: %s' % nodeInfo.vsanMasterUuid)
      print('  vsanNodeUuid: %s' % nodeInfo.vsanNodeUuid)

# Start program
if __name__ == "__main__":
   main()

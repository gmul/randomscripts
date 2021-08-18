#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright 2019 VMware, Inc.  All rights reserved.

This file includes sample code for the vSAN Data Protection API. Pre-requisite
for using this is a Virtual Machine associated with a vSAN Data Protection
policy with local protection enabled.

usage: vsandpsamples.py [-h] (-l <vm-name> | -r <vm-name>) [-e]

vSAN Data Protection sample script

Specify one of the given options -l or -r and optionally include -e:
  -h, --help            show this help message and exit
  -l <vm-name>, --local <vm-name>
                        Query details about local snapshots of the given VM
  -r <vm-name>, --restore <vm-name>
                        Restore from a local snapshot of the given VM
  -e, --esx             Optional parameter to run all commands on ESXi host
"""

__author__ = 'VMware, Inc'

import atexit
import argparse
import getpass
import logging
import random
import re
import string
import sys
import ssl
import uuid

from pyVmomi import vim, VmomiSupport, SoapStubAdapter, VsanDpTypes
from pyVim import sso
from pyVim.connect import SmartConnect, Disconnect
from pyVim.task import WaitForTask

import vsanmgmtObjects

if sys.version[0] < '3':
   input = raw_input

# Secure token service URL template
STS_URL_TEMPLATE = 'http://%s:7444/sts/STSService/'

# Default domain name
DEFAULT_DOMAIN_NAME = 'vsphere.local'

# Virtual Machine name character limit in vCenter
VM_NAME_LIMIT = 80

# Port number used for connection
PORT = 443

# Path to vSphere API
VSPHERE_PATH = "/sdk"

# Path to vSAN Data Protection API
VSAN_DP_PATH = "/vsandp"

# Path to vSAN API in vCenter
VSAN_VC_PATH = "/vsanHealth"

# Path to vSAN API in ESX
VSAN_ESX_PATH = "/vsan"

# vSAN Data Protection version
VSAN_DP_VERSION = "vim.vsandp.version.version10"

# Duration for which SAML token is issued for in seconds
SAML_TOKEN_DURATION = 3600

def main():
   """
   Script entry point. This script can be used to query details about local snapshots for a given VM.
   """
   parser = argparse.ArgumentParser(description='vSAN Data Protection sample script')
   parser._optionals.title = "Specify one of the given options -l or -r and optionally include -e"
   group = parser.add_mutually_exclusive_group(required=True)
   group.add_argument('-l', '--local', metavar='<vm-name>',
                      help='Query details about local snapshots of the given VM')
   group.add_argument('-r', '--restore', metavar='<vm-name>',
                      help='Restore from a local snapshot of the given VM')
   parser.add_argument('-e', '--esx', action='store_true', help='Optional parameter to run all commands on ESXi host')
   args = vars(parser.parse_args())

   logging.getLogger().setLevel(logging.INFO)

   # Create connection to all servers
   (vsphereInstance, vsanStub, vsandpStub) = connectToServers(hostConnect=args['esx'])

   if args['local']:
      vmName = args['local']
      vmObj = lookupVmWithName(vmName, vsphereInstance.content)
      result = retrieveLocalProtectionInfo(vmObj, vsanStub, vsandpStub, fromHost=args['esx'])
      logging.info("Retrieved local protection info for VM '%s'. Result is: %s\n", vmObj.name, result)
   elif args['restore']:
      vmName = args['restore']
      vmObj = lookupVmWithName(vmName, vsphereInstance.content)
      (restoredVm, restoredVmName) = restoreVmFromLocalSnapshot(
         vmObj, vsanStub, vsandpStub, vsphereInstance, fromHost=args['esx'])
      logging.info("Restored VM '%s' from local instance of VM '%s'\n", restoredVmName, vmObj.name)

def connectToServers(hostConnect=False):
   """
   Creates connections to the vCenter/ESXi, vSAN and DPS/DPD server
   @param hostConnect Host connection. If set to True, connections are made to ESXi and vSAN/Data Protection daemon running in it.
                      If set to False, connections are made to vCenter and vSAN/Data Protection service running in it
   @return vCenter/ESXi server instance, vSAN stub and DPS/DPD stub
   """
   # For python 2.7.9 and later, the default SSL context has stricter
   # connection handshaking rule, hence we are turning off the hostname checking
   # and client side cert verification.
   sslContext = None
   if sys.version_info[:3] > (2,7,8):
      sslContext = ssl.create_default_context()
      sslContext.check_hostname = False
      sslContext.verify_mode = ssl.CERT_NONE

   if hostConnect:
      # Create connection to ESXi host to retrieve clone ticket used for login to Data Protection Daemon (DPD)
      hostIp = input('Enter ESXi host IP: ')
      hostUserName = input('Enter ESXi host username: ')
      hostPassword = getpass.getpass(prompt='Enter ESXi host password: ')
      print()

      try:
         vsphereInstance = SmartConnect(host=hostIp, user=hostUserName, pwd=hostPassword,
                                        port=PORT, path=VSPHERE_PATH, sslContext=sslContext)
      except vim.InvalidLogin:
         sys.exit("ERROR: Incorrect login provided for ESXi")
      except Exception as e:
         msg = "ERROR: Could not connect to ESXi. Exception thrown is \n {0}".format(e)
         sys.exit(msg)
      atexit.register(Disconnect, vsphereInstance)

      # Create connection to vSAN service running on ESXi
      try:
         vsanStub = SoapStubAdapter(
            host=hostIp, port=PORT, path=VSAN_ESX_PATH, version=VmomiSupport.newestVersions.Get('vsan'),
            sslContext=sslContext)
         vsanStub.cookie = vsphereInstance._stub.cookie
      except Exception as e:
         msg = "ERROR: Could not connect to vSAN service running on ESXi. Exception thrown is \n {0}".format(e)
         sys.exit(msg)

      hostSessionManager = vsphereInstance.content.sessionManager
      cloneTicket = hostSessionManager.AcquireCloneTicket()

      # Create stub to DPD and login
      vsandpStub = SoapStubAdapter(host=hostIp, port=PORT,
                                   path=VSAN_DP_PATH, version=VSAN_DP_VERSION,
                                   sslContext=sslContext)
      dpdSessionManager = vim.vsandp.host.SessionManager('vsan-dp-session-manager', vsandpStub)
      dpdSessionManager.UserLoginByCloneTicket(cloneTicket, None)
      atexit.register(dpdSessionManager.UserLogout)
   else:
      vcIp = input("Enter vCenter IP address: ")
      username = input('Enter vCenter username: ')
      password = getpass.getpass(prompt='Enter vCenter password: ')
      print()

      # Retrieve domain name from username. If not present, use default
      # Expected username format is "UserName@DomainName"
      m = re.search("(.*)@(.*)", username)
      try:
         domainName = m.group(2)
      except AttributeError as e:
         # User has not provided the domain name as part of the user name, assume default domain
         domainName = DEFAULT_DOMAIN_NAME
         username = username + '@' + domainName
      # Connect to vCenter
      try:
         vsphereInstance = SmartConnect(host=vcIp, user=username,
                                        pwd=password, port=PORT, path=VSPHERE_PATH,
                                        sslContext=sslContext)
      except vim.InvalidLogin:
         sys.exit("ERROR: Incorrect login provided for vCenter")
      except Exception as e:
         msg = "ERROR: Could not connect to vCenter. Exception thrown is \n {0}".format(e)
         sys.exit(msg)
      atexit.register(Disconnect, vsphereInstance)

      # Create vSAN stub
      try:
         vsanStub = SoapStubAdapter(
            host=vcIp, port=PORT, path=VSAN_VC_PATH, version=VmomiSupport.newestVersions.Get('vsan'),
            sslContext=sslContext)
         vsanStub.cookie = vsphereInstance._stub.cookie
      except Exception as e:
         msg = "ERROR: Could not connect to vCenter side vSAN server. Exception thrown is \n {0}".format(e)
         sys.exit(msg)

      try:
         # Create stub to Data Protection Service (DPS)
         vsandpStub = SoapStubAdapter(host=vcIp, port=PORT,
                                      path=VSAN_DP_PATH, version=VSAN_DP_VERSION,
                                      sslContext=sslContext)
         authenticator = sso.SsoAuthenticator(sts_url=STS_URL_TEMPLATE%vcIp+domainName)
         bearer = authenticator.get_bearer_saml_assertion(
            username, password, delegatable=True, token_duration=SAML_TOKEN_DURATION, ssl_context=sslContext)
         vsandpStub.samlToken = bearer
         sessionManager = vim.vsandp.dps.SessionManager('vsan-dp-session-manager', vsandpStub)
         sessionManager.VsanDpsLoginByToken('en') # User can login using non-English locale if needed
      except Exception as e:
         msg = "ERROR: Could not connect to DPS server. Exception thrown is \n {0}".format(e)
         sys.exit(msg)
      atexit.register(sessionManager.VsanDpsLogout)

   return (vsphereInstance, vsanStub, vsandpStub)

def lookupVmWithName(vmName, content):
   """
   Looks up VM with given name in vCenter and returns the VM object
   @param vmName Given VM name
   @param content Content
   @return VM object
   """
   logging.info("Looking up VM with name '%s'\n", vmName)
   # Go through VMs in all datacenters and select the one that matches
   vmRefMatch = getObj(content, [vim.VirtualMachine], vmName)
   if not vmRefMatch:
      msg = "ERROR: Could not lookup VM with name '{0}'. Please run script again with correct VM name ".format(vmName)
      sys.exit(msg)

   vmNum = 1
   if len(vmRefMatch) != 1:
      # If there are multiple VMs with the same name, list all the VMs and ask user to select one.
      print("\nThere are multiple VMs in vCenter with the same name. Choose the correct VM ID:")
      for i in range(len(vmRefMatch)):
         print("{}: {}".format(i + 1, vmRefMatch[i]))
      vmNum = -1
      while vmNum < 1 or vmNum > len(vmRefMatch):
         try:
            vmNum = int(input("Please choose your VM (1 - {}): ".format(len(vmRefMatch))))
         except ValueError:
            print("Please enter an integer.")
      print()

   logging.debug("Found VM ID %s corresponding to VM name '%s'\n",
                 vmRefMatch[vmNum - 1], vmName)
   return vmRefMatch[vmNum - 1]

def getObj(content, vimtype, name):
   """
   Retrieve object matching given type and name
   @param content Service Instance content
   @param vimtype Type of the object
   @param name Name of the object to be retrieved
   @return Array of matched objects
   """
   matchedObjs = []
   container = content.viewManager.CreateContainerView(
      content.rootFolder, vimtype, True)
   for c in container.view:
      if name and c.name == name:
         matchedObjs.append(c)
   return matchedObjs

def retrieveLocalProtectionInfo(vmObj, vsanStub, vsandpStub, fromHost=False):
   """
   Retrieves local protection information of the given VM
   @param vmObj VM object
   @param vsanStub vSAN stub
   @param vsandpStub vSAN Data Protection stub
   @param fromHost Retrieve info from ESXi host instead of vCenter if True
   @return Local protection information of given VM
   """
   if fromHost:
      # Cluster parameter is not required for host calls
      cluster = None
   else:
      # Retrieve vSAN cluster for the virtual machine (VM)
      cluster = vmObj.runtime.host.parent

   # Check if VM is on a vSAN cluster
   if not vmObj.config.vmStorageObjectId:
      msg = "ERROR: VM is not on a vSAN cluster. Exiting..."
      sys.exit(msg)

   # The VM's configuration contains its storage object ID in the vSAN cluster. This ID is used to query the
   # data protection Consistency Group (CG) for the VM
   queryCgByObjectSpec = vim.vsandp.cluster.InventoryService.CgMemberQuery.Spec(
      object=[vmObj.config.vmStorageObjectId],
      cluster=cluster)
   dpInventorySystem = vim.vsandp.cluster.InventoryService('vsan-dp-inventory-service', vsandpStub)
   queryCgByObjectResult = dpInventorySystem.QueryCgByObject(queryCgByObjectSpec)
   # Check if the VM is vSAN data protected
   if not queryCgByObjectResult.result:
      msg = "ERROR: VM is not vSAN data protected. Exiting..."
      sys.exit(msg)
   # Retrieve the CG ID
   cgId = queryCgByObjectResult.result[0].cg.key
   cgName = queryCgByObjectResult.result[0].cg.displayName
   logging.info("VM is associated with Consistency Group ID '%s' (%s)\n", cgId, cgName)

   # Retrieve UUIDs of the VM's namespace and disk objects
   uuids = []
   uuids.append(vmObj.config.vmStorageObjectId)
   for device in vmObj.config.hardware.device:
      if isinstance(device, vim.vm.device.VirtualDisk):
         uuids.append(device.backing.backingObjectId)

   if fromHost:
      # Retrieving DP health stats from host
      vhs = vim.host.VsanHealthSystem("ha-vsan-health-system", vsanStub)
      vos = vim.cluster.VsanObjectSystem("vsan-object-system", vsanStub)

      hsResult = vhs.QueryObjectHealthSummary(objUuids=[vmObj.config.vmStorageObjectId], localHostOnly=True,
                                              includeObjUuids=True, includeDataProtectionHealth=True)
   else:
      # Retrieving DP health stats from vCenter
      chs = vim.cluster.VsanVcClusterHealthSystem("vsan-cluster-health-system", vsanStub)
      vos = vim.cluster.VsanObjectSystem("vsan-cluster-object-system", vsanStub)

      hsResult = chs.VsanQueryVcClusterHealthSummary(cluster=cluster, objUuids=[vmObj.config.vmStorageObjectId],
                                                     includeObjUuids=True, includeDataProtectionHealth=True).objectHealth
   # Process results to retrieve VM's health state
   for vsanObjectHealth in hsResult.objectHealthDetail:
      if vsanObjectHealth.objUuids:
         logging.info("VM's vSAN Data Protection health state is '%s'\n", vsanObjectHealth.dataProtectionHealth)
         break

   # Retrieving summary of the space used by vSAN Data Protection
   result = vos.QueryObjectIdentities(cluster=cluster, objUuids=uuids, objTypes=["vdisk", "namespace"],
                                      includeSpaceSummary=True)
   logging.info("VM's vSAN Data Protection space summary report:\n%s\n", result)

   # Query CG information to get detailed snapshot information for the VM. Snapshot information will be shown as
   # instances in the local protection series of the result
   queryCgInfoSpec = vim.vsandp.cluster.ProtectionService.CgInfoQuery.Spec(
      cg=cgId,
      cluster=cluster)
   dpProtectionSystem = vim.vsandp.cluster.ProtectionService('vsan-dp-protection-service', vsandpStub)
   queryCgInfoResult = dpProtectionSystem.QueryCgInfo(queryCgInfoSpec)
   return queryCgInfoResult

def restoreVmFromLocalSnapshot(vmObj, vsanStub, vsandpStub, vsphereInstance, fromHost=False):
   """
   Restore VM from local snapshot
   @param vmObj VM object
   @param vsanStub vSAN stub
   @param vsandpStub vSAN Data Protection stub
   @param vsphereInstance vSphere server instance
   @param fromHost Restore using ESXi host instead of vCenter if True
   @return Name of the restored VM
   """
   # Retrieve local protection info
   lpInfo = retrieveLocalProtectionInfo(vmObj, vsanStub, vsandpStub, fromHost)

   # Check if the VM is vSAN data protected
   if not lpInfo.result:
      msg = "ERROR: VM is not vSAN data protected. Exiting..."
      sys.exit(msg)

   # Retrieve VM's CG ID
   cgId = lpInfo.result[0].local.series.key
   # Retrieve instances
   instances = lpInfo.result[0].local.instance
   if instances is None or (len(instances) == 0):
      msg = "ERROR: VM does not have any local snapshots. Exiting..."
      sys.exit(msg)
   logging.info("VM has %d local instances. Picking latest instance and restoring from it...\n", len(instances))
   instanceId = instances[-1].key
   # Restored VM name
   suffix = '-dpSample-Restore-' + ''.join(random.choice(string.ascii_uppercase) for x in range(6))
   restoredVmName = vmObj.name + suffix
   # Check if name is less than vCenter limit
   if len(restoredVmName) >= VM_NAME_LIMIT:
      msg = "ERROR: VM's name is too long. Please rename to less than {0} characters".format(VM_NAME_LIMIT - len(suffix))
      sys.exit(msg)
   # Specifying which snapshot to restore
   location=vim.vsandp.InstanceLocation(location=vim.vsandp.LocalVsanLocation(),
                                        groupInstanceKey=instanceId, # ID of the local snapshot being restored
                                        series=cgId) # CG ID of the original VM
   if fromHost:
      restoredVmRef = hostRestore(vmObj, location, restoredVmName, vsandpStub)
   else:
      restoredVmRef = vcRestore(vmObj, location, restoredVmName, vsanStub, vsandpStub, vsphereInstance)

   return (restoredVmRef, restoredVmName)

def hostRestore(vmObj, location, restoredVmName, vsandpStub):
   """
   Performs host level restore of vSAN data protected VM using DPD APIs
   @param vmObj VM object
   @param location Location
   @param restoredVmName Restored VM name
   @param vsandpStub vSAN DP stub
   @return Restored VM
   """
   # Use DPD's CreateImage API to create image containing restored objects of the VM from latest snapshot.
   createImageEntry = vim.vsandp.cluster.ImageService.CreateImagesOp.Spec.Entry(
      instance=location,
      creationType='linkedClone',
      entitySpec=vim.vsandp.ImageCreateSingleVMEntitySpec(removeVcInstanceUuid=True)  # Remove vCenter instance UUID field
                                                                                      # from the restored VM so that it
                                                                                      # shows up in vCenter UI after
                                                                                      # registration
   )
   createImageSpec = vim.vsandp.cluster.ImageService.CreateImagesOp.Spec(
      initiatorId="VSAN-DP-Sample-Script-%s" % uuid.uuid4(),
      entry=[createImageEntry]
   )
   imageService = vim.vsandp.cluster.ImageService('vsan-dp-image-service', vsandpStub)
   createImagesOp = imageService.CreateImage(createImageSpec)
   # Retrieve CreateImage task and wait until completion
   createImageTask = createImagesOp.result[0].createImageOp
   serviceInstance = vim.vsandp.dpd.ServiceInstance("vsan-dp-service-instance", vsandpStub)
   WaitForTask(createImageTask, si=serviceInstance, raiseOnError=False)
   createImageTaskInfo = createImageTask.info
   if createImageTaskInfo.error is not None:
      msg = "Restore failed with error '{0}'".format(createImageTaskInfo.error)
      sys.exit(msg)
   # Retrieve key of created image
   imageInfo = createImageTaskInfo.result.info
   imageKey = imageInfo.key
   # Iterate and retrieve path of the restored namespace object
   for object in imageInfo.object:
      if object.info.objClass == vim.vsandp.ObjectClass.vmnamespace:
         nsPath = object.info.namespacePath
         break
   if nsPath is None:
      msg = "Restore failed as result is incorrect: {0}".format(createImageTaskInfo.result)
      sys.exit(msg)
   # Convert absolute namespace path to relative namespace path to register the restored objects
   # Absolute path eg: /vmfs/volumes/vsan:527ab91c37473ca4-e40f3438db9ee4c2/testVm-10282016-004744_1/testVm-10282016-004744.vmx
   # Relative path eg: [vsanDatastore] testVm-10282016-004744_1/testVm-10282016-004744.vmx
   # Retrieve datastore URL (eg:/vmfs/volumes/vsan:527ab91c37473ca4-e40f3438db9ee4c2) from original VM's datastore
   dsInfo = vmObj.datastore[0].info
   dsUrl = dsInfo.url.strip()
   if nsPath.find(dsUrl) == -1:
      msg = "Restored namespace object's path '{0}' is incorrect".format(nsPath)
      sys.exit(msg)
   dsUrlLen = len(dsUrl)
   relNsPath = "[%s] %s" % (dsInfo.name, nsPath[dsUrlLen:])
   # Register restored objects in same folder/resource pool/host as original VM
   registerVmTask = vmObj.parent.RegisterVM_Task(relNsPath, restoredVmName, asTemplate=False,
                                                 pool=vmObj.resourcePool, host=vmObj.runtime.host)
   WaitForTask(registerVmTask, raiseOnError=False)
   if registerVmTask.info.error is not None:
      # Registering restored objects failed, call DPD's DeleteImage API to delete the image in order to
      # avoid leaking images
      deleteImageSpec = vim.vsandp.cluster.ImageService.DeleteImagesOp.Spec(
         imageKey=[imageKey]
      )
      imageService.DeleteImage(deleteImageSpec)
      msg = "Restore failed with error '{0}'".format(registerVmTask.info.error)
      sys.exit(msg)
   restoredVmRef = registerVmTask.info.result
   # Restored VM has been registered. Now call DPD's ReleaseImage API to remove image from vSAN DP's management
   releaseImageEntry = vim.vsandp.cluster.ImageService.ReleaseImagesOp.Spec.Entry(
      imageKey=imageKey
   )
   releaseImageSpec = vim.vsandp.cluster.ImageService.ReleaseImagesOp.Spec(
      entry=[releaseImageEntry]
   )
   releaseImagesOp = imageService.ReleaseImage(releaseImageSpec)
   # Retrieve ReleaseImage task and wait until completion
   releaseImageTask = releaseImagesOp.result[0].releaseImageOp
   WaitForTask(releaseImageTask, si=serviceInstance, raiseOnError=False)
   if releaseImageTask.info.error is not None:
      # If ReleaseImage fails, the caller should ideally retry or undo previous steps by unregistering the VM
      # and calling DeleteImage. We will skip this in the sample script
      msg = "Restore failed with error '{0}'".format(releaseImageTask.info.error)
      sys.exit(msg)

   # Power on the restored VM
   powerOnTask=restoredVmRef.PowerOn()
   WaitForTask(powerOnTask)
   return restoredVmRef

def vcRestore(vmObj, location, restoredVmName, vsanStub, vsandpStub, vsphereInstance):
   """
   Performs vCenter level restore of vSAN data protected VM using DPS APIs
   @param vmObj VM object
   @param location Location
   @param restoredVmName Restored VM name
   @param vsanStub vSAN stub
   @param vsandpStub vSAN DP stub
   @param vsphereInstance vSphere instance
   @return Restored VM
   """
   # Retrieve protected VM's policy ID from vSAN health. For the purposes of this sample code, we shall reuse
   # same policy for the restored VM.
   # A policy ID can also be retrieved using Storage Policy Based Management server (SPBM server)
   vsanVcObjectSystem = vim.cluster.VsanObjectSystem("vsan-cluster-object-system", vsanStub)
   cluster = vmObj.runtime.host.parent
   query = vim.cluster.VsanObjectQuerySpec()
   query.uuid = vmObj.config.vmStorageObjectId
   queries = []
   queries.append(query)
   vsanObjInfo = vsanVcObjectSystem.QueryVsanObjectInformation(cluster=cluster,
                                                               vsanObjectQuerySpecs=queries)
   profileId = vsanObjInfo[0].spbmProfileUuid

   restoreSpec = vim.vsandp.cluster.VsanDataProtectionRecoverySystem.RestoreSpec(
      cluster=cluster,  # Restored VM will be in the same vCenter cluster as original VM
      datastore=vmObj.datastore[0],  # Restored VM will be in the same vSAN datastore as original VM
      name=restoredVmName,
      powerOn=True,  # Restored VM will be powered ON
      fullClone=False,  # Restored VM will be a linked clone i.e not promoted.
      # User can restore to a full clone by flipping this switch or calling
      # vCenter promoteDisks API on the linked clone VM
      folder=vmObj.parent,  # Restored VM will be present in same folder in vCenter as original VM
      host=vmObj.runtime.host,  # Restored VM will be present in same host as original VM.
      # This parameter is optional if cluster has Distributed Resource Scheduling (DRS)
      # turned ON
      resourcePool=vmObj.resourcePool,  # Restored VM will be present in same resource pool as original VM
      profileId=profileId,  # Restored VM will be associated with same policy as original VM
      location=location  # Specifies which sanpshot to restore
   )
   dpRecoverySystem = vim.vsandp.cluster.VsanDataProtectionRecoverySystem('vsan-dp-recovery-system', vsandpStub)
   # Initiate restore
   restoreVmTaskMoRef = dpRecoverySystem.RestoreVm_Task(restoreSpec)
   restoreVmTask = vim.Task(restoreVmTaskMoRef._moId, vsphereInstance._stub)
   logging.info("Restoring from local snapshot using task '%s'\n", restoreVmTaskMoRef)
   WaitForTask(restoreVmTask, raiseOnError=False)
   restoreVmTaskInfo = restoreVmTask.info
   if restoreVmTaskInfo.error is not None:
      msg = "Restore failed with error '{0}'".format(restoreVmTaskInfo.error)
      sys.exit(msg)
   return restoreVmTaskInfo.result

if __name__ == "__main__":
   main()

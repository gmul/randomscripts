#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Greg Mulholland
# Description: This script extracts the performance data from a host
# Usage: python vsanapi_esxi_template.py --host 10.160.83.126 --user root --password ca$hc0w

#import pvVim
from pyVim.connect import SmartConnect, Disconnect
import sys
import ssl
import atexit
import argparse
import getpass

# import the VSAN API python bindings
import vsanmgmtObjects
import vsanapiutils

# define required inputs
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
    parser.add_argument('-p', '--password', required=True, action='store',
                        help='Password to use when connecting to host')
    args = parser.parse_args()
    return args




# Start program



def main():
    args = GetArgs()
    if args.password:
        password = args.password
    else:
        password = getpass.getpass(prompt='Enter password for host %s and '
                                          'user %s: ' % (args.host, args.user))

# For python 2.7.9 and later, the defaul SSL conext has more strict
# connection handshaking rule. We may need turn off the hostname checking
# and client side cert verification
    context = None
    if sys.version_info[:3] > (2, 7, 8):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    si = SmartConnect(host=args.host,
                      user=args.user,
                      pwd=password,
                      port=int(args.port),
                      sslContext=context)

    atexit.register(Disconnect, si)


# for detecting whether the host is VC or ESXi
    aboutInfo = si.content.about

    if aboutInfo.apiType == 'VirtualCenter':
        majorApiVersion = aboutInfo.apiVersion.split('.')[0]
        if int(majorApiVersion) < 6:
            print('The Virtual Center with version %s (lower than 6.0) is not supported.'
                  % aboutInfo.apiVersion)
            return -1

     


# Here is an example of how to access ESXi side VSAN Performance
# Service API
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

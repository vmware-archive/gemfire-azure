from __future__ import print_function

import argparse
import json
import os.path
import subprocess
import sys

# global variables
azureregions = [
  "australiaeast",
  "australiasoutheast",
  "brazilsouth",
  "canadacentral",
  "canadaeast",
  "centralindia",
  "centralus",
  "centraluseuap",
  "eastasia",
  "eastus",
  "eastus2",
  "eastus2euap",
  "japaneast",
  "japanwest",
  "koreacentral",
  "koreasouth",
  "northcentralus",
  "northeurope",
  "southcentralus",
  "southeastasia",
  "southindia",
  "uksouth",
  "ukwest",
  "westcentralus",
  "westeurope",
  "westus",
  "westus2"
]

def parseArgs():
    parser = argparse.ArgumentParser(description = 'This script deploys a GemFire cluster on Azure')
    allgroup = parser.add_argument_group('arguments')
    allgroup.add_argument('--cluster-name', required=True, help='A unique name for the cluster.')
    allgroup.add_argument('--use-resource-group', help='The name of an existing resource group in which to deploy the GemFire cluster.')
    allgroup.add_argument('--create-resource-group', help='The name of a new resource group.  The GemFire cluster will be deployed in this group after it is created. This option is incompatible with --use-resource-group.')
    allgroup.add_argument('--location', help='The Azure region where the new resource group will be created.  This option must be supplied if --create-resource-group is supplied.This option is incompatible with --use-resource-group.', choices = azureregions)
    allgroup.add_argument('--public-ssh-key-file',type=argparse.FileType('rb'), required = True,help='The path to a file containing the public half of the ssh key you will use to access the servers.')
    allgroup.add_argument('--datanode-count', type=int, required = True, choices=range(2,16), help='Number of data nodes that will be deployed.')
    allgroup.add_argument('--locator-count', type=int, default = 2, choices=range(1,3), help='Number of locators that will be deployed.The default is 2.')

    try:
        args = parser.parse_args()
    except IOError as ioe:
        if ioe.filename is not None:
            sys.exit('{0}: {1}'.format(ioe.strerror, ioe.filename))
        else:
            sys.exit(ioe.strerror)

    if args.use_resource_group is None and args.create_resource_group is None:
        sys.exit('one of  --user-resource-group and  --create_resource_group must be supplied')

    if args.use_resource_group is not None and args.create_resource_group is not None:
        sys.exit('only one of  --user-resource-group and  --create_resource_group must be supplied')

    if args.create_resource_group is not None and args.location is None:
        sys.exit('--location must be supplied whenever --create-resource-group is given')

    return args

def azrun_list(cmds):
    """
    runs an Azure cli command and parses the results as json
    this method calls sys.exit if the command is not successful
    """
    proc = subprocess.Popen(['az'] + cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin = subprocess.PIPE , cwd = here)
    out, err = proc.communicate()
    if proc.returncode != 0:
        sys.exit('An error occurred while executing ({0}): {1}'.format('az ' + ' '.join(cmds), err))

    return json.loads(out)

def azrun(cmds):
    """
    runs an Azure cli command and parses the results as json
    this method calls sys.exit if the command is not successful
    """
    return azrun_list(cmds.split())

def resource_group_exists(rgname):
    """
    return True if the resource group exists or False if not
    """
    listgroups = azrun('group list')
    for group in listgroups:
        if group['name'] == rgname:
            return True

    return False

def create_resource_group(name, location):
    azrun('group create --name {0} --location {1}'.format(name, location))

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(sys.argv[0]))

    args = parseArgs()

    # create the resource group, or verify an existing one
    resourcegroup = None
    if args.use_resource_group is not None :
        if resource_group_exists(args.use_resource_group):
            resourcegroup= args.use_resource_group
        else:
            sys.exit('The specified resource group ({0}) does not exist.'.format(args.use_resource_group))
    else:
        if resource_group_exists(args.create_resource_group):
            sys.exit('Cannot create the resource group ({0}) because it already exists'.format(args.create_resource_group))

        create_resource_group(args.create_resource_group, args.location)
        resourcegroup = args.create_resource_group

    # retrieve the ssh key material
    sshkey = args.public_ssh_key_file.read(17384)
    args.public_ssh_key_file.close()

    # compose the az command
    overrides = ['--parameters', 'clusterName={0}'.format(args.cluster_name)]
    overrides = overrides + ['adminPublicKey="{0}"'.format(sshkey)]
    if args.datanode_count is not None:
        overrides = overrides + ['gemfireHostsCount={0}'.format(args.datanode_count)]

    if args.locator_count is not None:
        overrides = overrides + ['gemfireLocatorsCount={0}'.format(args.locator_count)]
    # overrides = overrides + ['--parameters', 'adminPublicKey="{0}"'.format(sshkey)]
    # if args.datanode_count is not None:
    #     overrides = overrides + [' --parameters','gemfireHostsCount={0}'.format(args.datanode_count)]
    #
    # if args.locator_count is not None:
    #     overrides = overrides + ['--parameters', 'gemfireLocatorsCount={0}'.format(args.locator_count)]

    print('Deployment has begun.  This may take a while. Use the Azure portal to view progress...')
    azrun_list(['group', 'deployment', 'create', '--resource-group', resourcegroup, '--template-file', os.path.join(here, 'gemfire_template.json'), '--resource-group', resourcegroup, '--parameters', os.path.join(here,'default_parameters.json')] + overrides)
    print('GemFire cluster deployed.')

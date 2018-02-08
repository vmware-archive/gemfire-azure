from __future__ import print_function
import jinja2
import json
import os
import os.path
import random
import shutil
import pwd
import sys
import subprocess

def validate_env():
    for key in ['GEMFIRE_USER', 'CLUSTER_NAME', 'GF_SUPERUSER_PASS']:
        if key not in os.environ:
            sys.exit('A required environment variable is not present: ' + key)

def install_systemd_service(runAsUser):
    """
    This function installs systemd unit to start and stop the
    GemFire cluster when the machine is started and stopped.
    """
    # set up the jinja2 template environment
    context = dict()
    context['RunAsUser'] = runAsUser

    # render the template
    jinja2Env = jinja2.Environment(loader = jinja2.FileSystemLoader('/home/{0}/gemfire-azure/init_scripts'.format(runAsUser)), trim_blocks = True, lstrip_blocks = True)

    tplate = jinja2Env.get_template('gemfire.service.tpl')
    target = '/etc/systemd/system/gemfire.service'
    with open(target,'w') as f:
        tplate.stream(context).dump(f)

    # install the service
    subprocess.check_call(['systemctl','enable','gemfire.service'])
    print('installed systemd service for gemfire')

if __name__ == '__main__':
    """
    This script starts the first locator and imports the initial cluster
    configuration.  It also installs the systemd service

    This script expects the following environment variables
    GEMFIRE_USER the user that will run the GemFire processes
    CLUSTER_NAME the name of the cluster
    GF_SUPERUSER_PASS  the password for the GemFire super user
    """
    validate_env()

    # parameters
    clusterName = os.environ['CLUSTER_NAME']
    gemuser = os.environ['GEMFIRE_USER']
    gemfireSuperUserPassword = os.environ['GF_SUPERUSER_PASS']

    # install systemd
    install_systemd_service(gemuser)

    # check to see if we are the 0th host
    hostname = subprocess.check_output(['hostname']).strip()
    if hostname == clusterName + '0':
        cluster_home = '/datadisks/disk1/gemfire_cluster'
        java_home = '/etc/alternatives/java_sdk'
        gemfire = '/usr/local/gemfire'

        subprocess.check_call(['systemctl','start','gemfire.service'])
        print 'started gemfire'
        #rc = subprocess.call(['sudo','-u',gemuser, 'GEMFIRE={0}'.format(gemfire),'JAVA_HOME={0}'.format(java_home), 'python', 'cluster.py','start'], cwd=cluster_home)

        if (rc == 0):
            print('First locator started')
        else:
            print('First locator failed to start')
            sys.exit(-1)

    else:
        print('nothing to do for init_gemfire_cluster on this server')
        sys.exit(0)

    # now figure out the locator port and run a gfsh import cluster config
    clusterdef_file = os.path.join(cluster_home,'cluster.json')
    with open(clusterdef_file, 'r') as f:
        cdef = json.load(f)

    locator_port = cdef['locator-properties']['port']
    gfsh = os.path.join(gemfire,'bin','gfsh')
    zipfile_name = os.path.join('/home',gemuser,'gemfire-azure','init_scripts','cluster.zip')

    subprocess.call([gfsh,'-e','connect --locator=localhost[{0}] --user={1} --password={2}'.format(locator_port, 'gfpeer', gemfireSuperUserPassword), '-e','import cluster-configuration --zip-file-name={0}'.format(zipfile_name)])
    # TODO - it appears gfsh does not return a non-zero error code when this
    #        command fails. Investigate and log a ticket
    if (rc == 0):
        print('initial cluster configuration imported')
    else:
        sys.exit('cluster configuration import failed')

    # now signal readiness by starting a simple HttpServer
    subprocess.Popen(['python', '-m', 'SimpleHTTPServer', '80'], cwd=os.path.join('/home',gemuser,'gemfire-azure','init_scripts','http'))

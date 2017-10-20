import os
import os.path
import pwd
import shutil
import subprocess


MAVEN = '/usr/local/maven/bin/mvn'

if __name__ == '__main__':
    """
    This script expects the following environment variables:

    GEMFIRE_USER the user that will run the GemFire processes
    """
    runAsUser = os.environ['GEMFIRE_USER']
    build_dir = '/home/{0}/gemfire-azure/gemfire-dynamic-security'.format(runAsUser)

    p = subprocess.Popen([MAVEN], cwd = build_dir,  stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output = p.communicate()
    if p.returncode != 0:
        raise Exception('"{0}" failed with the following output: {1}'.format(' '.join(list(args)), output[0]))

    subprocess.check_output(['chown', '-R', runAsUser, build_dir])
    print 'built gemfire-dynamic-security'
import os
import sys
import shutil
import platform
import socket

def detect_environment() -> dict:
    return {
        'python_version': sys.version.split()[0],
        'platform': platform.system(),
        'cwd': os.getcwd(),
        'has_root': shutil.which('root') is not None,
        'has_cmssw': 'CMSSW_BASE' in os.environ,
        'has_condor': shutil.which('condor_submit') is not None,
        'hostname': socket.gethostname(),
    }

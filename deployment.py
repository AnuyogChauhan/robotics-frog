#!/usr/bin/env python

import os
import json
from datetime import datetime
from fabric.api import env
from fabric.api import run
from fabric.api import local
from fabric.contrib.files import exists
from fabric.context_managers import cd
from fabric.operations import put
from fabric.operations import get
from fabric.operations import sudo

#env.hosts = ['172.19.74.221']
#env.user = 'root'
#env.password = 'ubuntu'


def deployENSImage():

    run("rm -rf /root/Frog-integration/frog-apps-code/robotics-network")
    run("mkdir -p /root/Frog-integration/frog-apps-code/robotics-network")
    files = ['ens','app-catalog.db','*.py','Docker*','Makefile']
    for f in files:
        put(f,"/root/Frog-integration/frog-apps-code/robotics-network/")

    with cd("/root/Frog-integration/frog-apps-code/robotics-network"):
        run("make buildens")
        run("cp ens/mecsdk.conf ./mecsdk.conf")

    run("mv /root/Frog-integration/frog-apps-code/robotics-network/app-catalog.db /root/Frog-integration/tcp_frog-sdk/tcp_frog-sdk/frog-sdk/sdk/cloudlet/bin/app-catalog.db")


def getChanges():
    files = ["ens/enswr.py", "ens/enswmain.py", "ens/ensiwc.so", "ens/workloadPy.sh"]
    for f1 in files:
        get("/root/Frog-integration/frog-apps-code/robotics-network/{0}".format(f1), "ens/")

    get("/root/Frog-integration/frog-apps-code/robotics-network/RobotClientENS.py", "./")
    get("/root/Frog-integration/frog-apps-code/robotics-network/Dockerfile.ens", "./")
    get("/root/Frog-integration/tcp_frog-sdk/tcp_frog-sdk/frog-sdk/sdk/cloudlet/bin/app-catalog.db", "./")

def initMachine():
    sudo("apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D")
    sudo("apt-add-repository 'deb https://apt.dockerproject.org/repo ubuntu-xenial main'")
    sudo("apt-get update")
    sudo("apt-get install -y docker-engine")

def deployDocker():
    run("mkdir -p /home/ubuntu/robotics-network")
    put("Dockerfile*", "/home/ubuntu/robotics-network/")
    put("Makefile", "/home/ubuntu/robotics-network/")
    put("messages*", "/home/ubuntu/robotics-network/")
    put("robot*", "/home/ubuntu/robotics-network/")
    put("Robot*", "/home/ubuntu/robotics-network/")
    with("cd /home/ubuntu/robotics-network"):
        sudo("make build")
        sudo("make run")


def speedstick():
    run("wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-2.5.0.tar.bz2")
    run("wget http://www.draisberghof.de/usb_modeswitch/usb-modeswitch-data-20170205.tar.bz2")



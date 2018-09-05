"""
jdss-api-tools send REST API commands to JovianDSS servers

In order to create single exe file run:
C:\Python27\Scripts>pyinstaller.exe --onefile jdss-api-tools.py

And try it:
C:\Python27>dist\jdss-api-tools.exe -h

Missing Python modules need to be installed with pip, e.g.:
C:\Python27\Scripts>pip install ipcalc

NOTE:
In case of error "msvcr100.dll missing...",
download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe


2018-02-07  initial release
2018-03-06  add create pool
2018-03-18  add delete_clone option (it deletes the snapshot as well) (kris@dddistribution.be)
2018-04-23  add set_host  --host --server --description
2018-04-23  add network
2018-04-23  add info
2018-05-05  add network info
2018-05-06  add pools info
2018-05-28  add set_time
2018-06-06  fix spelling
2018-06-07  add clone_existing_snapshot option (kris@dddistribution.be)
2018-06-09  add delete_clone_existing_snapshot option (kris@dddistribution.be)
2018-06-21  add user defined share name for clone and make share invisible by default
2018-06-23  add bond create and delete
2018-06-25  add bind_cluster
2018-07-03  add HA-cluster mirror path
2018-07-03  add start-cluster
2018-07-05  add move (failover)
2018-07-24  add missing msg for ip addr change
2018-07-27  network improvements and fixes
2018-08-08  add create_vip
2018-08-27  add create storage resources and scrub and help-in-color
2018-09-05  add batch_setup, create_factory_setup_files, scrub, set_scrub_scheduler, node-ip requires --nodes prefix 
"""
    
from __future__ import print_function
import sys
import time
import datetime
import argparse
import collections
import ipcalc
import ping
from jovianapi import API
from jovianapi.resource.pool import PoolModel
from colorama import init
from colorama import Fore, Back, Style


__author__  = 'janusz.bak@open-e.com'
__version__ = 1.0

## Script global variables - to be updated in parse_args():
line_separator          = '='*62
action                  = ''
action_message          = ''
delay                   = 0
nodes                   = []
auto_target_name        = "iqn.auto.api.backup.target"        
auto_scsiid             = time.strftime("%Yi%mi%di%Hi%M")  #"1234567890123456"
auto_snap_name          = "auto_api_backup_snap"
auto_vol_clone_name     = "_auto_api_vol_clone"
auto_zvol_clone_name    = "_auto_api_zvol_clone"


KiB,MiB,GiB,TiB = (pow(1024,i) for i in (1,2,3,4))

## TARGET NAME
target_name_prefix= "iqn.%s-%s:jdss.target" % (time.strftime("%Y"),time.strftime("%m"))

## ZVOL NAME
zvol_name_prefix = 'zvol00'


def interface():
    wait_for_node()
    return API.via_rest(node, api_port, api_user, api_password)


def get(endpoint):
    global error
    result = None
    error = ''
    api=interface()
    try:
        result = api.driver.get(endpoint)['data']
    except Exception as e:
        error = str(e[0])
    return result


def put(endpoint,data):
    global error
    result = None
    error = ''
    api=interface()
    try:
        result = api.driver.put(endpoint,data)
    except Exception as e:
        error = str(e[0])
    return result


def post(endpoint,data):
    global error
    result = None
    error = ''
    api=interface()
    try:
        result = api.driver.post(endpoint,data)
    except Exception as e:
        error = str(e[0])
    return result


def delete(endpoint,data):
    api=interface()
    return api.driver.delete(endpoint,data)

'''
##to-do
def delete(endpoint,data):
    global error
    result = None
    error = ''
    api=interface()
    try:
        result = api.driver.delete(endpoint,data)
    except Exception as e:
        error = str(e[0])
    return result
'''

def wait_for_node():

    global waiting_dots_printed
    waiting_dots_printed = False
    ## PING
    repeat = 100
    counter = 0
    while ping.quiet_ping(node)[0]>0:
        if counter < 2:
            print_with_timestamp( 'Node {} does not respond to ping command.'.format(node))
        elif counter > 1:
            print('.',end='')
            waiting_dots_printed = True
        counter += 1
        if counter == repeat:   ## Connection timed out
            exit_with_timestamp( 'Connection timed out: {}'.format(node_ip_address))

    waiting_dots_printed = False

    ## REST API
    repeat = 100
    counter = 0
    while True:
        try:
            api = API.via_rest(node, api_port, api_user, api_password)
            endpoint = '/conn_test'
            api.driver.get(endpoint)['data']  ## GET
        except Exception as e:
            error = str(e[0])
            if counter in (1,2):
                print_with_timestamp( 'Node {} does not respond to REST API commands.'.format(node))
            elif counter == 3:
                    print_with_timestamp(
                    'Please enable REST API on {} in GUI: System Settings -> Administration -> REST access, or check access credentials.'.format(node))
            elif counter > 3:
                print('.',end='')
                waiting_dots_printed = True
        else:
            try:
                if to_print_timestamp_msg[node]:
                    if action_message:
                        print_with_timestamp(action_message)
                    else:
                        print_with_timestamp('Node {} is running.'.format(node))
                    to_print_timestamp_msg[node] = False

            except Exception as e:
                pass
            break
        counter += 1
        time.sleep(4)
        if counter == repeat:   ## Connection timed out
            exit_with_timestamp( 'Connection timed out: {}'.format(node_ip_address))


def get_args(batch_args_line=None):
    
    global parser

    parser = argparse.ArgumentParser(
        prog='jdss-api-tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='The %(prog)s remotely execute given command.',
        epilog='''
{LG}# jdss-api-tools{ENDF}


{BOLD}Execute given JovianDSS command for automated setup and to control JovianDSS remotely.{END}


{LG}EXAMPLES:{ENDF}

 1. {BOLD}Create clone{END} of iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.

    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the target exports most recent data every run.
    The example is using default password and port.
    Tools automatically recognize the volume type. If given volume is iSCSI volume,
    the clone of the iSCSI volume will be attached to iSCSI target.
    If given volume is NAS dataset, the created clone will be exported via network share
    as shown in the next example.

    {LG}%(prog)s clone --pool Pool-0 --volume zvol00 --node 192.168.0.220{ENDF}

 2. {BOLD}Create clone{END} of NAS volume vol00 from Pool-0 and share via new created SMB share.

    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the share exports most recent data every run. The share is invisible by default.
    The example is using default password and port and make the share visible with default share name.

    {LG}%(prog)s clone --pool Pool-0 --volume vol00 --visible --node 192.168.0.220{ENDF}

    The examples are using default password and port and make the shares invisible.
     
    {LG}%(prog)s clone --pool Pool-0 --volume vol00 --share_name vol00_backup --node 192.168.0.220{ENDF}
    {LG}%(prog)s clone --pool Pool-0 --volume vol01 --share_name vol01_backup --node 192.168.0.220{ENDF}

 3. {BOLD}Delete clone{END} of iSCSI volume zvol00 from Pool-0.

    {LG}%(prog)s delete_clone --pool Pool-0 --volume zvol00 --node 192.168.0.220{ENDF}

 4. {BOLD}Delete clone{END} of NAS volume vol00 from Pool-0.

    {LG}%(prog)s delete_clone --pool Pool-0 --volume vol00 --node 192.168.0.220{ENDF}

 5. {BOLD}Create clone{END} of existing snapshot on iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.

    The example is using password 12345 and default port.

    {LG}%(prog)s clone_existing_snapshot --pool Pool-0 --volume zvol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}

 6. {BOLD}Create clone{END} of existing snapshot on NAS volume vol00 from Pool-0 and share via new created SMB share.

    The example is using password 12345 and default port.

    {LG}%(prog)s clone_existing_snapshot --pool Pool-0 --volume vol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}

 7. {BOLD}Delete clone{END} of existing snapshot on iSCSI volume zvol00 from Pool-0.

    The example is using password 12345 and default port.

    {LG}%(prog)s delete_clone_existing_snapshot --pool Pool-0 --volume zvol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}

 8. {BOLD}Delete clone{END} of existing snapshot on NAS volume vol00 from Pool-0.

    The example is using password 12345 and default port.

    {LG}%(prog)s delete_clone_existing_snapshot --pool Pool-0 --volume vol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}

 9. {BOLD}Create pool{END} on single node or cluster with single JBOD:

    Pool-0 with 2 * raidz1(3 disks) total 6 disks 

    {LG}%(prog)s create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --node 192.168.0.220{ENDF}

10. {BOLD}Create pool{END} on Metro Cluster with single JBOD with 4-way mirrors:

    Pool-0 with 2 * mirrors(4 disks) total 8 disks 

    {LG}%(prog)s create_pool --pool Pool-0 --vdevs 2 --vdev mirror --vdev_disks 4 --node 192.168.0.220{ENDF}

11. {BOLD}Create pool{END} with raidz2(4 disks each) over 4 JBODs with 60 HDD each.

    Every raidz2 vdev consists of disks from all 4 JBODs. An interactive menu will be started.
    In order to read disks, POWER-ON single JBOD only. Read disks selecting "0" for the first JBOD.
    Next, POWER-OFF the first JBOD and POWER-ON the second one. Read disks of the second JBOD selecting "1".
    Repeat the procedure until all JBODs disk are read. Finally, create the pool selecting "c" from the menu.

    {LG}%(prog)s create_pool --pool Pool-0 --jbods 4 --vdevs 60 --vdev raidz2 --vdev_disks 4 --node 192.168.0.220{ENDF}

12. {BOLD}Shutdown{END} three JovianDSS servers using default port but non default password.

    {LG}%(prog)s --pswd password shutdown --nodes 192.168.0.220 192.168.0.221 192.168.0.222{ENDF}

    or with IP range syntax ".."

    {LG}%(prog)s --pswd password shutdown --node 192.168.0.220..222{ENDF}

13. {BOLD}Reboot{END} single JovianDSS server.

    {LG}%(prog)s reboot --node 192.168.0.220{ENDF}

14. {BOLD}Set host name{END} to "node220", server name to "server220" and server description to "jdss220".

    {LG}%(prog)s set_host --host node220 --server server220 --description jdss220 --node 192.168.0.220{ENDF}

15. {BOLD}Set timezone and NTP-time{END} with default NTP servers.

    {LG}%(prog)s set_time --timezone America/New_York --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone America/Chicago --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone America/Los_Angeles --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone Europe/Berlin --node 192.168.0.220{ENDF}

16. {BOLD}Set new IP settings{END} for eth0 and set gateway-IP and set eth0 as default gateway.

    Missing netmask option will set default 255.255.255.0

    {LG}%(prog)s network --nic eth0 --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.220{ENDF}

    Setting new DNS only.

    {LG}%(prog)s network --new_dns 192.168.0.1 --node 192.168.0.220{ENDF}

    Setting new gateway only. The default gateway will be set automatically.

    {LG}%(prog)s network --nic eth0 --new_gw 192.168.0.1 --node 192.168.0.220{ENDF}

17. {BOLD}Create bond{END} examples. Bond types: balance-rr, active-backup.
    Default   active-backup

    {LG}%(prog)s create_bond --bond_nics eth0 eth1 --new_ip 192.168.0.80 --node 192.168.0.80{ENDF}
    {LG}%(prog)s create_bond --bond_nics eth0 eth1 --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.80{ENDF}
    {LG}%(prog)s create_bond --bond_nics eth0 eth1 --bond_type active-backup --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.80{ENDF}

18. {BOLD}Delete bond{END}.

    {LG}%(prog)s delete_bond --nic bond0 --node 192.168.0.80{ENDF}

19. {BOLD}Bind cluster{END}. Bind node-b: 192.168.0.81 with node-a: 192.168.0.80{ENDF}

    RESTapi user   admin, RESTapi password   password, node-b GUI password   admin

    {LG}%(prog)s bind_cluster --user admin --pswd password --bind_node_password admin --node 192.168.0.80 192.168.0.81{ENDF}

20. {BOLD}Set HA-cluster ping nodes{END}. First IP   access node IP, next IPs are new ping nodes

    RESTapi user   administrator, RESTapi password   password, netmask   255.255.0.0

    {LG}%(prog)s set_ping_nodes --user administrator --pswd password --netmask 255.255.0.0  --ping-nodes 192.168.0.240 192.168.0.241 192.168.0.242 --node 192.168.0.80 {ENDF}

    Same, but with defaults: user   admin, password   admin and netmask   255.255.255.0

    {LG}%(prog)s set_ping_nodes  --ping-nodes 192.168.0.240 192.168.0.241 192.168.0.242 --node 192.168.0.80{ENDF}

21. {BOLD}Set HA-cluster mirror path{END}. Please enter comma separated NICs, the first NIC must be from the same node as the specified access IP.

    {LG}%(prog)s set_mirror_path --mirror_nics eth4 eth4 --node 192.168.0.82{ENDF}

22. {BOLD}Create VIP (Virtual IP){END} examples. 

    {LG}%(prog)s create_vip --pool Pool-0 --vip_name vip21 --vip_nics eth2,eth2 --vip_ip 192.168.21.100  --vip_mask 255.255.0.0 --node 192.168.0.80{ENDF}
    {LG}%(prog)s create_vip --pool Pool-0 --vip_name vip31 --vip_nics eth2      --vip_ip 192.168.31.100  --node 192.168.0.80{ENDF}

    If cluster is configured both vip_nics must be provided.
    With single node (no cluster) only first vip_nic specified will be used.
    The second nic (if specified) will be ignored. Default vip_mask 255.255.255.0

23. {BOLD}Start HA-cluster{END}. Please enter first node IP address only.

    {LG}%(prog)s start_cluster --node 192.168.0.82{ENDF}

24. {BOLD}Move (failover){END} given pool.

    The current active node of given pool will be found and pool will be moved to passive node.

    {LG}%(prog)s move --pool Pool-0 --node 192.168.0.82{ENDF}

25. {BOLD}Create storage resource{END}. Creates iSCSI target with volume or SMB share with dataset.

    iSCSI target with volume

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --volume zvol00 --target_name iqn.2018-08:ha-00.target0 --size 1TB --provisioning thin --node 192.168.0.220{ENDF}

    with defaults: size 1TB, provisioning thin volume auto target_name auto
    if target_name auto(default), the cluster name "ha-00" will be used in the auto-target_name. In this example target name will be: iqn.2018-09:ha-00.target000
    if iqn.2018-09:ha-00.target000 and zvol000 allreday exist program will use next one: if iqn.2018-09:ha-00.target1 and zvol001

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --cluster ha-00 --node 192.168.0.220{ENDF}

    with missing --cluster ha-00, it will produce same result as "ha-00" is default cluster name.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --node 192.168.0.220{ENDF}
       
    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb --volume vol000 --share_name data  --node 192.168.0.220{ENDF}

    with defaults: volume auto share_name auto

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb  --node 192.168.0.220{ENDF}

    and multi-resource with --quantity option, starting consecutive number from zero (default)

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 5  --node 192.168.0.220{ENDF}

    and multi-resource with --quantity option, but starting consecutive number from 5 (--start_with 10)
    
    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 5 --start_with 10  --node 192.168.0.220{ENDF}
    

26. {BOLD}Scrub start|stop{END}.
 
    Scrub all pools. If the node belongs to cluster, scrub all pools in cluster.

    {LG}%(prog)s scrub 192.168.0.220{ENDF}

    Scrub specified pools only.
    
    {LG}%(prog)s scrub --pool Pool-0 --node 192.168.0.220{ENDF}
    {LG}%(prog)s scrub --pool Pool-0 --pool Pool-1 --pool Pool-2 --node 192.168.0.220{ENDF}

    {LG}%(prog)s scrub --action stop --node 192.168.0.220{ENDF}
    

27. {BOLD}Set scrub scheduler{END}.
    By default the command search all pools on node ot cluster(if configured) and set default schedule: evey month at 0:15.
    Every pool will set on diffrent month day.

    {LG}%(prog)s set_scrub_scheduler --node 192.168.0.220{ENDF}

    set default schedule on Pool-0 and Pool-1 only.
    
    {LG}%(prog)s set_scrub_scheduler  --pool Pool-0 Pool-1 --node 192.168.0.220{ENDF}

    set chedule on every week on Monday at 1:10 AM on Pool-0 only.
    
    {LG}%(prog)s set_scrub_scheduler  --pool Pool-0 --day_of_the_month * --day_of_the_week 1 --hour 1 --minute 10 --node 192.168.0.220{ENDF}

    set chedule on every day at 2:30 AM on Pool-0 only.
    
    {LG}%(prog)s set_scrub_scheduler  --pool Pool-0 --day_of_the_month * --hour 2 --minute 30 --node 192.168.0.220{ENDF}

    set chedule on every second day at 21:00 (9:00 PM))on Pool-0 only.
    
    {LG}%(prog)s set_scrub_scheduler  --pool Pool-0 --day_of_the_month */2 --hour 20 --minute 0 --node 192.168.0.220{ENDF}

    {BOLD}TIP:{END}
    Quick schedule params check via browser on {LG}Pool-0 192.168.0.220{ENDF}:
    https://{LG}192.168.0.220{ENDF}:82/api/v3/pools/{LG}Pool-0{ENDF}/scrub/scheduler


28. {BOLD}Genarate factory setup files for batch setup.{END}.
    It creates and overwrite(if previously created) batch setup files.
    Setup files need to be edited and changed to required setup accordingly.
    For single node setup single node ip address can be specified.
    For cluster, both cluster nodes, so it will create setup file for every node.

    {LG}%(prog)s create_factory_setup_files --nodes 192.168.0.80 192.168.0.81{ENDF}


29. {BOLD}Execute factory setup files for batch setup.{END}.
     This example run setup for nodes 192.168.0.80, 192.168.0.81.
     Both nodes nned to be fresh rebooted with factory defaults eth0=192.168.0.220.
     First only one node must be started. Once booted, the REST api must be enabled via GUI.
     The batch setup will start to cofigure first node. Now, the second node can be booted.
     Once the second node is up, also the REST api must be enabled via GUI.


    {LG}%(prog)s batch_setup  --setup_files  api_setup_single_node_80.txt api_setup_single_node_81.txt api_setup_cluster_80.txt api_test_cluster_80.txt  --node 192.168.0.80{ENDF}


30. {BOLD}Print system info{END}.

    {LG}%(prog)s info --node 192.168.0.220{ENDF}


############################################################################################

After any modifications of source jdss-tools.py, run pyinstaller to create new jdss-tools.exe:

	C:\Python27\Scripts>pyinstaller.exe --onefile jdss-api-tools.py

And try it:

	C:\Python27>dist\jdss-api-tools.exe -h

Missing Python modules need to be installed with pip, e.g.:

	C:\Python27\Scripts>pip install ipcalc
	C:\Python27\Scripts>pip install ping
	C:\Python27\Scripts>pip install colorama


NOTE:
In case of error: "msvcr100.dll missing...",
download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe
'''
.format(BOLD=Style.BRIGHT,END=Style.NORMAL,LG=Fore.LIGHTGREEN_EX ,ENDF=Fore.RESET))
    ## ENDS->End-Style, ENDF->End-Foreground
    global commands    
    commands = parser.add_argument(
        'cmd',
        metavar='command',
        choices=['clone', 'clone_existing_snapshot', 'create_pool', 'scrub', 'set_scrub_scheduler', 'create_storage_resource', 'delete_clone',
                 'delete_clone_existing_snapshot', 'set_host', 'set_time', 'network', 'create_bond', 'delete_bond',
                 'bind_cluster', 'set_ping_nodes','set_mirror_path', 'create_vip', 'start_cluster', 'move', 'info',
                 'shutdown', 'reboot', 'batch_setup', 'create_factory_setup_files'],
        help='Commands:  %(choices)s.'
    )
    parser.add_argument(
        '--nodes',
        metavar='ip-addr',
        required=True,
        nargs='+',
        help='Enter nodes IP(s). Some commands work with multi nodes. Enter space separated IP or with .. range of IPs.'
    )
    parser.add_argument(
        '--pool',
        metavar='name',
        action='append',
        help='Enter pool name. If command require more pools, enter one more --pool name option.'
    )
    parser.add_argument(
        '--volume',
        metavar='name',
        default='auto',
        help='Enter required volume name. Default=auto, volume name will be auto-generated'
    )
    parser.add_argument(
        '--storage_type',
        metavar='iscsi|smb|nfs|smb nfs|fc',
	nargs='+',
        help='Enter iscsi or fc(not implemented yet) or smb or nfs or smb nfs.'
    )
    parser.add_argument(
        '--size',
        metavar='size',
        default='1TB',
        help='Enter SAN(zvol) size in human readable format i.e. 100GB, 1TB, etc. Default = 1TB.'
    )
    parser.add_argument(
        '--provisioning',
        metavar='thin|thick',
        default='thin',
        help='Enter thick or thin provisioning option. Thin provisioning is default'
    )
    parser.add_argument(
        '--target',
        metavar='name',
        default='auto',
        help='Enter iSCSI target name. If not specified, auto-target-name will be generated '
    )
    parser.add_argument(
        '--quantity',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of storage-resources to create , default=1'
    )
    parser.add_argument(
        '--start_with',
        metavar='number',
        default=0,
        type=int,
        help='Enter starting number of the consecutive number. Default=0'
    )
    parser.add_argument(
        '--cluster',
        metavar='name',
        default='ha-00',
        help='Enter the cluster name. The default cluster name = ha-00'
    )
    parser.add_argument(
        '--snapshot',
        metavar='name',
        help='Enter snapshot name'
    )
    parser.add_argument(
        '--jbods',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of JBODs, default=1'
    )
    parser.add_argument(
        '--jbod_disks',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of disks in JBOD'
    )
    parser.add_argument(
        '--vdev_disks',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of disks in vdev'
    )
    parser.add_argument(
        '--vdev',
        metavar='type',
        default='single',
        help='Enter vdev type: single, mirror, raidz1, raidz2, raid3'
    )
    parser.add_argument(
        '--vdevs',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of vdevs in pool'
    )
    parser.add_argument(
        '--host',
        metavar='name',
        default=None,
        help='Enter host name'
    )
    parser.add_argument(
        '--server',
        metavar='name',
        default=None,
        help='Enter server name'
    )
    parser.add_argument(
        '--description',
        metavar='desc.',
        default=None,
        help='Enter server description'
    )
    parser.add_argument(
        '--timezone',
        metavar='zone',
        default=None,
        help='Enter timezone'
    )
    parser.add_argument(
        '--ntp',
        metavar='ON|OFF',
        default='ON',
        help='Enter "ON" to enable, "OFF" to disable NTP'
    )
    parser.add_argument(
        '--ntp_servers',
        metavar='servers',
        default='0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org',
        help='Enter NTP servers(s)'
    )
    parser.add_argument(
        '--nic',
        metavar='name',
        default=None,
        help='Enter NIC name. Example: eth0, eth1, bond0, bond1, etc.'
    )
    parser.add_argument(
        '--new_ip',
        metavar='address',
        default=None,
        help='Enter new IP address for selected NIC'
    )
    parser.add_argument(
        '--new_mask',
        metavar='mask',
        default='255.255.255.0',
        help='Enter new subnet mask for selected NIC'
    )
    parser.add_argument(
        '--new_gw',
        metavar='address',
        default=None,
        help='Enter new gateway for selected NIC'
    )
    parser.add_argument(
        '--new_dns',
        metavar='address',
        default=None,   # default None, empty string "" will clear dns
        help='Enter new dns address or comma separated list'
    )
    parser.add_argument(
        '--bond_type',
        metavar='type',
        choices=['active-backup', 'balance-rr'],
        default='active-backup',
        help='Enter bond type: balance-rr, active-backup. Default=active-backup'
    )
    parser.add_argument(
        '--bond_nics',
        metavar='nics',
        nargs='+',
        help='Enter at least two nics names, space separated bond NICs.'
    )
    parser.add_argument(
        '--mirror_nics',
        metavar='nics',
        nargs='+',
        default=None,   
        help='Enter space separated mirror path NICs.'
    )
    parser.add_argument(
        '--ping_nodes',
        metavar='ip-addr',
        nargs='+',
        help='Enter ping nodes IP(s). Enter at least 2 space separated IPs.'
    )
    parser.add_argument(
        '--vip_name',
        metavar='name',
        default=None,   
        help='Enter new VIP name (alias).'
    )
    parser.add_argument(
        '--vip_nics',
        metavar='nics',
        nargs='+',
        default=None,   
        help='Enter space separated both cluster nodes NICs, or single NIC for single node. '
    )
    parser.add_argument(
        '--vip_ip',
        metavar='address',
        default=None,   
        help='Enter new VIP address. '
    )
    parser.add_argument(
        '--vip_mask',
        metavar='mask',
        default='255.255.255.0',
        help='Enter VIP subnet mask'
    )
    parser.add_argument(
        '--user',
        metavar='user',
        default='admin',
        help='RESTapi user, default=admin'
    )
    parser.add_argument(
        '--pswd',
        metavar='password',
        default='admin',
        help='Administrator password, default=admin'
    )
    parser.add_argument(
        '--port',
        metavar='port',
        default=82,
        type=int,
        help='RESTapi port, default=82'
    )
    parser.add_argument(
        '--delay',
        metavar='seconds',
        default=30,
        type=int,
        help='User defined reboot/shutdown delay, default=30 sec'
    )
    parser.add_argument(
        '--tolerance',
        metavar='GiB',
        default=5,
        type=int,
        help='Disk size tolerance. Treat smaller disks still as equal in size, default=5 GiB'
    )
    parser.add_argument(
        '--share_name',
        metavar='name',
        default='auto',   
        help='Enter share name. Default for clone actions=auto_api_backup_share, Default for create NAS-resource=auto'
    )
    parser.add_argument(
        '--visible',
        dest='visible',
        action='store_true',
        default=False,
        help='SMB share is created as invisible by default'
    )
    parser.add_argument(
        '--bind_node_password',
        metavar='password',
        default='admin',
        help='Bind node password, default=admin'
    )
    parser.add_argument(
        '--scrub_action',
        metavar='start|stop|status',
        choices=['start', 'stop', 'status'],
        default='start',
        help='Enter scrub action, Default=start.'
    )
    parser.add_argument(
        '--day_of_the_month',
        metavar='day',
        nargs = '*',
        choices=[str(i) for i in range(1,32)],
        default = all,  
        help='Enter the day of a month of schedule plan. Default=1.'
    )
    parser.add_argument(
        '--month_of_the_year',
        metavar='day',
        nargs = '*',
        choices=[str(i) for i in range(1,13)],
        default = all,  
        help='Enter the month or months (space separated) of the year of schedule plan, Default 1 2 3 4 5 6 7 8 9 10 11 12 (every-month).'
    )
    parser.add_argument(
        '--day_of_the_week',
        metavar='day',
        nargs = '*',
        choices=[str(i) for i in range(1,8)],
        default = all,  
        help='Enter the day or days (space separated) of the week of schedule plan.'
    )
    parser.add_argument(
        '--hour',
        metavar='hour',
        nargs = '*',
        choices=[str(i) for i in range(24)],
        default = all,  
        help='Enter the hour of schedule plan, Default=0.'
    )
    parser.add_argument(
        '--minute',
        metavar='minute',
        nargs = '*',
        choices=[str(i) for i in range(60)],
        default = all,  
        help='Enter the minute of schedule plan, Default=15.'
    )
    parser.add_argument(
        '--menu',
        dest='menu',
        action='store_true',
        default=False,
        help='Interactive menu. Auto-start with --jbods_num > 1'
    )
    parser.add_argument(
        '--setup_files',
        metavar='file',
        nargs='+',
        type=argparse.FileType('r')
    )


    ## ARGS
    if batch_args_line:
        args = parser.parse_args(batch_args_line.split())
    else:
        args = parser.parse_args()
    ## convert args Namespace to dictionary
    args = vars(args)
    ## '' in command line is validated as "''"
    ## need to replace it with empty string
    for key,value in args.items():
        if type(value) is str:
            if value in "''":
                args[key] = ""

    
    global api_port, api_user, api_password, action, pool_name, pools_names, volume_name, storage_type, storage_volume_type, size, sparse, snapshot_name
    global nodes, ping_nodes, node
    global delay, menu
    global share_name, visible
    global jbod_disks_num, vdev_disks_num, jbods_num, vdevs_num, vdev_type, disk_size_tolerance
    global nic_name, new_ip_addr, new_mask, new_gw, new_dns, bond_type, bond_nics, mirror_nics
    global host_name, server_name, server_description, timezone, ntp, ntp_servers
    global vip_name, vip_nics, vip_ip, vip_mask
    global bind_node_password
    global to_print_timestamp_msg, waiting_dots_printed
    global pool_based_consecutive_number_generator
    global cluster_pool_names
    global target_name, cluster_name
    global quantity, start_with
    global scrub_action
    global day_of_the_month, month_of_the_year, day_of_the_week, hour, minute

    global setup_files
    

    api_port                = args['port']
    api_user                = args['user']
    api_password            = args['pswd']
    action                  = args['cmd']     ## the command
    pool_name               = args['pool']
    volume_name             = args['volume']
    storage_type            = args['storage_type']
    sparse                  = args['provisioning'].upper() ## THICK | THIN, default==THIN
    size                    = args['size']
    target_name             = args['target']
    quantity                = args['quantity']
    start_with              = args['start_with']
    cluster_name            = args['cluster']

    share_name              = args['share_name']
    visible                 = args['visible']
    snapshot_name           = args['snapshot']
    jbod_disks_num          = args['jbod_disks']
    vdev_disks_num          = args['vdev_disks']
    jbods_num               = args['jbods']
    vdevs_num               = args['vdevs']
    vdev_type               = args['vdev']
    disk_size_tolerance     = args['tolerance'] * GiB
    host_name               = args['host']
    server_name             = args['server']
    server_description      = args['description']
    timezone                = args['timezone']
    ntp                     = args['ntp'].upper() ## ON | OFF, default=ON
    ntp_servers             = args['ntp_servers']
    
    nic_name                = args['nic']
    new_ip_addr             = args['new_ip']
    new_mask                = args['new_mask']
    new_gw                  = args['new_gw']
    new_dns                 = args['new_dns']
    bond_type               = args['bond_type']
    bond_nics               = args['bond_nics']
    bind_node_password      = args['bind_node_password']
    mirror_nics             = args['mirror_nics']

    vip_name                = args['vip_name']
    vip_nics                = args['vip_nics']
    vip_ip                  = args['vip_ip']
    vip_mask                = args['vip_mask']

    delay                   = args['delay']
    nodes                   = args['nodes']
    ping_nodes              = args['ping_nodes']

    scrub_action            = args['scrub_action']
    day_of_the_month        = args['day_of_the_month']
    month_of_the_year       = args['month_of_the_year']
    day_of_the_week         = args['day_of_the_week']
    hour                    = args['hour']
    minute                  = args['minute']
    
    menu                    = args['menu']
    setup_files             = args['setup_files']
    

    ## scrub scheduler
    ## set default to 1st of every month at 0:15
    if day_of_the_month == all:
        day_of_the_month = '1'
    if month_of_the_year == all:
        month_of_the_year = '*'
    if day_of_the_week == all:
        day_of_the_week = '*'
    if hour == all:
        hour = '0'
    if minute == all:
        minute = '15'
  
    
    pools_names = pool_name
    if pool_name:
        pool_name = pool_name[0]
        

    ## start menu if multi-JBODs
    if jbods_num > 1: 
        menu = True

    ## storage_type   list  ISCSI, FC, SMB, NFS or SMB,NFS
    ## storage_volume_type  ISCSI, FC ='volume', SMB, NFS ='dataset'
    if storage_type:
        storage_type=[ item.upper() for item in storage_type]
        if len(storage_type)>1:
            if not ('SMB' in storage_type and 'NFS' in storage_type):
                sys_exit_with_timestamp('Error: Only SMB with NFS combination is allowed.')
            else:
                if 'FC' in storage_type :
                    sys_exit_with_timestamp('Error: FC setup automation not implemented yet.')
        vt = dict(ISCSI='volume',FC='volume',SMB='dataset',NFS='dataset')
        storage_volume_type = vt[storage_type[0]]
        
    ## THIN=True, THICK=False 
    if sparse:
        sparse.upper()
        s = dict(THIN=True,THICK=False)
        sparse = s[sparse]
        
    ## size: human to bytes (default=1TB)
    size = size.strip('Bb')    
    size = str(human2bytes(size))

    ## change default share name from "auto" to "auto_api_backup_share"
    if 'clone' in action and share_name == 'auto':
        share_name = 'auto_api_backup_share'
        
    
    ## expand nodes list if IP range provided in args
    ## i.e. 192.168.0.220..221 will be expanded to: ["192.168.0.220","192.168.0.221"]
    expanded_nodes = []
    for ip in nodes:
        if ".." in ip:
            expanded_nodes += expand_ip_range(ip)
        else:
            expanded_nodes.append(ip)
    nodes = expanded_nodes

    ## first node
    node    = nodes[0]
    
    ## True if action msg need to be printed
    to_print_timestamp_msg = dict(zip(nodes,(True for i in nodes)))
    waiting_dots_printed = False

            
    ## validate all-ip-addr => (nodes + new_ip, new_gw, new_dns)
    all_ip_addr = nodes[:]  ## copy
    all_ip_addr = all_ip_addr + ping_nodes if ping_nodes else all_ip_addr
    for ip in new_ip_addr, new_gw, new_dns, new_mask:
        if ip:
            all_ip_addr.append(ip)
    for ip in all_ip_addr :
        if not valid_ip(ip) :
            sys_exit( 'IP address {} is invalid'.format(ip))

    ## detect doubles
    doubles = [ip for ip, c in collections.Counter(nodes).items() if c > 1]
    if doubles:
        sys_exit( 'Double IP address: {}'.format(', '.join(doubles)))

    ## validate port
    if not 22 <= api_port <= 65535:
        sys_exit( 'Port {} is out of allowed range 22..65535'.format(port))


#_____________________END_OF_ARGS_____________________#



def is_node_alive(test_node):
    api = API.via_rest(test_node, api_port, api_user, api_password)
    try:
        result = api.driver.get('/conn_test')['data']
    except:
        result = None
    return True if result else False

    
def wait_for_move_destination_node(test_node):
    repeat = 100
    counter = 0
    time.sleep(15)
    while not is_node_alive(test_node):
        counter += 1
        time.sleep(30)
        print_with_timestamp( 'Waiting for : {}.'.format(test_node))
        if counter == repeat:   ## timed out
            exit_with_timestamp( 'Time out of waiting for : {}.'.format(test_node))


def wait_for_zero_unmanaged_pools():
    repeat = 300
    counter = 0
    time.sleep(5)
    while is_node_running_any_unmanaged_pool():
        counter += 1
        time.sleep(20)
        unmanaged_pools_names = unmanaged_pools()
        print_with_timestamp( 'Unmanaged pools: {}. Wait for managed state.'.format(','.join(unmanaged_pools_names)))
        if counter == repeat:   ## timed out
            unmanaged_pools_names = unmanaged_pools()
            exit_with_timestamp( 'Unmanaged pools: {}'.format(','.join(unmanaged_pools_names)))


def human2bytes(s):
    """
    Author: Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
    License: MIT
    """
    SYMBOLS = {
        'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
        'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                           'zetta', 'iotta'),
        'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
        'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                           'zebi', 'yobi'),
    }
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])


def consecutive_number_generator():
    i = start_with
    while 1:
        yield i
        i+=1


def initialize_pool_based_consecutive_number_generator():
    global pool_based_consecutive_number_generator
    pool_based_consecutive_number_generator = {}  
    cluster_pool_names = get_cluster_pools_names()
    for cluster_pool_name in cluster_pool_names:
        ## add generator for every cluster pool
        pool_based_consecutive_number_generator[cluster_pool_name] = consecutive_number_generator()


def convert_comma_separated_to_list(arg):
    if arg is None:
        return None
    if arg is '':
        return []
    for sep in ',;':
        if sep in arg:
            arg=arg.split(sep)
    if type(arg) is str:
        arg=arg.split() ## no separator, single item arg listnew_dns
    return arg


def count_provided_args(*args):
    return len(args) - args.count(None)


def seconds_to_string(seconds):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(seconds))) if seconds > 0 else '-'


def time_stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def time_stamp_clone_syntax():
    return time.strftime("_%Y-%m-%d_%H-%M-%S")


def print_with_timestamp(msg):
    if waiting_dots_printed:
        print()
    print('{}  {}'.format(time_stamp(), msg))


def sys_exit_with_timestamp(msg):
    print_with_timestamp(msg)
    print()
    sys.exit(1)


def sys_exit(msg):
    print('\n\t',msg)
    sys.exit(1)


def valid_ip(address):
    if [ch for ch in  address if ch not in '.0123456789']:
        return False
    try:
        host_bytes = address.split('.')
        valid = [int(b) for b in host_bytes]
        valid = [b for b in valid if 0 <= b <= 255]
        return len(host_bytes) == len(valid) == 4
    except:
        return False


def increment_3rd_ip_subnet(address):
    if not valid_ip(address):
        return None
    segments = address.split('.')
    segments[2] = str(int(segments[2])+1)
    new_ip = '.'.join(segments)
    if valid_ip(new_ip):
        return new_ip
    segments[2] = str(0)
    new_ip = '.'.join(segments)
    return new_ip


def expand_ip_range(ip_range):
	start=int(ip_range.split("..")[0].split(".")[-1])
	end=int(ip_range.split("..")[-1])
	base=".".join(ip_range.split(".")[:3])+"."
	ip_list = []
	for i in range(start,end+1):
		ip_list.append(base+str(i))
	return ip_list


def display_delay(msg):
    for sec in range(delay, 0, -1) :
        print( '{} in {:>2} seconds \r'.format(msg,sec))
        time.sleep(1)


def shutdown_nodes():
    global node
    global action_message
    action_message = 'Sending shutdown request to: {}'.format(node)
    _nodes = get_cluster_nodes_addresses()
    passive_node = [_node for _node in _nodes if _node not in node][0]
    wait_for_move_destination_node(passive_node)
    wait_for_zero_unmanaged_pools() 
    display_delay('Shutdown')
    for node in nodes:
        post('/power/shutdown',dict(force=False))
        print_with_timestamp( 'Shutdown: {}'.format(node))


def reboot_nodes() :
    global node
    global action_message
    action_message = 'Sending reboot request to: {}'.format(node)
    _nodes = get_cluster_nodes_addresses()
    passive_node = [_node for _node in _nodes if _node not in node][0]
    wait_for_move_destination_node(passive_node)
    wait_for_zero_unmanaged_pools() 
    display_delay('Reboot')
    for node in nodes:
        post('/power/reboot', dict(force=False))
        print_with_timestamp( 'Reboot: {}'.format(node))


def set_host_server_name(host_name=None, server_name=None, server_description=None):
    global action_message
    action_message = 'Sending Host,Server Name Setting request to: {}'.format(node)

    data = dict()
    if host_name:
        data["host_name"] = host_name
    if server_name:
        data["server_name"] = server_name
    if server_description:
        data["server_description"] = server_description

    put('/product',data)

    if host_name:
        print_with_timestamp( 'Set host name: {}'.format(host_name))
    if server_name:
        print_with_timestamp( 'Set server name: {}'.format(server_name))        
    if server_description:
        print_with_timestamp( 'Set server description: {}'.format(server_description))
        

def set_time(timezone=None, ntp=None, ntp_servers=None):
    global action_message
    action_message = 'Sending Time Settings request to: {}'.format(node)

    data = dict()
    if timezone:
        data["timezone"] = timezone
    if ntp == "OFF":
        data["daemon"] = False
    if ntp == "ON":
        data["daemon"] = True
    if ntp_servers:
        data["servers"] = ntp_servers.split(",")

    ## exit if DNS is missing
    dns = get_dns()
    if (ntp == 'ON') and (dns is None):
        sys_exit_with_timestamp('Cannot set NTP. Missing DNS setting on node: {}.'.format(node))

    ## PUT
    put('/time',data)

    if error:
        sys_exit_with_timestamp('Cannot set NTP. Error: {}.'.format())

    if timezone:
        print_with_timestamp( 'Set timezone: {}'.format(timezone))
    if ntp is 'ON':
        print_with_timestamp( 'Set time from NTP: {}'.format("Yes"))
    if ntp_servers:
        print_with_timestamp( 'Set NTP servers: {}'.format(ntp_servers))


def print_pools_details(header,fields):
    pools = get('/pools')
    pools.sort(key=lambda k : k['name'])

    fields_length={}
    for field in fields:
        fields_length[field]=0
    for pool in pools:
        for i,field in enumerate(fields):
            value = '-'
            if field in ('size','available'):
                pool[field] =  round(float(pool[field])/pow(1024,4),2)
            if field in ('iostats'):
                pool[field] =  str(pool[field]).replace("u'","").replace("{","").replace("}","").replace("'","")
            if field in pool.keys():
                value = str(pool[field])
            current_max_field_length = max(len(header[i]), len(value)) 
            if current_max_field_length > fields_length[field]:
                fields_length[field] = current_max_field_length

    ## add field seperator
    for key in fields_length.keys():
            fields_length[key] +=  3

    header_format_template  = '{:_>' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
    field_format_template   =  '{:>' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

    print()
    if len(pools):
        print( header_format_template.format( *(header)))
    else:
        print('\tNo imported/active pools found')

    for pool in pools:
        pool_details = []
        for field in fields:
            value = '-'
            if field in pool.keys():
                value = str(pool[field])
                if value in 'None':
                    value = '-'
            pool_details.append(value)
        print(field_format_template.format(*pool_details))


def print_scrub_pools_details(header,fields):
    global node
    global pool_name
    to_print_timestamp_msg[node] = False

    if pools_names:
        pools_names_to_scrub = pools_names
        cluster_pools_names = get_cluster_pools_names()
        for pool_name in pools_names_to_scrub:
            if pool_name not in cluster_pools_names:
                sys_exit_with_timestamp( 'Error: {} does not exist on Node: {}'.format(pool_name,node))
    else:
        pools_names_to_scrub = get_cluster_pools_names()
    pools_names_to_scrub.sort()

    pools = [] #list of pools scrab details
    for pool_name in pools_names_to_scrub:
        node = get_active_cluster_node_address_of_given_pool(pool_name)
        to_print_timestamp_msg[node] = False
        endpoint = '/pools/{POOL}'.format(POOL=pool_name)
        scan_details = get(endpoint)['scan']
        scan_details['pool'] = pool_name
        ## init pool dict
        pool = dict(zip(fields,list('-'*len(fields))))
        for key in scan_details.keys():
            value = scan_details[key]
            value = seconds_to_string(value) if key in ('start_time','end_time') else str(value)
            pool[key] = value
        pools.append(pool)
    
    fields_length={}
    for field in fields:
        fields_length[field]=0
    for pool in pools:
        for i,field in enumerate(fields):
            value = '-'
            if field in pool.keys():
                value = str(pool[field])
            current_max_field_length = max(len(header[i]), len(value)) 
            if current_max_field_length > fields_length[field]:
                fields_length[field] = current_max_field_length

    ## add field seperator
    for key in fields_length.keys():
            fields_length[key] +=  3

    header_format_template  = '{:_>' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
    field_format_template   =  '{:>' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

    print()
    if len(pools):
        print( header_format_template.format( *(header)))
    else:
        print('\tNo imported/active pools found')

    for pool in pools:
        pool_details = []
        for field in fields:
            value = '-'
            if field in pool.keys():
                value = str(pool[field])
                if value in 'None':
                    value = '-'
            pool_details.append(value)
        print(field_format_template.format(*pool_details))


def print_interfaces_details(header,fields):

    interfaces = get('/network/interfaces')
    interfaces.sort(key=lambda k : k['name'])

    fields_length={}
    for field in fields:
        fields_length[field]=0
    for interface in interfaces:
        for i,field in enumerate(fields):
            value = '-'
            if field in ('negotiated_speed','speed'):
                if type(interface[field]) is int:
                    interface[field] /= 1000
            if field in interface.keys():
                value = str(interface[field])
            current_max_field_length = max(len(header[i]), len(value)) 
            if current_max_field_length > fields_length[field]:
                fields_length[field] = current_max_field_length

    ## add field seperator
    for key in fields_length.keys():
            fields_length[key] +=  3

    header_format_template  = '{:_>' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
    field_format_template   =  '{:>' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

    print()
    print( header_format_template.format( *(header)))

    for interface in interfaces:
        interface_details = []
        for field in fields:
            value = '-'
            if field in interface.keys():
                value = str(interface[field])
                if value in 'None':
                    value = '-'
            interface_details.append(value)
        print(field_format_template.format(*interface_details))


def set_default_gateway():
    global action_message
    action_message = 'Sending Default Gateway set request to: {}'.format(node)

    endpoint = '/network/default-gateway'
    data = dict(interface=nic_name)

    ## PUT
    put(endpoint,data)

    endpoint = '/network/default-gateway'
    dgw_interface = None

    ## GET
    dgw_interface = get(endpoint)['interface']

    if dgw_interface is None:
        sys_exit_with_timestamp( 'No default gateway set')
    else:
        print_with_timestamp( 'Default gateway set to: {}'.format(dgw_interface))


def set_dns(dns):
    global action_message
    action_message = 'Sending DNS set request to: {}'.format(node)

    endpoint = '/network/dns'
    data = dict(servers=dns)

    ## PUT
    put(endpoint,data)

    if error:
        sys_exit_with_timestamp( 'Error: setting DNS. {}'.format(error))

    print_with_timestamp( 'DNS set to: {}'.format(', '.join(dns)))


def get_dns():
    dns = None
    endpoint = '/network/dns'
    ## GET
    dns = get(endpoint)
    if error:
        print_with_timestamp( 'Error: getting DNS. {}'.format(error))
    if dns is None:
        return None
    if len(dns['servers']) == 0:
        return None
    else:
        return dns['servers']


def set_scrub_scheduler():
    global node
    global action_message
    action_message = 'Sending set scrub schedule request to: {}'.format(node)
    if not pool_name:
        cluster_pools_names = get_cluster_pools_names()
    incr = 28 / len(cluster_pools_names)
    _day_of_the_month = day_of_the_month
    for _pool_name in sorted(cluster_pools_names):
        data = dict(day_of_the_month=_day_of_the_month, hour=hour, month_of_the_year=month_of_the_year, day_of_the_week=day_of_the_week, minute=minute)
        node = get_active_cluster_node_address_of_given_pool(_pool_name)
        post('/pools/{POOL}/scrub/scheduler'.format(POOL = _pool_name), data)
        print_with_timestamp( 'Scrub schedule set for: {} on {}'.format(_pool_name,node))
        _day_of_the_month = str(int(_day_of_the_month)+incr)
        

def scrub():
    global node
    global action_message
    global pool_name
    action_message = 'Sending scrub {} request to: {}'.format(scrub_action,node)
    if pools_names:
        pools_names_to_scrub = pools_names
        cluster_pools_names = get_cluster_pools_names()
        for pool_name in pools_names_to_scrub:
            if pool_name not in cluster_pools_names:
                sys_exit_with_timestamp( 'Error: {} does not exist on Node: {}'.format(pool_name,node))
    else:
        pools_names_to_scrub = get_cluster_pools_names()
    pools_names_to_scrub.sort()
    for pool_name in pools_names_to_scrub:
        to_print_timestamp_msg[node] = False
        node = get_active_cluster_node_address_of_given_pool(pool_name)
        to_print_timestamp_msg[node] = True
        if scrub_action in ('start','stop'):
            endpoint = '/pools/{POOL}/scrub'.format(POOL=pool_name)
            action_message = 'Sending scrub request to {} on : {}'.format(pool_name, node)
            post(endpoint, dict(action=scrub_action))

    ## print scrub pools details
    header= ('pool','state', 'scrub_start_time', 'end_time', 'rate', 'mins_left','examined', '%', 'total')
    fields= ('pool','state', 'start_time', 'end_time', 'rate', 'mins_left', 'examined', 'percent', 'total')
    print_scrub_pools_details(header,fields)
    

def get_pools_names():
    pools = get('/pools')
    if pools:
        return [pool['name'] for pool in pools]
    else:
        return []


def get_cluster_pools_names():
    global node
    cluster_pools_names = []
    cluster_nodes = get_cluster_nodes_addresses()
    for node in cluster_nodes:
        pools = get('/pools')
        if pools:
            cluster_pools_names += [pool['name'] for pool in pools]
    return cluster_pools_names


def get_active_cluster_node_address_of_given_pool(pool_name):
    global node
    active_node = ''
    cluster_nodes = get_cluster_nodes_addresses()
    for node in cluster_nodes:
        pools = get('/pools')
        pool_names = [pool['name'] for pool in pools]
        if pool_name in pool_names:
            active_node = node
            break
    return active_node


def is_cluster_configured():
    return get('/cluster')['enabled']


def is_cluster_started():
    result = ''
    result = get('/cluster')
    result = result['status'] if result else ''
    return True if 'started' in result else False


def is_node_running_all_managed_pools():
    result = get('/cluster/resources')
    if result:
        return all((item['managed'] for item in result))
    else:
        return True  ## result is None if no cluster cofigured


def is_node_running_any_unmanaged_pool():
    result = get('/cluster/resources')
    if result:
        return not all((item['managed'] for item in result))
    else:
        return False  ## result is None if no cluster cofigured


def managed_pools():
    result = get('/cluster/resources')
    if result:
        return [item['name'] for item in result if item['managed']]
    else:
        return []


def unmanaged_pools():
    result = get('/cluster/resources')
    if result:
        return [item['name'] for item in result if not item['managed']]
    return []

    
def generate_iscsi_target_and_volume_name(pool_name):
    host_name = get('/product')["host_name"]
    consecutive_integer = pool_based_consecutive_number_generator[pool_name].next()
    consecutive_string = "{:0>3}".format(consecutive_integer)
    iscsi_target_name = "iqn.{}:{}.target{}".format(time.strftime("%Y-%m"), host_name, consecutive_string)
    if is_cluster_configured():
        iscsi_target_name = iscsi_target_name.replace(host_name,cluster_name)
    volume_name = "zvol{}".format(consecutive_string)
    return (iscsi_target_name, volume_name)

def generate_share_and_volume_name(pool_name):
    consecutive_integer = pool_based_consecutive_number_generator[pool_name].next()
    consecutive_string = "{:0>3}".format(consecutive_integer)
    share_name = "data{}".format(consecutive_string)
    volume_name =                   "vol{}".format(consecutive_string)
    return (share_name, volume_name)


def get_iscsi_targets_names():
    targets= get('/pools/{POOL_NAME}/san/iscsi/targets'.format(POOL_NAME=pool_name))
    return [target['name'] for target in targets]


def get_nas_volumes_names():
    nas_volumes = get('/pools/{POOL_NAME}/nas-volumes'.format(POOL_NAME=pool_name))
    return [nas_volume['name'] for nas_volume in nas_volumes]


def get_san_volumes_names():
    san_volumes = get('/pools/{POOL_NAME}/volumes'.format(POOL_NAME=pool_name))
    return [san_volume['name'] for san_volume in san_volumes]

        
def get_nic_name_of_given_ip_address(ip_address):
    interfaces = get('/network/interfaces')
    return next((interface['name'] for interface in interfaces if interface['address'] == ip_address), None)

def get_mac_address_of_given_nic(nic):
    interfaces = get('/network/interfaces')
    return next((interface['mac_address'] for interface in interfaces if interface['name'] == nic), None)


def get_bond_slaves(bond_name):
    ''' return list of slaves NICs'''
    interfaces = get('/network/interfaces')
    return next((interface['slaves'] for interface in interfaces if interface['name'] == bond_name), None)


def get_interface_ip_addr(interface_name):
    ''' return IP of given bond'''
    interfaces = get('/network/interfaces')
    return next((interface['address'] for interface in interfaces if interface['name'] == interface_name), None)


def get_interface_gw_ip_addr(interface_name):
    ''' return IP of given bond'''
    interfaces = get('/network/interfaces')
    return next((interface['gateway'] for interface in interfaces if interface['name'] == interface_name), None)


def get_interface_netmask(interface_name):
    ''' return IP of given bond'''
    interfaces = get('/network/interfaces')
    return next((interface['netmask'] for interface in interfaces if interface['name'] == interface_name), None)


def get_ring_interface_of_first_node():
    if get('/cluster/rings'):
        return get('/cluster/rings')[0]['interfaces'][0]['interface']
    else:
        # get return empty list
        sys_exit_with_timestamp( 'Error: Cluster not bound yet.')
        

def get_cluster_nodes_addresses():
    global is_cluster
    is_cluster = False
    result = get('/cluster/nodes')
    cluster_nodes_addresses = [cluster_node['address']for cluster_node in result ]
    if ('127.0.0.1' not in cluster_nodes_addresses) and (len(cluster_nodes_addresses)>1):
        is_cluster = True
    else:
        cluster_nodes_addresses = node.split()  ## the node as single item list
    return cluster_nodes_addresses 


def get_cluster_node_id(node):
    if get('/cluster/nodes')[0]['address'] in '127.0.0.1':
        ## cluster not cofigured yet
        sys_exit_with_timestamp( 'Error: Cluster not bound yet.')
    else:
        result = get('/cluster/nodes')
        return (cluster_node['id']for cluster_node in result if cluster_node['address'] in node).next()


def get_vips():
    endpoint = '/pools/{pool_name}/vips'.format(pool_name=pool_name)
    ## GET
    result =  get(endpoint)
    return (result[0]['address'], result[0]['interface'], result[0]['remote_interface'][0]['interface'])

def cluster_bind_set():
    """
    True if set
    False if not set
    """
    endpoint = '/cluster/nodes'
    bind_node_address = '127.0.0.1'
    ## GET
    bind_node_address = get('/cluster/nodes')[0]['address']
    return False if bind_node_address in '127.0.0.1' else True


def create_vip():
    global action_message
    action_message = 'Sending Create VIP request to: {}'.format(node)

    if not pool_name:
        sys_exit_with_timestamp( 'Error: Pool name missing.')

    #nics = convert_comma_separated_to_list(vip_nics)
    nics = list(vip_nics)
    if len(nics)==1:
        nics.append(nics[0])
    if len(nics)==2:
        nic_a, nic_b = nics
    else:
        sys_exit_with_timestamp( 'Error: --vip_nics expects one or two nics t')
    cluster_ip_addresses = get_cluster_nodes_addresses()
    cluster = False if len(cluster_ip_addresses) == 1 else True
    node_b_address = cluster_ip_addresses
    node_b_address.remove(node)
    endpoint = '/pools/{pool_name}/vips'.format(pool_name=pool_name)
    if cluster:
        ## cluster
        data = dict(name=vip_name,
                    address = vip_ip,
                    netmask = vip_mask,
                    interface = nic_a,
                    remote_interface = [ dict( node_id = get_cluster_node_id(node_b_address),
                                               interface = nic_b)])
    else:
        ## single node
        data = dict(name=vip_name,
                    address = vip_ip,
                    netmask = vip_mask,
                    interface = nic_a)
    ## POST
    post(endpoint,data)
    if error:
        sys_exit_with_timestamp( 'Error setting VIP: {} with: {} on: {}. {}'.format(vip_ip, ','.join(nics), pool_name, error ))
    else:
        print_with_timestamp( 'New VIP: {} set, with: {} on: {}.'.format(vip_ip, ','.join(nics), pool_name ))

    
def set_mirror_path():
    global action_message
    action_message = 'Sending Mirror Path Set request to: {}'.format(node)

    interfaces_items = []
    cluster_nodes_addresses = get_cluster_nodes_addresses()
    ## first cluster node must be same as node from args
    if cluster_nodes_addresses[0] != node:
        cluster_nodes_addresses[0], cluster_nodes_addresses[1] =  \
        cluster_nodes_addresses[1], cluster_nodes_addresses[0]
    for i, cluster_node_address in enumerate(cluster_nodes_addresses):
        node_id = get_cluster_node_id(cluster_node_address)
        interfaces_items.append(dict(interface=mirror_nics[i], node_id=node_id))
    data = dict(interfaces=interfaces_items)
    return_code = {}
    ## POST
    return_code = post('/cluster/remote-disks/paths',data)
    is_all_OK = False
    for _ in range(20):
        time.sleep(5)
        result = get('/cluster/remote-disks/paths')
        is_all_OK = all(['OK' in interface['status'] for interface in result[0]['interfaces']])
        if is_all_OK:
            print()
            print_with_timestamp( 'Mirror path set to: {}'.format(', '.join(mirror_nics)))
            break
        else:
            print('.', end='')
    if not is_all_OK:
        print()
        sys_exit_with_timestamp( 'Error setting mirror path with: {}. {}'.format(', '.join(mirror_nics),error))


def get_ping_nodes():
    ping_nodes=[]
    endpoint = '/cluster/ping-nodes'
    ## GET
    ping_nodes = [ping_node['address'] for ping_node in get(endpoint)]
    if error:
        print_with_timestamp('Error getting ping nodes. {}'.format(error))
    return None if error else ping_nodes


def set_ping_nodes():
    global action_message
    action_message = 'Sending Ping Node Set request to: {}'.format(node)

    current_ping_nodes = get_ping_nodes()
    if current_ping_nodes is None:
        sys_exit_with_timestamp( 'Cannot set ping nodes on {}'.format(node))
    endpoint = '/cluster/ping-nodes'
    #e = None
    if len(ping_nodes)<2:
        print_with_timestamp( 'Warning: One ping node provided. At least 2 ping nodes are recommended')
    for ping_node in ping_nodes:   
        if ping_node in current_ping_nodes:
            print_with_timestamp('Error: Ping node {} already set.'.format(ping_node))
            continue
        ring_ip_addres_of_first_node = get_interface_ip_addr(get_ring_interface_of_first_node())
        if ping_node not in ipcalc.Network(ring_ip_addres_of_first_node, new_mask):
            sys_exit_with_timestamp( 'Error: Given ping node IP address {} in not in ring subnet'.format(ping_node))
        data = dict(address=ping_node)

        ## POST
        post('/cluster/ping-nodes',data)

        if ping_node in get_ping_nodes():
            print_with_timestamp('New ping node {} set.'.format(ping_node))


def start_cluster():
    global action_message
    action_message = 'Sending Cluster Service Start request to: {}'.format(node)
    
    started = False
    
    cluster_nodes_addresses = get_cluster_nodes_addresses()
    if not cluster_bind_set():
        sys_exit_with_timestamp( 'Cannot start cluster on {}. Nodes are not bound yet.'.format(node))

    ## GET
    status = get('/cluster/nodes')

    started = status[0]['status'] == status[1]['status'] == 'online'
    if started:
        sys_exit_with_timestamp( 'Cluster on {} is already started.'.format(node))

    data=dict(mode='cluster')

    ## POST
    post('/cluster/start-cluster',data)
    if 'timeout' not in error:
        sys_exit_with_timestamp( 'Error: Cluster service start failed. {}'.format(error))

    print_with_timestamp('Cluster service starting...')
    
    ## check start
    is_started = False
    for _ in range(5):
        is_started = is_cluster_started()
        time.sleep(10)
        if is_cluster:
            print()
            print_with_timestamp('Cluster service started successfully.')
            break
        else:
            print('.', end='')
    if not is_cluster:
        print()
        sys_exit_with_timestamp( 'Error: Cluster service start failed. {}'.format(error if error else ''))


def move():

    global node
    global nodes
    global action_message
    action_message = 'Sending Failover(Move) request to: {}'.format(node)
    command_line_node = node
    if not all((is_cluster_configured,is_cluster_started)):
        sys_exit_with_timestamp( 'Error: Cluster not running on: {}.'.format(node))
    time.sleep(15)  ## in batch mode reboot can be in progress
    nodes = get_cluster_nodes_addresses() ## nodes are now just both cluster nodes
    if len(nodes)<2:
        sys_exit_with_timestamp( 'Error: Cannot move. {} is running as single node.'.format(node))
    active_node = ''
    passive_node = ''
    new_active_node = ''
    for i,node in enumerate(nodes):
        if node not in command_line_node:
            wait_for_move_destination_node(node)
            #wait_for_node()

        ## GET
        pools = get('/pools')

        pools.sort(key=lambda k : k['name'])
        pool_names = [pool['name'] for pool in pools ]
        if pool_name in pool_names:
            active_node = node
            passive_node = nodes[(i+1)%2]     # get node_id of other node (i+1)%2
            print_with_timestamp('{} is moving from: {} to: {} '.format(pool_name, active_node, passive_node))
            ## wait ...
            wait_for_move_destination_node(passive_node)
            wait_for_zero_unmanaged_pools() 
            data=dict(node_id= get_cluster_node_id(passive_node))
            endpoint='/cluster/resources/{}/move-resource'.format(pool_name)
            ## POST
            post(endpoint,data)
            if error:
                sys_exit_with_timestamp( 'Cannot move pool {}. Error: {}'.format(pool_name, error))
    print_with_timestamp('Moving in progress...')
    ## wait for pool import
    time.sleep(15)
    new_active_node = ''
    for _ in range(15):
        for node in nodes:
            ## GET
            pools = get('/pools')
            if not pools:
                continue
            pool_names = [pool['name'] for pool in pools ]
            if pool_name in pool_names:
                new_active_node = node
            if new_active_node:
                break
        if new_active_node:
            break
        print_with_timestamp('Moving in progress...')
        time.sleep(10)
    if new_active_node == passive_node: ## after move (failover) passive node is active
        time.sleep(15)
        print_with_timestamp('{} is moved from: {} to: {} '.format(pool_name, active_node, new_active_node))
    else:
        sys_exit_with_timestamp( 'Cannot move pool {}. Error: {}'.format(pool_name, error))


def network(nic_name, new_ip_addr, new_mask, new_gw, new_dns):
    
    global node    ## the node IP can be changed
    global action_message
    action_message = 'Sending Network Setting request to: {}'.format(node)
    timeouted = False
    
    # list_of_ip
    dns = convert_comma_separated_to_list(new_dns)
    # validate all IPs, exit if no valid IP found
    for ip in [new_ip_addr, new_mask, new_gw] + dns if dns else []:
        if ip:
            if not valid_ip(ip):
                sys_exit( 'IP address {} is invalid'.format(new_ip_addr))
    endpoint = '/network/interfaces/{INTERFACE}'.format(
                   INTERFACE=nic_name)
    data = dict(configuration="static", address=new_ip_addr, netmask=new_mask)
    if new_gw or new_gw == '':
        data["gateway"]=new_gw if new_gw else None

    ## if new_ip_addr is missing, set gateway & DNS and return
    if new_ip_addr is None:
        if new_gw:
            set_default_gateway()
        if dns is not None:
            set_dns(dns)
        return
        #sys_exit( 'Error: Expected, but not specified --new_ip for {}'.format(nic_name))

    ## PUT
    put(endpoint,data)

    if error:
        # in case the node-ip-address changed, the RESTapi request cannot complete as the connection is lost due to IP change
        # e: HTTPSConnectionPool(host='192.168.0.80', port=82): Read timed out. (read timeout=30)
        timeouted = ("HTTPSConnectionPool" in error) and ("timeout" in error)
        if timeouted:
            node = new_ip_addr  ## the node IP was changed
        time.sleep(1)

    if "HTTPSConnectionPool" in error and "timeout" in error:
        print_with_timestamp( 'The acccess NIC {} changed to {}'.format(nic_name, new_ip_addr))
    else:
        if get_interface_ip_addr(nic_name) == new_ip_addr:
            print_with_timestamp('New IP address {} set to {}'.format(new_ip_addr,nic_name))
        else:
            print_with_timestamp('ERROR: New IP address {} set to {} FAILED'.format(new_ip_addr,nic_name))

    ## set default gateway interface
    if new_gw:
        set_default_gateway()
    
    if dns is not None:
        set_dns(dns)
    

def create_bond(bond_type, bond_nics, new_gw, new_dns):
    global node    ## the node IP can be changed
    global nic_name
    global action_message
    action_message = 'Sending Create Bond request to: {}'.format(node)

    timeouted = False

    if len(bond_nics) <2:
        sys_exit_with_timestamp( 'Error: at least two nics required')
    ip_addr = new_ip_addr if new_ip_addr else node

    endpoint='/network/interfaces'

    if 'active-backup' in bond_type.lower():
        data = dict(type = 'bonding',
                configuration = 'static',
                address = ip_addr,
                netmask = new_mask,
                slaves = bond_nics,
                bond_mode = bond_type.lower(),
                primary_interface = bond_nics[0],
                bond_primary_reselect = 'failure')

    if 'balance-rr' in bond_type.lower():
        data = dict(type = 'bonding',
                configuration = 'static',
                address = ip_addr,
                netmask = new_mask,
                slaves = bond_nics,
                bond_mode = bond_type.lower(),
                bond_primary_reselect = 'always')

    if new_gw or new_gw == '':
        data["gateway"]=new_gw if new_gw else None
    ## POST
    post(endpoint,data)
    if error:
        # in case the node-ip-address changed, the RESTapi request cannot complete as the connection is lost due to IP change
        # e: HTTPSConnectionPool(host='192.168.0.80', port=82): Read timed out. (read timeout=30)
        timeouted = ("HTTPSConnectionPool" in error) and ("timeout" in error)
        if timeouted:
            node = ip_addr  ## the node IP was changed (ip_addr set above & not new_ip_addr)
        time.sleep(1)
    ##
    nic_name = get_nic_name_of_given_ip_address(ip_addr)  # global nic_name
    if nic_name and ('bond' in nic_name):
        print_with_timestamp( '{} created with IP: {}'.format(nic_name, new_ip_addr))
    else:
        sys_exit_with_timestamp( 'Error: cannot create bond with {} on {}'.format(','.join(bond_nics), node))
    ## set default gateway interface
    if new_gw:
        set_default_gateway()

    ## set dns
    dns = convert_comma_separated_to_list(new_dns)
    if dns is not None:
        set_dns(dns)


def delete_bond(bond_name):
    
    global node    ## the node IP can be changed
    global action_message
    action_message = 'Sending Delete Bond request to: {}'.format(node)
    #global nic_name
    node_id_220 = 0
    orginal_node_id = 1   ## just different init value than node_id_220
    
    timeouted = False
    
    bond_slaves = get_bond_slaves(bond_name) ## list
    if bond_slaves is  None or len(bond_slaves)<2:
        sys_exit_with_timestamp( 'Error : {} not found'.format(bond_name))

    first_nic_name, second_nic_name = sorted(bond_slaves)
    bond_ip_addr = get_interface_ip_addr(bond_name)
    bond_gw_ip_addr = get_interface_gw_ip_addr(bond_name)
    bond_netmask = get_interface_netmask(bond_name)
    orginal_node_id = node_id()

    endpoint = '/network/interfaces/{}'.format(bond_name)
    try:
        delete(endpoint,None)
    except Exception as e:
        error = str(e)
        # in case the node-ip-address changed, the RESTapi request cannot complete as the connection is lost due to IP change
        # e: HTTPSConnectionPool(host='192.168.0.80', port=82): Read timed out. (read timeout=30)
        timeouted = ("HTTPSConnectionPool" in error) and ("timeout" in error)
        if timeouted:
            node = new_ip_addr  # the node IP was changed
        else:
            sys_exit_with_timestamp( 'Error: {}'.format(e[0]))
        time.sleep(1)

    ## default IP set after bond delete
    node = '192.168.0.220'
    try:
        node_id_220 = node_id()
    except  Exception as e:
        error = str(e)
        # in case the node-ip-address changed, the RESTapi request cannot complete as the connection is lost due to IP change
        # e: HTTPSConnectionPool(host='192.168.0.80', port=82): Read timed out. (read timeout=30)
        timeouted = ("HTTPSConnectionPool" in error) and ("timeout" in error)
        if timeouted:
            sys_exit_with_timestamp( 'Error: Cannot access default IP 192.168.0.220')
            
    time.sleep(1)
    if node_id_220 == orginal_node_id:
        endpoint = '/network/interfaces/{INTERFACE}'.format(
                       INTERFACE=first_nic_name)
        data = dict(configuration="static", address=bond_ip_addr, netmask=bond_netmask)
        if bond_gw_ip_addr or bond_gw_ip_addr == '':
            data["gateway"]= bond_gw_ip_addr if bond_gw_ip_addr else None

        ## PUT
        put(endpoint,data)

        if error:
            # in case the node-ip-address changed, the RESTapi request cannot complete as the connection is lost due to IP change
            # e: HTTPSConnectionPool(host='192.168.0.80', port=82): Read timed out. (read timeout=30)
            timeouted = ("HTTPSConnectionPool" in error) and ("timeout" in error)
            if timeouted:
                node = bond_ip_addr  # the node IP was changed
            time.sleep(1)

        ## set node IP address back to bond_ip_addr
        node = bond_ip_addr
        endpoint = '/network/interfaces/{INTERFACE}'.format(
                       INTERFACE=second_nic_name)
        data = dict(configuration="static", address=increment_3rd_ip_subnet(bond_ip_addr), netmask=bond_netmask)

        ## PUT
        put(endpoint,data)

    ## set default gateway interface
    if bond_gw_ip_addr:
        nic_name = first_nic_name
        set_default_gateway()


def node_id():
    ## GET
    version = get('/product')["header"]
    serial_number = get('/product')["serial_number"]
    server_name = get('/product')["server_name"]
    host_name = get('/product')["host_name"]
    interfaces = get('/network/interfaces')
    eth0_mac_address = get_mac_address_of_given_nic('eth0')
    return version + serial_number + server_name + host_name + eth0_mac_address


def bind_cluster(bind_ip_addr):
    global action_message
    action_message = 'Sending Cluster Nodes Bind request to: {}'.format(node)

    endpoint = '/cluster/nodes'
    data = dict(address=bind_ip_addr, password=bind_node_password)

    bind_node_address = '127.0.0.1'

    ## GET
    bind_node_address = get('/cluster/nodes')[0]['address']

    if bind_node_address != '127.0.0.1':
        sys_exit_with_timestamp('Error: cluster bind was already set')
    result = None

    ## POST
    result = post(endpoint, data)

    ## GET and check 
    bind_node_address = get('/cluster/nodes')[0]['address']
    if bind_node_address != '127.0.0.1':
        print_with_timestamp('Cluster bound: {}<=>{}'.format(node,bind_ip_addr))
    else:
        sys_exit_with_timestamp('Error: cluster bind {}<=>{} failed'.format(node,bind_ip_addr))
    

def info():
    ''' Time, Version, Serial number, Licence, Host name, DNS, GW, NICs, Pools
    '''
    global node
    global action_message

    for node in nodes:
        ## GET
        action_message = 'Reading setup details from: {}'.format(node)
        version = get('/product')["header"]
        serial_number = get('/product')["serial_number"]
        serial_number = '{} TRIAL'.format(serial_number) if serial_number.startswith('T') else serial_number
        storage_capacity = get('/product')['storage_capacity']     # -1  means Unlimited
        storage_capacity = int(storage_capacity/pow(1024,4)) if storage_capacity > -1 else 'Unlimited'
        server_name = get('/product')["server_name"]
        host_name = get('/product')["host_name"]
        current_system_time = get('/time')['timestamp']
        system_time = datetime.datetime.fromtimestamp(current_system_time).strftime('%Y-%m-%d %H:%M:%S')
        time_zone = get('/time')['timezone']
        ntp_status = get('/time')['daemon']
        ntp_status = 'Yes' if ntp_status else 'No'
        product_key = get('/licenses/product').keys()[0]
        dns = get('/network/dns')['servers']
        default_gateway = get('/network/default-gateway')['interface']

        key_name={"strg":"Storage extension key",
                  "ha_rd":"Advanced HA Metro Cluster",
                  "ha_aa":"Standard HA Cluster"}

        extensions = get('/licenses/extensions')
        print_out_licence_keys = []
        for lic_key in extensions.keys():
            licence_type = key_name[ extensions[lic_key]['type']]
            licence_storage =  extensions[lic_key]['value']
            licence_storage = '' if licence_storage in 'None' else ' {} TB'.format(licence_storage)
            licence_description = '{:>30}:'.format( licence_type + licence_storage) 
            print_out_licence_keys.append('{}\t{}'.format( licence_description , lic_key ))
        print_out_licence_keys.sort(reverse=True)
        
        print()
        print('{:>30}:\t{}'.format("NODE", node))
        print('{:>30}:\t{}'.format("System time",system_time))
        print('{:>30}:\t{}'.format("Time zone",time_zone))
        print('{:>30}:\t{}'.format("Time from NTP",ntp_status))
        print('{:>30}:\t{}'.format("Software version",version))
        print('{:>30}:\t{}'.format("Serial number",serial_number))
        print('{:>30}:\t{} TB'.format("Licensed storage capacity",storage_capacity))
        print('{:>30}:\t{}'.format("Product key", product_key))

        for key in print_out_licence_keys :
            print(key)

        print('{:>30}:\t{}'.format("Server name",server_name))
        print('{:>30}:\t{}'.format("Host name",host_name))
        print('{:>30}:\t{}'.format("DNS",', '.join([str(ip_addr) for ip_addr in dns])))
        print('{:>30}:\t{}'.format("Default gateway",default_gateway))

        ## PRINT NICs DETAILS
        header= ( 'name', 'model', 'Gbit/s', 'mac')
        fields= ( 'name', 'model', 'speed',  'mac_address')
        print_interfaces_details(header,fields)
        header= ('name', 'type', 'address', 'netmask', 'gateway', 'duplex', 'negotiated_Gbit/s' )
        fields= ('name', 'type', 'address', 'netmask', 'gateway', 'duplex', 'negotiated_speed')
        print_interfaces_details(header,fields)

        ## PRINT POOLs DETAILS
        header= ('name', 'size_TiB', 'available_TiB', 'health', 'io-error-stats' )
        fields= ('name', 'size',     'available',     'health', 'iostats' )
        print_pools_details(header,fields)
        

def get_pool_details(node, pool_name):
    api = interface()
    pools= api.storage.driver.list_pools()["data"]
    data_groups_vdevs = [
        vdev["name"] for pool in pools if pool["name"] in pool_name
                        for vdev in pool["vdevs"] if vdev["name"] not in ("logs","cache","spares")
        ]
    data_groups_disks = [
        disk["name"] for pool in pools if pool["name"] in pool_name
                        for vdev in pool["vdevs"] if vdev["name"] not in ("logs","cache","spares")
                            for disk in vdev["disks"]
        ]
    data_groups_type = data_groups_vdevs[0].split("-")[0]
    vdevs_num = len( data_groups_vdevs )
    disks_num = len( data_groups_disks )
    vdev_disks_num = disks_num / vdevs_num
    return vdevs_num, data_groups_type, vdev_disks_num
    
    
def check_given_pool_name(ignore_error=None):
    ''' If given pool_name exist:
            return True
        If given pool_name does not exist:
            exit with ERROR     '''
    global node
    for node in nodes:
        api = interface()
        try:
            api.storage.pools[pool_name]
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: {} does not exist on Node: {}'.format(pool_name,node))
            return False
    return True


def check_given_volume_name(ignore_error=None):
    ''' If given volume_name exist, return volume type:
            dataset (NAS-vol)
            volume (SAN-zvol)
        If given volume_name does not exist:
            sys.exit with ERROR     '''
    global node
    for node in nodes:
        api = interface()
        pool = api.storage.pools[pool_name]
        for vol in pool.datasets:
            if vol.name == volume_name:
                return 'dataset'
        for zvol in pool.volumes:
            if zvol.name == volume_name:
                return 'volume'
        if ignore_error is None:
            sys_exit_with_timestamp( 'Error: {} does not exist on {} Node: {}'.format(volume_name,pool_name,node))
        else:
            return None


def jbods_listing(jbods):
    available_disks = count_available_disks(jbods)
    jbod = []
    if available_disks :
        for j,jbod in enumerate(jbods):
            print("\tjbod-{}\n\t{}".format(j,line_separator))
            if jbod :
                for d,disk in enumerate(jbod):
                    print("\t{:2d} {}\t{} GB\t{}\t{}".format(
                        d,disk[1],disk[0]/1024/1024/1024,disk[3], disk[2]))
        msg = "\n\tTotal: {} available disks found".format(available_disks)
    else:
        msg = "JBOD is empty. Please choose the JBOD number in order to read disks."
    return msg


def read_jbod(n):
    """
    read unused disks serial numbers in given JBOD n= 0,1,2,...
    """
    jbod = []
    global metro
    metro = False
    
    api = interface()
    unused_disks = api.storage.disks.unused
    for disk in unused_disks:
        if disk.origin in "iscsi":
            disk.origin = "remote"
            metro = True
        jbod.append((disk.size,disk.name,disk.id,disk.origin))
    return jbod 


def create_pool(pool_name,vdev_type,jbods):
    timeouted = False
    
    if pool_name in get_pools_names():
        sys_exit_with_timestamp( 'Error: {} already exist on node {}.'.format(pool_name, node))
        
    api = interface()
    vdev_type = vdev_type.replace('single','')
    print_with_timestamp("Creating pool. Please wait...")

    ## CREATE
    error = ''
    try:
        pool = api.storage.pools.create(
            name = pool_name,
            vdevs = (PoolModel.VdevModel(type=vdev_type, disks=vdev_disks) for vdev_disks in zip(*jbods)) ) ## zip disks over JBODs
    except Exception as e:
        error = str(e[0])
        if 'timeout' not in error:
            sys_exit_with_timestamp( 'Error: Cannot create {}. {}'.format(pool_name, ' '.join(error.split())))

    for _ in range(10):
        if check_given_pool_name(ignore_error=True):
            print_with_timestamp("New storage pool: {} created".format(pool_name))
            break
        else:
            time.sleep(5)
    else:
        sys_exit_with_timestamp( 'Error: Cannot create {}.'.format(pool_name))
        

def create_volume(vol_type):
    
    if vol_type == 'volume':
        endpoint='/pools/{POOL_NAME}/volumes'.format(POOL_NAME=pool_name)
        data=dict(name=volume_name, sparse=sparse, size=size)
        result=post(endpoint,data)
    if vol_type == 'dataset':
        endpoint='/pools/{POOL_NAME}/nas-volumes'.format(POOL_NAME=pool_name)
        data=dict(name=volume_name)
        result=post(endpoint,data)


def enable_smb_nfs():
    for service in storage_type:
        endpoint = '/services/{SERVICE}'.format(SERVICE=service.lower())
        enabled = get(endpoint)['enabled']
        if not enabled:
            put(endpoint,dict(enabled=True))

    
def create_storage_resource():
    global node
    global volume_name
    global target_name
    global auto_target_name ##used by function create_target()
    global share_name
    global quantity
    global action_message
    action_message = 'Sending Create Storage Resource to: {}'.format(node)
    initialize_pool_based_consecutive_number_generator()
    ## pool_based_consecutive_number_generator
    node = get_active_cluster_node_address_of_given_pool(pool_name)
    generate_automatic_name = (
        True if target_name == 'auto' else False) or (
        True if share_name  == 'auto' else False)
    
    while quantity:
        if generate_automatic_name:
            if 'ISCSI' in storage_type:
                target_name,volume_name = generate_iscsi_target_and_volume_name(pool_name)
            if 'SMB' in storage_type:
                share_name,volume_name = generate_share_and_volume_name(pool_name)
        else:
            quantity = 1
        ## volume or dataset
        create_volume(storage_volume_type) 
        if 'ISCSI' in storage_type:
            auto_target_name = target_name
            ## target
            create_target()
            ## attach
            attach_volume_to_target()
        if 'SMB' in storage_type or 'NFS' in storage_type:
            create_share()
            enable_smb_nfs()
        quantity -= 1


def create_snapshot(vol_type,ignore_error=None):
    global node
    for node in nodes:
        api = interface()
        ## Create snapshot of NAS vol
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots'.format(
                   POOL_NAME=pool_name, DATASET_NAME=volume_name)
            ## Auto-Snapshot-Name
            data = dict(name=auto_snap_name)            
        ## Create snapshot of SAN zvol
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name)
            ## Auto-Snapshot-Name
            data = dict(snapshot_name=auto_snap_name)   

        ## POST
        post(endpoint, data)
        print_with_timestamp('Snapshot of {}/{} has been successfully created.'.format(pool_name,volume_name))
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Target: {} creation on Node: {} failed'.format(auto_target_name,node))    


def create_clone(vol_type, ignore_error=None):
    global node
    for node in nodes:
        global clone_name
        ## dataset(vol) clone and volume(zvol) clone names can be the same as belong to different resources
        api = interface()
        ## Create clone of NAS vol = dataset
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAPSHOT_NAME}/clones'.format(
                POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            ## vol
            clone_name = volume_name + time_stamp_clone_syntax() + auto_vol_clone_name
            data = dict(name=clone_name)
        ## Create clone of SAN zvol = volume
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/clone'.format(
                POOL_NAME=pool_name, VOLUME_NAME=volume_name)
            ## zvol
            clone_name = volume_name + time_stamp_clone_syntax() + auto_zvol_clone_name
            data = dict(name=clone_name, snapshot=auto_snap_name)

        ## POST
        post(endpoint, data)
        print_with_timestamp('Clone of {}/{}/{} has been successfully created.'.format(pool_name,volume_name,auto_snap_name))
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Clone: {} creation on Node: {} failed'.format(clone_name,node))


def delete_snapshot_and_clone(vol_type, ignore_error=None):
    global node
    for node in nodes:
        api = interface()
        ## Delete snapshot. It auto-delete clone and share of NAS vol
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAPSHOT_NAME}'.format(
                       POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            try:
                api.driver.delete(endpoint)
                print_with_timestamp('Share, clone and snapshot of {}/{} have been successfully deleted.'.format(pool_name,volume_name))
                print()
            except:
                print_with_timestamp( 'Snapshot delete error: {} does not exist on Node: {}'.format(auto_snap_name,node))
                print()
        ## Delete snapshot and clone of SAN zvol (using recursively options)
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots/{SNAPSHOT_NAME}'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            data = dict(recursively_children=True, recursively_dependents=True, force_umount=True)
            try:
                api.driver.delete(endpoint,data)
                print_with_timestamp('Clone and snapshot of {}/{} have been successfully deleted.'.format(pool_name,volume_name))
                print()
            except:
                print_with_timestamp( 'Snapshot delete error: {} does not exist on Node: {}'.format(auto_snap_name,node))
                print()


def create_clone_of_existing_snapshot(vol_type, ignore_error=None):
    global node
    for node in nodes:
        global clone_name
        ## dataset(vol) clone and volume(zvol) clone names can be the same as belong to different resources
        api = interface()
        ## Create clone of NAS vol = dataset
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAPSHOT_NAME}/clones'.format(
                POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAPSHOT_NAME=snapshot_name)
            ## vol
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            data = dict(name=clone_name, snapshot=snapshot_name)
        ## Create clone of SAN zvol = volume
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/clone'.format(
                POOL_NAME=pool_name, VOLUME_NAME=volume_name, SNAPSHOT_NAME=snapshot_name)
            ## zvol
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            data = dict(name=clone_name, snapshot=snapshot_name)

        ## POST
        post(endpoint,data)
        print_with_timestamp('Clone of {}/{}/{} has been successfully created.'.format(pool_name,volume_name,snapshot_name))
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Clone: {} creation on Node: {} failed'.format(clone_name,node))


def delete_clone_existing_snapshot(vol_type, ignore_error=None):
    global node
    for node in nodes:
        api = interface()
        ## Delete existing clone and share of NAS vol
        if vol_type == 'dataset':
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAPSHOT_NAME}/clones/{VOL_CLONE_NAME}'.format(
                       POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAPSHOT_NAME=snapshot_name, VOL_CLONE_NAME=vol_clone_name)
            data = dict(name=clone_name)
            try:
                api.driver.delete(endpoint,data)
                print_with_timestamp('Share and clone of {}/{}/{} have been successfully deleted.'.format(pool_name,volume_name,snapshot_name))
                print()
            except:
                print_with_timestamp( 'Clone delete error: {} does not exist on Node: {}'.format(clone_name,node))
                print()
        ## Delete existing clone of SAN zvol
        if vol_type == 'volume':
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots/{SNAPSHOT_NAME}/clones/{CLONE_NAME}'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name, SNAPSHOT_NAME=snapshot_name, CLONE_NAME=clone_name)
            data = dict(name=clone_name)
            try:
                api.driver.delete(endpoint,data)
                print_with_timestamp('Clone of {}/{}/{} has been successfully deleted.'.format(pool_name,volume_name,snapshot_name))
                print()
            except:
                print_with_timestamp( 'Clone delete error: {} does not exist on Node: {}'.format(clone_name,node))
                print()


def create_target(ignore_error=None):
    global node
    for node in nodes:
        endpoint = '/pools/{POOL_NAME}/san/iscsi/targets'.format(
                   POOL_NAME=pool_name)
        ## Auto-Target-Name
        data = dict(name=auto_target_name)       

        ## POST
        target_object = post(endpoint, data)
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Target: {} creation on Node: {} failed'.format(auto_target_name,node))
    

def attach_volume_to_target(ignore_error=None):
    global node
    for node in nodes:
        endpoint = '/pools/{POOL_NAME}/san/iscsi/targets/{TARGET_NAME}/luns'.format(
                   POOL_NAME=pool_name, TARGET_NAME=auto_target_name)
        data = dict(name=volume_name)       
        ## POST
        post(endpoint,data)
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Cannot attach target: {} to {} on Node:{}'.format(
                    auto_target_name,volume_name,node))
        
        print_with_timestamp('Volume: {} has been successfully attached to target.'.format(
            volume_name))
        print("\n\tTarget:\t{}".format(auto_target_name))
        print("\tVolume:\t{}\n".format(volume_name))


def attach_clone_to_target(ignore_error=None):
    global node
    for node in nodes:
        endpoint = '/pools/{POOL_NAME}/san/iscsi/targets/{TARGET_NAME}/luns'.format(
                   POOL_NAME=pool_name, TARGET_NAME=auto_target_name)
        data = dict(name=clone_name)       
        ## POST
        post(endpoint,data)
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Cannot attach target: {} to {} on Node:{}'.format(
                    auto_target_name,clone_name,node))
        
        print_with_timestamp('Clone: {} has been successfully attached to target.'.format(
            clone_name))
        print("\n\tTarget:\t{}".format(auto_target_name))
        print("\tClone:\t{}\n".format(clone_name))
            

def create_share_for_auto_clone(ignore_error=None):
    global node
    for node in nodes:
        endpoint = '/shares'
        data = dict(name=share_name,
                path='{POOL_NAME}/{CLONE_NAME}'.format(POOL_NAME=pool_name, CLONE_NAME=clone_name),
                smb=dict(enabled=True, visible=visible))   ### add visible=False
        ## POST
        post(endpoint,data)
        if error:
            sys_exit_with_timestamp( 'Error: Share: {} creation on Node: {} failed'.format(share_name,node))

        print_with_timestamp('Share for {}/{} has been successfully created.'.format(
                pool_name,clone_name))
        print("\n\tShare:\t\\\\{}\{}".format(node,share_name))
        print("\tClone:\t{}/{}\n".format(pool_name,clone_name))


def create_share(ignore_error=None):
    global node
    for node in nodes:
        endpoint = '/shares'
        data = dict(name=share_name,
                path='{POOL_NAME}/{DATASET_NAME}'.format(POOL_NAME=pool_name, DATASET_NAME=volume_name),
                smb=dict(enabled=True if 'SMB' in storage_type else False ),
                nfs=dict(enabled=True if 'NFS' in storage_type else False ))
        ## POST
        post(endpoint,data)
        if error:
            sys_exit_with_timestamp( 'Error: Share: {} creation on Node: {} failed'.format(share_name,node))

        print_with_timestamp('Share for {}/{} has been successfully created.'.format(
                pool_name,volume_name))
        print("\n\tShare:\t\\\\{}\{}".format(node,share_name))
        print("\tDataset:\t{}/{}\n".format(pool_name,volume_name))


def create_new_backup_clone(vol_type):
    create_snapshot(vol_type)
    create_clone(vol_type)
    if vol_type == 'dataset':
        create_share_for_auto_clone()
    if vol_type == 'volume':
        create_target(ignore_error=True)
        attach_clone_to_target()


def create_existing_backup_clone(vol_type):
    create_clone_of_existing_snapshot(vol_type)
    if vol_type == 'dataset':
        create_share_for_auto_clone()
    if vol_type == 'volume':
        create_target(ignore_error=True)
        attach_clone_to_target()


def count_available_disks(jbods):
    if jbods:
        return [ bool(d) for jbod in jbods  for d in jbod  ].count(True)
    else:
        sys_exit_with_timestamp( 'Error: No disks available.')


def merge_sublists(list_of_lists):
    """
    merge list of sub_lists into single list
    """
    return [ item for sub_list in list_of_lists for item in sub_list]  


def convert_jbods_to_id_only(jbods):
    return [ [(disk[2]) for disk in jbod] for jbod in jbods ]   ## (disk.size,disk.name,disk.id) 


def split_for_metro_cluster(jbods,vdev_disks=2):
    """
    in case of METRO Cluster assume single JBOD in JBODs and split into 2 JBOD,
    first with disk.origin="local" and second with disk.origin="remote"
    and split into 4 JBODs for 4-way mirror (2 local and 2 remote) if vdev_disks=4
    """
    ## disk[3] => disk.origin
    ## split into 2 JBODs for 2-way mirror (1 local and 1 remote)
    jbods_2way_mirrors = [ [ disk for disk in jbod if disk[3] == place ] for jbod in jbods if jbod for place in ("local","remote") ] 
    if vdev_disks == 2:
        return jbods_2way_mirrors
    else:
        ## split into 4 JBODs for 4-way mirror (2 local and 2 remote)
        jbods_4way_mirrors =[]
        for i in range(4):
            jbods_4way_mirrors.append(jbods_2way_mirrors[i%2][i/2::2])
        return jbods_4way_mirrors


def remove_disks(jbods):
    available_disks = count_available_disks(jbods)
    if available_disks:
        jbods_disks_size = [ [disk[0] for disk in jbod]  for jbod in jbods ]
        all_disks_size = merge_sublists( jbods_disks_size ) ## convert lists of JBODs to single disks list
        average_disk_size = float(sum(all_disks_size)) / len(all_disks_size)  ## 
        return [ [ disk for disk in jbod if disk[0]>= (average_disk_size - disk_size_tolerance)] for jbod in jbods ] ## >= do not remove if all drives are same size
    

def check_all_disks_size_equal(jbods):
    jbods_disks_size  = [ [disk[0] for disk in jbod]  for jbod in jbods ]
    all_disks_size = merge_sublists( jbods_disks_size ) ## convert lists of JBODs to single disks list
    if (max(all_disks_size) - min(all_disks_size)) < disk_size_tolerance:
        return True
    else:
        return False


def user_choice():

    while 1:
        try :
            choice = raw_input('\tEnter your choice: ').upper()
            if choice in '':
                return "L"  ## treat pressed enter as "L"
            if choice in '0123456789LCQ':
                return choice
            else:
                print('\tInvalid choice')
        except:
            sys_exit('Interrupted             ')


def read_jbods_and_create_pool(choice='0'):

    global  vdevs_num,vdev_type
    global action_message
    action_message = 'Sending Create Pool request to: {}'.format(node)

    jbods = [[] for i in range(jbods_num)]
    given_jbods_num = jbods_num
    empty_jbod = True
    msg = None

    def run_menu(msg):
        print("""
        {}
         CREATE POOL MENU
        {}
         {}\t: Read single Powered-ON JBOD disks (first JBOD = 0)
         L\t: List JBODs disks
         C\t: Create pool & quit
         Q\t: Quit
        {}""".format(line_separator, line_separator, ",".join(map(str,range(given_jbods_num))), line_separator))
        print("\tGiven JBODs number: {}".format(given_jbods_num))
        print("\tPool to be created:\t{}: {}*{}[{} disk]".format(pool_name,vdevs_num,vdev_type,vdev_disks_num))
        if msg: print("\n\t{}\n\t".format(msg))
        return user_choice() 

    while 1:

        if menu:
            choice = run_menu(msg)
        if choice in "01234567":
            jbod_number = int(choice)
            ## read disks        
            if jbod_number in range(jbods_num):
                ## read JBOD
                jbods[jbod_number] = read_jbod(jbod_number)
                jbods = remove_disks(jbods)   ##### REMOVE smaller disks 
                if metro:
                    ## metro mirror both nodes with 2-way (--vdev_disks_num=2)or 4-way mirror (--vdev_disks_num=4)
                    vdev_type = "mirror"
                    jbods = split_for_metro_cluster(jbods,vdev_disks_num)
                ## reset JBODs[i] if double serial number detected
                for i in range(jbods_num):
                    if i == jbod_number or not jbods[i]:
                        continue
                    for disk1 in jbods[i]:
                        for disk2 in jbods[jbod_number]:
                            if disk2 == disk1:
                                jbods[i] = []
                jbods_listing(jbods)
            ##
            available_disks = count_available_disks(jbods)
            msg = "\n\tTotal: {} available disks found\n\tTotal: {} disks required to create the pool".format(
                available_disks,vdev_disks_num*vdevs_num)
            
            empty_jbod = False
            for i in range(jbods_num):
                if not jbods[i]:       
                    empty_jbod = True
            ## non-interactive mode, run create after read
            if not menu:
                choice = "C"

        elif choice in "L":
            ## show
            msg = jbods_listing(jbods)

        elif choice in "C":
            if not menu:
                jbods = remove_disks(jbods)
                msg = jbods_listing(jbods)
            ## create pool
            if empty_jbod:
                msg = 'At least one JBOD is empty. Please press 0,1,... in order to read JBODs disks.'
            else:
                if check_all_disks_size_equal(jbods) == False:
                    msg = 'Disks with different size present. Please press "r" in order to remove smaller disks.'
                else:
                    jbods_id_only = convert_jbods_to_id_only(jbods)
                    required_disks_num = vdevs_num * vdev_disks_num 
                    available_disks = count_available_disks(jbods_id_only)
                    if available_disks < required_disks_num:
                        msg ='Error: {}: {}*{}[{} disk] requires {} disks. {} disks available.\n'.format(
                            pool_name,vdevs_num,vdev_type,vdev_disks_num,required_disks_num,available_disks)
                    else:
                        if jbods_num == 1 and not metro:
                            ## transpose single JBOD for JBODs [number_of_disks_in_vdev * number_of_vdevs]
                            jbods_id_only = zip(*[iter(jbods_id_only[0])] * vdevs_num )
                            jbods_id_only = jbods_id_only[: vdev_disks_num]
                            create_pool(pool_name,vdev_type, jbods_id_only)
                        else:
                            ## limit to given vdevs_num
                            jbods_id_only = [jbod[:vdevs_num] for jbod in jbods_id_only] 
                            create_pool(pool_name,vdev_type,jbods_id_only)
                        ##### reset
                        jbods = [[] for i in range(jbods_num)]
            ##
            break
        ## exit
        elif choice in "Q":
            break

    ## display pools details 
    api = interface()
    pools = [pool.name for pool in api.storage.pools]
    print("\n")
    for pool in sorted(pools):
        print("\tNode {} {}: {}*{}[{} disk]".format(node, pool, *get_pool_details(node, pool)))
        

def command_processor() :

    print()

    if action == 'clone':
        c = count_provided_args( pool_name, volume_name )   ## if both provided (not None), c must be equal 2
        if c < 2:
            sys_exit_with_timestamp( 'Error: Clone command expects 2 arguments(pool, volume), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )
        create_new_backup_clone( vol_type )

    elif action == 'clone_existing_snapshot':
        c = count_provided_args( pool_name, volume_name, snapshot_name )   ## if all provided (not None), c must be equal 3
        if c < 3:
            sys_exit_with_timestamp( 'Error: Clone_existing_snapshot command expects 3 arguments(pool, volume, snapshot), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_clone_existing_snapshot( vol_type, ignore_error=True )
        create_existing_backup_clone( vol_type )

    elif action == 'delete_clone':
        c = count_provided_args( pool_name, volume_name )   ## if both provided (not None), c must be equal 2
        if c < 2:
            sys_exit_with_timestamp( 'Error: delete_clone command expects 2 arguments(pool, volume), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )

    elif action == 'delete_clone_existing_snapshot':
        c = count_provided_args( pool_name, volume_name, snapshot_name )   ## if all provided (not None), c must be equal 3
        if c < 3:
            sys_exit_with_timestamp( 'Error: delete_clone_existing_snapshot command expects 3 arguments(pool, volume, snapshot), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_clone_existing_snapshot( vol_type, ignore_error=True )

    elif action == 'create_pool':
        read_jbods_and_create_pool()
 
    elif action == 'scrub':
        scrub()

    elif action == 'set_scrub_scheduler':
        set_scrub_scheduler()


    elif action == 'create_storage_resource':
        c = count_provided_args( pool_name, volume_name, storage_type, size, sparse )   ## if all provided (not None), c must be equal 3
        if c < 5:
            sys_exit_with_timestamp( 'Error: create_storage_resource command expects (pool, volume, storage_type), {} provided.'.format(c))
        if 'iqn' in target_name:
            if storage_volume_type != 'volume':
                sys_exit_with_timestamp( 'Error: inconsisten options.')
        create_storage_resource()

        
    elif action == 'set_host':
        c = count_provided_args(host_name, server_name, server_description)   ## if all provided (not None), c must be equal 3 set_host
        if c not in (1,2,3):
            sys_exit_with_timestamp( 'Error: set_host command expects at least 1 of arguments: --host, --server, --description')
        set_host_server_name(host_name, server_name, server_description)

    elif action == 'set_time':
        c = count_provided_args(timezone, ntp, ntp_servers)   
        if c not in (1,2,3):
            sys_exit_with_timestamp( 'Error: set_host command expects at least 1 of arguments: --timezone, --ntp, --ntp_servers')
        set_time(timezone, ntp, ntp_servers)

    elif action == 'network':
        c = count_provided_args(nic_name, new_ip_addr, new_mask, new_gw, new_dns)  
        if c not in (2,3,4,5):
            sys_exit_with_timestamp( 'Error: network command expects at least 2 of arguments: --nic, --new_ip, --new_mask, --new_gw --new_dns or just --new_dns')
        network(nic_name, new_ip_addr, new_mask, new_gw, new_dns)

    elif action == 'create_bond':
        c = count_provided_args(bond_type, bond_nics, new_gw, new_dns)   
        if c not in (2,3,4):
            sys_exit_with_timestamp( 'Error: Bond create command expects at least 2 of arguments: -bond_type, --bond_nics')
        create_bond(bond_type, bond_nics, new_gw, new_dns)

    elif action == 'delete_bond':
        c = count_provided_args(bond_type, bond_nics, new_gw, new_dns)   
        if c not in (0,1,2):
            sys_exit_with_timestamp( 'Error: Delete Bond command expects at least 2 of arguments: -bond_type, --bond_nics')
        delete_bond(nic_name)

    elif action == 'bind_cluster':
        if len(nodes) !=2:
            sys_exit_with_timestamp( 'Error: bind_cluster command expects exactly 2 IP addresses')
        bind_ip_addr = nodes[1]
        bind_cluster(bind_ip_addr)

    elif action == 'set_ping_nodes':
        if len(ping_nodes) < 1:
            sys_exit_with_timestamp( 'Error: set_ping_nodes command expects at least 1 IP addresses')
        set_ping_nodes()

    elif action == 'set_mirror_path':
        if len(nodes) !=1:
            sys_exit_with_timestamp( 'Error: set_mirror_path command expects exactly 1 IP address')
        c = count_provided_args(mirror_nics)
        if c not in (1,):
            sys_exit_with_timestamp( 'Error: set_mirror_path command expects --mirror_nics')
        set_mirror_path()

    elif action == 'create_vip':
        if len(nodes) !=1:
            sys_exit_with_timestamp( 'Error: create_vip command expects exactly 1 node IP address')
        c = count_provided_args(pool_name, vip_name, vip_nics, vip_ip, vip_mask)
        if c not in (4,5):
            sys_exit_with_timestamp( 'Error: create_vip command expects --pool --vip_name --vip_nics --vip_ip and --vip_mask')
        create_vip()

 
    elif action == 'start_cluster':
        start_cluster()

    elif action == 'move':
        c = count_provided_args(pool_name)
        if c != 1:
            sys_exit_with_timestamp( 'Error: move command expects pool name: --pool=pool-name')
        move()

    elif action == 'info':
        info()

    elif action == 'shutdown':
        shutdown_nodes()

    elif action == 'reboot':
        reboot_nodes()
    

def print_README_md_for_GitHub():
    print(parser.epilog.replace('\x1b[1m','<br><b>').replace('\x1b[22m','</b>').replace('\x1b[92m%(prog)s',' jdss-api-tools.exe').replace('\x1b[92m',' ').replace('\x1b[39m',''))
    with open('README.md','w') as f:
        f.write(parser.epilog.replace('\x1b[1m','<br><b>').replace('\x1b[22m','</b>').replace('\x1b[92m%(prog)s','    jdss-api-tools.exe').replace('\x1b[92m',' ').replace('\x1b[39m',''))
    

##  FACTORY DEFAULT BATCH SETUP FILES
factory_setup_files_content = dict(
    api_setup_single_node = """# The '#' comments-out the rest of the line
#------------------------------------------------------------------------------------------------------------------------
network     --nic eth0	  --new_ip _192.168.0.80_   --node 192.168.0.220        # SET ETH
#------------------------------------------------------------------------------------------------------------------------
network     --nic eth1	  --new_ip:nic      --node _192.168.0.80_       # SET ETH
#------------------------------------------------------------------------------------------------------------------------
network     --nic eth2	  --new_ip:nic      --node _192.168.0.80_       # SET ETH
#------------------------------------------------------------------------------------------------------------------------
network     --nic eth3	  --new_ip:nic      --node _192.168.0.80_       # SET ETH
#------------------------------------------------------------------------------------------------------------------------
network     --nic eth4	  --new_ip:nic      --node _192.168.0.80_       # SET ETH
#------------------------------------------------------------------------------------------------------------------------
network     --nic eth5	  --new_ip:nic      --node _192.168.0.80_       # SET ETH
#------------------------------------------------------------------------------------------------------------------------
# network   --nic eth6	  --new_ip:nic         --node _192.168.0.80_
# network   --nic eth7	  --new_ip:nic         --node _192.168.0.80_
# network   --nic eth8	  --new_ip:nic         --node _192.168.0.80_
# network   --nic eth9	  --new_ip:nic         --node _192.168.0.80_
# network   --nic eth10	  --new_ip:nic        --node _192.168.0.80_
# network   --nic eth11	  --new_ip:nic        --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# CREATE BOND : nodes bind and ring : with default --bond_type active-backup 
#------------------------------------------------------------------------------------------------------------------------
create_bond --bond_nics eth0 eth1   --new_ip:bond    --new_gw 192.168.0.1    --new_dns 192.168.0.1   --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# CREATE BOND : mirror path : active-backup or  balance-rr (round-robin) 
#------------------------------------------------------------------------------------------------------------------------
create_bond --bond_nics eth4 eth5   --new_ip:bond   --bond_type active-backup   --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
set_host  --host node-80-ha00 --server node-80-ha00 --node _192.168.0.80_           # SET HOST & SERVER
#------------------------------------------------------------------------------------------------------------------------
set_time  --timezone Europe/Berlin                  --node _192.168.0.80_           # SET TIME
#------------------------------------------------------------------------------------------------------------------------
info                                                --node _192.168.0.80_           # PRINT INFO
#------------------------------------------------------------------------------------------------------------------------
""",
    api_setup_cluster = """# The '#' comments-out the rest of the line
# BIND CLUSTER
#------------------------------------------------------------------------------------------------------------------------
bind_cluster        --nodes _192.168.0.80_ _192.168.0.81_
#------------------------------------------------------------------------------------------------------------------------
# PING NODES  
#------------------------------------------------------------------------------------------------------------------------
set_ping_nodes      --ping_nodes 192.168.0.30 192.168.0.40                                          --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# MIRROR PATH
#------------------------------------------------------------------------------------------------------------------------
set_mirror_path     --mirror_nics bond1 bond1                                                       --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# START CLUSTER
#------------------------------------------------------------------------------------------------------------------------
start_cluster                                                                                       --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# CREATE Pool-0
#------------------------------------------------------------------------------------------------------------------------
create_pool     --pool Pool-0   --vdevs 1   --vdev mirror --vdev_disks 4                            --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# VIP FOR Pool-0
#------------------------------------------------------------------------------------------------------------------------
create_vip      --pool Pool-0   --vip_name vip21    --vip_ip 192.168.21.100   --vip_nics eth2 eth2  --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# VIP FOR Pool-0
#------------------------------------------------------------------------------------------------------------------------
create_vip      --pool Pool-0   --vip_name vip31    --vip_ip 192.168.31.100   --vip_nics eth3 eth3  --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# CREATE Pool-1
#------------------------------------------------------------------------------------------------------------------------
create_pool     --pool Pool-1   --vdevs 1   --vdev mirror   --vdev_disks 4                          --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# VIP FOR Pool-1
#------------------------------------------------------------------------------------------------------------------------
create_vip      --pool Pool-1   --vip_name vip22    --vip_ip 192.168.22.100   --vip_nics eth2 eth2  --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# VIP FOR Pool-1
#------------------------------------------------------------------------------------------------------------------------
create_vip      --pool Pool-1   --vip_name vip32    --vip_ip 192.168.32.100   --vip_nics eth3 eth3  --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# CREATE ZVOLS
#------------------------------------------------------------------------------------------------------------------------
create_storage_resource     --pool Pool-0   --storage_type iscsi    --quantity 2                    --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# CREATE VOLs
#------------------------------------------------------------------------------------------------------------------------
create_storage_resource     --pool Pool-0   --storage_type smb nfs  --quantity 2 --start_with 100   --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# MOVE
#------------------------------------------------------------------------------------------------------------------------
move            --pool Pool-1   --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# SCRUB ALL
#------------------------------------------------------------------------------------------------------------------------
scrub                           --node _192.168.0.80_
#------------------------------------------------------------------------------------------------------------------------
# SET SCRUB SCHEDULER to all pools (also on other cluster node)
#------------------------------------------------------------------------------------------------------------------------
set_scrub_scheduler             --node 192.168.0.80
#------------------------------------------------------------------------------------------------------------------------
""",
    api_test_cluster = """### The '#' comments-out the rest of the line ###
move            --pool Pool-1   --node _192.168.0.80_	# move 
move            --pool Pool-0   --node _192.168.0.80_	# move 
move            --pool Pool-1   --node _192.168.0.80_	# move 
move            --pool Pool-0   --node _192.168.0.80_	# move 
move            --pool Pool-1   --node _192.168.0.80_	# move 
scrub                           --node _192.168.0.80_   # scrub all
reboot          --delay 5       --node _192.168.0.80_   # reboot
move            --pool Pool-0   --node _192.168.0.80_	# move 
move            --pool Pool-1   --node _192.168.0.80_	# move 
reboot          --delay 1       --node _192.168.0.80_   # reboot
scrub                           --node _192.168.0.80_   # scrub all
move            --pool Pool-0   --node _192.168.0.80_	# move 
""")


def main() :

    global nodes

    if 'batch_setup' in action:
        for setup_file in setup_files:
            with setup_file as f:
                for line in f.readlines():
                    line = line.split('#')[0].strip()
                    if line and line.split()[0] in commands.choices:
                        get_args(line)
                        command_processor()
    elif 'create_factory_setup_files' in action:
        trigger = True                      # to produce 2 files of "api_setup_single_node"
        if len(nodes)==1:
            nodes = nodes + nodes           # fake second node if missing in cli for simpler code
            factory_files_names = factory_setup_files_content.keys()
        else:
            factory_files_names = factory_setup_files_content.keys() + ['api_setup_single_node']
        for factory_file_name in factory_files_names:
            if 'api_setup_single_node' in factory_file_name:
                current_node = nodes[0] if trigger else nodes[1]
                content = factory_setup_files_content[factory_file_name].replace('_192.168.0.80_',current_node)
                ending = current_node.split('.')[-1]
                host_server_name = 'node-{}-ha00'.format(ending)
                content = content.replace('node-80-ha00',host_server_name)
                for i in range(content.count('--new_ip:nic')):
                    _current_node = current_node.replace('0.',str(i+1)+'.')
                    content = content.replace('--new_ip:nic','--new_ip '+_current_node,1)
                ## numbers of first nics in --bond_nics 
                first_nics_number_of_bonds = [item.split()[0].strip().strip('eth') for item in content.split('--bond_nics') if item.strip().startswith('eth')]
                for i in first_nics_number_of_bonds:
                    _current_node = current_node.replace('0.',str(i)+'.')
                    content = content.replace('--new_ip:bond','--new_ip '+_current_node,1)
                trigger = False
            else:
                current_node = nodes[0]
                content = factory_setup_files_content[factory_file_name].replace('_192.168.0.80_',current_node)
                if nodes[0] != nodes[1]:    # replace the second ip in bind_cluster
                    content = content.replace('_192.168.0.81_',nodes[1])
                if ping_nodes:
                    content = content.replace('192.168.0.30 192.168.0.40',' '.join(ping_nodes))
                if mirror_nics:
                    content = content.replace('eth4 eth4',' '.join(mirror_nics))
            ending = current_node.split('.')[-1]
            file_name =  '{}_{}.txt'.format(factory_file_name, ending)
            with open(file_name,'w') as f:
                f.write(content)
                print_with_timestamp( '{}\twriten into current directory.'.format(file_name))
    else:
        command_processor()


if __name__ == '__main__':
    
    init()          ## colorama
    get_args()      ## args
    try:
        main()
    except KeyboardInterrupt:
        sys_exit('Interrupted             ')
    print()
    print_README_md_for_GitHub()

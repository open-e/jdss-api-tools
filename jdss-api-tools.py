"""
After any modifications of source of jdss-api-tools.py,
run pyinstaller to create new jdss-api-tools.exe:

pyinstaller.exe --onefile jdss-api-tools.py

And try it:
C:\Python\Scripts\dist>jdss-api-tools.exe -h

NOTE:
To fix anti-virus false positive problem of the exe file generated using PyInstaller,
it needs to re-compile the pyinstaller bootloader. Follow step-by-step below:

1) git clone https://github.com/pyinstaller/pyinstaller             # download the source
2) cd pyinstaller
3) cd bootloader
4) python ./waf distclean all                                       # to build the bootloader for your system
5) cd ..                            
6) python setup.py install                                          # to install the fresh re-compiled pyinstaller
7) pyinstaller.exe --onefile jdss-api-tools.py                      # to create the executable

Missing Python modules need to be installed with pip, e.g.:

C:\Python\Scripts>pip install ipcalc
C:\Python\Scripts>pip install ping3
C:\Python\Scripts>pip install colorama
C:\Python\Scripts>pip install requests

NOTE:
Some modules may require MS Visual Studio:
https://visualstudio.microsoft.com/downloads

In case of error: "msvcr100.dll missing...",
download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe


2018-02-07  initial release
2018-03-06  add create_pool
2018-03-18  add delete_clone (it deletes the snapshot as well) (kris@dddistribution.be)
2018-04-23  add set_host  --host --server --description
2018-04-23  add network
2018-04-23  add info
2018-05-05  add network info
2018-05-06  add pools info
2018-05-28  add set_time
2018-06-06  fix spelling
2018-06-07  add clone_existing_snapshot (kris@dddistribution.be)
2018-06-09  add delete_clone_existing_snapshot (kris@dddistribution.be)
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
2018-09-08  add volumes details in info
2018-10-10  info lists snapshot
2018-10-12  info show snapshot age
2018-10-19  add modify_volume
2018-11-02  add quota & reservation
2018-11-22  online help improve
2018-11-25  add disk_size_range
2018-11-27  new_dns & ntp_servers are list now
2018-11-30  add --zvols_per_target option
2018-12-02  add increment option
2018-12-31  add number_of_disks_in_jbod for raidz2 & raidz3
2019-01-13  add new_gw, new_dns for batch setup
2019-03-15  add online activation
2019-03-22  add pool import
2019-05-18  improve info output (show if listed volume is nas or san volume)
2019-05-18  add list_snapshots (kris@dddistribution.be)
2019-05-22  fix problem auto target name while host name using upper case
2019-05-22  set iSCSI mode=BIO (as in up27 defaults to FIO) while iSCSI target attach
2019-05-22  do not exit after error on target or volume creation
2019-06-01  add detach_volume_from_iscsi_target
2019-06-13  add sync option to create_storage_resource
2019-06-18  add blocksize and recordsize for create_storage_resource
2019-07-02  add detach_disk_from_pool
2019-07-07  add delay to Move function
2019-07-29  add attach_volume_to_iscsi_target (kris@dddistribution.be)
2019-08-22  add delete clones
2019-09-09  add delete snapshots
2020-01-10  validation removed: as from up28 it is NOT required to keep ping in the same subnet as ring
2020-01-17  add primarycache and secondarycache option for create_clone
2020-01-23  add primarycache and secondarycache option for create_storage_resource
2020-03-05  fixed get_all_volume_snapshots_older_than_given_age for datasets
2020-03-05  add ".iscsi" segment into iscsi target template & add Europe/Amsterdam timezone
2020-03-16  add forced reboot be used as hard-reset equivalent (requires up29 or newer)
2020-03-27  add cluster second ring
2020-04-09  add volume size modify
2020-05-20  add ".iscsi" segment into auto generated iscsi target
2021-04-07  add export pool command
2021-05-31  move to python ver.3.9.5
2021-06-09  replace imported module jovianapi with local function call_requests
2021-09-06  fixed KeyError while delete snapshots
2022-01-13  fixed create & delete clone, help text for scrub_action
2022-02-03  improve pylint score
2022-02-06  improve pylint score
2022-02-09  fix forced reboot & shutdown
2022-02-18  fix move function
2022-05-03  add stop cluster
2022-07-22  add remove_disk_from_pool
2022-07-22  add add_read_cache_disk
2022-07-28  add list_snapshots options: all_dataset_snapshots, all_zvol_snapshots
2022-08-22  add download settings, change volblocksize default to 16k
"""

import os, sys, re, time, string, datetime, argparse, ping3, requests, urllib3
from colorama import init, Fore, Style

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


__author__  = 'janusz.bak@open-e.com'
__version__ = 1.2

## Script global variables
api_version             = '/api/v3'
api_timeout             = 300
action                  = ''
action_message          = ''
delay                   = 0
nodes                   = []
auto_target_name        = "iqn.auto.api.backup.target"        
auto_scsiid             = time.strftime("%Yi%mi%di%Hi%M")  #"1234567890123456"
auto_snap_name          = "auto_api_backup_snap"
auto_vol_clone_name     = "_auto_api_vol_clone"
auto_zvol_clone_name    = "_auto_api_zvol_clone"
increment_options       = [1,5,10,15,20,50,100,150,200,500,1000]
time_periods            = 'year month week day hour minute second'.split()
line_separator          = '='*62
BOLD     = Style.BRIGHT         ## '\x1b[1m'
END      = Style.NORMAL         ## '\x1b[22m'
LG       = Fore.LIGHTGREEN_EX   ## '\x1b[92m'
ENDF     = Fore.RESET           ## '\x1b[39m'

KiB,MiB,GiB,TiB = (pow(1024,i) for i in (1,2,3,4))

## TARGET NAME sys, re, time, string, datetime, argparse, ping3, requests, json, urllib3
target_name_prefix= "iqn.%s-%s.iscsi:jdss.target" % (time.strftime("%Y"),time.strftime("%m"))

## ZVOL NAME
zvol_name_prefix = 'zvol00'


def get(endpoint):
    return call_requests('GET',endpoint)
def put(endpoint,data={}):
    return call_requests('PUT',endpoint,data)
def post(endpoint,data={}):
    return call_requests('POST',endpoint,data)
def delete(endpoint,data={}):
    return call_requests('DELETE',endpoint,data)
def api_connection_test_passed():
    return call_requests('GET','/conn_test') # 'OK': if passed, '': if not passed
    
def call_requests(method,endpoint,data = None):
    global error, timeouted
    response = error = err = error_message = None
    http_code = 0; timeouted = False
    if endpoint not in '/conn_test': wait_for_node()
    try:
        r = dict(GET    = requests.get,
                 PUT    = requests.put,
                 POST   = requests.post,
                 DELETE = requests.delete)[method](url=f"https://{node}:{api_port}/{api_version.lstrip('/')}/{endpoint.lstrip('/')}",
                                                   json=data, auth=(api_user, api_password), timeout=api_timeout, verify=False)

        if endpoint.strip('/').startswith('settings') and endpoint.endswith('.cnf'): # binary output for download settings
            response = r.content
        else:
            response = r.json()['data']        # json output
        error_message = str(r.json()['error']['message'])
        http_code = r.status_code
    except Exception as err: #Exception example :"HTTPSConnectionPool(host='192.168.0.82', port=82): Max retries exceeded with url: /api/v3/conn_test (Caused by ConnectTimeoutError(<urllib3.connection.HTTPSConnection object at 0x000002D67E009280>, 'Connection to 192.168.0.82 timed out. (connect timeout=15)'))"
        if endpoint in ('/power/reboot','/power/shutdown') and force:
            return '' ## after the force down the node is GONE
        timeouted = 'ConnectTimeoutError' in str(err)
    #200, 201 or 204 = success, but JSONDecodeError passible        
    error = '' if http_code in (200,201,204) else error_message if error_message else http_code
    return '' if response is None else response


def wait_for_node():
    waiting_dots_printed = False
    ## PING
    counter = 0; repeat = 1000
    while type(ping3.ping(node)) is not float:
        if counter < 2:
            print_with_timestamp(f"Node {node} does not respond to ping command")
        elif counter > 1:
            print('.',end='')
            waiting_dots_printed = True
        counter += 1
        if counter == repeat:   ## Connection timed out
            sys_exit_with_timestamp(f"Connection timed out: {node}")

    if waiting_dots_printed: print()
    waiting_dots_printed = False

    ## REST API
    counter = 0; repeat = 1000
    while True:
        if not api_connection_test_passed():
            if counter in (2,3):
                print_with_timestamp(f"Node {node} does not respond to REST API commands")
            elif counter == 4:
                print_with_timestamp(f"Please enable REST API on {node} in GUI: System Settings \
                                     -> Administration -> REST access, or check access credentials")
            elif counter > 4:
                print('.',end='')
                waiting_dots_printed = True
        else:
            if to_print_timestamp_msg.get(node):
                if waiting_dots_printed: print()
                if action_message:
                    print_with_timestamp(action_message)
                else:
                    print_with_timestamp(f"Node {node} is running")
                to_print_timestamp_msg[node] = False
            break
        counter += 1
        time.sleep(3)
        if counter == repeat:   ## Connection timed out
            sys_exit_with_timestamp(f"Connection timed out: {node}")


def get_args(batch_args_line=None):
    r'''
{LG}jdss-api-tools{ENDF}


{BOLD}Execute single or batch commands for automated setup or to control JovianDSS remotely.{END}


{BOLD}Commands:{END}

{LG}{COMMANDS}{ENDF}

{BOLD}Commands description:{END}

{} {BOLD}Create clone{END} of iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.

    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the target exports most recent data every run.
    The example is using default password and port.
    Tools automatically recognize the volume type. If given volume is iSCSI volume,
    the clone of the iSCSI volume will be attached to iSCSI target.
    If given volume is NAS dataset, the created clone will be exported via network share.
    The example is using default password and port.

    {LG}%(prog)s clone --pool Pool-0 --volume zvol00 --node 192.168.0.220{ENDF}

    By default primarycache and secondarycache is set to all. It can be disabled or set to cache metadata only:

    {LG}%(prog)s clone --pool Pool-0 --volume zvol00 --primarycache none --secondarycache none --node 192.168.0.220{ENDF}
    {LG}%(prog)s clone --pool Pool-0 --volume zvol00 --primarycache metadata --secondarycache none --node 192.168.0.220{ENDF}

    {BOLD}Create clone{END} of NAS volume vol00 from Pool-0 and share via new created SMB share.

    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the share exports most recent data every run. The share is invisible by default.
    The example is using default password and port and makes the share {BOLD}visible{END} with default share name
    and primarycache set to metadata only.

    {LG}%(prog)s clone --pool Pool-0 --volume vol00 --visible --primarycache metadata --node 192.168.0.220{ENDF}

    The following examples are using default password and port and make the shares {BOLD}invisible{END}.

    {LG}%(prog)s clone --pool Pool-0 --volume vol00 --share_name vol00_backup --node 192.168.0.220{ENDF}
    {LG}%(prog)s clone --pool Pool-0 --volume vol01 --share_name vol01_backup --node 192.168.0.220{ENDF}


    {BOLD}Create clone{END} of existing snapshot on iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.

    The example is using password 12345 and default port.

    {LG}%(prog)s clone_existing_snapshot --pool Pool-0 --volume zvol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}


    {BOLD}Create clone{END} of existing snapshot on NAS volume vol00 from Pool-0 and share via new created SMB share.

    The example is using password 12345 and default port.

    {LG}%(prog)s clone_existing_snapshot --pool Pool-0 --volume vol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}



{} {BOLD}Delete clone{END} of iSCSI volume zvol00 from Pool-0.

    {LG}%(prog)s delete_clone --pool Pool-0 --volume zvol00 --node 192.168.0.220{ENDF}


    {BOLD}Delete clone{END} of NAS volume vol00 from Pool-0.

    {LG}%(prog)s delete_clone --pool Pool-0 --volume vol00 --node 192.168.0.220{ENDF}


    {BOLD}Delete clone{END} of existing snapshot on iSCSI volume zvol00 from Pool-0.

    The example is using password 12345 and default port.

    {LG}%(prog)s delete_clone_existing_snapshot --pool Pool-0 --volume zvol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}


    {BOLD}Delete clone{END} of existing snapshot on NAS volume vol00 from Pool-0.

    The example is using password 12345 and default port.

    {LG}%(prog)s delete_clone_existing_snapshot --pool Pool-0 --volume vol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345{ENDF}


{} {BOLD}Delete clones{END} (time-based).

    Delete clones of provided volume and pool with creation date older than provided time period.

    This example deletes clones of iSCSI zvol00 from Pool-0 with 5 seconds prompted delay, older than 2 months and 15 days.

    {LG}%(prog)s delete_clones --pool Pool-0 --volume zvol00 --older_than 2months 15days --delay 5 --node 192.168.0.220{ENDF}

    The older_than option is human readable clone age written with or without spaces with following units:
    year(s),y   month(s),m   week(s),w   day(s),d   hour(s),h   minute(s),min   second(s),sec,s
    Examples:  2m15d  -> two and a half months
               3w1d12h -> three weeks, one day and twelf hours
               2hours30min -> two and a half hours
               2hours 30min -> two and a half hours (with space between)

    {BOLD}Delete all (older_than 0 seconds) clones{END} of NAS volume vol00 from Pool-0.

    {LG}%(prog)s delete_clones --pool Pool-0 --volume vol00 --older_than 0seconds --delay 1 --node 192.168.0.220{ENDF}

    In order to delete all clones, the older_than must be zero.
    If the older_than option is missing, nothing will be deleted.


{} {BOLD}Delete snapshots{END} (time-based).

    Delete snapshots of provided volume and pool with creation date older than provided time period.

    This example deletes snapshots of iSCSI zvol00 from Pool-0 with 1 seconds prompted delay, older than 2 months and 15 days.

    {LG}%(prog)s delete_snapshots --pool Pool-0 --volume zvol00 --older_than 2months 15days --delay 1 --node 192.168.0.220{ENDF}

    The older_than option is human readable clone age written with or without spaces with following units:
    year(s),y   month(s),m   week(s),w   day(s),d   hour(s),h   minute(s),min   second(s),sec,s
    Examples:  2m15d  -> two and a half months
               3w1d12h -> three weeks, one day and twelf hours
               2hours30min -> two and a half hours
               2hours 30min -> two and a half hours (with space between)

    {BOLD}Delete all (older_than 0 seconds) snapshots{END} of NAS volume vol00 from Pool-0.

    {LG}%(prog)s delete_snapshots --pool Pool-0 --volume vol00 --older_than 0seconds --delay 1 --node 192.168.0.220{ENDF}

    In order to delete all snapshots, the older_than must be zero.
    If the older_than option is missing, nothing will be deleted.


{} {BOLD}Create pool{END} on single node or cluster with single JBOD:

    Pool-0 with 2 * raidz1 (3 disks) total 6 disks.

    Command create_pool creates data-groups only and use disks within provided disk_size_range,

    {LG}%(prog)s create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --disk_size_range 900GB 2TB --node 192.168.0.220{ENDF}

    if disk_size_range is omitted it takes disks with size near to avarage-disks-size. Default size difference is 5GB.

    {LG}%(prog)s create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --node 192.168.0.220{ENDF}

    The default size difference of 5GB can be changed with tolerance option.

    {LG}%(prog)s create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --tolerance 50GB --node 192.168.0.220{ENDF}


    {BOLD}Create pool{END} on Metro Cluster with single JBOD with 4-way mirrors:

    Pool-0 with 2 * mirrors (4 disks) total 8 disks.

    {LG}%(prog)s create_pool --pool Pool-0 --vdevs 2 --vdev mirror --vdev_disks 4 --node 192.168.0.220{ENDF}


    {BOLD}Create pool{END} with raidz2 (4 disks each) over 4 JBODs with 60 HDD each.

    Every raidz2 vdev consists of disks from all 4 JBODs. An interactive menu will be started.
    In order to read disks, POWER-ON single JBOD only. Read disks selecting "0" for the first JBOD.
    Next, POWER-OFF the first JBOD and POWER-ON the second one. Read disks of the second JBOD selecting "1".
    Repeat the procedure until all disks from all JBODs are read. Finally, create the pool selecting "args_count" from the menu.

    {LG}%(prog)s create_pool --pool Pool-0 --jbods 4 --vdevs 60 --vdev raidz2 --vdev_disks 4 --node 192.168.0.220{ENDF}


{} {BOLD}Import pool{END}:

    Get list of pools available for import:

    {LG}%(prog)s import --node 192.168.0.220{ENDF}

    Import pool Pool-0:

    {LG}%(prog)s import --pool Pool-0 --node 192.168.0.220{ENDF}

    Import pool Pool-0 with force option.
    Forces import, even if the pool appears to be potentially active.

    {LG}%(prog)s import --pool Pool-0 --force --node 192.168.0.220{ENDF}

    Forced import of Pool-0 with missing write-log device.

    {LG}%(prog)s import --pool Pool-0 --force --ignore_missing_write_log --node 192.168.0.220{ENDF}

    Forced import of Pool-0 in recovery mode for a non-importable pool.
    Attempt to return the pool to an importable state by discarding the last few transactions.
    Not all damaged pools can be recovered by using this option.
    If successful, the data from the discarded transactions is irretrievably lost.

    {LG}%(prog)s import --pool Pool-0 --force --recovery_import --node 192.168.0.220{ENDF}

    Forced import of Pool-0 in recovery mode and missing write-log device.

    {LG}%(prog)s import --pool Pool-0 --force --recovery_import --ignore_missing_write_log --node 192.168.0.220{ENDF}

    Forced import of Pool-0 in recovery mode and ignore unfinished resilver.

    {LG}%(prog)s import --pool Pool-0 --force --recovery_import --ignore_unfinished_resilver --node 192.168.0.220{ENDF}


{} {BOLD}Export pool{END}:

    Export pools. If the node belongs to cluster, export given pool in cluster.

    {LG}%(prog)s export --pool Pool-0 --node 192.168.0.220{ENDF}
    {LG}%(prog)s export --pool Pool-0 Pool-1 Pool-2 --node 192.168.0.220{ENDF}

    Export with optional 5 seconds delay.

    {LG}%(prog)s export --pool Pool-0 --delay 5 --node 192.168.0.220{ENDF}


{} {BOLD}Shutdown{END} three JovianDSS servers using default port but non default password,

    {LG}%(prog)s --pswd password shutdown --nodes 192.168.0.220 192.168.0.221 192.168.0.222{ENDF}

    or with IP range syntax "..".

    {LG}%(prog)s --pswd password shutdown --node 192.168.0.220..222{ENDF}

    Shutdown with optional 10 seconds delay.

    {LG}%(prog)s shutdown --delay 10 --node 192.168.0.220{ENDF}


{} {BOLD}Reboot{END} single JovianDSS server.

    {LG}%(prog)s reboot --node 192.168.0.220{ENDF}

    Forced reboot with optional 10 seconds delay.

    {LG}%(prog)s reboot --force --delay 10 --node 192.168.0.220{ENDF}

    The forced reboot can be used as hard-reset equivalent for deployment tests.
    NOTE: The shutdown command does not support forced option.
    Please use reboot command if hard-reset equivalent is required.


{} {BOLD}Set host name{END} to "node220", server name to "server220" and server description to "jdss220".

    {LG}%(prog)s set_host --host node220 --server server220 --description jdss220 --node 192.168.0.220{ENDF}


{} {BOLD}Set timezone and NTP-time{END} with default NTP servers.

    {LG}%(prog)s set_time --timezone America/New_York --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone America/Chicago --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone America/Los_Angeles --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone Asia/Tokyo --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone Europe/Amsterdam --node 192.168.0.220{ENDF}
    {LG}%(prog)s set_time --timezone Europe/Berlin --node 192.168.0.220{ENDF}

    Set NTP servers only.

    {LG}%(prog)s set_time --ntp_servers 0.pool.ntp.org 1.pool.ntp.org --node 192.168.0.220{ENDF}


{} {BOLD}Set new IP settings{END} for eth0 and set gateway-IP and set eth0 as default gateway.

    Missing netmask option will set default 255.255.255.0.

    {LG}%(prog)s network --nic eth0 --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.220{ENDF}

    Setting new DNS only,

    {LG}%(prog)s network --new_dns 192.168.0.1 --node 192.168.0.220{ENDF}

    or with 2 DNS servers.

    {LG}%(prog)s network --new_dns 192.168.0.1 192.168.100.254 --node 192.168.0.220{ENDF}

    Setting new gateway only. The default gateway will be set automatically.

    {LG}%(prog)s network --nic eth0 --new_gw 192.168.0.1 --node 192.168.0.220{ENDF}


{} {BOLD}Create bond{END} examples. Bond types: balance-rr, active-backup.

    Default = active-backup.

    {LG}%(prog)s create_bond --bond_nics eth0 eth1 --new_ip 192.168.0.80 --node 192.168.0.80{ENDF}
    {LG}%(prog)s create_bond --bond_nics eth0 eth1 --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.80{ENDF}
    {LG}%(prog)s create_bond --bond_nics eth0 eth1 --bond_type active-backup --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.80{ENDF}


{} {BOLD}Delete bond{END}.

    {LG}%(prog)s delete_bond --nic bond0 --node 192.168.0.80{ENDF}


{} {BOLD}Bind cluster{END}. Bind node-b (192.168.0.81) with node-a (192.168.0.80).

    RESTapi user = admin, RESTapi password = password, node-b GUI password = admin.

    {LG}%(prog)s bind_cluster --user admin --pswd password --bind_node_password admin --node 192.168.0.80 192.168.0.81{ENDF}


{} {BOLD}Add ring{END}. Add second ring to the cluster.

    RESTapi user = admin, RESTapi password = password, node-b GUI password = admin.
    The second ring to be set on bond2 on first node and also on bond2 on the second cluster node.

    {LG}%(prog)s add_ring --user admin --pswd password --bind_node_password admin --ring_nics bond2 bond2 --node 192.168.0.80{ENDF}

    Same, but using default user & password.

    {LG}%(prog)s add_ring --ring_nics bond2 bond2 --node 192.168.0.80{ENDF}


{} {BOLD}Set HA-cluster ping nodes{END}.

    RESTapi user = administrator, RESTapi password = password, netmask = 255.255.0.0.

    {LG}%(prog)s set_ping_nodes --user administrator --pswd password --netmask 255.255.0.0 --ping_nodes 192.168.0.240 192.168.0.241 192.168.0.242 --node 192.168.0.80{ENDF}

    Same, but with defaults: user = admin, password = admin, netmask = 255.255.255.0.

    {LG}%(prog)s set_ping_nodes --ping_nodes 192.168.0.240 192.168.0.241 192.168.0.242 --node 192.168.0.80{ENDF}


{} {BOLD}Set HA-cluster mirror path{END}. Please enter space separated NICs, the first NIC must be from the same node as the specified access IP.

    {LG}%(prog)s set_mirror_path --mirror_nics eth4 eth4 --node 192.168.0.82{ENDF}


{} {BOLD}Create VIP (Virtual IP){END} examples.

    {LG}%(prog)s create_vip --pool Pool-0 --vip_name vip21 --vip_nics eth2 eth2 --vip_ip 192.168.21.100 --vip_mask 255.255.0.0 --node 192.168.0.80{ENDF}
    {LG}%(prog)s create_vip --pool Pool-0 --vip_name vip31 --vip_nics eth2 --vip_ip 192.168.31.100 --node 192.168.0.80{ENDF}

    If cluster is configured both vip_nics must be provided.
    With single node (no cluster) only first vip_nic specified will be used.
    The second vip_nic (if specified) will be ignored.
    Default vip_mask = 255.255.255.0.


{} {BOLD}Start HA-cluster{END}. Please enter first node IP address only.

    {LG}%(prog)s start_cluster --node 192.168.0.82{ENDF}


{} {BOLD}Stop HA-cluster{END}. Please enter first node IP address only.

    {LG}%(prog)s stop_cluster --node 192.168.0.82{ENDF}


{} {BOLD}Move (failover){END} given pool.

    The current active node of given pool will be found and pool will be moved to passive node
    with optional delay in seconds.

    {LG}%(prog)s move --pool Pool-0 --delay 120 --node 192.168.0.82{ENDF}


{} {BOLD}Create storage resource{END}. Creates iSCSI target with volume (zvol) or SMB/NFS share with dataset.

    Defaults are: size = 1TB, blocksize = 16KB, recordsize = 1MB, provisioning = thin, volume = auto, target = auto, share_name = auto.
    The blocksize or recordsize can be: 4KB, 8KB, 16KB, 32KB, 64KB, 128KB, 256KB, 512KB, 1MB.

    Example for iSCSI target with specified volume, target, size, blocksize and provisioning.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --volume zvol00 --target iqn.2018-09:target0 --size 1TB --blocksize 64KB --provisioning thin --node 192.168.0.220{ENDF}

    If cluster name is specified, it will be used in the target name. Next examples will create both the same target name.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --cluster ha-00 --node 192.168.0.220{ENDF}
    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --volume zvol00 --target iqn.2018-09:target0 --cluster ha-00 --node 192.168.0.220{ENDF}

    With missing --target argument, it will produce auto-target name based on the host name.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --node 192.168.0.220{ENDF}

    By default primarycache and secondarycache is set to all. It can be disabled or set to cache metadata only:

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --primarycache metadata --secondarycache none --node 192.168.0.220{ENDF}

    If sync (Write Cache sync requests) is not provided the default is set, which is "always" for zvols and "standard" for datasets. Here the sync is set to "disabled".

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --sync disabled --cluster ha-00 --node 192.168.0.220{ENDF}

    Example for SMB share with dataset, using defaults (volume = auto, share_name = auto, sync = standard).

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb --node 192.168.0.220{ENDF}

    Example for SMB share with dataset, using specified volume, recordsize, sync and share_name.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb --volume vol00 --recordsize 128KB --sync always --share_name data --node 192.168.0.220{ENDF}

    Example with specified quota and reservation.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb --quota 100GB --reservation 50GB --node 192.168.0.220{ENDF}

    Example for multi-resource with --quantity option, starting consecutive number from zero (default),

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 5 --node 192.168.0.220{ENDF}
    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb nfs --quantity 5 --node 192.168.0.220{ENDF}

    and multi-resource with --quantity option, but starting consecutive number with 50 and increment 10.

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 5 --start_with 10 --increment 10 --node 192.168.0.220{ENDF}
    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type smb nfs --quantity 5 --start_with 10 --increment 10 --node 192.168.0.220{ENDF}

    To attach more than single zvol to a target, use --zvols_per_target option.
    This example will create 3 targets with 2 zvols each with following auto-numbering:
    (vol 10,target 10),(vol 11,target 10),(vol 12,target 11),(vol 13,target 11),(vol 14,target 12),(vol 15,target 12).

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 3 --start_with 10 --zvols_per_target 2 --node 192.168.0.220{ENDF}

    This example will create 2 targets with 4 volumes each with following auto-numbering:
    (vol 100,target 100),(vol 101,target 100),(vol 102,target 100),(vol 103,target 100),
    (vol 200,target 200),(vol 201,target 200),(vol 202,target 200),(vol 203,target 200).

    {LG}%(prog)s create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 2 --start_with 100 --increment 100 --zvols_per_target 4 --node 192.168.0.220{ENDF}


{} {BOLD}Modify volumes settings{END}. Modifiy volume (SAN) or dataset (NAS) setting.

    Current version modify only: Write cache logging (sync) settings, quota and reservation for datasets (NAS)
    and volume size for volumes (SAN).

    {LG}%(prog)s modify_volume --pool Pool-0 --volume zvol00 --sync always --node 192.168.0.220{ENDF}
    {LG}%(prog)s modify_volume --pool Pool-0 --volume zvol00 --sync disabled --node 192.168.0.220{ENDF}

    {LG}%(prog)s modify_volume --pool Pool-0 --volume vol00 --sync always --node 192.168.0.220{ENDF}
    {LG}%(prog)s modify_volume --pool Pool-0 --volume vol00 --sync standard --node 192.168.0.220{ENDF}
    {LG}%(prog)s modify_volume --pool Pool-0 --volume vol00 --sync disabled --node 192.168.0.220{ENDF}

    Modify quota and reservation.

    {LG}%(prog)s modify_volume --pool Pool-0 --volume vol00 --quota 200GB --reservation 80GB --node 192.168.0.220{ENDF}

    Modify SAN volume size in human readable format i.e. 100GB, 1TB, etc.
    New size must be bigger than current size, but not bigger than double of current size.

    {LG}%(prog)s modify_volume --pool Pool-0 --volume zvol00 --new_size 1024 GB --node 192.168.0.220{ENDF}


{} {BOLD}Attach volume to iSCSI target{END}.

    {LG}%(prog)s attach_volume_to_iscsi_target --pool Pool-0 --volume zvol00 --target iqn.2019-06:ha-00.target0 --node 192.168.0.220{ENDF}


{} {BOLD}Detach volume form iSCSI target{END}.

    {LG}%(prog)s detach_volume_from_iscsi_target --pool Pool-0 --volume zvol00 --target iqn.2019-06:ha-00.target0 --node 192.168.0.220{ENDF}


{} {BOLD}Detach disk form pool{END}.

    Detach disk from pool works with mirrored vdevs
    or with disks in raidz vdevs which are during or stopped replace process.

    {LG}%(prog)s detach_disk_from_pool --pool Pool-0 --disk_wwn wwn-0x5000c5008574a736 --node 192.168.0.220{ENDF}


{} {BOLD}Remove (delete) disk form pool{END}.

    Only spare, single log and cache disks can be removed from pool.

    {LG}%(prog)s remove_disk_from_pool --pool Pool-0 --disk_wwn wwn-0x5000c5008574a736 --node 192.168.0.220{ENDF}


{} {BOLD}Add read cache disk to pool{END}.

    Only single read cache disk can be add a time.

    {LG}%(prog)s add_read_cache_disk --pool Pool-0 --disk_wwn wwn-0x5000c5008574a736 --node 192.168.0.220{ENDF}



{} {BOLD}Scrub{END} start|stop|status.

    Scrub all pools. If the node belongs to cluster, scrub all pools in cluster.

    {LG}%(prog)s scrub --node 192.168.0.220{ENDF}

    Scrub on specified pools only.

    {LG}%(prog)s scrub --pool Pool-0 --node 192.168.0.220{ENDF}
    {LG}%(prog)s scrub --pool Pool-0 Pool-1 Pool-2 --node 192.168.0.220{ENDF}

    Stop scrub on all pools.

    {LG}%(prog)s scrub --scrub_action stop --node 192.168.0.220{ENDF}

    Scrub status on all pools.

    {LG}%(prog)s scrub --scrub_action status --node 192.168.0.220{ENDF}


{} {BOLD}Set scrub scheduler{END}.

    By default the command searches all pools on node or cluster (if configured) and set default schedule: every month at 0:15 AM.
    Every pool will be set on different month day.

    {LG}%(prog)s set_scrub_scheduler --node 192.168.0.220{ENDF}

    Set default schedule on Pool-0 and Pool-1 only.

    {LG}%(prog)s set_scrub_scheduler --pool Pool-0 Pool-1 --node 192.168.0.220{ENDF}

    Set schedule every week on Monday at 1:10 AM on Pool-0 only.

    {LG}%(prog)s set_scrub_scheduler --pool Pool-0 --day_of_the_month * --day_of_the_week 1 --hour 1 --minute 10 --node 192.168.0.220{ENDF}

    Set schedule every day at 2:30 AM on Pool-0 only.

    {LG}%(prog)s set_scrub_scheduler --pool Pool-0 --day_of_the_month * --hour 2 --minute 30 --node 192.168.0.220{ENDF}

    Set schedule every second day at 21:00 (9:00 PM) on Pool-0 only.

    {LG}%(prog)s set_scrub_scheduler --pool Pool-0 --day_of_the_month */2 --hour 21 --minute 0 --node 192.168.0.220{ENDF}

    {BOLD}TIP:{END}
    Quick schedule params check via browser on {BOLD}Pool-0{END} on {BOLD}192.168.0.220{END}:

    {LG}{BOLD}https:{END}//{BOLD}192.168.0.220{END}:82/api/v3/pools/{BOLD}Pool-0{END}/scrub/scheduler{ENDF}


{} {BOLD}Generate factory setup files for batch setup{END}.

    It creates and overwrites (if previously created) batch setup files.
    Setup files need to be edited and changed to required setup accordingly.
    For single node setup single node ip address can be specified.
    For cluster, both cluster nodes ip addresses, so it will create setup file for every node.

    {LG}%(prog)s create_factory_setup_files --nodes 192.168.0.80 192.168.0.81{ENDF}
    {LG}%(prog)s create_factory_setup_files --nodes 192.168.0.80 192.168.0.81 --ping_nodes 192.168.0.30 192.168.0.40 --mirror_nics bond1 bond1{ENDF}
    {LG}%(prog)s create_factory_setup_files --nodes 192.168.0.80..81 --ping_nodes 192.168.0.30 192.168.0.40 --mirror_nics eth4 eth4 --new_gw 192.168.0.1 --new_dns 192.168.0.1{ENDF}


{} {BOLD}Execute factory setup files for batch setup{END}.

    This example runs setup for nodes 192.168.0.80 and 192.168.0.81.
    Both nodes need to be fresh rebooted with factory defaults: eth0 = 192.168.0.220.
    First only one node must be started. Once booted, the RESTapi must be enabled via GUI.
    The batch setup will start to configure first node.
    Now, the second node can be booted.
    Once the second node is up, the RESTapi must also be enabled via GUI.

    {LG}%(prog)s batch_setup --setup_files api_setup_single_node_80.txt api_setup_single_node_81.txt api_setup_cluster_80.txt{ENDF}
    {LG}%(prog)s batch_setup --setup_files api_test_cluster_80.txt{ENDF}


{} {BOLD}Product activation{END}.

    {LG}%(prog)s activate --online --node 192.168.0.220{ENDF}

    Sends online Product Activation request.
	On-line activation requires an internet connection.
    Note: The off-line activation is not implemented yet.


{} {BOLD}Download current system settings{END}.

    {LG}%(prog)s download_settings --directory c:\downloads --nodes 192.168.0.220 192.168.0.221{ENDF}

    It generates current system settings and download to provided directory.
    More than one node is supported. if the --directory option is missing,
    the settings file will be saved in the current directory.
    
    {LG}%(prog)s download_settings --keep_settings --node 192.168.0.220{ENDF}

    The just generated and downloaded settings are NOT preserved in the storage node by default.
    The just generated and downloaded settings will be preserved if --keep_settings option is provided.


{} {BOLD}Print system info{END}.

    {LG}%(prog)s info --node 192.168.0.220{ENDF}

    The info command lists system information together with only the most recent snapshots.
    In order to list all snapshots use --all_snapshots option,

    {LG}%(prog)s info --all_snapshots --node 192.168.0.220{ENDF}

    or just --all.

    {LG}%(prog)s info --all --node 192.168.0.220{ENDF}


{} {BOLD}Print only snapshot info{END}.

    {LG}%(prog)s list_snapshots --node 192.168.0.220{ENDF}

    The list_snapshots command lists only the most recent snapshots.
    In order to list all snapshots use --all_snapshots option,
    In order to list all dataset (NAS) snapshots use --all_dataset_snapshots option,
    In order to list all zvol (SAN) snapshots use --all_zvol_snapshots option,

    {LG}%(prog)s list_snapshots --all_snapshots --node 192.168.0.220{ENDF}
    {LG}%(prog)s list_snapshots --all_dataset_snapshots --node 192.168.0.220{ENDF}
    {LG}%(prog)s list_snapshots --all_zvol_snapshots --node 192.168.0.220{ENDF}

    Note: If you want complete system information, please use the info command instead.

########################################################################################
 After any modifications of source of jdss-api-tools.py,
 run pyinstaller to create new jdss-api-tools.exe:

	pyinstaller.exe --onefile jdss-api-tools.py

 And try it:

    C:\Python\Scripts\dist>jdss-api-tools.exe -h

 NOTE:
 To fix anti-virus false positive problem of the exe file generated using PyInstaller,
 it needs to re-compile the pyinstaller bootloader. Follow step-by-step below:

        1) git clone https://github.com/pyinstaller/pyinstaller         # download the source
        2) cd pyinstaller
        3) cd bootloader
        4) python ./waf distclean all               # to build the bootloader for your system
        5) cd ..                            
        5) python setup.py install             # to install the fresh re-compiled pyinstaller  
        6) pyinstaller.exe --onefile jdss-api-tools.py             # to create the executable

 Missing Python modules need to be installed with pip, e.g.:

    C:\Python\Scripts>pip install ipcalc
    C:\Python\Scripts>pip install ping3
    C:\Python\Scripts>pip install colorama
    C:\Python\Scripts>pip install requests
    ...

 NOTE:
 Some modules may requrie MS Visual Studio:
 https://visualstudio.microsoft.com/downloads
 In case of error: "msvcr100.dll missing...",
 download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe
########################################################################################

{BOLD}Get help:{END}

     {LG}%(prog)s -h{ENDF}

{BOLD}Get help for a single command:{END}

     {LG}%(prog)s create_factory_setup_files{ENDF}
     {LG}%(prog)s batch_setup{ENDF}
     {LG}%(prog)s create_pool{ENDF}
     {LG}...{ENDF}

{BOLD}Commands:{END}

{LG}{COMMANDS}{ENDF}
 
 
'''

    global parser
    global commands

    parser = argparse.ArgumentParser(
        prog='jdss-api-tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='The %(prog)s remotely execute given command.'
    )
    commands = parser.add_argument(
        'cmd',
        metavar='command',
         choices =  'clone clone_existing_snapshot create_pool scrub set_scrub_scheduler create_storage_resource modify_volume      \
                    attach_volume_to_iscsi_target detach_volume_from_iscsi_target                                                   \
                    detach_disk_from_pool remove_disk_from_pool add_read_cache_disk                                                 \
                    delete_clone delete_clones delete_snapshots delete_clone_existing_snapshot set_host set_time network            \
                    create_bond delete_bond bind_cluster add_ring set_ping_nodes set_mirror_path                                    \
                    create_vip start_cluster stop_cluster move info download_settings                                               \
                    list_snapshots shutdown reboot batch_setup create_factory_setup_files activate import export'.split(),
        help='Commands:   %(choices)s.'
    )

    help_content     = get_args.__doc__
    help_items_count = help_content.count('{}')
    help_content     = help_content.replace('{}','{:2d}.')
    ## parser.epilog
    parser.epilog    = help_content.format(
        *range(1,help_items_count+1),                   ## auto numbering
        COMMANDS = nice_print(commands.choices),        ## commands set printed in columns
        BOLD     = Style.BRIGHT,
        END      = Style.NORMAL,                        ## END->End-Style
        LG       = Fore.LIGHTGREEN_EX,
        ENDF     = Fore.RESET                           ## ENDF->End-Foreground
    )

    parser.add_argument(
        '--nodes',
        metavar='ip-addr',
	#required=True,
        nargs='+',
        help='Enter nodes IP(s). Some commands work with multi nodes. Enter space separated IP or with .. range of IPs'
    )
    parser.add_argument(
        '--pool',
        metavar='name',
        nargs='+',
        help='Enter pool name'
    )
    parser.add_argument(
        '--volume',
        metavar='name',
        #default='auto',  #
        help='Enter required volume name. Default=auto, volume name will be auto-generated'
    )
    parser.add_argument(
        '--storage_type',
        metavar='iscsi|smb|nfs|smb,nfs|fc',
        nargs='+',
        help='Enter iSCSI or FC(not implemented yet) or SMB or NFS or SMB,NFS'
    )
    parser.add_argument(
        '--size',
        metavar='size',
        default='1TB',
        help='Enter SAN (zvol) size in human readable format i.e. 100GB, 1TB, etc. Default=1TB'
    )
    parser.add_argument(
        '--new_size',
        metavar='new_size',
        help='Enter SAN (zvol) NEW bigger size in human readable format i.e. 100GB, 1TB, etc. Default=1TB'
    )
    parser.add_argument(
        '--blocksize',
        metavar='size',
        default='16KB',
        help='Enter SAN (zvol) blocksize: 4KB, 8KB, 16KB, 32KB, 64KB, 128KB, 256KB, 512KB, 1MB. Default=16KB'
    )
    parser.add_argument(
        '--recordsize',
        metavar='size',
        default='1MB',
        help='Enter NAS (vol) recordsize: 4KB, 8KB, 16KB, 32KB, 64KB, 128KB, 256KB, 512KB, 1MB. Default=1MB'
    )
    parser.add_argument(
        '--quota',
        metavar='quota',
        help='Enter NAS (vol) quota size in human readable format i.e. 100MB 100GB, 1TB, etc.'
    )
    parser.add_argument(
        '--reservation',
        metavar='reservation',
        help='Enter NAS (vol) reservation size in human readable format i.e. 100MB 100GB, 1TB, etc.'
    )
    parser.add_argument(
        '--provisioning',
        metavar='thin|thick',
        default='thin',
        help='Enter thin or thick provisioning option. Default=thin'
    )
    parser.add_argument(
        '--sync',
        metavar='always|standard|disabled',
        default='always',
        help='Enter write cache logging (sync): always, standard, disabled. Default=always'
    )
    parser.add_argument(
        '--logbias',
        metavar='latency|throughput',
        default='latency',
        help='Enter logbias. Default=latency'
    )
    parser.add_argument(
        '--primarycache',
        metavar='all|none|metadata',
        default='all',
        help='Enter primarycache: all, none, metadata. Default=all'
    )
    parser.add_argument(
        '--secondarycache',
        metavar='all|none|metadata',
        default='all',
        help='Enter secondarycache: all, none, metadata. Default=all'
    )
    parser.add_argument(
        '--compression',
        metavar='off|lz4|lzjb|zle|gzip|gzip-1|gzip-2|gzip-3|gzip-4|gzip-5|gzip-6|gzip-7|gzip-8|gzip-9',
        default='lz4',
        help='Enter compression type or disable with "off"'
    )
    parser.add_argument(
        '--dedup',
        metavar='off|on|verify|sha256|sha256|verify',
        default='off',
        help='Enter dedup type or disable with "off"'
    )
    parser.add_argument(
        '--target',
        metavar='name',
        default='auto',
        help='Enter iSCSI target name. If not specified, target name will be auto-generated'
    )
    parser.add_argument(
        '--quantity',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of storage resources to create. Default=1'
    )
    parser.add_argument(
        '--start_with',
        metavar='number',
        default=0,
        type=int,
        help='Enter starting number of the consecutive number. Default=0'
    )
    parser.add_argument(
        '--zvols_per_target',
        metavar='number',
        default=1,
        type=int,
        help='Enter number of zvols to be attached to a single target. Default=1'
    )
    parser.add_argument(
        '--increment',
        metavar='number',
        choices=increment_options,
        default=100,
        type=int,
        help='Enter the target auto-numbering incremental. Default=100'
    )
    parser.add_argument(
        '--cluster',
        metavar='name',
        help='Enter the cluster name'
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
        help='Enter number of JBODs. Default=1'
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
        '--disk_wwn',
        metavar='wwn',
        default=None,
        help='Enter disk wwn, i.e.: wwn-0x5000c5008574a736'
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
        nargs='+',
        default=['0.pool.ntp.org','1.pool.ntp.org','2.pool.ntp.org'],
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
        nargs='+',
        default=None,   ## default None, empty string "" will clear DNS
        help='Enter new DNS address or space separated list'
    )
    parser.add_argument(
        '--bond_type',
        metavar='type',
        choices=['active-backup', 'balance-rr'],
        default='active-backup',
        help='Enter bond type (balance-rr, active-backup). Default=active-backup'
    )
    parser.add_argument(
        '--bond_nics',
        metavar='nics',
        nargs='+',
        help='Enter at least two NICs names, space separated bond NICs'
    )
    parser.add_argument(
        '--mirror_nics',
        metavar='nics',
        nargs='+',
        default=None,
        help='Enter space separated mirror path NICs'
    )
    parser.add_argument(
        '--ring_nics',
        metavar='nics',
        nargs='+',
        default=None,
        help='Enter space separated ring NICs'
    )
    parser.add_argument(
        '--vip_name',
        metavar='name',
        default=None,
        help='Enter new VIP name (alias)'
    )
    parser.add_argument(
        '--ping_nodes',
        metavar='ip-addr',
        nargs='+',
        help='Enter ping nodes IPs. Enter at least 2 space separated IPs'
    )
    parser.add_argument(
        '--vip_nics',
        metavar='nics',
        nargs='+',
        default=None,
        help='Enter space separated NICs of both cluster nodes, or single NIC for single node'
    )
    parser.add_argument(
        '--vip_ip',
        metavar='address',
        default=None,
        help='Enter new VIP address'
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
        help='RESTapi user. Default=admin'
    )
    parser.add_argument(
        '--pswd',
        metavar='password',
        default='admin',
        help='Administrator password. Default=admin'
    )
    parser.add_argument(
        '--port',
        metavar='port',
        default=82,
        type=int,
        help='RESTapi port. Default=82'
    )
    parser.add_argument(
        '--delay',
        metavar='seconds',
        default=30,
        type=int,
        help='User defined reboot/shutdown or move delay. Default=30 sec'
    )
    parser.add_argument(
        '--disk_size_range',
        metavar='size',
        nargs='+',
        help='Enter disk size range in human readable format i.e. 100GB, 1TB'
    )
    parser.add_argument(
        '--tolerance',
        metavar='tolerance',
        default='5GB',
        help='Disk size tolerance in human readable format i.e. 50GB. Treat smaller disks still as equal in size. Default=5GB'
    )
    parser.add_argument(
        '--share_name',
        metavar='name',
        default='auto',
        help='Enter share name. Default for clone actions=auto_api_backup_share. Default for creating NAS-resource=auto'
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
        help='Bind node password. Default=admin'
    )
    parser.add_argument(
        '--scrub_action',
        metavar='start|stop|status',
        choices=['start', 'stop', 'status'],
        default='start',
        help='Enter scrub action. Default=start'
    )
    parser.add_argument(
        '--day_of_the_month',
        metavar='day',
        nargs = '*',
        choices=[str(i) for i in range(1,32)],
        help='Enter the day of a month of schedule plan. Default=1'
    )
    parser.add_argument(
        '--month_of_the_year',
        metavar='day',
        nargs = '*',
        choices=[str(i) for i in range(1,13)],
        help='Enter the month or months (space separated) of the year of schedule plan. Default=1 2 3 4 5 6 7 8 9 10 11 12 (every month)'
    )
    parser.add_argument(
        '--day_of_the_week',
        metavar='day',
        nargs = '*',
        choices=[str(i) for i in range(1,8)],
        help='Enter the day or days (space separated) of the week of schedule plan'
    )
    parser.add_argument(
        '--hour',
        metavar='hour',
        nargs = '*',
        choices=[str(i) for i in range(24)],
        help='Enter the hour of schedule plan. Default=0'
    )
    parser.add_argument(
        '--minute',
        metavar='minute',
        nargs = '*',
        choices=[str(i) for i in range(60)],
        help='Enter the minute of schedule plan. Default=15'
    )
    parser.add_argument(
        '--older_than',
        metavar='age_string',
        nargs = '*',
        default=['99years'],
        help='The older_than option is human readable clone age. Units: year(s),y   month(s),m   week(s),w   day(s),d   hour(s),h   minute(s),min   second(s),sec'
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
    parser.add_argument(
        '--all_snapshots',
        dest='all_snapshots',
        action='store_true',
        default=False,
        help='The info command will list all snapshots, otherwise the info command will show most recent snapshot only'
    )
    parser.add_argument(
        '--all_dataset_snapshots',
        dest='all_dataset_snapshots',
        action='store_true',
        default=False,
        help='The info command will list all dataset snapshots (skipping zvol snapshots), otherwise the info command will show all most recent snapshot only'
    )
    parser.add_argument(
        '--all_zvol_snapshots',
        dest='all_zvol_snapshots',
        action='store_true',
        default=False,
        help='The info command will list all zvol snapshots (skipping dataset snapshots), otherwise the info command will show all most recent snapshot only'
    )
    parser.add_argument(
        '--online',
        dest='online',
        action='store_true',
        default=False,
        help='Send Online Product Activation request. It requires an internet connection'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        default=False,
        help='Force action'
    )
    parser.add_argument(
        '--directory',
        metavar='directory',
        default='',
        help='Enter the directory where the settings file will be saved. Default is current directory'
    )
    parser.add_argument(
        '--keep_settings',
        action='store_true',
        default=False,
        help='Keep just generated and downloaded settings in the system'
    )
    parser.add_argument(
        '--recovery_import',
        dest='recovery_import',
        action='store_true',
        default=False,
        help='Forced import of pool in recovery mode. It must be used for a non-importable pool'
    )
    parser.add_argument(
        '--ignore_missing_write_log',
        dest='ignore_missing_write_log',
        action='store_true',
        default=False,
        help='Forced import of pool with missing write-log device'
    )
    parser.add_argument(
        '--ignore_unfinished_resilver',
        dest='ignore_unfinished_resilver',
        action='store_true',
        default=False,
        help='Forced import of pool with unfinished resilver'
    )

    test_mode = False

    ## TESTING ONLY!
    #test_mode = True
    #test_command_line = 'activate --online --node 192.168.0.82'
    #test_command_line = 'modify_volume --pool Pool-0 --volume zvol --new_size 11060GB --node 192.168.0.42'
    #test_command_line = 'network --nic bond0 --new_ip 192.168.0.85 --node 192.168.0.82'
    #test_command_line = 'set_ping_nodes --ping_nodes 192.168.0.30 192.168.0.40 --node 192.168.0.82'
    #test_command_line = 'set_scrub_scheduler --pool Pool-PROD --node 192.168.0.82'
    #test_command_line = 'set_scrub_scheduler --node 192.168.0.82'
    #test_command_line = 'bind_cluster --node 192.168.0.82 192.168.0.83'
    #test_command_line = 'add_ring --ring_nics eth4 eth4 --node 192.168.0.82'
    #test_command_line = 'delete_snapshots --pool Pool-NEW --volume vol00 --older_than 30min --delay 1 --node 192.168.0.32'
    #test_command_line = 'reboot --force --delay 0 --node 192.168.0.42'
    #test_command_line = 'delete_bond --nic bond0 --node 192.168.0.82'
    #test_command_line = 'create_bond --bond_nics eth2 eth3 --bond_type active-backup --new_ip 192.168.33.82 --node 192.168.0.82'
    #test_command_line = 'move --pool Pool-0 --delay 0 --node 192.168.0.82'
    #test_command_line = 'clone --pool Pool-0 --volume zvol00 --primarycache none --secondarycache none --node 192.168.0.82'
    #test_command_line = 'delete_snapshots --pool Pool-0 --volume zvol100 --older_than 20min --delay 10 --node 192.168.0.80'
    #test_command_line = 'set_mirror_path --mirror_nics bond1 bond1 --node 192.168.0.80'
    #test_command_line = 'detach_disk_from_pool --pool Pool-0 --disk_wwn wwn-0x500003948833b740 --node 192.168.0.80'

    #test_command_line = 'remove_disk_from_pool --pool Pool-TEST --disk_wwn wwn-0x500003948833b688 --node 192.168.0.32'
    #test_command_line = 'add_read_cache_disk --pool Pool-TEST --disk_wwn wwn-0x500003948833b688 --node 192.168.0.32'

    #test_command_line = 'create_storage_resource --pool Pool-0 --storage_type iscsi --node 192.168.0.80'
    #test_command_line = 'start_cluster --node 192.168.0.82'
    #test_command_line = 'stop_cluster --node 192.168.0.82'
    #test_command_line = 'info --node 192.168.0.42'
    #test_command_line = 'download_settings --directory c:\cli --nodes 192.168.0.32 192.168.0.42'
    #test_command_line = 'info --pool Pool-0 --volume zvol00 --node 192.168.0.82'
    #test_command_line = 'clone --pool Pool-TEST --volume vol00 --node 192.168.0.82'
    #test_command_line = 'create_storage_resource --pool Pool-0 --storage_type iscsi --volume TEST-0309-1100 --target iqn.2019-09:zfs-odps-backup01.disaster-recovery --node 192.168.0.32'
    #test_command_line = 'create_vip --pool Pool-0 --vip_name vip21 --vip_ip 192.168.21.100 --vip_nics eth2 eth2 --node 192.168.0.80'
    #test_command_line = 'delete_clones --pool Pool-0 --volume zvol100 --older_than 15_sec --delay 1 --node 192.168.0.32'
    #test_command_line = 'import --pool Pool-0 --node 192.168.0.80'
    #test_command_line = 'create_pool --pool Pool-PROD --vdev mirror --vdevs 1 --vdev_disks 4 --node 192.168.0.82'
    #test_command_line = 'create_pool --pool Pool-PROD --vdev mirror --vdevs 1 --vdev_disks 4 --disk_size_range 20GB 20GB --node 192.168.0.82'
    #test_command_line = 'create_storage_resource --pool Pool-0 --storage_type iscsi --volume TEST01 --quantity 3 --node 192.168.0.80'
    #test_command_line = 'create_storage_resource --pool Pool-0 --storage_type iscsi --target testme --quantity 3 --node 192.168.0.80'
    #test_command_line = 'create_storage_resource --pool Pool-0 --storage_type smb --share_name testshare --quantity 3 --node 192.168.0.80'
    #test_command_line = 'create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 3 --start_with 223 --zvols_per_target 4 --node 192.168.0.80'


    ## ARGS
    if test_mode:
        args = parser.parse_args(test_command_line.split())
    elif batch_args_line:
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

    global api_port, api_user, api_password, action, pool_name, pools_names, volume_name
    global storage_type, storage_volume_type, size, new_size, blocksize, recordsize, quota
    global reservation, sync, logbias, sparse, primarycache, secondarycache, compression, dedup
    global snapshot_name, properties, nodes, ping_nodes, node, delay, menu, older_than
    global share_name, visible, jbod_disks_num, vdev_disks_num, jbods_num, vdevs_num, vdev_type
    global disk_size_tolerance, disk_size_range, number_of_disks_in_jbod, disk_wwn
    global nic_name, new_ip_addr, new_mask, new_gw, new_dns, bond_type, bond_nics, mirror_nics
    global ring_nics, host_name, server_name, server_description, timezone, ntp, ntp_servers
    global vip_name, vip_nics, vip_ip, vip_mask, bind_node_password
    global pool_based_consecutive_number_generator
    #global cluster_pool_names
    global target_name, cluster_name, quantity, start_with, zvols_per_target, increment, scrub_action
    global day_of_the_month, month_of_the_year, day_of_the_week, hour, minute, setup_files
    global all_snapshots, all_dataset_snapshots, all_zvol_snapshots, online
    global force, recovery_import, ignore_missing_write_log, ignore_unfinished_resilver
    global to_print_timestamp_msg, keep_settings, directory

    api_port                    = args['port']
    api_user                    = args['user']
    api_password                = args['pswd']
    action                      = args['cmd']				## the command
    pool_name                   = args['pool']
    volume_name                 = args['volume']

                                ## set default to auto except 'delete_clones', 'delete_snapshots'
    volume_name                 = volume_name if volume_name or action in ('delete_clones','delete_snapshots') else 'auto' 
    storage_type                = args['storage_type']			## it will be converted to upper below

    sparse                      = args['provisioning'].upper()	        ## THICK | THIN, default==THIN
    sparse                      = True if sparse in 'THIN' else False

    size                        = args['size']
    size                        = human_to_bytes(size)

    new_size                    = args['new_size']
    new_size                    = human_to_bytes(new_size)

    blocksize                   = args['blocksize']
    blocksize                   = human_to_bytes(blocksize)

    recordsize                  = args['recordsize']
    recordsize                  = human_to_bytes(recordsize)

    quota                       = args['quota']
    quota                       = human_to_bytes(quota)

    reservation                 = args['reservation']
    reservation                 = human_to_bytes(reservation)

    sync                        = args['sync']
    logbias                     = args['logbias']
    primarycache                = args['primarycache']
    secondarycache              = args['secondarycache']
    compression                 = args['compression']
    dedup                       = args['dedup']
    target_name                 = args['target']

    start_with                  = args['start_with']
    quantity                    = args['quantity']
    zvols_per_target            = args['zvols_per_target']
    increment                   = args['increment']

    cluster_name                = args['cluster']

    share_name                  = args['share_name']     ## change default share name from "auto" to "auto_api_backup_share"
    share_name                  = 'auto_api_backup_share' if 'clone' in action and share_name == 'auto' else share_name

    visible                     = args['visible']
    snapshot_name               = args['snapshot']
    jbod_disks_num              = args['jbod_disks']
    vdev_disks_num              = args['vdev_disks']
    jbods_num                   = args['jbods']
    vdevs_num                   = args['vdevs']
    vdev_type                   = args['vdev']

    disk_wwn                    = args['disk_wwn']

    disk_size_tolerance         = args['tolerance']
    disk_size_tolerance         = int(human_to_bytes(disk_size_tolerance))

    disk_size_range             = args['disk_size_range']
    disk_size_range             = map(int, map(human_to_bytes, disk_size_range)) \
                                    if disk_size_range else disk_size_range

    host_name                   = args['host']
    server_name                 = args['server']
    server_description          = args['description']
    timezone                    = args['timezone']
    ntp                         = args['ntp'].upper()			## ON | OFF, default=ON
    ntp_servers                 = args['ntp_servers']

    nic_name                    = args['nic']
    new_ip_addr                 = args['new_ip']
    new_mask                    = args['new_mask']
    new_gw                      = args['new_gw']
    new_dns                     = args['new_dns']
    bond_type                   = args['bond_type']
    bond_nics                   = args['bond_nics']
    bind_node_password          = args['bind_node_password']
    mirror_nics                 = args['mirror_nics']
    ring_nics                   = args['ring_nics']

    vip_name                    = args['vip_name']
    vip_nics                    = args['vip_nics']
    vip_ip                      = args['vip_ip']
    vip_mask                    = args['vip_mask']

    delay                       = args['delay']
    nodes                       = args['nodes']
    ping_nodes                  = args['ping_nodes']

    scrub_action                = args['scrub_action']
    day_of_the_month            = args['day_of_the_month']
    month_of_the_year           = args['month_of_the_year']
    day_of_the_week             = args['day_of_the_week']
    hour                        = args['hour']
    minute                      = args['minute']

    older_than                  = args['older_than']                ## list
    older_than                  = ''.join(older_than)               ## list to string
    older_than                  = human2seconds(older_than)         ## string to seconds

    menu                        = args['menu']
    setup_files                 = args['setup_files']
    all_snapshots               = args['all_snapshots']
    all_dataset_snapshots       = args['all_dataset_snapshots']
    all_zvol_snapshots          = args['all_zvol_snapshots']
    all_snapshots               = True if all_dataset_snapshots or all_zvol_snapshots else all_snapshots
                                  # setting all_snapshots to true if other params nee less checks,
                                  # if not all_snapshots, only most recent are listed
    online                      = args['online']

    directory                   = args['directory']
    keep_settings               = args['keep_settings']

    force                       = args['force']
    recovery_import             = args['recovery_import']
    ignore_missing_write_log    = args['ignore_missing_write_log']
    ignore_unfinished_resilver  = args['ignore_unfinished_resilver']

    ## volumes use properties dict, but datasets not
    properties                  = dict( sync=sync,
                                        compression=compression,
                                        primarycache=primarycache,
                                        secondarycache=secondarycache,
                                        logbias=logbias,
                                        dedup=dedup,
                                        copies=1)
    
    ## if vdev_type is raidz2 and vdev_disks = 2 * number of jbods
    ## or vdev_type is raidz3 and vdev_disks = 3 * number of jbods
    number_of_disks_in_jbod = 1
    if vdev_type == 'raidz2' and vdev_disks_num/jbods_num == 2 :
        number_of_disks_in_jbod = 2
    if vdev_type == 'raidz3' and vdev_disks_num/jbods_num == 3 :
        number_of_disks_in_jbod = 3

    ## scrub scheduler
    ## set default to 1st of every month at 0:15 AM
    if not day_of_the_month:
        day_of_the_month = '1'
    if not month_of_the_year:
        month_of_the_year = '*'
    if not day_of_the_week:
        day_of_the_week = '*'
    if not hour:
        hour = '0'
    if not minute:
        minute = '15'

    pools_names = pool_name
    if pool_name:
        pool_name = pool_name[0]

    ## start menu if multi-JBODs
    if jbods_num > 1:
        menu = True
    
    ## storage_type   list  ISCSI, FC, SMB, NFS or SMB,NFS
    ## storage_volume_type  ISCSI, FC ='volume'; SMB, NFS ='dataset'
    if storage_type:
        storage_type=[ item.upper() for item in storage_type]
        if len(storage_type)>1:
            if not ('SMB' in storage_type and 'NFS' in storage_type):
                sys_exit_with_timestamp('Error: Only SMB with NFS combination is allowed')
            else:
                if 'FC' in storage_type:
                    sys_exit_with_timestamp('Error: FC setup automation not implemented yet')
        vt = dict(ISCSI='volume',FC='volume',SMB='dataset',NFS='dataset')
        storage_volume_type = vt[storage_type[0]]

    expanded_nodes = []

    if not nodes and not setup_files:
        if action:
            print_help_item(action)
            sys_exit('')
        else:
            sys_exit_with_timestamp('--nodes with valid ip_addr is required')

    ## do not validate ip if batch_setup and first ARGS call (second ARGS call is from batch command processor)
    ## expand nodes list if IP range provided in args
    ## i.e. 192.168.0.220..221 will be expanded to: ["192.168.0.220","192.168.0.221"]
    caller = sys._getframe(1).f_code.co_name      ## caller is  <module>  or  main() function
    if not(caller in '<module>' and action in 'batch_setup'):
        for ip in nodes:
            if ".." in ip:
                expanded_nodes += expand_ip_range(ip)
            else:
                expanded_nodes.append(ip)
        nodes = expanded_nodes
        ## first node
        node = nodes[0]
        ## True if action msg need to be printed
        to_print_timestamp_msg = dict(zip(nodes,(True for i in nodes)))
        ## validate all-ip-addr => (nodes + new_ip, new_gw, new_dns)
        all_ip_addr = nodes[:]  ## copy
        all_ip_addr = all_ip_addr + ping_nodes if ping_nodes else all_ip_addr
        for ip in [new_ip_addr, new_gw, new_mask] + new_dns if new_dns else []:   ## new_dns is a list
            if ip:
                all_ip_addr.append(ip)
        for ip in all_ip_addr:
            if not valid_ip(ip):
                sys_exit(f"IP address {ip} is invalid")
        ## detect doubles
        doubles =  len(nodes) != len(set(nodes))
        if doubles:
            sys_exit(f"Double IP address: {', '.join(nodes)}")

    ## validate port
    if not 22 <= api_port <= 65535:
        sys_exit(f"Port {api_port} is out of allowed range 22..65535")


#_____________________END_OF_ARGS_____________________#


def is_node_alive(test_node):
    ## this function do can not use global node variable, this is why cannot use get function.
    result = get('/conn_test')
    return True if result in 'OK' else False


def wait_for_move_destination_node(test_node):
    repeat = 100
    counter = 0
    time.sleep(5)
    while not is_node_alive(test_node):
        counter += 1
        time.sleep(20)
        print_with_timestamp(f"Waiting for : {test_node}")
        if counter == repeat:   ## timed out
            sys_exit_with_timestamp(f"Time out of waiting for : {test_node}")


def wait_for_zero_unmanaged_pools():
    repeat = 300
    counter = 0
    time.sleep(5)
    while is_node_running_any_unmanaged_pool():
        unmanaged_pools_names = unmanaged_pools()
        print_with_timestamp(f"Unmanaged pools: {','.join(unmanaged_pools_names)}. Wait for managed state")
        counter += 1
        time.sleep(20)
        if counter == repeat:   ## timed out
            unmanaged_pools_names = unmanaged_pools()
            sys_exit_with_timestamp(f"Unmanaged pools: {','.join(unmanaged_pools_names)}")
    if force :
        time.sleep(60) ## need some time to complete all operations


def wait_for_cluster_started():
    if not is_cluster_configured():
        return
    repeat = 300 # wait 25min
    counter = 0
    time.sleep(5)
    while not is_cluster_started():
        counter += 1
        time.sleep(20)
        print_with_timestamp(f"Waiting for the cluster to start")
        if counter == repeat:   ## timed out
            sys_exit_with_timestamp(f"ERROR: Cluster failed to start")

def wait_for_pools_online():
    repeat = 300 # wait 25min
    counter = 0
    time.sleep(5)
    online = False
    while not online:
        online = all(pool['health'] in 'ONLINE' for pool in get('/pools'))
        if online:
            break
        counter += 1
        time.sleep(5)
        print_with_timestamp(f"Waiting for all pools ONLINE status")
        if counter == repeat:   ## timed out
            sys_exit_with_timestamp(f"ERROR: failed to get pools ONLINE status")



def human_to_bytes(value):
    if value:
        value = value.strip('Bb')
        return str(human2bytes(value))
    return value


def bytes2human(n, format='%(value).1f %(symbol)s', symbols='customary'):
    """
    Convert n bytes into a human readable string based on format.
    Symbols can be either "customary", "customary_ext", "iec" or "iec_ext",
    see: http://goo.gl/kTQMs

      >>> bytes2human(0)
      '0.0 B'
      >>> bytes2human(0.9)
      '0.0 B'
      >>> bytes2human(1)
      '1.0 B'
      >>> bytes2human(1.9)
      '1.0 B'
      >>> bytes2human(1024)
      '1.0 K'
      >>> bytes2human(1048576)
      '1.0 M'
      >>> bytes2human(1099511627776127398123789121)
      '909.5 Y'

      >>> bytes2human(9856, symbols="customary")
      '9.6 K'
      >>> bytes2human(9856, symbols="customary_ext")
      '9.6 kilo'
      >>> bytes2human(9856, symbols="iec")
      '9.6 Ki'
      >>> bytes2human(9856, symbols="iec_ext")
      '9.6 kibi'

      >>> bytes2human(10000, "%(value).1f %(symbol)s/sec")
      '9.8 K/sec'

      >>> # precision can be adjusted by playing with %f operator
      >>> bytes2human(10000, format="%(value).5f %(symbol)s")
      '9.76562 K'
    """
    SYMBOLS = {
        'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
        'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                           'zetta', 'iotta'),
        'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
        'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                           'zebi', 'yobi'),
    }

    n = int(n)
    if n < 0:
        raise ValueError("n < 0")
    symbols = SYMBOLS[symbols]
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)


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
            ## treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])


def interval_seconds(plan):
    '''
    example plan: plan='1hours=>5minutes,3days=>15minutes'
    function returns minimum interval of the plan in seconds
    '''
    return min([eval(item.split('=>')[-1].replace(
          'seconds',          '*'+str(1)).replace(
          'minutes',         '*'+str(60)).replace(
          'hours',        '*'+str(60*60)).replace(
          'days',      '*'+str(60*60*24)).replace(
          'weeks',   '*'+str(60*60*24*7)).replace(
          'months', '*'+str(60*60*24*30)).replace(
          'years', '*'+str(60*60*24*365)) ) for item in plan.split(',')])


def human2seconds(age):
    '''
    param: human_readable age written with or without spaces with following units:
    year(s),y   month(s),m   week(s),w   day(s),d   hour(s),h   minute(s),min  second(s),sec,s
    Examples:  2m15d  -> two and a half months
               3w1d12h -> three weeks, one day and twelf hours
               2hours30min -> two and a half hours
    '''
    global older_than_string_to_print
    older_than_string_to_print  = ''


    def split_items(age):
        out=''
        previous = '0'
        for char in age:
            if char.isdigit() or char in 'year month week day hour minute second':
                out += '#' + char if char.isdigit() and not previous.isdigit() else char
                previous = char
        return out.split('#')

    def item2seconds(age):
        if age in '0': age = '0sec'
        alpha = age.strip(string.digits)
        seconds = 3600*24*365*99 # 99 years
        if alpha in ('second','minute','hour','day','week','month','year'):
            age = age + 's'
        d={'sec':'seconds', 's':'seconds', 'min':'minutes', 'h':'hours', \
             'd':'days',    'w':'weeks',     'm':'months',  'y':'years'}
        if alpha in d.keys(): age=age.replace(alpha,d[alpha])
        
        #if alpha in 'sec'       : age = age.replace('sec','seconds')
        #if alpha in 's'         : age = age.replace('s','seconds')
        #if alpha in 'min'       : age = age.replace('min','minutes')
        #if alpha in 'h'         : age = age.replace('h','hours')
        #if alpha in 'd'         : age = age.replace('d','days')
        #if alpha in 'w'         : age = age.replace('w','weeks')
        #if alpha in 'm'         : age = age.replace('m','months')
        #if alpha in 'y'         : age = age.replace('y','years')
        
        global older_than_string_to_print
        older_than_string_to_print += age.replace(
            'seconds','-second ').replace(
            'minutes','-minute ').replace(
            'hours',    '-hour ').replace(
            'days',      '-day ').replace(
            'weeks',    '-week ').replace(
            'months',  '-month ').replace(
            'years',    '-year ').strip() + ' '

        try:
            seconds = eval(age.replace(
                'seconds',          '*'+str(1)).replace(
                'minutes',         '*'+str(60)).replace(
                'hours',        '*'+str(60*60)).replace(
                'days',      '*'+str(60*60*24)).replace(
                'weeks',   '*'+str(60*60*24*7)).replace(
                'months', '*'+str(60*60*24*30)).replace(
                'years', '*'+str(60*60*24*365)))
        except (NameError,ValueError):
            print(f"Age:{age} Syntax error")
            print(human2seconds.__doc__)
            sys.exit() ## cannot use print_with_exit as this func is called
                   ## before intialize the print_with_exit
        return seconds

    ##
    return sum([item2seconds(item) for item in split_items(age.lower())])


def snapshot_creation_to_seconds(creation):
    '''
    creation = snapshot creation time in seconds or date-string. Example: 2018-10-14 22:45:3
    '''
    if '-' in creation:
        mytime = creation
        myformat = "%Y-%m-%d %H:%M:%S"
        mydt = datetime.datetime.strptime(mytime, myformat)
        return time.time() - time.mktime(mydt.timetuple())
    return time.time() - float(creation)


def seconds2human(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    periods = [('days', days),('hours', hours), ('minutes', minutes), ('seconds', seconds)]
    for name,value in periods:
        value = int(value)
        if value == 0:
            continue
        if value == 1:
            return f"{str(value)} {name[:-1]}"
        return f"{str(value)} {name}"


def consecutive_number_generator(increment):
    i = j = start_with
    z = zvols_per_target
    for increment_option in increment_options:
        if increment < zvols_per_target:
            increment = increment_option
    while 1:
        if increment == 1:
            # return example if start_with=10 and zvols_per_target=2
            # (10,10) next (11,10) next (12,11) next (13,11) next (14,12) next (15,12)...
            yield (i, ((i - ((i - start_with) % zvols_per_target) - start_with)/zvols_per_target) + start_with)
        else:
            # return example if start_with=10 and zvols_per_target=2
            # (10,10) next (11,10) next (20,20) next (21,20) next (30,30) next (31,30)...
            yield i, j
        z -= 1
        if z < 1:
            i += (increment - zvols_per_target)
            j = i + 1
            z = zvols_per_target
        i += 1


def initialize_pool_based_consecutive_number_generator():
    global pool_based_consecutive_number_generator
    pool_based_consecutive_number_generator = {}
    cluster_pool_names = get_cluster_pools_names()
    for cluster_pool_name in cluster_pool_names:
        ## add generator for every cluster pool
        pool_based_consecutive_number_generator[cluster_pool_name] = consecutive_number_generator(increment)


def convert_comma_separated_to_list(arg):
    if arg is None:
        return None
    if arg == '':
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
    print( f"{time_stamp()}  {msg}" )


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

    def backspace(n):
        sys.stdout.write((b'\x08' * n).decode()) # use \x08 char to go back

    for sec in range(delay, 0, -1) :
        print
        s = f"{msg} in {sec:>2} seconds ...          "
        sys.stdout.write(s)                     # just print
        sys.stdout.flush()                      # needed for flush when using \x08
        backspace(len(s))                       # back n chars
        time.sleep(1)


def wait_ping_lost_while_reboot():
    waiting_dots_printed = False
    ## PING
    counter = 0; repeat = 60
    while isinstance(ping3.ping(node),float):
        if counter < 2:
            print_with_timestamp(f"Node {node} stopping the system ...")
        elif counter > 1:
            print('.',end='')
            waiting_dots_printed = True
        counter += 1
        time.sleep(10)
        if counter == repeat:   ## Connection timed out
            sys_exit_with_timestamp(f"Connection timed out: {node}")

    if waiting_dots_printed: print()
    waiting_dots_printed = False


def reboot_nodes(shutdown=False):
    global node
    global action_message
    global api_timeout
    mode = 'shutdown' if shutdown else 'reboot'
    if force:
        api_timeout = 5
    for node in nodes:
        action_message = f"Sending {'Forced ' if force else ''}{mode} request to: {node}"
        wait_for_node()
        display_delay(mode.capitalize())
#        is_cluster = is_cluster_configured()
#        if is_cluster:
#            wait_for_cluster_started()
        if 'batch_setup' in action :
            wait = 60 if force else 30 
            print_with_timestamp("Wait {wait} sec for failover(move) ...")
            time.sleep(wait) # for test running in loop need time for failover
        wait_for_zero_unmanaged_pools()
        wait_for_pools_online()
        print_with_timestamp(f"{'Forced ' if force else ''}{mode}: {node}")
        time.sleep(5)
        post(f"/power/{mode}", dict(force=force))
        if not force:
            wait_ping_lost_while_reboot()
#        if is_cluster:
#               break


def set_host_server_name(host_name=None, server_name=None, server_description=None):
    global action_message
    action_message = f"Sending host name, server name and server description setting request to: {node}"

    data = dict()
    if host_name:
        data["host_name"] = host_name
    if server_name:
        data["server_name"] = server_name
    if server_description:
        data["server_description"] = server_description

    put('/product',data)

    if host_name:
        print_with_timestamp(f"Set host name: {host_name}")
    if server_name:
        print_with_timestamp(f"Set server name: {server_name}")
    if server_description:
        print_with_timestamp(f"Set server description: {server_description}")


def set_time(timezone=None, ntp=None, ntp_servers=None):
    global action_message
    action_message = f"Sending time settings request to: {node}"

    data = dict()
    if timezone:
        data["timezone"] = timezone
    if ntp == "OFF":
        data["daemon"] = False
    if ntp == "ON":
        data["daemon"] = True
    if ntp_servers:
        data["servers"] = ntp_servers

    ## exit if DNS is missing
    dns = get_dns()
    if ntp == 'ON' and not dns:
        sys_exit_with_timestamp(f"Cannot set NTP. Missing DNS setting on node: {node}")

    ## PUT
    put('/time',data)

    if error:
        print_with_timestamp(f"Cannot set NTP. Error: {error}")

    if timezone:
        print_with_timestamp(f"Set timezone: {timezone}")
    if ntp == 'ON':
        print_with_timestamp("Set time from NTP: Yes")
    if ntp_servers:
        print_with_timestamp(f"Set NTP servers: {' '.join(ntp_servers)}")


def add_fields_seperator(fields,fields_length,seperator_length):
    for key in fields_length:
        fields_length[key] +=  seperator_length
    ## The very first field is aligned to the right,
    ## and all next fields are aligned to the right.
    ## It looks like double separator, need to remove it.
    fields_length[fields[0]] -= seperator_length
    return fields_length


def natural_sub_dict_sort_by_name_key(items):

    if items and isinstance(items,list) and isinstance(items[0],dict) and 'name' in items[0].keys():
        format_string = '{0:0>'+str(max((len(item['name']) for item in items)))+'}' #natural sorting
        items.sort(key=lambda k : format_string.format(str(k['name'])).lower())     #human sort
        return items
    else:
        return items


def natural_list_sort(items):
    if items and isinstance(items,list):
        format_string = '{0:0>'+str(max((len(item) for item in items)))+'}' ## natural sorting
        items.sort(key=lambda k : format_string.format(str(k)).lower())     ## human sort
        return items
    else:
        return items


def print_volumes_details(header,fields):
    pools = get('/pools')
    pools.sort(key=lambda k : k['name'])
    fields_length={}
    for pool in pools:
        is_field_separator_added = False
        ## reset dict to zero, origin field is used by clones
        fields_length = fields_length.fromkeys(fields+('origin',), 0)
        endpoint = f"/pools/{pool['name']}/volumes"
        volumes = get(endpoint)     ## ZVOLs
        if not volumes:
            continue			## SKIP if no vol
        is_origin = any([volume['origin'] for volume in volumes])
        if is_origin:
            header,fields = header+('origin',),fields+('origin',)
        for volume in volumes:
            for i,field in enumerate(fields):
                value = '-'
                if field in ('volblocksize', 'volsize', 'used', 'available'):
                    volume[field] =  bytes2human(volume[field], format='%(value).0f%(symbol)s', symbols='customary')
                if field in volume.keys():
                    value = str(volume[field])
                current_max_field_length = max(len(header[i]), len(value))
                if current_max_field_length > fields_length[field]:
                    fields_length[field] = current_max_field_length

        if not is_field_separator_added:
            fields_length = add_fields_seperator(fields,fields_length,3)
            is_field_separator_added = True

        header_format_template  = '{:_<' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
        field_format_template   =  '{:<' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

        print()
        print( header_format_template.format( *(header)))

        for volume in volumes:
            volume_details = []
            for field in fields:
                value = '-'
                if field in volume.keys():
                    value = str(volume[field])
                    if value in ('None',):
                        value = '-'
                volume_details.append(value)
            print(field_format_template.format(*volume_details))


def print_nas_volumes_details(header,fields):
    pools = get('/pools')
    pools.sort(key=lambda k : k['name'])
    fields_length={}
    for pool in pools:
        is_field_separator_added = False
        fields_length = fields_length.fromkeys(fields+('origin',), 0)  ## reset dict to zero, origin field is used by clones
        endpoint = f"/pools/{pool['name']}/nas-volumes"
        volumes = get(endpoint) ## datasets
        if not volumes:
            continue			## SKIP if no vol
        is_origin = any([volume['origin'] for volume in volumes])
        if is_origin:
            header,fields = header+('origin',),fields+('origin',)
        for volume in volumes:
            for i,field in enumerate(fields):
                value = '-'
                if field in ('recordsize',):
                    volume[field] =  bytes2human(volume[field], format='%(value).0f%(symbol)s', symbols='customary')
                if field in volume.keys():
                    value = str(volume[field])
                current_max_field_length = max(len(header[i]), len(value))
                if current_max_field_length > fields_length[field]:
                    fields_length[field] = current_max_field_length

        if not is_field_separator_added:
            fields_length = add_fields_seperator(fields,fields_length,3)
            is_field_separator_added = True

        header_format_template  = '{:_<' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
        field_format_template   =  '{:<' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

        print()
        print( header_format_template.format( *(header)))

        for volume in volumes:
            volume_details = []
            for field in fields:
                value = '-'
                if field in volume.keys():
                    value = str(volume[field])
                    if value in ('None',):
                        value = '-'
                volume_details.append(value)
            print(field_format_template.format(*volume_details))


def delete_clones(vol_type):
    global action_message
    action_message = f"Sending delete clones request to: {node}"
    clones = get_all_volume_clones_older_than_given_age(vol_type)
    if clones:
        for clone in clones:
            clone_name = clone[0]
            print_with_timestamp(f"Clone: {clone_name} of {pool_name} {volume_name} will be deleted")
        display_delay('DELETING clones ...')
        print()
        for clone in clones:
            clone_name = clone[0]
            snapshot_name = clone[3]
            resp = delete_clone(vol_type,clone_name, snapshot_name)
            if error:
                print_with_timestamp(f"Cannot delete clone: {clone_name} of {pool_name} {volume_name}")
            else:
                print_with_timestamp(f"Clone: {clone_name} of {pool_name} {volume_name} has been deleted")
    else:
        _older_than_string_to_print = ' '.join(sorted(older_than_string_to_print.split(), key=lambda item: time_periods.index(item.split('-')[-1])))
        print_with_timestamp(f"No clones older than {_older_than_string_to_print} found on {pool_name} {volume_name}")


def delete_clone(vol_type,clone_name, snapshot_name):
    data = dict(umount=True, force_umount=True)
    if vol_type in 'volume':
        delete( f"/pools/{pool_name}/volumes/{volume_name}/snapshots/{snapshot_name}/clones/{clone_name}", data)
    if vol_type in 'dataset':
        delete( f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{snapshot_name}/clones/{clone_name}", data)
    return False if error else True


def get_all_volume_clones_older_than_given_age(vol_type):
    if vol_type in 'volume':
        volumes = get( f"/pools/{pool_name}/volumes" )
    if vol_type in 'dataset':
        volumes = get( f"/pools/{pool_name}/nas-volumes" )

    clones_origin_names = [(volume['name'],volume['origin'].replace('@','/').split('/')) for volume in volumes if volume['is_clone'] and snapshot_creation_to_seconds(volume['creation']) > older_than]
    # Example: [(u'clone-zvol00', [u'Pool-0', u'zvol00', u'autosnap_2019-08-15-193200'])]
    clones_pools_volumes_snapshots = [(item[0],item[1][0],item[1][1],item[1][2]) for item in clones_origin_names]
    # Example: [(u'clone-zvol00', u'Pool-0', u'zvol00', u'autosnap_2019-08-15-193200')]

    ## filter-out clones of other volumes than volume_name
    clones_pools_volumes_snapshots = [item for item in  clones_pools_volumes_snapshots if item[2] in volume_name]
    return clones_pools_volumes_snapshots


def delete_snapshots(vol_type):
    global action_message
    action_message = f"Sending delete snapshots request to: {node}"
    #snapshots_names = get_snapshots_names()
    snapshots_names = get_all_volume_snapshots_older_than_given_age(vol_type)
    display_delay('DELETING snapshot ...')
    print()

    for snapshot_name in snapshots_names:
        delete_snapshot(vol_type,snapshot_name)
        if error:
            print_with_timestamp(f"Cannot delete snapshot: {snapshot_name}")
        else:
            print_with_timestamp(f"Snapshot: {snapshot_name} deleted")


def delete_snapshot(vol_type, snapshot_name):
    #data = {'recursively_dependents':True}
    if vol_type in 'volume':
        delete( f"/pools/{pool_name}/volumes/{volume_name}/snapshots/{snapshot_name}" )
    if vol_type in 'dataset':
        delete( f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{snapshot_name}" )
    return not bool(error) # false if error
    
    
def get_snapshot_clones(snapshot_name):
    clones = clones_names = None
    if vol_type in 'volume':
        clones = get(f"/pools/{pool_name}/volumes/{volume_name}/snapshots/{snapshot_name}/clones")
    if vol_type in 'dataset':
        clones = get(f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{snapshot_name}/clones")
    if clones:
        clones_names = [clone['full_name'] for clone in clones]
    return clones_names or []


def get_all_volume_snapshots_older_than_given_age(vol_type):
    if vol_type in 'volume':
        snapshots = get(f"/pools/{pool_name}/volumes/{volume_name}/snapshots?page=0&per_page=0&sort_by=name&order=asc")
        if snapshots:
            # snapshots['entries'][0]['creation'] -> u'2019-8-15 14:0:1'
            snapshots_names = [snapshot['name'] for snapshot in snapshots['entries'] if snapshot_creation_to_seconds(snapshot['creation']) > older_than]
    if vol_type in 'dataset':
        snapshots = get(f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots?page=0&per_page=0&sort_by=name&order=asc")
        if snapshots:
            try:
                snapshots_names = [snapshot['name'] for snapshot in snapshots['entries'] for prop_item in snapshot['properties'] if prop_item['name']=='creation' and snapshot_creation_to_seconds(prop_item['value']) > older_than]
            except KeyError:
                snapshots_names = [snapshot['name'] for snapshot in snapshots['entries'] if snapshot_creation_to_seconds(snapshot['creation']) > older_than]
    return snapshots_names or []


def print_nas_snapshots_details(header,fields):
    global pool_name
    pools = get('/pools')
    is_field_separator_added = False
    fields_length = {}.fromkeys(fields, 0)
    for pool in pools:
        snapshot_exist = False
        pool_name = pool['name']
        nas_volumes = get_nas_volumes_names()
        if not nas_volumes:
            continue    ## SKIP if no vol
        for nas_volume in nas_volumes:
            snapshots = get(f"/pools/{pool_name}/nas-volumes/{nas_volume}/snapshots?page=0&per_page=10&sort_by=name&order=asc")
            if not snapshots or not snapshots['results'] or snapshots['results']== 0:
                continue
            snapshot_exist = True
            for snapshot in snapshots['entries']:
                snapshot_name = pool_name + '/' + nas_volume + '@' + snapshot['name']  ## pool/vol@snap
                ## convert list of properties into dict of name:values
                try:
                    property_dict = {item['name']:item['value'] for item in snapshot['properties']} ## properties list is optional.
                except:
                    property_dict = False

                for i,field in enumerate(fields):
                    value = '-'
                    if field in ('name',):
                        value = snapshot_name
                    elif field in ('referenced',):
                        value = property_dict['referenced'] if property_dict else snapshot['referenced']
                        value = bytes2human(value, format='%(value).0f%(symbol)s', symbols='customary')
                    elif field in ('written',):
                        value = property_dict['written'] if property_dict else snapshot['written']
                        value = bytes2human(value, format='%(value).0f%(symbol)s', symbols='customary')
                    elif field in ('age',):
                        value = 'xx minutes' ## fake value as only few snaps are checked in the loop
                    current_max_field_length = max(len(header[i]), len(value))
                    if current_max_field_length > fields_length[field]:
                        fields_length[field] = current_max_field_length
        if not snapshot_exist: continue     ## SKIP if no snap
        if not is_field_separator_added:
            fields_length = add_fields_seperator(fields,fields_length,3)
            is_field_separator_added = True

        header_format_template  = '{:_<' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
        field_format_template   =  '{:<' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

        print()
        print( header_format_template.format( *(header)))

        for nas_volume in nas_volumes:
            snapshot_details = []
            snapshots = get(f"/pools/{pool_name}/nas-volumes/{nas_volume}/snapshots?page=0&per_page=0&sort_by=name&order=asc")
            if not snapshots or not snapshots['results'] or snapshots['results']== 0: continue
            for snapshot in snapshots['entries']:
                snapshot_details = []
                snapshot_name = pool_name + '/' + nas_volume + '@' + snapshot['name']  ## pool/vol@snap
                ## convert list of properties into dict of name:values
                #property_dict = {item['name']:item['value'] for item in snapshot['properties']}
                try:
                    property_dict = {item['name']:item['value'] for item in snapshot['properties']} ##properties list is optional.
                except:
                    property_dict = False
                    
                for field in fields:
                    value = '-'
                    if field in ('name',):
                        value = snapshot_name
                    elif field in ('referenced',):
                        value = property_dict['referenced'] if property_dict else snapshot['referenced']
                        value = bytes2human(value, format='%(value).0f%(symbol)s', symbols='customary')
                    elif field in ('written',):
                        value = property_dict['written'] if property_dict else snapshot['written']
                        value = bytes2human(value, format='%(value).0f%(symbol)s', symbols='customary')
                    elif field in ('age',):
                        time_stamp_string = snapshot_name.split('_')[-1]
                        #value = seconds2human(snapshot_creation_to_seconds(time_stamp_string))
                        value = seconds2human(snapshot_creation_to_seconds(property_dict['creation'] if property_dict else snapshot['creation']))
                        try:
                            source_plan = property_dict['org.znapzend:src_plan'] if property_dict else snapshot['org.znapzend:src_plan']
                        except:
                            source_plan = False
                        if source_plan:
                            plan = source_plan
                        else:
                            plan = ""
                    snapshot_details.append(value)
            print_out = field_format_template.format(*snapshot_details)
            if all_snapshots:
                print(print_out)
        if not all_snapshots:
            print(print_out)
        fields_length = {}.fromkeys(fields, 0)
        is_field_separator_added = False


def print_san_snapshots_details(header,fields):
    global pool_name
    pools = get('/pools')
    is_field_separator_added = False
    fields_length = {}.fromkeys(fields, 0)
    for pool in pools:
        snapshot_exist = False
        pool_name = pool['name']
        san_volumes = get_san_volumes_names()
        if not san_volumes:
            continue            ## SKIP if no vol
        for san_volume in san_volumes:
            snapshots = get(f"/pools/{pool_name}/volumes/{san_volume}/snapshots?page=0&per_page=10&sort_by=name&order=asc")
            if not snapshots or not snapshots['results'] or snapshots['results']== 0: continue
            snapshot_exist = True
            for snapshot in snapshots['entries']:
                snapshot_name = pool_name + '/' + san_volume + '@' + snapshot['name']  ## pool/vol@snap
                for i,field in enumerate(fields):
                    value = '-'
                    if field in ('name',):
                        value = snapshot_name
                    elif field in ('age',):
                        value = 'xx minutes' ## fake value as only few snaps are checked in the loop
                    else:
                        value = snapshot[field]
                        if value in ('None',):
                            value = '-'
                        elif str.isdigit(str(value)):
                            value = bytes2human(value, format='%(value).0f%(symbol)s', symbols='customary')
                    current_max_field_length = max(len(header[i]), len(value))
                    if current_max_field_length > fields_length[field]:
                        fields_length[field] = current_max_field_length
        if not snapshot_exist:
            continue            ##  SKIP if no snap
        if not is_field_separator_added:
            fields_length = add_fields_seperator(fields,fields_length,3)
            is_field_separator_added = True

        header_format_template  = '{:_<' + '}{:_>'.join([str(fields_length[field]) for field in fields]) + '}'
        field_format_template   =  '{:<' +  '}{:>'.join([str(fields_length[field]) for field in fields]) + '}'

        print()
        print( header_format_template.format( *(header)))

        for san_volume in san_volumes:
            snapshot_details = []
            snapshots = get(f"/pools/{pool_name}/volumes/{san_volume}/snapshots?page=0&per_page=0&sort_by=name&order=asc")
            if not snapshots or not snapshots['results'] or snapshots['results']== 0: continue
            for snapshot in snapshots['entries']:
                snapshot_details = []
                snapshot_name = pool_name + '/' + san_volume + '@' + snapshot['name']  ## pool/vol@snap
                for field in fields:
                    value = '-'
                    if field in ('name',):
                        value = snapshot_name
                    elif field in ('age',):
                        value = seconds2human(snapshot_creation_to_seconds(snapshot['creation']))
                    else:
                        value = snapshot[field]
                        if value in ('None',):
                            value = '-'
                        elif str.isdigit(str(value)):
                            value = bytes2human(value, format='%(value).0f%(symbol)s', symbols='customary')
                    snapshot_details.append(value)
                if snapshot_details:
                    print_out = field_format_template.format(*snapshot_details)
                    if all_snapshots:
                        print(print_out)
            if not all_snapshots:
                print(print_out)
            if all_snapshots:
                print()
        fields_length = {}.fromkeys(fields, 0)
        is_field_separator_added = False


def print_pools_details(header,fields):
    pools = get('/pools')
    if not pools: return
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

    fields_length = add_fields_seperator(fields,fields_length,3)

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
                if value in ('None',):
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
                sys_exit_with_timestamp(f"Error: {pool_name} does not exist on node: {node}")
    else:
        pools_names_to_scrub = get_cluster_pools_names()
    pools_names_to_scrub.sort()

    pools = [] ## list of pools scrub details
    for pool_name in pools_names_to_scrub:
        node = get_active_cluster_node_address_of_given_pool(pool_name)
        to_print_timestamp_msg[node] = False
        endpoint = f"/pools/{pool_name}"
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

    fields_length = add_fields_seperator(fields,fields_length,3)

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
                if value in ('None',):
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
                if isinstance(interface[field],int):
                    interface[field] /= 1000
            if field in interface.keys():
                value = str(interface[field])
            current_max_field_length = max(len(header[i]), len(value)) 
            if current_max_field_length > fields_length[field]:
                fields_length[field] = current_max_field_length

    fields_length = add_fields_seperator(fields,fields_length,3)

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
                if value in ('None',):
                    value = '-'
            interface_details.append(value)
        print(field_format_template.format(*interface_details))


def set_default_gateway():
    global action_message
    action_message = f"Sending default gateway setting request to: {node}"
    ## PUT
    put('/network/default-gateway', dict(interface=nic_name))
    ## GET
    dgw_interface = None
    dgw_interface = get('/network/default-gateway')['interface']
    if dgw_interface is None:
        print_with_timestamp('No default gateway set')
    else:
        print_with_timestamp(f"Default gateway set to: {dgw_interface}")


def set_dns(dns):
    global action_message
    action_message = f"Sending DNS setting request to: {node}"
    ## PUT
    put('/network/dns', dict(servers=dns))
    if error:
        print_with_timestamp(f"Error: setting DNS. {error}")
    print_with_timestamp(f"DNS set to: {', '.join(dns)}")


def get_dns():
    dns = None
    endpoint = '/network/dns'
    ## GET
    dns = get(endpoint)
    if error:
        print_with_timestamp(f"Error: getting DNS. {error}")
    if dns is None:
        return None
    if len(dns['servers']) == 0:
        return None
    return dns['servers']


def set_scrub_scheduler():
    global node
    global action_message
    action_message = f"Sending set scrub schedule request to: {node}"
    _pools_names = []
    if pool_name:
        _pools_names.append(pool_name)
    else:
        _pools_names = get_cluster_pools_names()
    incr = int(28 / len(_pools_names))
    _day_of_the_month = day_of_the_month
    for _pool_name in sorted(_pools_names):
        data = dict(day_of_the_month=_day_of_the_month, month_of_the_year=month_of_the_year,
                    day_of_the_week=day_of_the_week, hour=hour, minute=minute)
        _node = get_active_cluster_node_address_of_given_pool(_pool_name)
        if _node:
            node = _node
        else:
            continue
        post(f"/pools/{_pool_name}/scrub/scheduler", data)
        print_with_timestamp(f"Scrub schedule set for: {_pool_name} on {node}")


def scrub():
    global node
    global action_message
    global pool_name
    action_message = f"Sending scrub {scrub_action} request to: {node}"
    if pools_names:
        pools_names_to_scrub = pools_names
        cluster_pools_names = get_cluster_pools_names()
        for pool_name in pools_names_to_scrub:
            if pool_name not in cluster_pools_names:
                sys_exit_with_timestamp(f"Error: {pool_name} does not exist on node: {node}")
    else:
        pools_names_to_scrub = get_cluster_pools_names()
    pools_names_to_scrub.sort()
    for pool_name in pools_names_to_scrub:
        to_print_timestamp_msg[node] = False
        node = get_active_cluster_node_address_of_given_pool(pool_name)
        to_print_timestamp_msg[node] = True
        if scrub_action in ('start','stop'):
            endpoint = f"/pools/{pool_name}/scrub"
            action_message = f"Sending scrub request to {pool_name} on : {node}"
            post(endpoint, dict(action=scrub_action))

    ## print scrub pools details
    header= tuple('pool  state  scrub_start_time  end_time  rate  mins_left  examined  %        total'.split())
    fields= tuple('pool  state  start_time        end_time  rate  mins_left  examined  percent  total'.split())
    print_scrub_pools_details(header,fields)


def export():
    global node
    global action_message
    global pool_name
    action_message = f"Sending export {scrub_action} request to: {node}"
    if pools_names:
        pools_names_to_export = pools_names
        cluster_pools_names = get_cluster_pools_names()
        for pool_name in pools_names_to_export:
            if pool_name not in cluster_pools_names:
                sys_exit_with_timestamp(f"Error: {pool_name} does not exist on node: {node}")
    else:
        pools_names_to_export = get_cluster_pools_names()
    pools_names_to_export.sort()
    for pool_name in pools_names_to_export:
        to_print_timestamp_msg[node] = False
        node = get_active_cluster_node_address_of_given_pool(pool_name)
        to_print_timestamp_msg[node] = True
        display_delay('Export')
        endpoint = f"/pools/{pool_name}/export"
        action_message = f"Sending export request to {pool_name} on : {node}"
        # POST
        post(endpoint)


def get_pools_names():
    pools = get('/pools')
    if pools:
        return [pool['name'] for pool in pools]
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
    return bool(get('/cluster/nodes'))


def is_cluster_started():
    result = ''
    result = get('/cluster')
    # {u'status': u'started', u'enabled': True}
    result = result['status'] if result else ''
    return bool('started' in result)


def is_node_running_all_managed_pools():
    result = get('/cluster/resources')
    if result and isinstance(result,list):
        return all((item['managed'] for item in result))
    return True  ## result is '' if no cluster configured


def is_node_running_any_unmanaged_pool():
    result = get('/cluster/resources')
    if result and isinstance(result,list):
        return not all((item['managed'] for item in result))
    return False  ## result is '' if no cluster configured


def managed_pools():
    result = get('/cluster/resources')
    if result and isinstance(result,list):
        return [item['name'] for item in result if item['managed']]
    return []


def unmanaged_pools():
    result = get('/cluster/resources')
    if result and isinstance(result,list):
        return [item['name'] for item in result if not item['managed']]
    return []

def get_host_name():
    return get('/product')["host_name"]

def generate_iscsi_target_and_volume_name(pool_name):
#    host_name = get('/product')["host_name"]
    host_name = get_host_name()
    if cluster_name:
        host_name = cluster_name
    consecutive_integer_tuple = next(pool_based_consecutive_number_generator[pool_name])
    consecutive_integer_volume, consecutive_integer_target = consecutive_integer_tuple
    consecutive_string_volume = "{:0>3}".format(consecutive_integer_volume)
    consecutive_string_target = "{:0>3}".format(consecutive_integer_target)
    ## target name MUST use lower case only 
    iscsi_target_name = "iqn.{}.iscsi:{}.target{}".format(time.strftime("%Y-%m"), host_name.lower(), consecutive_string_target)
    if is_cluster_configured():
        # default cluster name = ha-00
        iscsi_target_name = iscsi_target_name.replace(host_name,cluster_name if cluster_name else 'ha-00')
    volume_name = "zvol{}".format(consecutive_string_volume)
    return (iscsi_target_name, volume_name)


def generate_share_and_volume_name(pool_name):
    consecutive_integer_tuple = next(pool_based_consecutive_number_generator[pool_name])
    consecutive_integer = consecutive_integer_tuple[0]
    consecutive_string = "{:0>3}".format(consecutive_integer)
    share_name = "data{}".format(consecutive_string)
    volume_name = "vol{}".format(consecutive_string)
    return (share_name, volume_name)


def get_iscsi_targets_names():
    targets= get(f"/pools/{pool_name}/san/iscsi/targets")
    if targets:
        return [target['name'] for target in targets]
    return []


def get_nas_volumes_names():
    nas_volumes = get(f"/pools/{pool_name}/nas-volumes")
    if nas_volumes:
        return natural_list_sort([nas_volume['name'] for nas_volume in nas_volumes])
    return []


def get_san_volumes_names():
    san_volumes = get(f"/pools/{pool_name}/volumes")
    if san_volumes:
        return natural_list_sort([san_volume['name'] for san_volume in san_volumes])
    return []

def get_san_volume_size():
    volume_properties = get(f"/pools/{pool_name}/volumes/{volume_name}/properties")
    return [ property_item['value'] for property_item in volume_properties if 'volsize' in property_item['name']][0]

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
    ''' output = get('/cluster/rings')
    [{u'status': u'ok', u'interfaces': [{u'interface': u'bond0', u'node_id': u'f46f6d14'},
                        {u'interface': u'bond0', u'node_id': u'ae4b08ce'}], u'id': 0}]
    '''
    n = 30
    while n:
        output = get('/cluster/rings')
        if output:
            return output[0]['interfaces'][0]['interface']
        n -= 1
        time.sleep(1)
    ## get return empty list
    sys_exit_with_timestamp('Error getting ring interface: Cluster not bound yet')


def get_number_of_rings():
    rings = get('/cluster/rings')
    return len([ ring['interfaces'][0]['interface'] for ring in rings ])

def get_rings():
    ''' rings = get('/cluster/rings')
    [{u'status': u'n/a', u'interfaces': [{u'interface': u'bond0', u'node_id': u'e5c83031'}, {u'interface': u'bond0', u'node_id': u'e2cb9ad2'}],u'id': 0},
     {u'status': u'n/a', u'interfaces': [{u'interface': u'eth3', u'node_id': u'e5c83031'}, {u'interface': u'eth3', u'node_id': u'e2cb9ad2'}], u'id': 1}]
    '''
    n = 30; rings = []
    while n:
        rings = get('/cluster/rings')
        if rings:
            break
        n -= 1
        time.sleep(1)
    if len(rings) == 2:
        first_ring =  rings[0]['interfaces'][0]['interface'],rings[0]['interfaces'][1]['interface']
        second_ring = rings[1]['interfaces'][0]['interface'],rings[1]['interfaces'][1]['interface']
    elif len(rings) == 1:
        first_ring =  rings[0]['interfaces'][0]['interface'],rings[0]['interfaces'][1]['interface']
        second_ring = []
    elif len(rings) == 0:
        first_ring = []
        second_ring = []
    return tuple(first_ring), tuple(second_ring)


def get_cluster_nodes_addresses():
    global is_cluster
    resp = get('/cluster/nodes')
    ## single-node  [{u'localnode': True, u'status': None, u'hostname': u'node-32', u'reachable': True, u'address': u'127.0.0.1', u'id': u'5c913a76'}]
    ## cluster      [{u'localnode': False, u'status': u'online', u'hostname': u'node-81-ha00', u'reachable': True, u'address': u'192.168.0.81', u'id': u'8e126ece'},
    ##               {u'localnode': True, u'status': u'online', u'hostname': u'node-80-ha00', u'reachable': True, u'address': u'192.168.0.80', u'id': u'67596e40'}]
    if type(resp) is list and len(resp) > 1 :
        is_cluster = True
        resp.sort(key=lambda item:item['localnode'],reverse=True)
        return [item['address'] for item in resp]
    is_cluster = False
    return [node]  ## the node as single item list


def get_cluster_node_id(node):

    result = get('/cluster/nodes')
    result = result if result else []
    if len(result) > 1:
        return [ cluster_node['id'] for cluster_node in result if cluster_node['address'] in node][0]
    ## cluster not configured yet
    sys_exit_with_timestamp('Error: Cluster not bound yet')

#    if len(result) < 2:
##   cluster not configured yet
#        sys_exit_with_timestamp('Error: Cluster not bound yet')
#    else:
#       return [ cluster_node['id'] for cluster_node in result if cluster_node['address'] in node][0]


def get_cluster_nodes_ids():

    result = get('/cluster/nodes')
    result = result if result else []

    if len(result) < 2:
        single_node_cluster_id = result[0]['id']    ## NO cluster, just single node
        return single_node_cluster_id

    cluster_id_local  = [ cluster_node['id'] for cluster_node in result if     cluster_node['localnode']][0]
    cluster_id_remote = [ cluster_node['id'] for cluster_node in result if not cluster_node['localnode']][0]
    return cluster_id_local, cluster_id_remote


def get_vips():
    endpoint = f"/pools/{pool_name}/vips"
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
    return not bool('127.0.0.1' in bind_node_address)


def create_vip():
    global action_message
    action_message = f"Sending create VIP request to: {node}"

    if not pool_name:
        sys_exit_with_timestamp('Error: Pool name missing')
    ######
    #nics = convert_comma_separated_to_list(vip_nics)
    ###### nics = list(vip_nics)
    nics = vip_nics
    if len(nics)==1:
        nics.append(nics[0])
    if len(nics)==2:
        nic_a, nic_b = nics
    else:
        sys_exit_with_timestamp('Error: --vip_nics expects one or two NICs')
    cluster_nodes_ids = get_cluster_nodes_ids()
    #cluster_ip_addresses = get_cluster_nodes_addresses()
    cluster = True if cluster_nodes_ids and len(cluster_nodes_ids) > 1 else False
    endpoint = f"/pools/{pool_name}/vips"
    if cluster:
        data = dict(name=vip_name,
                    address = vip_ip,
                    netmask = vip_mask,
                    interface = nic_a,
                    remote_interface = [ dict( node_id = cluster_nodes_ids[-1],
                                               interface = nic_b)])
    else: ## single node
        data = dict(name=vip_name,
                    address = vip_ip,
                    netmask = vip_mask,
                    interface = nic_a)
    ## POST
    post(endpoint,data)
    if error:
        sys_exit_with_timestamp(f"Error setting VIP: {vip_ip} with: {','.join(nics)} on: {pool_name}. {error}")

    print_with_timestamp(f"New VIP: {vip_ip} set, with: {','.join(nics)} on: {pool_name}")


def set_mirror_path():
    global action_message
    action_message = f"Sending mirror path setting request to: {node}"

    cluster_nodes_addresses = get_cluster_nodes_addresses()
    cluster_nodes_ids = get_cluster_nodes_ids()
    ## first cluster node must be same as node from args
    if cluster_nodes_addresses[0] != node:
        cluster_nodes_addresses[0], cluster_nodes_addresses[1] =  \
        cluster_nodes_addresses[1], cluster_nodes_addresses[0]
    interfaces_items = []
    for i, cluster_node_address in enumerate(cluster_nodes_addresses):
        interfaces_items.append(dict(interface=mirror_nics[i], node_id=cluster_nodes_ids[i]))
    data = dict(interfaces=interfaces_items)
    #### return_code = {}
    ## POST
    #### return_code = post('/cluster/remote-disks/paths',data)
    post('/cluster/remote-disks/paths',data)
    is_all_OK = False
    for _ in range(50):
        time.sleep(10)
        result = get('/cluster/remote-disks/paths')
        if result and len(result)>0:
            is_all_OK = all('OK' in interface['status'] for interface in result[0]['interfaces'])
        if is_all_OK:
            print()
            print_with_timestamp(f"Mirror path set to: {', '.join(mirror_nics)}")
            break
        else:
            print('.', end='')
    if not is_all_OK:
        print()
        sys_exit_with_timestamp(f"Error setting mirror path with: {', '.join(mirror_nics)}. {error}")


def get_ping_nodes():
    ping_nodes=[]
    endpoint = '/cluster/ping-nodes'
    ## GET
    ping_nodes = [ping_node['address'] for ping_node in get(endpoint)]
    if error:
        print_with_timestamp(f"Error getting ping nodes. {error}")
    return [] if error else ping_nodes


def set_ping_nodes():
    global action_message
    action_message = f"Sending ping node setting request to: {node}"

    current_ping_nodes = get_ping_nodes()

    if len(ping_nodes)<2:
        print_with_timestamp('Warning: One ping node provided. At least 2 ping nodes are recommended')
    for ping_node in ping_nodes:   
        if ping_node in current_ping_nodes:
            print_with_timestamp(f"Error: Ping node {ping_node} already set")
            continue
        ## as from up28 it is NOT required to keep ping in the same subnet as ring
        ## POST
        post('/cluster/ping-nodes', dict(address=ping_node))
        if ping_node in get_ping_nodes():
            print_with_timestamp(f"New ping node {ping_node} set")


def start_cluster():
    global action_message
    action_message = f"Sending cluster service start request to: {node}"

    started = False

    ## to-do  cluster_nodes_addresses = get_cluster_nodes_addresses()
    if not cluster_bind_set():
        sys_exit_with_timestamp(f"Cannot start cluster on {node}. Nodes are not bound yet")

    ## GET
    if is_cluster_started():
        print_with_timestamp(f"Cluster on {node} is already started")
        return

    ## POST
    print_with_timestamp('Cluster service starting ...')
    post('/cluster/start-cluster', dict(mode='cluster'))

    ## check start
    for _ in range(50):
        if is_cluster_started():
            print()
            print_with_timestamp('Cluster service started successfully')
            break
        print('.', end='')
        time.sleep(5)
    else:
        print()
        sys_exit_with_timestamp(f"Error: Cluster service start failed. {error if error else ''}")


def stop_cluster():
    global action_message
    action_message = f"Sending cluster service stop request to: {node}"

    stopped = False

    ## to-do  cluster_nodes_addresses = get_cluster_nodes_addresses()
    if not cluster_bind_set():
        sys_exit_with_timestamp(f"Cannot stop cluster on {node}. Nodes are not bound yet")

    ## GET
    if not is_cluster_started():
        print_with_timestamp(f"Cluster on {node} is already stopped")
        return

    ## POST
    print_with_timestamp('Cluster service stopping ...')
    post('/cluster/stop-cluster', dict(mode='cluster'))

    ## check stop
    for _ in range(50):
        if not is_cluster_started():
            print()
            print_with_timestamp('Cluster service stopped successfully')
            break
        print('.', end='')
        time.sleep(5)
    else:
        print()
        sys_exit_with_timestamp(f"Error: Cluster service stop failed. {error if error else ''}")



def move():
    global node
    global nodes
    global action_message
    action_message = f"Sending failover (move) request to: {node}"
    command_line_node = node
    if not all((is_cluster_configured,is_cluster_started)):
        sys_exit_with_timestamp(f"Error: Cluster not running on: {node}")
    nodes = get_cluster_nodes_addresses() ## nodes are now just both cluster nodes
    if len(nodes)<2:
        sys_exit_with_timestamp(f"Error: Cannot move. {node} is running as single node")
    cluster_pools_names = get_cluster_pools_names()
    if pool_name not in cluster_pools_names:
        print_with_timestamp(f"Pool: {pool_name} was not found")
        return

    active_node = passive_node = new_active_node = ''
    for node in nodes:
        if node not in command_line_node:
            wait_for_move_destination_node(node)
            #wait_for_node()
        ## GET
        pools = get('/pools')
        pool_names = [pool['name'] for pool in pools]
        
        if pool_name in pool_names:
            active_node = node
            passive_node = nodes[0 if nodes.index(node) else 1]   #
            display_delay('Move')
            print_with_timestamp(f"{pool_name} is moving from: {active_node} to: {passive_node}")
            ## wait ...
            wait_for_move_destination_node(passive_node)
            wait_for_zero_unmanaged_pools()
            data=dict(node_id = get_cluster_node_id(passive_node))
            endpoint = f"/cluster/resources/{pool_name}/move-resource"
            ## POST
            post(endpoint,data)
            if error:
                sys_exit_with_timestamp(f"Cannot move POOL: {pool_name}. Error: {error}")
            else:
                break
    new_active_node = ''
    for _ in range(120):    # wait for move completed with timeout
        print_with_timestamp('Moving in progress ...')
        time.sleep(1)
        for node in nodes:
            ## GET
            pools = get('/pools')
            if not pools:
                continue
            pool_names = [pool['name'] for pool in pools]
            if pool_name in pool_names:
                if node in active_node: # pool still not exported
                    continue
                else:
                    new_active_node = node
            if new_active_node:
                break
        if new_active_node:
            break
    if new_active_node == passive_node: ## after move (failover) passive node is active
        print_with_timestamp(f"{pool_name} is moved from: {active_node} to: {new_active_node}")
    else:
        sys_exit_with_timestamp(f"Cannot move pool {pool_name}. Error: {error}")


def network(nic_name, new_ip_addr, new_mask, new_gw, new_dns):
    global node    ## the node IP can be changed
    global action_message
    global api_timeout
    api_timeout = 5
    access_nic_changed = False
    action_message = f"Sending network setting request to: {node}"
    timeouted = False

    ## list_of_ip
    ## validate all IPs, exit if no valid IP found
    for ip in [new_ip_addr, new_mask, new_gw] + new_dns if new_dns else []:
        if ip:
            if not valid_ip(ip):
                sys_exit(f"IP address {new_ip_addr} is invalid")
    endpoint = f"/network/interfaces/{nic_name}"
    data = dict(configuration="static", address=new_ip_addr, netmask=new_mask)
    if new_gw or new_gw == '':
        data["gateway"]=new_gw if new_gw else None

    ## if new_ip_addr is missing, set gateway & DNS and return
    if new_ip_addr is None:
        if new_gw:
            set_default_gateway()
        if new_dns is not None:
            set_dns(new_dns)
        return
        #sys_exit( 'Error: Expected, but not specified --new_ip for {}'.format(nic_name))

    ## PUT
    put(endpoint,data)

    if not api_connection_test_passed():
        node = new_ip_addr  ## the node IP was changed
        access_nic_changed = True
        time.sleep(1)

    if access_nic_changed:
        print_with_timestamp(f"The acccess NIC {nic_name} changed to {new_ip_addr}")
    else:
        if get_interface_ip_addr(nic_name) == new_ip_addr:
            print_with_timestamp(f"New IP address {new_ip_addr} set to {nic_name}")
        else:
            print_with_timestamp(f"ERROR: New IP address {new_ip_addr} set to {nic_name} failed")

    ## set default gateway interface
    if new_gw:
        set_default_gateway()

    if new_dns is not None:
        set_dns(new_dns)


def create_bond(bond_type, bond_nics, new_gw, new_dns):
    global node    ## the node IP can be changed
    global nic_name
    global action_message
    action_message = f"Sending create bond request to: {node}"

    if len(bond_nics) <2:
        sys_exit_with_timestamp('Error: at least two NICs required')
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
                bond_primary_reselect = 'always')
    if 'balance-rr' in bond_type.lower():
        data = dict(type = 'bonding',
                configuration = 'static',
                address = ip_addr,
                netmask = new_mask,
                slaves = bond_nics,
                bond_mode = bond_type.lower(),
                bond_primary_reselect = 'always')
    if new_gw:
        data["gateway"]=new_gw
    ## POST
    post(endpoint,data)
    if error: #bond already exist
        print_with_timestamp(f"Error: cannot create bond with {','.join(bond_nics)} on {node}")
        return
    time.sleep(1)
    ##
    nic_name = get_nic_name_of_given_ip_address(ip_addr)  ## global nic_name
    if nic_name and ('bond' in nic_name):
        print_with_timestamp(f"{nic_name} created with IP: {new_ip_addr}")
    else:
        sys_exit_with_timestamp(f"Error: cannot create bond with {','.join(bond_nics)} on {node}")
    ## set default gateway interface
    if new_gw:
        set_default_gateway()
    ## set DNS
    if new_dns is not None:
        set_dns(new_dns)


def delete_bond(bond_name):
    global node    ## the node IP can be changed
    global action_message
    action_message = f"Sending delete bond request to: {node}"
    ## global nic_name
    node_id_220 = 0
    orginal_node_id = 1   ## just different init value than node_id_220


    bond_slaves = get_bond_slaves(bond_name) ## list
    if bond_slaves is  None or len(bond_slaves)<2:
        sys_exit_with_timestamp(f"Error : {bond_name} not found")

    first_nic_name, second_nic_name = sorted(bond_slaves)
    bond_ip_addr = get_interface_ip_addr(bond_name)
    bond_gw_ip_addr = get_interface_gw_ip_addr(bond_name)
    bond_netmask = get_interface_netmask(bond_name)
    orginal_node_id = node_id()

    endpoint = f"/network/interfaces/{bond_name}"
    delete(endpoint)
    if error:
        sys_exit_with_timestamp(f"Error, bond: {bond_name} cannot be deleted as it is used in cluster configuration")
    else:
        print_with_timestamp(f"Bond: {bond_name} deleted")
        if timeouted:
            node = new_ip_addr  ## the node IP was changed

    time.sleep(1)
    if node_id_220 == orginal_node_id:
        endpoint = f"/network/interfaces/{first_nic_name}"
        data = dict(configuration="static", address=bond_ip_addr, netmask=bond_netmask)
        if bond_gw_ip_addr or bond_gw_ip_addr == '':
            data["gateway"]= bond_gw_ip_addr if bond_gw_ip_addr else None
        ## PUT
        put(endpoint,data)
        if error:
            print_with_timestamp(f"Error: Cannot set gateway IP. {error}")
        time.sleep(1)
        ## set node IP address back to bond_ip_addr
        node = bond_ip_addr
        endpoint = f"/network/interfaces/{second_nic_name}"
        data = dict(configuration="static", address=increment_3rd_ip_subnet(bond_ip_addr), netmask=bond_netmask)
        ## PUT
        put(endpoint,data)

    ## set default gateway interface
    if bond_gw_ip_addr:
        nic_name = first_nic_name
        set_default_gateway()


def node_id():
    ## GET
    product = get('/product')
    version = product["header"] if product else "1.0"
    serial_number = get('/product')["serial_number"]
    server_name = get('/product')["server_name"]
    host_name = get('/product')["host_name"]
    #### interfaces = get('/network/interfaces')
    eth0_mac_address = get_mac_address_of_given_nic('eth0')
    return version + serial_number + server_name + host_name + eth0_mac_address


def bind_cluster(bind_ip_addr):
    global action_message
    action_message = f"Sending Cluster Nodes Bind request to: {node}"

    if cluster_bind_set():
        print_with_timestamp("Cluster bind was already set")
        print_with_timestamp(f"Cluster bound: {node}<=>{bind_ip_addr}")
        return

    ## POST
    endpoint = '/cluster/nodes'
    data = dict(address=bind_ip_addr, password=bind_node_password)
    result = None
    result = post(endpoint, data)

    ## GET and check 
    if cluster_bind_set():
        print_with_timestamp(f"Cluster bound: {node}<=>{bind_ip_addr}")
    else:
        sys_exit_with_timestamp(f"Error: cluster bind {node}<=>{bind_ip_addr} failed")


def add_ring():
    global action_message
    action_message = f"Sending Add Ring request to: {node}"

    if not cluster_bind_set():
        print_with_timestamp('Cluster bind was not set yet')
        return

    rings = get_rings()
    number_of_rings = sum(1 for ring in rings if ring)
    if number_of_rings == 2 :
        print_with_timestamp('Cluster has already 2 rings')
        print_with_timestamp(f" First Ring: {rings[0][0]} {rings[0][1]}")
        print_with_timestamp(f"Second Ring: {rings[1][0]} {rings[1][1]}")
        return

    ##same code for "data" as in bing_cluster for "mirror_nics"
    cluster_nodes_addresses = get_cluster_nodes_addresses()
    cluster_nodes_ids = get_cluster_nodes_ids()
    ## first cluster node must be same as node from args
    if cluster_nodes_addresses[0] != node:
        cluster_nodes_addresses[0], cluster_nodes_addresses[1] =  \
        cluster_nodes_addresses[1], cluster_nodes_addresses[0]
    interfaces_items = []
    for i, cluster_node_address in enumerate(cluster_nodes_addresses):
        interfaces_items.append(dict(interface=ring_nics[i], node_id=cluster_nodes_ids[i]))
    data = dict(interfaces=interfaces_items)
    ## POST
    post('/cluster/rings', data)

    ## GET and check
    rings = get_rings()
    number_of_rings = sum(1 for ring in rings if ring)
    if number_of_rings == 2 :
        print_with_timestamp('The second cluster ring added successfully')
        print_with_timestamp(f" First Ring: {rings[0][0]} {rings[0][1]}")
        print_with_timestamp(f"Second Ring: {rings[1][0]} {rings[1][1]}")
    else:
        print_with_timestamp(f"Error: cluster add ring {ring_nics[0]}<=>{ring_nics[1]} failed")


def import_pool():
    '''
    '''
    global node
    global action_message
    pools_details = []

    def print_pools_available_for_import(pools_details):
        for pool_details in pools_details:
            print(f"\nPool available for IMPORT:\n  {pool_details['name']} Size: {bytes2human(pool_details['size'])} Status: {pool_details['health']}")
            for vdev in pool_details['vdevs']:
                vdev_name = vdev['name']
                vdev_name = 'single' if vdev_name.startswith('wwn-') else vdev_name
                print(f"    {vdev_name}")
                disk_name_to_replace = [ vdev_replacing['to_replace']['name'] for vdev_replacing in vdev['vdev_replacings']]
                for disk in vdev['disks']:
                    if disk['name'] in disk_name_to_replace:
                        continue
                    print(f"\t{disk['name']} {bytes2human(disk['size'])} Status: {disk['health']} SN: {disk['sn']}",end=' IOErors: ')
                    for stat in disk['iostats']:
                        print(f"{stat}: {disk['iostats'][stat]}",end=' ')
                    print()
                for vdev_replacing in vdev['vdev_replacings']:
                    print(f"\t{vdev_replacing['name']} Status: {vdev_replacing['health']}")
                    disk_to_replace = vdev_replacing['to_replace']
                    disk_replacing = vdev_replacing['replacement']
                    print(f"\t\t{disk_to_replace['name']} {bytes2human(disk_to_replace['size'])} (to-replace) SN: {disk_to_replace['sn']}")
                    print(f"\t\t{disk_replacing['name']} {bytes2human(disk_replacing['size'])} (replacing)  SN: {disk_replacing['sn']}")
        print()

    for node in nodes:
        action_message = f"Sending import pool request, Node: {node}, Pool: {pool_name}"
        pools_details = get('/pools/import')
        if pools_details:
            if pool_name:
                print_pools_available_for_import(pools_details)
                pool_id_list = [pool['id'] for pool in pools_details if pool_name in pool['name']]
                if pool_id_list:
                    pool_id = pool_id_list[0]
                else:
                    sys_exit_with_timestamp(f"Pool: {pool_name} is NOT available for import. Node: {node}")
                # exit if "--force" is missing if one of options provided: recovery_import or ignore_missing_write_log or ignore_unfinished_resilver
                if (recovery_import or ignore_missing_write_log or ignore_unfinished_resilver) and not force:
                    options_names = dict( recovery_import               = recovery_import,
                                          ignore_missing_write_log      = ignore_missing_write_log,
                                          ignore_unfinished_resilver    = ignore_unfinished_resilver)
                    options_names = ', '.join(option_name for option_name in options_names if options_names[option_name])
                    sys_exit_with_timestamp(f"{options_names} option requires --force option. Node: {node}")

                data = dict(id=pool_id, name=pool_name, force=force, recovery_import=recovery_import,
                        omit_missing=ignore_missing_write_log, ignore_unfinished_resilver=ignore_unfinished_resilver)
                result=post('/pools/import', data)
                if result and result['error']:
                    print_with_timestamp(f"{result['error']}. Node: {node}")
                if check_given_pool_name_in_current_node(pool_name):
                    print_with_timestamp(f"Pool: {pool_name} was imported on node: {node}")
                else:
                    print_with_timestamp(f"Pool: {pool_name} was NOT imported on node: {node}")
            else:
                print_with_timestamp(f"Searching for pools available for import. Node: {node}")
                print_pools_available_for_import(pools_details)
        else:
            sys_exit_with_timestamp(f"No pools available for import. Node: {node}")


def activate():
    ''' Online activation only
    '''
    global node
    global action_message
    for node in nodes:
        action_message = f"Sending Activation request, node: {node}"
        if online:
            post('/product/activation/activate-product')
            if error:
                print_with_timestamp(f"Error: Product activation failed. Node: {node}")
            else:
                print_with_timestamp(f"Product successfully activated. Node: {node}")
        else:
            print_with_timestamp(f"Error: Offline activation not implemented yet. Please use --online option. Node: {node}")


def info():
    ''' Time, Version, Serial number, Licence, Host name, DNS, GW, NICs, Pools
    '''
    global node
    global action_message

    for node in nodes:
        ## GET
        action_message = f"Reading setup details from: {node}"
        product_dict = get('/product')
        version = product_dict.get("header") if product_dict.get("header") else product_dict.get("version_name")
        serial_number = product_dict["serial_number"]
        serial_number = f"{serial_number} TRIAL" if serial_number.startswith('T') else serial_number
        storage_capacity = product_dict["storage_capacity"]     ## -1  means Unlimited
        storage_capacity = int(storage_capacity/pow(1024,4)) if storage_capacity > -1 else "Unlimited"
        server_name = product_dict["server_name"]
        host_name = product_dict["host_name"]
        current_system_time = get('/time')["timestamp"]
        system_time = datetime.datetime.fromtimestamp(current_system_time).strftime('%Y-%m-%d %H:%M:%S')
        time_zone = get('/time')["timezone"]
        ntp_status = get('/time')["daemon"]
        ntp_status = 'Yes' if ntp_status else 'No'
        product_key, = get('/licenses/product').keys()
        dns = get('/network/dns')["servers"]
        default_gateway = get('/network/default-gateway')["interface"]
        key_name={"strg":"Storage extension key",
                  "ha_rd":"Advanced HA Metro Cluster",
                  "ha_aa":"Standard HA Cluster"}

        extensions = get('/licenses/extensions') if not serial_number.startswith('T') else {}
        print_out_licence_keys = []
        for lic_key in extensions.keys():
            licence_type = key_name[ extensions[lic_key]['type']]
            licence_storage =  extensions[lic_key]['value']
            licence_storage = '' if licence_storage in 'None' else f" {licence_storage} TB"
            licence_description = '{:>30}:'.format( licence_type + licence_storage)
            print_out_licence_keys.append(f"{licence_description}\t{lic_key}")
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
        header = ( 'name', 'model', 'Gbit/s', 'mac')
        fields = ( 'name', 'model', 'speed',  'mac_address')
        print_interfaces_details(header,fields)
        header = ('name', 'type', 'address', 'netmask', 'gateway', 'duplex', 'negotiated_Gbit/s' )
        fields = ('name', 'type', 'address', 'netmask', 'gateway', 'duplex', 'negotiated_speed')
        print_interfaces_details(header,fields)

        ## PRINT POOLs DETAILS
        header = ('name', 'size_TiB', 'available_TiB', 'health', 'io-error-stats' )
        fields = ('name', 'size',     'available',     'health', 'iostats' )
        print_pools_details(header,fields)

        ## PRINT ZVOLs DETAILS
        header= ('san_volume',    'size', 'used', 'available',        'block', 'sync', 'compressratio', 'dedup' )
        fields= ('full_name', 'volsize', 'used', 'available', 'volblocksize', 'sync', 'compressratio', 'dedup' )
        print_volumes_details(header,fields)

        ## PRINT DATASETs DETAILS
        header= ('nas_volume', 'recordsize', 'sync', 'compression',  'dedup')
        fields= ('full_name', 'recordsize', 'sync', 'compression',  'dedup')
        print_nas_volumes_details(header,fields)

        ## PRINT NAS SNAPs DETAILS
        if all_snapshots:
            header= ('snapshot_(nas_volume)', 'referenced','written','age')
        else:
            header= ('the_most_recent_snapshot_(nas_volume)', 'referenced','written','age')
        fields= ('name', 'referenced','written','age')
        print_nas_snapshots_details(header,fields)

        ## PRINT SAN SNAPs DETAILS
        if all_snapshots:
            header= ('snapshot_(san_volume)', 'referenced','written','age')
        else:
            header= ('the_most_recent_snapshot_(san_volume)', 'referenced','written','age')
        fields= ('name', 'referenced','written','age')
        print_san_snapshots_details(header,fields)



def download_settings():
    ''' Download system settings and save into file in provided directory
    '''
    global node
    global action_message

    for node in nodes:
        action_message = f"Downloading settings from node: {node}"
        endpoint = '/settings/save'
        data = dict(system=True, storage=True)
        settings_file_name = post(endpoint,data)
        host_name = get_host_name()
        endpoint = '/settings/{}'.format(settings_file_name)
        # downnload settings
        content = get(endpoint)
        # delete just generated settings
        if not keep_settings:
            delete(endpoint)
        settings_file_name = '{}_{}'.format(host_name,settings_file_name)
        settings_file_name = os.path.join(directory,settings_file_name)
        with open(settings_file_name,'wb') as settings_file:
            settings_file.write(content)
            print_with_timestamp(f"Settings from node: {node} saved into: {settings_file_name}")

    
def list_snapshots():
    ''' Pools
    '''
    global node
    global action_message

    for node in nodes:
        ## GET
        snap_range_txt = 'Datasets ' if all_dataset_snapshots else 'zvol ' if all_zvol_snapshots else 'all ' if all_snapshots else ''
        action_message = f"Listing {snap_range_txt}snapshots from: {node}"
        host_name = get('/product')["host_name"]
        print(f"{'Host name':>30}:\t{host_name}")

        ## PRINT NAS SNAPs DETAILS
        if all_snapshots:
            header= ('snapshot_(nas_volume)', 'referenced','written','age')
        else:
            header= ('the_most_recent_snapshot_(nas_volume)', 'referenced','written','age')
        fields= ('name', 'referenced','written','age')
        if not all_zvol_snapshots:
            print_nas_snapshots_details(header,fields)

        ## PRINT SAN SNAPs DETAILS
        if all_snapshots:
            header= ('snapshot_(san_volume)', 'referenced','written','age')
        else:
            header= ('the_most_recent_snapshot_(san_volume)', 'referenced','written','age')
        fields= ('name', 'referenced','written','age')
        if not all_dataset_snapshots:
            print_san_snapshots_details(header,fields)


def get_pool_details(node, pool_name):
    pools = get('/pools')
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
    vdev_disks_num = int(disks_num / vdevs_num)
    return vdevs_num, data_groups_type, vdev_disks_num


def check_given_pool_name_in_current_node(pool_name):
    global node
    pools = None
    pools = get('/pools')
    if pools:
        pools_names = [ pool['name'] for pool in pools]
        if pool_name in pools_names:
            return True
    return False


def check_given_pool_name(ignore_error=None):
    ''' If given pool_name exist:
            return True
        If given pool_name does not exist:
            exit with ERROR     '''
    global node
    for node in nodes:
        pools = None
        pools = get('/pools')
        if pools:
            pools_names = [ pool['name'] for pool in pools]
            if pool_name in pools_names:
                return True
        else:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: {pool_name} does not exist on node: {node}")
            return False


def check_given_volume_name(ignore_error=None):
    ''' If given volume_name exist, return volume type:
            dataset (NAS-vol)
            volume (SAN-zvol)
        If given volume_name does not exist:
            sys.exit with ERROR     '''
    global node
    for node in nodes:
        ## GET /pools/<pool_name>/nas-volumes
        datasets = get(f"/pools/{pool_name}/nas-volumes")
        if datasets:
            datasets_names = [dataset['name'] for dataset in datasets]
            if volume_name in datasets_names:
                return 'dataset'
        ## GET /pools/<pool_name>/volumes
        volumes = get(f"/pools/{pool_name}/volumes")
        if volumes:
            volumes_names = [volume['name'] for volume in volumes]
            if volume_name in volumes_names:
                return 'volume'
        if ignore_error is None:
            sys_exit_with_timestamp(f"Error: {volume_name} does not exist on {pool_name} Node: {node}")
        else:
            return None


def jbods_listing(jbods):
    available_disks = count_available_disks(jbods)
    jbod = []
    if available_disks :
        for j,jbod in enumerate(jbods):
            print(f"\tjbod-{j}\n\t{line_separator}")
            if jbod :
                for d,disk in enumerate(jbod):
                    print("\t{:2d} {}\t{} GB\t{}\t{}".format(
                        d,disk[1],disk[0]/1024/1024/1024,disk[3], disk[2]))
        msg = f"\n\tTotal: {available_disks} available disks found"
    else:
        msg = "JBOD is empty. Please choose the JBOD number in order to read disks."
    return msg


def read_jbod(n):  #### to-do unused arg
    """
    read unused disks serial numbers in given JBOD n= 0,1,2,...
    """
    jbod = []
    global metro
    metro = False
    unused_disks = get('/disks/unused')
    for disk in unused_disks:
        if disk['origin'] in "iscsi":
            disk['origin'] = "remote"
            metro = True
        jbod.append((disk['size'],disk['name'],disk['id'],disk['origin']))
    return jbod


def zip_n(number_of_items_a_time,*args):
    ''' zip_n zips with given number of items a time
        (the orginal zip function take single item a time only)
    '''
    iter_args = map(iter,args)
    for _ in range(number_of_items_a_time):
####    yield tuple([next(item) for item in iter_args])
        yield tuple(next(item) for item in iter_args)


def create_pool(pool_name,vdev_type,jbods):
    
    if pool_name in get_pools_names():
        sys_exit_with_timestamp(f"Error: {pool_name} already exist on node {node}")

    vdev_type = vdev_type.replace('single','')
    print_with_timestamp("Creating pool. Please wait ...")

    ## CREATE
    endpoint = '/pools'
    data = dict(name = pool_name, vdevs = [dict(type=vdev_type, disks=vdev_disks) for vdev_disks in zip_n(number_of_disks_in_jbod, *jbods)])
    # P O S T
    post(endpoint,data)

    for _ in range(10):
        if check_given_pool_name(ignore_error=True):
            print_with_timestamp(f"New storage pool: {pool_name} created")
            break
        #else:
        time.sleep(10)
    else:
        sys_exit_with_timestamp(f"Error: Cannot create {pool_name}")


def add_read_cache_disk(pool_name,disk_wwn):
    if pool_name not in get_pools_names():
        sys_exit_with_timestamp(f"Error: {pool_name} not present on node {node}")

    vdev_type = 'cache'
    print_with_timestamp("Adding read cache. Please wait ...")

    # POST/pools/<string:poolname>/vdevs
    endpoint = f'/pools/{pool_name}/vdevs'
    data = dict(name = pool_name, vdevs = [dict(type=vdev_type, disks=[disk_wwn])])
    # P O S T
    ret =post(endpoint,data)
    if ret == '' and error == 0:
        print_with_timestamp(f"New read cache disk addded to pool: {pool_name}")
    else:
        print_with_timestamp(f"Error while adding cache disk to pool: {pool_name}")


def create_volume(vol_type):
    global sync
    ## POST
    quota_text, reservation_text = ('','')
    if vol_type == 'volume':
        endpoint = f"/pools/{pool_name}/volumes"
        sync = sync if sync else 'always'      # set default sync for zvol
        data = dict(name=volume_name, sparse=sparse, size=size, blocksize=blocksize, properties=properties)
        post(endpoint,data)

    if vol_type == 'dataset':
        endpoint = f"/pools/{pool_name}/nas-volumes"
        sync = sync if sync else 'standard'    # set default sync for dataset
        data = dict(name=volume_name, recordsize=int(recordsize), sync=sync, logbias=logbias, compression=compression, dedup=dedup, quota=quota, reservation=reservation)
        # P O S T
        post(endpoint,data)
        quota_text = "Quota set to: {}, ".format(bytes2human(quota) if quota else '') if quota else ''
        reservation_text = "Reservation set to: {}.".format(bytes2human(reservation) if reservation else '') if reservation else ''
    if error:
        print_with_timestamp(f"Error: {error}")
    else:
        print_with_timestamp(f"{pool_name}/{volume_name}: Write cache logging (sync) set to: {sync}. {quota_text}{reservation_text}")


def modify_volume(vol_type):
    global action_message
    action_message = f"Sending modify volume request to: {node}"
    print_with_timestamp(action_message)
    quota_text, reservation_text = ('','')
    ## PUT /pools/<string:poolname>/volumes/<string:volumename>/properties
    if vol_type == 'volume':
        endpoint = f"/pools/{pool_name}/volumes/{volume_name}/properties"
        data=dict(property_name='sync',property_value=sync)
        if new_size:
            current_size = get_san_volume_size()
            #print(new_size,current_size)
            if int(new_size) < int(current_size):
                print_with_timestamp(f"Error: {pool_name}/{volume_name} Provided new size: \
                        {bytes2human(new_size)} is smaller then current size:{bytes2human(current_size)}")
                return
            if int(new_size) == int(current_size):
                print_with_timestamp(f"Error: {pool_name}/{volume_name} Provided new size: \
                        {bytes2human(new_size)} is euqal to current size:{bytes2human(current_size)}")
                return
            if int(new_size) > 2* int(current_size):
                print_with_timestamp(f"Error: {pool_name}/{volume_name} Provided new size: \
                        {bytes2human(new_size)} cannot be bigger than double of current size:{bytes2human(current_size)}")
                return
            data=dict(property_name='volsize',property_value=new_size)
        result=put(endpoint,data)
    if vol_type == 'dataset':
        endpoint = f"/pools/{pool_name}/nas-volumes/{volume_name}"
        data=dict(sync=sync, quota=quota, reservation=reservation)
        result = put(endpoint,data)
        quota_text = "Quota set to: {}, ".format(bytes2human(quota) if quota else '') if quota else ''
        reservation_text = "Reservation set to: {}.".format(bytes2human(reservation) if reservation else '') if reservation else ''
    if result and (result['error'] is None):
        if new_size:
            print_with_timestamp(f"{pool_name}/{volume_name}: New volume size set to: {bytes2human(new_size)}")
        else:
            print_with_timestamp(f"{pool_name}/{volume_name}: Write cache logging (sync) set to: {sync}. {quota_text}{reservation_text}")
    else:
        print_with_timestamp(f"Error: {pool_name}/{volume_name} Modify volume request failed")


def enable_smb_nfs():
    for service in storage_type:
        endpoint = f"/services/{service.lower()}"
        enabled = get(endpoint)['enabled']
        if not enabled:
            put(endpoint,dict(enabled=True))


def create_storage_resource():
    global node
    global volume_name
    global target_name
    global auto_target_name ## used by function create_target()
    global share_name
    global quantity
    global action_message
    action_message = f"Sending create storage resource request to: {node}"
    initialize_pool_based_consecutive_number_generator()
    ####
    active_node = get_active_cluster_node_address_of_given_pool(pool_name)

    if not active_node:
        sys_exit_with_timestamp(f"Error: {pool_name} does not exist on node: {node}")
    else:
        node = active_node

    generate_automatic_volume_name = ( volume_name == 'auto' )
    generate_automatic_target_name = ( target_name == 'auto' )
    generate_automatic_share_name  = ( share_name  == 'auto' )
    ##
    while quantity:
        _zvols_per_target = zvols_per_target
        while _zvols_per_target:
            ## ISCSI
            if 'ISCSI' in storage_type:
                _target_name,_volume_name = generate_iscsi_target_and_volume_name(pool_name)
                if generate_automatic_target_name:
                    target_name = _target_name
                else:
                    ## create target with provided target name
                    target_name = f"iqn.{time.strftime('%Y-%m')}:{target_name}"
                    ## modify target name with provided cluster name
                    if cluster_name:
                        ## iqn.yyyy.mm: included
                        if re.match('iqn.[0-9]{4}-[0-9]{2}:', target_name):
                            split = target_name.split(':',1)
                            split[1] = split[1].replace(':','.')
                            split.insert(1, f":{cluster_name}.")
                            target_name = ''.join(split)
                        else:
                            ## iqn.yyyy.mm: NOT included
                            target_name = f"iqn.{time.strftime('%Y-%m')}:{cluster_name}.{target_name}"
                if generate_automatic_volume_name:
                    volume_name = _volume_name
            ## NAS
            if ('SMB' in storage_type) or ('NFS' in storage_type):
                _share_name,_volume_name = generate_share_and_volume_name(pool_name)
                if generate_automatic_share_name:
                    share_name = _share_name
                else:
                    ## modify share name with provided cluster name
                    if cluster_name:
                        share_name = f"{cluster_name.lower()}-{share_name.lower()}"
                if generate_automatic_volume_name:
                    volume_name = _volume_name

            # ignore given quantity if share name or volume name provided in command line
            if not (generate_automatic_volume_name and
                    generate_automatic_share_name):
                quantity = 1

            ## volume or dataset
            create_volume(storage_volume_type)
            if 'ISCSI' in storage_type:
                ## target name must be lower case
                auto_target_name = target_name.lower()
                if _zvols_per_target == zvols_per_target:
                    create_target(ignore_error=True)
                ## attach
                attach_volume_to_target(ignore_error=True)
            if 'SMB' in storage_type or 'NFS' in storage_type:
                create_share()
                enable_smb_nfs()
            _zvols_per_target -= 1
        quantity -= 1


def create_snapshot(vol_type,ignore_error=None):
    global node
    for node in nodes:
        ## Create snapshot of NAS vol
        if vol_type == 'dataset':
            endpoint = f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots"
            ## Auto-Snapshot-Name
            data = dict(name=auto_snap_name)            
        ## Create snapshot of SAN zvol
        if vol_type == 'volume':
            endpoint = f"/pools/{pool_name}/volumes/{volume_name}/snapshots"
            ## Auto-Snapshot-Name
            data = dict(snapshot_name=auto_snap_name)   

        ## POST
        post(endpoint, data)
        print_with_timestamp(f"Snapshot of {pool_name}/{volume_name} has been successfully created")
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: Target: {auto_target_name} creation on node: {node} failed")


def create_clone(vol_type, ignore_error=None):
    global node
    for node in nodes:
        global clone_name
        ## dataset(vol) clone and volume(zvol) clone names can be the same as belong to different resources
        ## Create clone of NAS vol = dataset
        if vol_type == 'dataset':
            endpoint = f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{auto_snap_name}/clones"
            ## vol
            clone_name = volume_name + time_stamp_clone_syntax() + auto_vol_clone_name
            data = dict(name=clone_name, primarycache=primarycache, secondarycache=secondarycache)
        ## Create clone of SAN zvol = volume
        if vol_type == 'volume':
            endpoint = f"/pools/{pool_name}/volumes/{volume_name}/clone"
            clone_name = volume_name + time_stamp_clone_syntax() + auto_zvol_clone_name
            data = dict(name=clone_name, snapshot=auto_snap_name, properties=properties)


        ## POST
        post(endpoint, data)
        print_with_timestamp(f"Clone of {pool_name}/{volume_name}/{auto_snap_name} has been successfully created")
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: Clone: {clone_name} creation on node: {node} failed")


def delete_snapshot_and_clone(vol_type, ignore_error=None):
    global node
    for node in nodes:
        ## Delete snapshot. It auto-deletes clone and share of NAS vol
        if vol_type == 'dataset':
            endpoint = f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{auto_snap_name}"
            delete(endpoint)
            if error:
                print_with_timestamp(f"Snapshot delete error: {auto_snap_name} does not exist on node: {node}")
            else:
                print_with_timestamp(f"Share, clone and snapshot of {pool_name}/{volume_name} have been successfully deleted")
            print()
        ## Delete snapshot and clone of SAN zvol (using recursively options)
        if vol_type == 'volume':
            endpoint = f"/pools/{pool_name}/volumes/{volume_name}/snapshots/{auto_snap_name}"
            data = dict(recursively_children=True, recursively_dependents=True, force_umount=True)
            delete(endpoint,data)
            if error:
                print_with_timestamp(f"Snapshot delete error: {auto_snap_name} does not exist on node: {node}")
            else:
                print_with_timestamp(f"Clone and snapshot of {pool_name}/{volume_name} have been successfully deleted")
            print()


def create_clone_of_existing_snapshot(vol_type, ignore_error=None):
    global node
    for node in nodes:
        global clone_name
        ## dataset(vol) clone and volume(zvol) clone names can be the same as belong to different resources
        ## Create clone of NAS vol = dataset
        if vol_type == 'dataset':
            endpoint = f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{snapshot_name}/clones"
            ## vol
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            data = dict(name=clone_name, snapshot=snapshot_name)
        ## Create clone of SAN zvol = volume
        if vol_type == 'volume':
            endpoint = f"/pools/{pool_name}/volumes/{volume_name}/clone"
            ## zvol
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            data = dict(name=clone_name, snapshot=snapshot_name)

        ## POST
        post(endpoint,data)
        print_with_timestamp(f"Clone of {pool_name}/{volume_name}/{snapshot_name} has been successfully created")
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: Clone: {clone_name} creation on node: {node} failed")


def delete_clone_existing_snapshot(vol_type, ignore_error=None):
    global node
    for node in nodes:
        ## Delete existing clone and share of NAS vol
        if vol_type == 'dataset':
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            endpoint = f"/pools/{pool_name}/nas-volumes/{volume_name}/snapshots/{snapshot_name}/clones/{vol_clone_name}"
            data = dict(name=clone_name)
            delete(endpoint,data)
            if error:
                print_with_timestamp(f"Clone delete error: {clone_name} does not exist on node: {node}")
            else:
                print_with_timestamp(f"Share and clone of {pool_name}/{volume_name}/{snapshot_name} have been successfully deleted")
            print()
        ## Delete existing clone of SAN zvol
        if vol_type == 'volume':
            clone_name = 'Clone_of_' + volume_name + '_' + snapshot_name
            endpoint = f"/pools/{pool_name}/volumes/{volume_name}/snapshots/{snapshot_name}/clones/{clone_name}"
            data = dict(name=clone_name)
            delete(endpoint,data)
            if error:
                print_with_timestamp(f"Clone delete error: {clone_name} does not exist on node: {node}")
            else:
                print_with_timestamp(f"Clone of {pool_name}/{volume_name}/{snapshot_name} has been successfully deleted")
            print()


def create_target(ignore_error=None):
    global node
    for node in nodes:

        targets = get(f"/pools/{pool_name}/san/iscsi/targets")
        if targets and target_name in [target['name']for target in targets]:
            print_with_timestamp(f"Info: Target: {auto_target_name} already exist on node: {node}")

        else:
            endpoint = f"/pools/{pool_name}/san/iscsi/targets"
            ## Auto-Target-Name
            data = dict(name=auto_target_name)

            ## POST
            target_object = post(endpoint, data)
            if error:
                if ignore_error is None:
                    sys_exit_with_timestamp(f"Error: Target: {auto_target_name} creation on node: {node} failed")
                else:
                    print_with_timestamp(f"Error: Target: {auto_target_name} creation on node: {node} failed")


def attach_volume_to_target(ignore_error=None):
    global node
    for node in nodes:
        endpoint = f"/pools/{pool_name}/san/iscsi/targets/{auto_target_name}/luns"
        data = dict(name=volume_name, mode='wt', device_handler='vdisk_blockio')
        ## POST
        post(endpoint,data)
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: Cannot attach target: {auto_target_name} to {volume_name} on node: {node}")

        print_with_timestamp(f"Volume: {pool_name}/{volume_name} has been successfully attached to target")
        print(f"\n\tTarget:\t{auto_target_name}")
        print(f"\tVolume:\t{pool_name}/{volume_name}\n")


def attach_volume_to_iscsi_target(ignore_error=None):
    global node
    for node in nodes:
        endpoint = f"/pools/{pool_name}/san/iscsi/targets/{target_name}/luns"
        data = dict(name=volume_name, mode='wt', device_handler='vdisk_blockio')
        ## POST
        post(endpoint,data)
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: Cannot attach target: {target_name} to {volume_name} on node: {node}")

        print_with_timestamp(f"Volume: {pool_name}/{volume_name} has been successfully attached to target")
        print(f"\n\tTarget:\t{target_name}")
        print(f"\tVolume:\t{pool_name}/{volume_name}\n")


def detach_volume_from_iscsi_target(ignore_error=None):
    global node
    for node in nodes:
        # DELETE /pools/<string:poolname>/san/iscsi/targets/<string:target_name>/luns/<string:zvol>
        endpoint = f"/pools/{pool_name}/san/iscsi/targets/{target_name}/luns/{volume_name}"
        ## DELETE
        delete(endpoint)
        if error:
            if ignore_error is None:
                print_with_timestamp(f"{error}")
                sys_exit_with_timestamp(f"Error: Cannot detach volume: {volume_name} from {target_name} on node: {node}")

        print_with_timestamp(f"Volume: {pool_name}/{volume_name} has been successfully detached from target {target_name}")


def detach_disk_from_pool(ignore_error=None):

    global node
    global action_message
    action_message = f"Sending disk detach from pool request to: {node}"

    for node in nodes:
        # POST /pools/POOL_NAME/disks/DISK_ID/detach
        endpoint = f"/pools/{pool_name}/disks/{disk_wwn}/detach"
        ## POST
        post(endpoint,None)
        if error:
            if ignore_error is None:
                print_with_timestamp(f"{error}")
                sys_exit_with_timestamp(f"Error: Cannot detach disk: {disk_wwn} from {pool_name} on node: {node}")

        print_with_timestamp(f"Disk: {disk_wwn} has been successfully detached from pool {pool_name}")


def remove_disk_from_pool(ignore_error=None):

    global node
    global action_message
    action_message = f"Sending remove (delete) disk from pool request to: {node}"

    for node in nodes:
        # DELETE/pools/<string:poolname>/disks/<string:disk_id>
        endpoint = f"/pools/{pool_name}/disks/{disk_wwn}"
        ## DELETE
        delete(endpoint,None)
        if error:
            if ignore_error is None:
                print_with_timestamp(f"{error}")
                sys_exit_with_timestamp(f"Error: Cannot remove disk: {disk_wwn} from {pool_name} on node: {node}")

        print_with_timestamp(f"Disk: {disk_wwn} has been successfully removed from pool {pool_name}")


def attach_clone_to_target(ignore_error=None):
    global node
    for node in nodes:
        endpoint = f"/pools/{pool_name}/san/iscsi/targets/{auto_target_name}/luns"
        data = dict(name=clone_name)
        ## POST
        post(endpoint,data)
        if error:
            if ignore_error is None:
                sys_exit_with_timestamp(f"Error: Cannot attach target: {auto_target_name} to {clone_name} on node: {node}")

        print_with_timestamp(f"Clone: {clone_name} has been successfully attached to target")
        print(f"\n\tTarget:\t{auto_target_name}")
        print(f"\tClone:\t{clone_name}\n")


def create_share_for_auto_clone(ignore_error=None):
    global node
    for node in nodes:
        endpoint = '/shares'
        data = dict(name = share_name,
                    path = f"{pool_name}/{clone_name}",
                    smb = dict(enabled=True, visible=visible))   ### add visible=False
        ## POST
        post(endpoint,data)
        if error:
            sys_exit_with_timestamp(f"Error: Share: {share_name} creation on node: {node} failed")

        print_with_timestamp(f"Share for {pool_name}/{clone_name} has been successfully created")
        print(f"\n\tShare:\t\\\\{node}\{share_name}")
        print(f"\tClone:\t{pool_name}/{clone_name}\n")


def create_share():
    global node
    for node in nodes:

        shares = get('/shares')
        if shares and shares['entries'] and share_name in [share['name'] for share in shares['entries']]:
            print_with_timestamp(f"Info: Share: {share_name} already exist on node: {node}")
        else:

            endpoint = '/shares'
            data = dict(name=share_name,
                    path= f"{pool_name}/{volume_name}",
                    smb=dict(enabled=bool('SMB' in storage_type)),
                    nfs=dict(enabled=bool('NFS' in storage_type)))
            ## P O S T
            post(endpoint,data)
            if error:
                sys_exit_with_timestamp(f"Error: Share: {share_name} creation on node: {node} failed")

            print_with_timestamp(f"Share for {pool_name}/{volume_name} has been successfully created")
            print( f"\n\tShare:\t\\\\{node}\{share_name}" )
            print( f"\tDataset:\t{pool_name}/{volume_name}\n" )


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
    if not jbods:
        sys_exit_with_timestamp('Error: No disks available')
    return [ bool(d) for jbod in jbods for d in jbod ].count(True)


def merge_sublists(list_of_lists):
    """
    merge list of sub_lists into single list
    """
    # return [ item for sub_list in list_of_lists for item in sub_list]
    return sum(list_of_lists,[])


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
    ## split into 4 JBODs for 4-way mirror (2 local and 2 remote)
    jbods_4way_mirrors =[]
    for i in range(4):
        jbods_4way_mirrors.append(jbods_2way_mirrors[i%2][int(i/2)::2])
    return jbods_4way_mirrors


def remove_disks(jbods):
    available_disks = count_available_disks(jbods)
    if available_disks:
        jbods_disks_size = [ [disk[0] for disk in jbod]  for jbod in jbods ]
        all_disks_size = merge_sublists( jbods_disks_size ) ## convert lists of JBODs to single disks list
        average_disk_size = float(sum(all_disks_size)) / len(all_disks_size)
        if disk_size_range:
            ## do not remove if drives are in provided range
            return [[disk for disk in jbod if min(disk_size_range) <= disk[0] <= max(disk_size_range)] for jbod in jbods]

        ## do not remove if all drives are same size
        return [[disk for disk in jbod if disk[0] >= (average_disk_size - disk_size_tolerance)] for jbod in jbods]
    return jbods

def check_all_disks_size_equal_or_in_provided_range(jbods):
    jbods_disks_size  = [ [disk[0] for disk in jbod]  for jbod in jbods ]
    ## convert lists of JBODs to single disks list
    all_disks_size = merge_sublists( jbods_disks_size )
    if disk_size_range:
        in_range = max(all_disks_size) <= max(disk_size_range) and min(all_disks_size) >= min(disk_size_range)
        return bool(in_range)

    within_tolerance = (max(all_disks_size) - min(all_disks_size)) <= disk_size_tolerance

    if within_tolerance:
        return True

    max_disks_size, min_disks_size = map(bytes2human,(max(all_disks_size),min(all_disks_size)))
    print_with_timestamp(f"Error:\tAvaialable disks size (Max: {max_disks_size} Min: {min_disks_size}) \
                           \n\t\t\t\tare not within provided size tolerance: {disk_size_tolerance}")
    return False


def user_choice():

    while 1:
        try :
            choice = input('\tEnter your choice: ').upper()
            if choice in '':
                return "L"  ## treat pressed enter as "L"
            if choice in '0123456789LCQ':
                return choice
            print('\tInvalid choice')
        except KeyboardInterrupt:
            sys_exit( f"Interrupted{' '*13}")


def read_jbods_and_create_pool(choice='0'):

    global vdev_type,action_message

    action_message = f"Sending Create Pool request to: {node}"

    jbods = [[] for i in range(jbods_num)]
    given_jbods_num = jbods_num
    empty_jbod = True
    msg = None

    def run_menu(msg):
        print( f"""
        {line_separator}
         CREATE POOL MENU
        {line_separator}
         {",".join(map(str,range(given_jbods_num)))}\t: Read single Powered-ON JBOD disks (first JBOD = 0)
         L\t: List JBODs disks
         C\t: Create pool & quit
         Q\t: Quit
        {line_separator}""" )
        print( f"\tGiven JBODs number: {given_jbods_num}" )
        print( f"\tPool to be created:\t{pool_name}: {vdevs_num}*{vdev_type}[{vdev_disks_num} disk]" )
        if msg:
            print( f"\n\t{msg}\n\t" )
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
            msg = f"\n\tTotal: {available_disks} available disks found\n\tTotal: {vdev_disks_num*vdevs_num} disks required to create the pool"
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

            ''' THIS IS FOR MULTI-JBOD TESTgS ONLY
            empty_jbod=False
            jbods = [[(17179869184L, u'sdk', u'wwn-0x6000c2900d9d4b8ad978e58cbeb69ec0', u'local'),
                          (32212254720L, u'sdc', u'wwn-0x6000c2986862e791e2f6a3b3caf812ea', u'local'),
                          (17179869184L, u'sdam', u'wwn-0x6000c29dc9c757892bc52737dfbb514f', u'local'),
                          (17179869184L, u'sdo', u'wwn-0x6000c29bfa933b7440799713fada1fff', u'local'),
                          (17179869184L, u'sdac', u'wwn-0x6000c29f7112633f908c03f6ef8eefe4', u'local'),
                          (17179869184L, u'sdbe', u'wwn-0x6000c29854805e7bbac41c4ce3ffb8e8', u'local'),
                          (21474836480L, u'sdd', u'wwn-0x6000c29de582985eefa78d632794cc4b', u'local'),
                          (17179869184L, u'sdaw', u'wwn-0x6000c299210e5602e8403dea289a5928', u'local'),
                          (17179869184L, u'sdau', u'wwn-0x6000c29f717e083f8d6be2eb39f8e74f', u'local'),
                          (17179869184L, u'sdh', u'wwn-0x6000c290dba4fba83d8d884c9fb9842c', u'local'),
                          (21474836480L, u'sde', u'wwn-0x6000c293f13d726d45d4f4326f64355f', u'local'),
                          (17179869184L, u'sdx', u'wwn-0x6000c29468b1e4cd493a19bdcfcce6f2', u'local'),
                          (17179869184L, u'sdl', u'wwn-0x6000c296268358c7c8147a0903b5a5fb', u'local'),
                          (17179869184L, u'sdbg', u'wwn-0x6000c29a0bee64560f0feee77e63521e', u'local'),
                          (17179869184L, u'sdbb', u'wwn-0x6000c29781d7c00dbac4ee4eed25d912', u'local'),
                          (17179869184L, u'sdaq', u'wwn-0x6000c29b587e6f90be9b0f1b8c67005e', u'local'),
                          (17179869184L, u'sdy', u'wwn-0x6000c296df02bc1596cbd18ab662d849', u'local'),
                          (17179869184L, u'sdax', u'wwn-0x6000c29ec4950ff52bf3e64272d6fd9c', u'local'),
                          (17179869184L, u'sdao', u'wwn-0x6000c2971e1450958e706560f48dec0a', u'local'),
                          (17179869184L, u'sdak', u'wwn-0x6000c29cb591895a94331622c1c64939', u'local'),
                          (17179869184L, u'sds', u'wwn-0x6000c29d6eb8c1e890be8e1b686ac372', u'local'),
                          (17179869184L, u'sdaf', u'wwn-0x6000c296596cb4ee2e734309b54bcff8', u'local'),
                          (17179869184L, u'sdbf', u'wwn-0x6000c299f603587a5d830d4c7b4dd68b', u'local'),
                          (17179869184L, u'sdav', u'wwn-0x6000c29b3580f052ecc3e30873514d72', u'local'),
                          (17179869184L, u'sdal', u'wwn-0x6000c29b78b864c3b5b7c70b2fe9eeef', u'local'),
                          (17179869184L, u'sdbh', u'wwn-0x6000c2909e9e2aaad13f7704cc002d47', u'local'),
                          (17179869184L, u'sdah', u'wwn-0x6000c2989a0a32dad5d40ba5776f8df4', u'local'),
                          (17179869184L, u'sdat', u'wwn-0x6000c2995e16830ce57a0d9413daf7d0', u'local'),
                          (17179869184L, u'sdv', u'wwn-0x6000c29f4d2c68c01e3b6a455a162201', u'local')   ],
                         [(17179869184L, u'sdbd', u'wwn-0x6000c29f00824e15649b0351963dc27c', u'local'),
                          (17179869184L, u'sdu', u'wwn-0x6000c29007b2ae35b63cc05047013ef6', u'local'),
                          (17179869184L, u'sdar', u'wwn-0x6000c29ddc7b37aed467d5a3cf33daf4', u'local'),
                          (17179869184L, u'sdap', u'wwn-0x6000c292ce0a319183e7fb9c40fc19c3', u'local'),
                          (17179869184L, u'sdbc', u'wwn-0x6000c2915460fc60ccd67d16fd0d8ef4', u'local'),
                          (17179869184L, u'sdaz', u'wwn-0x6000c29b56b450debdeb7d1209059062', u'local'),
                          (17179869184L, u'sdm', u'wwn-0x6000c299e4c638aa23752db9445d4a36', u'local'),
                          (21474836480L, u'sdb', u'wwn-0x6000c29a7c6d0b97a1c4cf1b203de7ed', u'local'),
                          (17179869184L, u'sdae', u'wwn-0x6000c2993ef8671f5807b30bdf4a5413', u'local'),
                          (17179869184L, u'sdag', u'wwn-0x6000c29e083d0608e7019404fde4e9cd', u'local'),
                          (17179869184L, u'sdaj', u'wwn-0x6000c2926bee6c46e4fca43e00e5205b', u'local'),
                          (17179869184L, u'sdp', u'wwn-0x6000c29db7121eaa7d4ae894003d2bbc', u'local'),
                          (17179869184L, u'sdaa', u'wwn-0x6000c29d79893c1ef84a9908b56c2d03', u'local'),
                          (17179869184L, u'sdf', u'wwn-0x6000c29328576616cffc6ab83548f72a', u'local'),
                          (17179869184L, u'sdi', u'wwn-0x6000c29f188cd60fb61e94ccbf5b9866', u'local'),
                          (17179869184L, u'sdan', u'wwn-0x6000c2953556855f7b7fd44c1c9cf24a', u'local'),
                          (17179869184L, u'sdq', u'wwn-0x6000c29d09265ac946b7f356d416bdb9', u'local'),
                          (17179869184L, u'sdw', u'wwn-0x6000c290e44574da1c5dea8c26d37ad3', u'local'),
                          (17179869184L, u'sdab', u'wwn-0x6000c29181403197752d3e5770108536', u'local'),
                          (17179869184L, u'sdr', u'wwn-0x6000c292626888dd90670565df3b4140', u'local'),
                          (17179869184L, u'sdz', u'wwn-0x6000c29c2620ed48313cf2160f38d830', u'local'),
                          (17179869184L, u'sdai', u'wwn-0x6000c293a72aa3e73c22fa57294180ab', u'local'),
                          (17179869184L, u'sdad', u'wwn-0x6000c2998e7b43c2f6d88c15f595c71a', u'local'),
                          (17179869184L, u'sdj', u'wwn-0x6000c2903eab1bd60c4e88ccde16e2f2', u'local'),
                          (17179869184L, u'sdt', u'wwn-0x6000c29bc36b9cc348dc762c32396315', u'local'),
                          (17179869184L, u'sdba', u'wwn-0x6000c299e9d4fcb43bdb5eecb7cb0a55', u'local'),
                          (17179869184L, u'sday', u'wwn-0x6000c291c86b55a3a398cca93e624f69', u'local'),
                          (17179869184L, u'sdn', u'wwn-0x6000c29ad0d25a4badcc0d0fd90cb36f', u'local'),
                          (17179869184L, u'sdas', u'wwn-0x6000c29b4ca5b5bc4af7e354e1e50f28', u'local'),
                          (17179869184L, u'sdg', u'wwn-0x6000c2955f680ea82af988fd222ce8d9', u'local')]]'''
        elif choice in "C":
            if not menu:
                jbods = remove_disks(jbods)
                #msg = jbods_listing(jbods)
            ## create pool
            if empty_jbod:
                msg = 'At least one JBOD is empty. Please press 0,1,... in order to read JBODs disks.'
            else:
                if check_all_disks_size_equal_or_in_provided_range(jbods) is False:
                    msg = 'Disks with different size present. Please press "r" in order to remove smaller disks.'
                else:

                    jbods_id_only = convert_jbods_to_id_only(jbods)
                    required_disks_num = vdevs_num * vdev_disks_num
                    available_disks = count_available_disks(jbods_id_only)
                    if available_disks < required_disks_num:
                        msg =f"Error: {pool_name}: {vdevs_num}*{vdev_type}[{vdev_disks_num} disk]\
                             requires {required_disks_num} disks. {available_disks} disks available.\n"
                    else:
                        if jbods_num == 1 and not metro:
                            ## transpose single JBOD for JBODs [number_of_disks_in_vdev * number_of_vdevs]
                            jbods_id_only = list(zip(*[iter(jbods_id_only[0])] * vdevs_num ))
                            jbods_id_only = jbods_id_only[: vdev_disks_num]
                            create_pool(pool_name,vdev_type, jbods_id_only)
                        else:
                            ## limit to given vdevs_num & number_of_disks_in_jbod
                            ## number_of_disks_in_jbod = 1   : if single disk per jbod
                            ## number_of_disks_in_jbod = 2   : this is for raidz2 with 2 disk per jbod
                            ## number_of_disks_in_jbod = 3   : this is for raidz3 with 3 disk per jbod
                            jbods_id_only = [jbod[:vdevs_num * number_of_disks_in_jbod] for jbod in jbods_id_only]
                            create_pool(pool_name,vdev_type,jbods_id_only)
                        ##### reset
                        jbods = [[] for i in range(jbods_num)]
            ##
            break
        ## exit
        elif choice in "Q":
            break
        ## end-of-while loop
    ## display pool details
    if pool_name in get_pools_names():
        #print("\n\tNode {} {}: {}*{}[{} disk]".format(node, pool_name, *get_pool_details(node, pool_name)))
        vdevs_count, vdev_type, disks_per_vdev = get_pool_details(node, pool_name)
        print(f"\n\tNode {node} {pool_name}: {vdevs_count}*{vdev_type}[{disks_per_vdev} disk]")
        


def command_processor() :

    print()

    if action == 'clone':
        args_count = count_provided_args( pool_name, volume_name )   ## if both provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: clone command expects 2 arguments (pool, volume), {args_count} provided")
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )
        create_new_backup_clone( vol_type )

    elif action == 'clone_existing_snapshot':
        args_count = count_provided_args( pool_name, volume_name, snapshot_name )   ## if all provided (not None), args_count must be equal 3
        if args_count < 3:
            sys_exit_with_timestamp(f"Error: clone_existing_snapshot command expects 3 arguments (pool, volume, snapshot), {args_count} provided")
        vol_type = check_given_volume_name()
        delete_clone_existing_snapshot( vol_type, ignore_error=True )
        create_existing_backup_clone( vol_type )

    elif action == 'delete_clone':
        args_count = count_provided_args( pool_name, volume_name )   ## if both provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: delete_clone command expects 2 arguments (pool, volume), {args_count} provided")
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )

    elif action == 'delete_clones':
        args_count = count_provided_args( pool_name, volume_name )   ## if both provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: delete_clones command expects 2 arguments (pool, volume), {args_count} provided")
        vol_type = check_given_volume_name()
        delete_clones( vol_type )

    elif action == 'delete_snapshots':
        args_count = count_provided_args( pool_name, volume_name )   ## if both provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: delete_snapshots command expects 2 arguments (pool, volume), {args_count} provided")
        vol_type = check_given_volume_name()
        delete_snapshots( vol_type )

    elif action == 'delete_clone_existing_snapshot':
        args_count = count_provided_args( pool_name, volume_name, snapshot_name )   ## if all provided (not None), args_count must be equal 3
        if args_count < 3:
            sys_exit_with_timestamp(f"Error: delete_clone_existing_snapshot command expects 3 arguments (pool, volume, snapshot), {args_count} provided")
        vol_type = check_given_volume_name()
        delete_clone_existing_snapshot( vol_type, ignore_error=True )

    elif action == 'create_pool':
        ##args_count = count_provided_args( pool_name )
        read_jbods_and_create_pool()

    elif action == 'export':
        args_count = count_provided_args( pool_name )   ## if all provided (not None), args_count must be equal 1
        if args_count < 1:
            sys_exit_with_timestamp(f"Error: export command expects pool name), {args_count} provided")
        export()

    elif action == 'scrub':
        scrub()

    elif action == 'set_scrub_scheduler':
        set_scrub_scheduler()

    elif action == 'create_storage_resource':
        if zvols_per_target> 15:
            sys_exit_with_timestamp('Error: the zvols_per_target must be in range 1..15')

        args_count = count_provided_args( pool_name, volume_name, storage_type, size, sparse )   ## if all provided (not None), args_count must be equal 3
        if args_count < 5:
            sys_exit_with_timestamp(f"Error: create_storage_resource command expects (pool, volume, storage_type), {args_count} provided")
        if 'iqn' in target_name:
            if storage_volume_type != 'volume':
                sys_exit_with_timestamp('Error: inconsistent options.')
        create_storage_resource()

    elif action == 'attach_volume_to_iscsi_target':
        args_count = count_provided_args( pool_name, volume_name, target_name )   ## if all provided (not None), args_count must be equal 3
        if args_count < 3:
            sys_exit_with_timestamp(f"Error: attach command expects (pool, volume, target_name), {args_count} provided")
        attach_volume_to_iscsi_target()

    elif action == 'detach_volume_from_iscsi_target':
        args_count = count_provided_args( pool_name, volume_name, target_name )   ## if all provided (not None), args_count must be equal 3
        if args_count < 3:
            sys_exit_with_timestamp(f"Error: detach command expects (pool, volume, target_name), {args_count} provided")
        detach_volume_from_iscsi_target()

    elif action == 'detach_disk_from_pool':
        args_count = count_provided_args( pool_name, disk_wwn)   ## if all provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: detach command expects (pool, disk_wwn), {args_count} provided")
        detach_disk_from_pool()

    elif action == 'remove_disk_from_pool':
        args_count = count_provided_args( pool_name, disk_wwn)   ## if all provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: remove disk command expects (pool, disk_wwn), {args_count} provided")
        remove_disk_from_pool()

    elif action == 'add_read_cache_disk':
        args_count = count_provided_args( pool_name, disk_wwn)   ## if all provided (not None), args_count must be equal 2
        if args_count < 2:
            sys_exit_with_timestamp(f"Error: add read cache disk command expects (pool, disk_wwn), {args_count} provided")
        add_read_cache_disk(pool_name,disk_wwn)

    elif action == 'modify_volume':
        args_count = count_provided_args( pool_name, volume_name, sync )   ## if all provided (not None), args_count must be equal 3
        if volume_name == 'auto':
            sys_exit_with_timestamp('Error: modify_volume command expects volume name to be specified')
        if args_count < 3:
            sys_exit_with_timestamp(f"Error: modify_volume command expects (pool, volume, sync or new_size), {args_count} provided")
        vol_type = check_given_volume_name()
        modify_volume(vol_type)

    elif action == 'set_host':
        args_count = count_provided_args( host_name, server_name, server_description )   ## if all provided (not None), args_count must be equal 3 set_host
        if args_count not in (1,2,3):
            sys_exit_with_timestamp('Error: set_host command expects at least 1 of arguments: --host, --server, --description')
        set_host_server_name(host_name, server_name, server_description)

    elif action == 'set_time':
        args_count = count_provided_args( timezone, ntp, ntp_servers )
        if args_count not in (1,2,3):
            sys_exit_with_timestamp('Error: set_time command expects at least 1 of arguments: --timezone, --ntp, --ntp_servers')
        set_time(timezone, ntp, ntp_servers)

    elif action == 'network':
        args_count = count_provided_args( nic_name, new_ip_addr, new_mask, new_gw, new_dns )
        if args_count not in (2,3,4,5):
            sys_exit_with_timestamp('Error: network command expects at least 2 of arguments: --nic, --new_ip, --new_mask, --new_gw --new_dns or just --new_dns')
        network(nic_name, new_ip_addr, new_mask, new_gw, new_dns)

    elif action == 'create_bond':
        args_count = count_provided_args( bond_type, bond_nics, new_gw, new_dns )
        if args_count not in (2,3,4):
            sys_exit_with_timestamp('Error: create_bond command expects at least 2 of arguments: --bond_type, --bond_nics')
        create_bond(bond_type, bond_nics, new_gw, new_dns)

    elif action == 'delete_bond':
        args_count = count_provided_args( bond_type, bond_nics, new_gw, new_dns )
        if args_count not in (0,1,2):
            sys_exit_with_timestamp('Error: delete_bond command expects at least 2 of arguments: --bond_type, --bond_nics')
        delete_bond(nic_name)

    elif action == 'bind_cluster':
        if len(nodes) !=2:
            sys_exit_with_timestamp('Error: bind_cluster command expects exactly 2 IP addresses')
        bind_ip_addr = nodes[1]
        bind_cluster(bind_ip_addr)

    elif action == 'add_ring':
        if len(nodes) !=1:
            sys_exit_with_timestamp('Error: add_ring command expects exactly 1 IP address')
        args_count = count_provided_args( ring_nics )
        if args_count not in (1,):
            sys_exit_with_timestamp('Error: add_ring command expects --ring_nics')
        add_ring()

    elif action == 'set_ping_nodes':
        if len(ping_nodes) < 1:
            sys_exit_with_timestamp('Error: set_ping_nodes command expects at least 1 IP address')
        set_ping_nodes()

    elif action == 'set_mirror_path':
        if len(nodes) !=1:
            sys_exit_with_timestamp('Error: set_mirror_path command expects exactly 1 IP address')
        args_count = count_provided_args( mirror_nics )
        if args_count not in (1,):
            sys_exit_with_timestamp('Error: set_mirror_path command expects --mirror_nics')
        set_mirror_path()

    elif action == 'create_vip':
        if len(nodes) !=1:
            sys_exit_with_timestamp('Error: create_vip command expects exactly 1 node IP address')
        args_count = count_provided_args( pool_name, vip_name, vip_nics, vip_ip, vip_mask )
        if args_count not in (4,5):
            sys_exit_with_timestamp('Error: create_vip command expects arguments: --pool --vip_name --vip_nics --vip_ip --vip_mask')
        create_vip()

    elif action == 'start_cluster':
        start_cluster()

    elif action == 'stop_cluster':
        stop_cluster()

    elif action == 'move':
        args_count = count_provided_args( pool_name, delay )
        if args_count not in (1,2):
            sys_exit_with_timestamp('Error: move command expects pool name to be specified')
        move()

    elif action == 'info':
        info()

    elif action == 'download_settings':
        download_settings()

    elif action == 'list_snapshots':
        list_snapshots()

    elif action == 'activate':
        activate()

    elif action == 'import':
        import_pool()

    elif action == 'shutdown':
        reboot_nodes(shutdown=True)

    elif action == 'reboot':
        reboot_nodes()


## FACTORY DEFAULT BATCH SETUP FILES
factory_setup_files_content = dict(
    api_setup_single_node = """
#
# The '#' comments-out the rest of the line
# 
network     --nic eth0      --new_ip _node-a-ip-address_   --node _node-a-ip-address_  # SET ETH
network     --nic eth1      --new_ip:nic   --node _node-a-ip-address_  # SET ETH
network     --nic eth2      --new_ip:nic   --node _node-a-ip-address_  # SET ETH
network     --nic eth3      --new_ip:nic   --node _node-a-ip-address_  # SET ETH
network     --nic eth4      --new_ip:nic   --node _node-a-ip-address_  # SET ETH
network     --nic eth5      --new_ip:nic   --node _node-a-ip-address_  # SET ETH
# network   --nic eth6      --new_ip:nic   --node _node-a-ip-address_
# network   --nic eth7      --new_ip:nic   --node _node-a-ip-address_
# network   --nic eth8      --new_ip:nic   --node _node-a-ip-address_
# network   --nic eth9      --new_ip:nic   --node _node-a-ip-address_
# network   --nic eth10     --new_ip:nic   --node _node-a-ip-address_
# network   --nic eth11     --new_ip:nic   --node _node-a-ip-address_

create_bond --bond_nics eth0 eth1 --new_ip:bond --bond_type active-backup --new_gw 192.168.0.1 --new_dns 192.168.0.1 --node _node-a-ip-address_

# CREATE BOND: mirror path: active-backup or balance-rr (round-robin)
create_bond --bond_nics eth4 eth5 --new_ip:bond --bond_type active-backup --node _node-a-ip-address_

set_host --host node-80-ha00 --server node-80-ha00 --node _node-a-ip-address_           # SET HOST & SERVER
set_time --timezone Europe/Berlin                  --node _node-a-ip-address_           # SET TIME
#   set_time  --timezone America/New_York              --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone America/Chicago               --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone America/Los_Angeles           --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone Europe/London                 --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone Asia/Tokyo                    --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone Asia/Taipei                   --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone Europe/Moscow                 --node _node-a-ip-address_       # SET TIME
#   set_time  --timezone Europe/Amsterdam              --node _node-a-ip-address_       # SET TIME

info                                               --node _node-a-ip-address_           # PRINT SYSTEM INFO
list_snapshots                                     --node _node-a-ip-address_           # PRINT ONLY SNAPSHOT INFO
activate                                 --online  --node _node-a-ip-address_           # PRODUCT ACTIVATION
""",
    api_setup_cluster = """
# The '#' comments-out the rest of the line

bind_cluster     --nodes _node-a-ip-address_ _node-b-ip-address_

add_ring         --ring_nics bond1 bond1                 --node _node-a-ip-address_

set_ping_nodes   --ping_nodes 192.168.0.30 192.168.0.40  --node _node-a-ip-address_

set_mirror_path  --mirror_nics bond1 bond1               --node _node-a-ip-address_

start_cluster                                            --node _node-a-ip-address_

create_pool --pool Pool-0 --vdevs 1 --vdev mirror --vdev_disks 4 --tolerance 20GB --node _node-a-ip-address_
create_pool --pool Pool-1 --vdevs 1 --vdev mirror --vdev_disks 4 --tolerance 20GB --node _node-a-ip-address_

set_scrub_scheduler             --node _node-a-ip-address_

create_vip --pool Pool-0 --vip_name vip21 --vip_ip 192.168.21.100 --vip_nics eth2 eth2 --node _node-a-ip-address_
create_vip --pool Pool-0 --vip_name vip31 --vip_ip 192.168.31.100 --vip_nics eth3 eth3 --node _node-a-ip-address_
create_vip --pool Pool-1 --vip_name vip22 --vip_ip 192.168.22.100 --vip_nics eth2 eth2 --node _node-a-ip-address_
create_vip --pool Pool-1 --vip_name vip32 --vip_ip 192.168.32.100 --vip_nics eth3 eth3 --node _node-a-ip-address_

create_storage_resource --pool Pool-0 --storage_type iscsi   --quantity 2 --start_with 100 --increment 100 --zvols_per_target 2 --node _node-a-ip-address_
create_storage_resource --pool Pool-0 --storage_type smb nfs --quantity 2 --start_with 100 --increment 100 --node _node-a-ip-address_

scrub                           --node _node-a-ip-address_

move            --pool Pool-1   --node _node-a-ip-address_
""",
    api_test_cluster = """
#   The '#' comments-out the rest of the line
scrub                                  --node _node-a-ip-address_    # scrub all
reboot    --force      --delay 10      --node _node-a-ip-address_    # reboot node-a
reboot    --force      --delay 10      --node _node-b-ip-address_    # reboot node-b
scrub                                  --node _node-a-ip-address_    # scrub all
reboot                 --delay 10      --node _node-a-ip-address_    # reboot node-a
reboot                 --delay 10      --node _node-b-ip-address_    # reboot node-b
scrub                                  --node _node-a-ip-address_    # scrub all

move      --delay 15   --pool Pool-0   --node _node-a-ip-address_    # move
move      --delay 15   --pool Pool-1   --node _node-a-ip-address_    # move

move      --delay 15   --pool Pool-0   --node _node-a-ip-address_    # move
move      --delay 15   --pool Pool-1   --node _node-a-ip-address_    # move

reboot    --force      --delay 10      --node _node-a-ip-address_    # reboot node-a
reboot    --force      --delay 10      --node _node-b-ip-address_    # reboot node-b
scrub                                  --node _node-a-ip-address_    # scrub all

move      --delay 15   --pool Pool-1   --node _node-a-ip-address_    # move
scrub                                  --node _node-a-ip-address_    # scrub all
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
            factory_files_names = list(factory_setup_files_content.keys()) + ['api_setup_single_node']
        for factory_file_name in factory_files_names:
            if 'api_setup_single_node' in factory_file_name:
                current_node = nodes[0] if trigger else nodes[1]
                content = factory_setup_files_content[factory_file_name].replace('_node-a-ip-address_',current_node)
                ending = current_node.split('.')[-1]
                host_server_name = f"node-{ending}-ha00"
                content = content.replace('node-80-ha00',host_server_name)
                for i in range(content.count('--new_ip:nic')):
                    _current_node = current_node.replace('0.',str(i+1)+'.')
                    content = content.replace('--new_ip:nic','--new_ip '+_current_node,1)
                ## numbers of first nics in --bond_nics
                first_nics_number_of_bonds = [item.split()[0].strip().strip('eth') for item in content.split('--bond_nics') if item.strip().startswith('eth')]
                for i in first_nics_number_of_bonds:
                    _current_node = current_node.replace('0.',str(i)+'.')
                    content = content.replace('--new_ip:bond','--new_ip '+_current_node,1)
                if new_gw:
                    content = content.replace('--new_gw 192.168.0.1','--new_gw ' + new_gw)
                if new_dns:
                    content = content.replace('--new_dns 192.168.0.1','--new_dns ' + ' '.join(new_dns))
                trigger = False
            else:
                current_node = nodes[0]
                content = factory_setup_files_content[factory_file_name].replace('_node-a-ip-address_',current_node)
                if nodes[0] != nodes[1]:    # replace the second ip
                    content = content.replace('_node-b-ip-address_',nodes[1])
                else:
                    content = content.replace('_node-b-ip-address_',nodes[0])
                if ping_nodes:
                    content = content.replace('192.168.0.30 192.168.0.40',' '.join(ping_nodes))
                if mirror_nics:   ## same for mirror_nics & ring_nics if ring_nics not specified
                    content = content.replace('--mirror_nics bond1 bond1', '--mirror_nics ' + ' '.join(mirror_nics))
                    content = content.replace('--ring_nics bond1 bond1', '--ring_nics ' + ' '.join(mirror_nics))
                if ring_nics:
                    content = content.replace('--ring_nics bond1 bond1', '--ring_nics ' + ' '.join(ring_nics))
            ending = current_node.split('.')[-1]
            file_name =  f"{factory_file_name}_{ending}.txt"
            with open(file_name,'w',encoding='utf-8') as f:
                f.write(content)
                print_with_timestamp(f"{file_name}\twritten into current directory")
    else:
        command_processor()


def print_help_item(item):
    title = ''
    next_help_item_line = None
    found= False
    for line in parser.epilog.splitlines():
        starts_with_number = line.split('.')[0].strip().isdigit()
        if '--' in line and item in line:
            found= True
        if starts_with_number and found:
            next_help_item_line = line
            if title not in line.split(END)[0].split(BOLD)[1]:
                break
        if starts_with_number and not found:
            first_help_item_line = line
            title = line.split(END)[0].split(BOLD)[1]
    found=False
    print()
    for line in parser.epilog.splitlines():
        if next_help_item_line and (next_help_item_line in line) or ('########' in line):
            break
        if not found and first_help_item_line in line:
            found = True
        if found and len(line)>0:
            if line.split('.')[0].strip().isdigit():
                line = '   ' + line.split('.')[1]
            line = line.replace('%(prog)s','    jdss-api-tools')
            print(line)


def nice_print(a_list,html=None):
    nice_txt = ''
    for i, item in enumerate(a_list):
        if (i + 1) % 3:
            nice_txt += f"{item:30}\t"
        else:
            nice_txt += f"{item}\n"
    return f"<pre>{nice_txt}</pre>" if html else nice_txt


def print_readme_md_for_github():
    with open('README.md','w',encoding='utf-8') as file:
        file.write(' ![Project Icon](JovianDSS-Logo.png)')
        file.write(parser.epilog.replace(
            LG+'jdss-api-tools','# jdss-api-tools').replace(   ## start first line with '#'
            BOLD,'<b>').replace(
            END,'</b>').replace(
            LG+'%(prog)s','    jdss-api-tools.exe').replace(
            LG,' ').replace(
            ENDF,'').replace(
            nice_print(commands.choices),nice_print(commands.choices,'html')))


if __name__ == '__main__':

    init()          ## colorama
    get_args()      ## args


    try:
        main()
    except KeyboardInterrupt:
        sys_exit('Interrupted             ')
    print()
    print_readme_md_for_github()

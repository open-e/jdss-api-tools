"""
jdss-api-tools send REST API commands to JovianDSS servers

In order to create single exe file run:
C:\Python27\Scripts\pyinstaller.exe --onefile jdss-api-tools.py
And try it:
C:\Python27\dist\jdss-api-tools.exe -h

NOTE:
In case of error "msvcr100.dll missing ...",
download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe


2018-02-07  initial release
2018-03-06  add create pool
2018-03-18  add delete_clone option (it deletes the snapshot as well) (kris@dddistribution.be)

"""
    
from __future__ import print_function
import sys
import time
from jovianapi import API
from jovianapi.resource.pool import PoolModel
import logging
import argparse
import collections


__author__  = 'janusz.bak@open-e.com'
__version__ = 1.0

# Script global variables - to be updated in parse_args():
line_sep                = '='*62
action                  = ''
delay                   = 0
nodes                   = []
auto_target_name        = "iqn.auto.api.backup.target"        
auto_share_name         = "auto_api_backup_share"        
auto_scsiid             = time.strftime("%Yi%mi%di%Hi%M")  #"1234567890123456"
auto_snap_name          = "auto_api_backup_snap"
auto_vol_clone_name     = "_auto_api_vol_clone"
auto_zvol_clone_name    = "_auto_api_zvol_clone"


KiB,MiB,GiB,TiB = (pow(1024,i) for i in (1,2,3,4))

## TARGET NAME
target_name_prefix= "iqn.%s-%s:jdss.target" % (time.strftime("%Y"),time.strftime("%m"))

## ZVOL NAME
zvol_name_prefix = 'zvol00'


def interface(node):
    return API.via_rest(node, api_port, api_user, api_password)


def get_args():

    parser = argparse.ArgumentParser(
        prog='jdss-api-tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''The %(prog)s remotely execute given command.''',
        epilog='''EXAMPLES:

 1. Create Clone of iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.
     Every time it runs, it will delete the clone created last run and re-create new one.
     So, the target exports most recent data every run.
     The example is using default password and port.
     Tools automatically recognize the volume type. If given volume is iSCSI volume,
     the clone of the iSCSI volume will be attached to iSCSI target.
     If given volume is NAS dataset, the crated clone will be exported via network share
     as shown in the next example.

      %(prog)s clone --pool=Pool-0 --volume=zvol00 192.168.0.220


 2. Create Clone of NAS volume vol00 from Pool-0 and share via new created SMB share.
     Every time it runs, it will delete the clone created last run and re-create new one.
     So, the share exports most recent data every run.
     The example is using default password and port.

      %(prog)s clone --pool=Pool-0 --volume=vol00 192.168.0.220


 3. Create pool on single node or cluster with single JBOD:
     Pool-0 with 2 * raidz1(3 disks) total 6 disks 

      %(prog)s create_pool --pool=Pool-0 --vdevs=2 --vdev=raidz1 --vdev_disks=3 192.168.0.220


 4. Create pool on Metro Cluster with single JBOD with 4-way mirrors:
     Pool-0 with 2 * mirrors(4 disks) total 8 disks 

      %(prog)s create_pool --pool=Pool-0 --vdevs=2 --vdev=mirror --vdev_disks=4 192.168.0.220


 5. Delete Clone of iSCSI volume zvol00 from Pool-0.

      %(prog)s delete_clone --pool=Pool-0 --volume=zvol00 192.168.0.220


 6. Delete Clone of NAS volume vol00 from Pool-0.

      %(prog)s delete_clone --pool=Pool-0 --volume=vol00 192.168.0.220


 7. Create pool with raidz2(4 disks each) over 4 JBODs with 60 HDD each.
     Every raidz2 vdev consists of disks from all 4 JBODs. An interactive menu will be started.
     In order to read disks, POWER-ON single JBOD only. Read disks selecting "0" for the first JBOD.
     Next, POWER-OFF the first JBOD and POWER-ON the second one. Read disks of the second JBOD selecting "1".
     Repeat the procedure until all JBODs disk are read. Finally, create the pool selecting "c" from the menu.

      %(prog)s create_pool --pool=Pool-0 --jbods=4 --vdevs=60 --vdev=raidz2 --vdev_disks=4 192.168.0.220


 8. Shutdown three JovianDSS servers using default port but non default password.

      %(prog)s --pswd password shutdown 192.168.0.220 192.168.0.221 192.168.0.222

    or with IP range syntax ".."

      %(prog)s --pswd password shutdown 192.168.0.220..222


 9. Reboot single JovianDSS server.

      %(prog)s reboot 192.168.0.220

 10. Set Host name to "node220", Server name to "server220" and server description to "jdss220".

      %(prog)s set_host --host=node220 --server=server220 --description=jdss220  192.168.0.220
    ''')

    parser.add_argument(
        'cmd',
        metavar='command',
        choices=['clone', 'create_pool', 'delete_clone', 'set_host', 'shutdown', 'reboot'],
        help='Commands:  %(choices)s.'
    )
    parser.add_argument(
        '--pool',
        metavar='name',
        help='Enter pool name'
    )
    parser.add_argument(
        '--volume',
        metavar='name',
        help='Enter SAN(zvol) or NAS(vol) volume name'
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
        'ip',
        metavar='jdss-ip-addr',
        nargs='+',
        help='Enter nodes IP(s)'
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
        help='Disk size tolerance. Treat smaller disks still as equal in size. Default=5 GiB'
    )
    parser.add_argument(
        '--menu',
        dest='menu',
        action='store_true',
        default=False,
        help='Interactive menu. Auto-Start with --jbods_num > 1 '
    )

    ## ARGS
    args = parser.parse_args()
    
    global api_port, api_user, api_password, action, pool_name, volume_name, delay, nodes, node, menu
    global jbod_disks_num, vdev_disks_num, jbods_num, vdevs_num, vdev_type, disk_size_tolerance
    global host_name, server_name, server_description

    api_port                = args.port
    api_user                = args.user
    api_password            = args.pswd
    action                  = args.cmd
    pool_name               = args.pool
    volume_name             = args.volume
    jbod_disks_num          = args.jbod_disks
    vdev_disks_num          = args.vdev_disks
    jbods_num               = args.jbods
    vdevs_num               = args.vdevs
    vdev_type               = args.vdev
    disk_size_tolerance     = args.tolerance * GiB
    host_name               = args.host
    server_name             = args.server
    server_description      = args.description
    
    delay                   = args.delay
    nodes                   = args.ip

    menu                    = args.menu

    if jbods_num > 1: 
        menu = True
    
    ##expand nodes list if ip range provided in args
    ## i.e. 192.168.0.220..221 will be expanded to: ["192.168.0.220","192.168.0.221"]
    expanded_nodes = []
    for ip in nodes:
        if ".." in ip:
            expanded_nodes += expand_ip_range(ip)
        else:
            expanded_nodes.append(ip)
    nodes = expanded_nodes

    ##  first node
    node    = nodes[0]
            
    ##  validate ip-addr
    for ip in nodes :
        if not valid_ip(ip) :
            sys_exit( 'IP address {} is invalid'.format(ip))

    ##  detect doubles
    doubles = [ip for ip, c in collections.Counter(nodes).items() if c > 1]
    if doubles:
        sys_exit( 'Double IP address: {}'.format(', '.join(doubles)))

    ##  validate port
    if not 22 <= args.port <= 65535:
        sys_exit( 'Port {} is out of allowed range 22..65535'.format(port))



def count_provided_args(*args):
    return map(bool, args).count(True)


def time_stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def time_stamp_clone_syntax():
    return time.strftime("_%Y-%m-%d_%H-%M-%S")


def print_with_timestamp(msg):
    print('{}  {}'.format(time_stamp(), msg))


def sys_exit_with_timestamp(msg):
    print_with_timestamp(msg)
    sys.exit(1)


def sys_exit(msg):
    print(msg)
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


def expand_ip_range(ip_range):
	start=int(ip_range.split("..")[0].split(".")[-1])
	end=int(ip_range.split("..")[-1])
	base=".".join(ip_range.split(".")[:3])+"."
	ip_list = []
	for i in range(start,end+1):
		ip_list.append(base+str(i))
	return ip_list


def wait_for_nodes():
    
    for node in nodes :
        api = interface(node)
        repeat = 100
        counter = 0
        while True:
            try:
                product = api.driver.get('/product')
            except:
                if counter % 3:
                    print_with_timestamp( 'Node {} does not respond to REST API commands.'.format(node))
                else:
                    print_with_timestamp(
                        'Please enable REST API on {} in GUI: System Settings -> Administration -> REST access, or check access credentials.'.format(node))
            else:
                print_with_timestamp( 'Node {} is running.'.format(node))
                break
            counter += 1
            time.sleep(4)
            if counter == repeat:   ##  Connection timed out
                exit_with_timestamp( 'Connection timed out: {}'.format(node_ip_address))


def display_delay(msg):
    for sec in range(delay, 0, -1) :
        print( '{} in {:>2} seconds \r'.format(msg,sec))
        time.sleep(1)


def shutdown_nodes():
    display_delay('Shutdown')
    for node in nodes:
        api = interface(node)
        endpoint = '/power/shutdown'
        data = dict(force=True) 
        api.driver.post(endpoint,data)
        print_with_timestamp( 'Shutdown: {}'.format(node))


def reboot_nodes() :
    display_delay('Reboot')
    for node in nodes:
        api = interface(node)
        endpoint = '/power/reboot'
        data = dict(force=True) 
        api.driver.post(endpoint,data)
        print_with_timestamp( 'Reboot: {}'.format(node))


def set_host_server_name(host_name=None, server_name=None, server_description=None):
    api = interface(node)
    data = dict()
    endpoint = '/product'  
    if host_name:
        data["host_name"] = host_name
    if server_name:
        data["server_name"] = server_name
    if server_description:
        data["server_description"] = server_description

    api.driver.put(endpoint,data)

    if host_name:
        print_with_timestamp( 'Set Host Name: {}'.format(host_name))
    if server_name:
        print_with_timestamp( 'Set Server Name: {}'.format(server_name))        
    if server_description:
        print_with_timestamp( 'Set Server Description: {}'.format(server_description))
        

def get_pool_details(node, pool_name):
    api = interface(node)
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
    for node in nodes:
        api = interface(node)
        try:
            api.storage.pools[pool_name]
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: {} does not exist on Node: {}'.format(pool_name, node))
            return False
    return True


def check_given_volume_name(ignore_error=None):
    ''' If given volume_name exist, return volume type:
            dataset (NAS-vol)
            volume (SAN-zvol)
        If given volume_name does not exist:
            sys.exit with ERROR     ''' 
    for node in nodes:
        api = interface(node)
        pool = api.storage.pools[pool_name]
        for vol in pool.datasets:
            if vol.name == volume_name:
                return 'dataset'
        for zvol in pool.volumes:
            if zvol.name == volume_name:
                return 'volume'
        if ignore_error is None:
            sys_exit_with_timestamp( 'Error: {} does not exist on {} Node: {}'.format(volume_name, pool_name, node))
        else:
            return None


def jbods_listing(jbods):
    available_disks = count_available_disks(jbods)
    jbod = []
    if available_disks :
        for j,jbod in enumerate(jbods):
            print("\tjbod-{}\n\t{}".format(j,line_sep))
            if jbod :
                for d,disk in enumerate(jbod):
                    print("\t{:2d} {}\t{} GB\t{}\t{}".format(
                        d,disk[1],disk[0]/1024/1024/1024,disk[3], disk[2]))
        msg = "\n\tTotal: {} available disks found".format(available_disks)
    else:
        msg = "JBOD is empty. Please choose the jbod number in order to read disks."
    return msg


def read_jbod(n):
    """
    read unused disks serial numbers in given jbod n= 0,1,2,...
    """
    api = interface(node)
    jbod = []
    global metro
    metro = False
    
    unused_disks = api.storage.disks.unused
    for disk in unused_disks:
        if disk.origin in "iscsi":
            disk.origin = "remote"
            metro = True
        jbod.append((disk.size,disk.name,disk.id,disk.origin))
    return jbod 


def create_pool(pool_name,vdev_type,jbods):
    api = interface(node)
    vdev_type = vdev_type.replace('single','')
    print("\n\tCreating pool. Please wait...")
    pool = api.storage.pools.create(
        name = pool_name,
        vdevs = (PoolModel.VdevModel(type=vdev_type, disks=vdev_disks) for vdev_disks in zip(*jbods)) ) ##zip disks over jbods  
    return pool


def create_snapshot(vol_type,ignore_error=None):
    for node in nodes:
        api = interface(node)
        # Create snapshot of NAS vol
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots'.format(
                   POOL_NAME=pool_name, DATASET_NAME=volume_name)
            ## Auto-Snapshot-Name
            data = dict(name=auto_snap_name)            
        # Create snapshot of SAN zvol
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name)
            ## Auto-Snapshot-Name
            data = dict(snapshot_name=auto_snap_name)   

        try:
            api.driver.post(endpoint, data)
            print_with_timestamp("Snapshot of {}/{} has been successfully created.".format(pool_name,volume_name))
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Target: {} creation on Node: {} failed'.format(auto_target_name, node))    


def create_clone(vol_type, ignore_error=None):
    for node in nodes:
        global clone_name
        ## dataset(vol) clone and volume(zvol) clone names can be the same as belong to different resources
        api = interface(node)
        # Create clone of NAS vol == dataset
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAP_NAME}/clones'.format(
                POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAP_NAME=auto_snap_name)
            ## vol
            clone_name = volume_name + time_stamp_clone_syntax() + auto_vol_clone_name
            data = dict(name=clone_name)
        # Create clone of SAN zvol == volume
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/clone'.format(
                POOL_NAME=pool_name, VOLUME_NAME=volume_name)
            ## zvol
            clone_name = volume_name + time_stamp_clone_syntax() + auto_zvol_clone_name
            data = dict(name=clone_name, snapshot=auto_snap_name)
        try:
            api.driver.post(endpoint, data)
            print_with_timestamp("Clone of {}/{} has been successfully created.".format(pool_name,volume_name))
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Clone: {} creation on Node: {} failed'.format(clone_name, node))


def delete_snapshot_and_clone(vol_type, ignore_error=None):
    for node in nodes:
        api = interface(node)
        # Delete snapshot. It auto-delete clone and share of NAS vol
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAPSHOT_NAME}'.format(
                       POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            try:
                api.driver.delete(endpoint)
                print_with_timestamp("Share, clone and snapshot of {}/{} have been successfully deleted.".format(pool_name,volume_name))
                print()
            except:
                print_with_timestamp( 'Snapshot delete error: {} does not exist on Node: {}'.format(auto_snap_name, node))
                print()
        # Delete snapshot and clone of SAN zvol (using recursively options) 
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots/{SNAPSHOT_NAME}'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            data = dict(recursively_children=True, recursively_dependents=True, force_umount=True)
            try:
                api.driver.delete(endpoint,data)
                print_with_timestamp("Clone and snapshot of {}/{} have been successfully deleted.".format(pool_name,volume_name))
                print()
            except:
                print_with_timestamp( 'Snapshot delete error: {} does not exist on Node: {}'.format(auto_snap_name, node))
                print()

def create_target(ignore_error=None):
    for node in nodes:
        api = interface(node)
        endpoint = '/pools/{POOL_NAME}/san/iscsi/targets'.format(
                   POOL_NAME=pool_name)
        ## Auto-Target-Name
        data = dict(name=auto_target_name)       
        try:
            target_object = api.driver.post(endpoint, data)
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Target: {} creation on Node: {} failed'.format(auto_target_name, node))
    

def attach_target(ignore_error=None):
    for node in nodes:
        api = interface(node)
        endpoint = '/pools/{POOL_NAME}/san/iscsi/targets/{TARGET_NAME}/luns'.format(
                   POOL_NAME=pool_name, TARGET_NAME=auto_target_name)
        data = dict(name=clone_name)       
        try:
            api.driver.post(endpoint, data)
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Cannot attach target: {} to {} on Node:{}'.format(
                    auto_target_name, clone_name, node))
        
        print_with_timestamp("Clone of {}/{} has been successfully attached to target.".format(
            pool_name,volume_name))
        print("\n\tTarget:\t{}".format(auto_target_name))
        print("\tClone:\t{}/{}\n".format(pool_name, clone_name))
            

def create_share_for_auto_clone(ignore_error=None):
    for node in nodes:
        api = interface(node)
        endpoint = '/shares'
        data = dict(name=auto_share_name,
                path='{POOL_NAME}/{CLONE_NAME}'.format(POOL_NAME=pool_name, CLONE_NAME=clone_name),
                smb=dict(enabled=True))
        try:
            api.driver.post(endpoint, data)
        except:
            sys_exit_with_timestamp( 'Error: Share: {} creation on Node: {} failed'.format(auto_share_name, node))

        print_with_timestamp("Share for {}/{} has been successfully created.".format(
                pool_name,clone_name))
        print("\n\tShare:\t\\\\{}\{}".format(node, auto_share_name))
        print("\tClone:\t{}/{}\n".format(pool_name, clone_name))


def create_new_backup_clone(vol_type):
    create_snapshot(vol_type)
    create_clone(vol_type)
    if vol_type == 'dataset':
        create_share_for_auto_clone()
    if vol_type == 'volume':
        create_target(ignore_error=True)
        attach_target()


def count_available_disks(jbods):
    return [ bool(d) for jbod in jbods  for d in jbod  ].count(True)


def merge_sublists(list_of_lists):
    """
    merge list of sub_lists into single list
    """
    return [ item for sub_list in list_of_lists for item in sub_list]  


def convert_jbods_to_id_only(jbods):
    return [ [(disk[2]) for disk in jbod] for jbod in jbods ]   ## (disk.size,disk.name,disk.id) 


def split_for_metro_cluster(jbods,vdev_disks=2):
    """
    in case of METRO Cluster assume single jbod in jbods and split into 2 jbod,
    first with disk.origin="local" and second with disk.origin="remote"
    and split into 4 jbods for 4-way mirror (2 local and 2 remote) if vdev_disks=4
    """
    ## disk[3] => disk.origin
    ## split into 2 jbods for 2-way mirror (1 local and 1 remote)
    jbods_2way_mirrors = [ [ disk for disk in jbod if disk[3] == place] for jbod in jbods if jbod   for place in ("local","remote") ] 
    if vdev_disks == 2 :
        return jbods_2way_mirrors
    else:
        ## split into 4 jbods for 4-way mirror (2 local and 2 remote)
        jbods_4way_mirrors =[]
        for i in range(4):
            jbods_4way_mirrors.append(jbods_2way_mirrors[i%2][i/2::2])
        return jbods_4way_mirrors


def remove_disks(jbods):
    available_disks = count_available_disks(jbods)
    if available_disks :
        jbods_disks_size = [ [disk[0] for disk in jbod]  for jbod in jbods ]
        all_disks_size = merge_sublists( jbods_disks_size ) ## convert lists of jbods to single disks list
        average_disk_size = float(sum(all_disks_size)) / len(all_disks_size)  ## 
        return [ [ disk for disk in jbod if disk[0]>= (average_disk_size - disk_size_tolerance)] for jbod in jbods ] ##>= do not remove if all drives are same size
    

def check_all_disks_size_equal(jbods):
    jbods_disks_size  = [ [disk[0] for disk in jbod]  for jbod in jbods ]
    all_disks_size = merge_sublists( jbods_disks_size ) ## convert lists of jbods to single disks list
    if (max(all_disks_size) - min(all_disks_size)) < disk_size_tolerance:
        return True
    else:
        return False


def user_choice():

    while 1:
        try :
            choice = raw_input('\tEnter your choice : ').upper()
            if choice in '':
                return "L"  ##treat pressed enter as "L"
            if choice in '0123456789LCQ':
                return choice
            else:
                print("\tInvalid choice")
        except:
            sys_exit('Interrupted             ')


def read_jbods_and_create_pool(choice='0'):

    global  vdevs_num,vdev_type

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
        {}""".format(line_sep, line_sep, ",".join(map(str,range(given_jbods_num))), line_sep))
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
                ## read_jbod
                jbods[jbod_number] = read_jbod(jbod_number)
                jbods = remove_disks(jbods)   ##### REMOVE smaller disks 
                if metro:
                    ## metro mirror both nodes with 2-way (--vdev_disks_num=2)or 4-way mirror (--vdev_disks_num=4)
                    vdev_type = "mirror"
                    jbods = split_for_metro_cluster(jbods,vdev_disks_num)
                ## reset jbods[i] if double serial number detected
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
                msg = "At least one JBOD is empty. Please press 0,1,.. in order to read JBODs disks."
            else:
                if check_all_disks_size_equal(jbods) == False:
                    msg = 'Disks with diffrent size present. Please press "r" in order to remove smaller disks.'
                else:
                    jbods_id_only = convert_jbods_to_id_only(jbods)
                    required_disks_num = vdevs_num * vdev_disks_num 
                    available_disks = count_available_disks(jbods_id_only)
                    if available_disks < required_disks_num:
                        msg ="Error: {}: {}*{}[{} disk] requires {} disks. {} disks available.\n".format(
                            pool_name,vdevs_num,vdev_type,vdev_disks_num,required_disks_num,available_disks)
                    else:
                        if jbods_num == 1 and not metro:
                            #transpose single jbod for jbods [number_of_disks_in_vdev * number_of_vdevs]
                            jbods_id_only = zip(*[iter(jbods_id_only[0])] * vdevs_num )
                            jbods_id_only = jbods_id_only[: vdev_disks_num]
                            pool = create_pool(pool_name,vdev_type, jbods_id_only)
                        else:
                            ##limit to given vdevs_num
                            jbods_id_only = [jbod[:vdevs_num] for jbod in jbods_id_only] 
                            pool = create_pool(pool_name,vdev_type,jbods_id_only)
                        ##### reset
                        jbods = [[] for i in range(jbods_num)]
            ##
            break
        ## exit
        elif choice in "Q":
            break

    ## display pools details 
    api = interface(node)
    pools = [pool.name for pool in api.storage.pools]
    print("\n")
    for pool in sorted(pools):
        print("\tNode {} {}: {}*{}[{} disk]".format(node, pool, *get_pool_details(node, pool)))
        

def main() :

    get_args()
    wait_for_nodes()

    if action == 'clone':
        c = count_provided_args( pool_name, volume_name )   ## if both provided (not None), c must be equal 2
        if c < 2:
            sys_exit_with_timestamp( 'Error: Clone command expects 2 arguments(pool, volume), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )
        create_new_backup_clone( vol_type )

    elif action == 'delete_clone':
        c = count_provided_args( pool_name, volume_name )   ## if both provided (not None), c must be equal 2
        if c < 2:
            sys_exit_with_timestamp( 'Error: delete_clone command expects 2 arguments(pool, volume), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )

    elif action == 'create_pool':
        if check_given_pool_name(ignore_error=True):
            sys_exit_with_timestamp("Error: Pool {} already exist.".format(pool_name))
        read_jbods_and_create_pool()
 
    elif action == 'set_host':
        c = count_provided_args(host_name, server_name, server_description)   ## if all provided (not None), c must be equal 3 set_host 
        if c not in (1,2,3):
            sys_exit_with_timestamp( 'Error: set_host command expects at least 1 of arguments: --host, --server, --description')
        set_host_server_name(host_name, server_name, server_description)

    elif action == 'shutdown':
        shutdown_nodes()

    elif action == 'reboot':
        reboot_nodes()


if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        sys_exit('Interrupted             ')

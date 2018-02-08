"""
jdss-api-tools send REST API commands to JovianDSS servers

In order to create single exe file run:
C:\Python27>Scripts\pyinstaller.exe --onefile jdss-api-tools.py
And try it:
C:\Python27>dist\jdss-api-tools.exe -h

NOTE:
In case of error: "msvcr100.dll missing ..."
please download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe
"""


from __future__ import print_function
import sys
import time
from jovianapi import API
import logging
import argparse
import collections


__author__ = 'janusz.bak@open-e.com'


# Script global variables - to be updated in parse_args():
action                  = ''
delay                   = 0
nodes                   = []
auto_target_name        = "iqn.auto-api.backup.target"        
auto_share_name         = "auto_api_backup_share"        
auto_scsiid             = time.strftime("%Yi%mi%di%Hi%M")  #"1234567890123456"
auto_snap_name          = "auto_api_backup_snap"
auto_vol_clone_name     = "auto_api_vol_clone"
auto_zvol_clone_name    = "auto_api_zvol_clone"



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
     So, the share  exports most recent data every run.
     The example is using default password and port.

      %(prog)s clone --pool=Pool-0 --volume=zvol00 192.168.0.220

 3. Shutdown three JovianDSS servers using default port but non default password

      %(prog)s --pswd password shutdown 192.168.0.220 192.168.0.221 192.168.0.222

 4. Reboot single JovianDSS server

      %(prog)s reboot 192.168.0.220
    ''')

    parser.add_argument(
        'cmd',
        metavar='command',
        choices=['clone', 'shutdown', 'reboot'],
        help='Available commands:  %(choices)s.'
    )
    parser.add_argument(
        '--pool',
        metavar='pool_name',
        help='Enter pool name'
    )
    parser.add_argument(
        '--volume',
        metavar='volume_name',
        help='Enter SAN(zvol) or NAS(vol) volume name'
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
        help='User defined reboot/shutdown delay in seconds, default=30'
    )

    # testing argv
    # sys.argv = sys.argv + \
    # ' create-vg00 192.168.0.220 192.168.0.80 192.168.0.81 '.split()
    # testing argv

    args = parser.parse_args()

    
    global api_port, api_user, api_password, action, pool_name, volume_name, delay, nodes

    api_port = args.port
    api_user = args.user
    api_password = args.pswd
    action = args.cmd
    pool_name = args.pool
    volume_name = args.volume
    delay = args.delay
    nodes = args.ip


    
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
    

def wait_for_nodes():
    
    for node in nodes :
        api = API.via_rest(node, 82, api_user, api_password)
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
        api = API.via_rest(node, 82, api_user, api_password)
        endpoint = '/power/shutdown'
        data = dict(force=True) 
        api.driver.post(endpoint,data)
        print_with_timestamp( 'Shutdown: {}'.format(node))


def reboot_nodes() :
    display_delay('Reboot')
    for node in nodes:
        api = API.via_rest(node, 82, api_user, api_password)
        endpoint = '/power/reboot'
        data = dict(force=True) 
        api.driver.post(endpoint,data)
        print_with_timestamp( 'Reboot: {}'.format(node))


def check_given_pool_name(ignore_error=None):
    ''' If given pool_name exist:
            return pool object
        If given pool_name does not exist:
            exit with ERROR     ''' 
    for node in nodes:
        api = API.via_rest(node, 82, api_user, api_password)
        try:
            api.storage.pools[pool_name]
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: {} does not exist on Node: {}'.format(pool_name, node))
    return True


def check_given_volume_name(ignore_error=None):
    ''' If given volume_name exist, return volume type:
            dataset (NAS-vol)
            volume (SAN-zvol)
        If given volume_name does not exist:
            sys.exit with ERROR     ''' 
    for node in nodes:
        api = API.via_rest(node, 82, api_user, api_password)
        pool = api.storage.pools[pool_name]
        for vol in pool.datasets:
            if vol.name == volume_name:
                return 'dataset'
        for zvol in pool.volumes:
            if zvol.name == volume_name:
                return 'volume'
        if ignore_error is None:
            sys_exit_with_timestamp( 'Error: {} does not exist on {} node: {}'.format(volume_name, pool_name, node))
        else:
            return None
        

def create_snapshot(vol_type,ignore_error=None):
    for node in nodes:
        api = API.via_rest(node, api_port, api_user, api_password)
        # Create snapshot of NAS vol
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots'.format(
                   POOL_NAME=pool_name, DATASET_NAME=volume_name)
            data = dict(name=auto_snap_name)            ## Auto-Snapshot-Name
        # Create snapshot of SAN zvol
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name)
            data = dict(snapshot_name=auto_snap_name)   ## Auto-Snapshot-Name

        try:
            api.driver.post(endpoint, data)
            print_with_timestamp("Snapshot of {}/{} has been successfully created.".format(pool_name,volume_name))
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Target: {} creation on Node: {} failed'.format(auto_target_name, node))    


def create_clone(vol_type, ignore_error=None):
    for node in nodes:
        global clone_name
        ## dataset(vol) clone and volume(zvol) clone names can be the same as belong to diffrent resources
        
        api = API.via_rest(node, api_port, api_user, api_password)
        # Create clone of NAS vol == dataset
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAP_NAME}/clones'.format(
                POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAP_NAME=auto_snap_name)
            clone_name = auto_vol_clone_name + time_stamp_clone_syntax()                                    ## vol
            data = dict(name=clone_name)
        # Create clone of SAN zvol == volume
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/clone'.format(
                POOL_NAME=pool_name, VOLUME_NAME=volume_name)
            clone_name = auto_zvol_clone_name + time_stamp_clone_syntax()                                  ## zvol
            data = dict(name=clone_name, snapshot=auto_snap_name)     
        try:
            api.driver.post(endpoint, data)
            print_with_timestamp("Clone of {}/{} has been successfully created.".format(pool_name,volume_name))
        except:
            if ignore_error is None:
                sys_exit_with_timestamp( 'Error: Clone: {} creation on Node: {} failed'.format(clone_name, node))    


def delete_snapshot_and_clone(vol_type, ignore_error=None):
    for node in nodes:
        api = API.via_rest(node, api_port, api_user, api_password)
        
        # Delete snapshot. It auto-delete clone and share of NAS vol
        if vol_type == 'dataset':
            endpoint = '/pools/{POOL_NAME}/nas-volumes/{DATASET_NAME}/snapshots/{SNAPSHOT_NAME}'.format(
                       POOL_NAME=pool_name, DATASET_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            try:
                api.driver.delete(endpoint)
            except:
                print_with_timestamp( 'Snapshot delete error: {} does not exist on Node: {}'.format(auto_snap_name, node))

        # Delete snapshot and clone of SAN zvol (using recursively options) 
        if vol_type == 'volume':
            endpoint = '/pools/{POOL_NAME}/volumes/{VOLUME_NAME}/snapshots/{SNAPSHOT_NAME}'.format(
                   POOL_NAME=pool_name, VOLUME_NAME=volume_name, SNAPSHOT_NAME=auto_snap_name)
            data = dict(recursively_children=True, recursively_dependents=True, force_umount=True)

            try:
                api.driver.delete(endpoint,data)
            except:
                print_with_timestamp( 'Snapshot delete error: {} does not exist on Node: {}'.format(auto_snap_name, node))


def create_target(ignore_error=None):
    for node in nodes:
            api = API.via_rest(node, api_port, api_user, api_password)
            endpoint = '/pools/{POOL_NAME}/san/iscsi/targets'.format(
                       POOL_NAME=pool_name)
            data = dict(name=auto_target_name)       ## Auto-Target-Name
            try:
                target_object = api.driver.post(endpoint, data)
            except:
                if ignore_error is None:
                    sys_exit_with_timestamp( 'Error: Target: {} creation on Node: {} failed'.format(auto_target_name, node))
    

def attach_target(ignore_error=None):
    for node in nodes:
            api = API.via_rest(node, api_port, api_user, api_password)
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
            api = API.via_rest(node, api_port, api_user, api_password)
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
        

def main() :

    get_args()
    wait_for_nodes()

    if action == 'clone':
        c = count_provided_args( pool_name, volume_name )   ## if both provided (not None), c must be euqal 2
        if c < 2:
            sys_exit_with_timestamp( 'Error: Clone command expects 2 arguments(pool, volume), {} provided.'.format(c))
        vol_type = check_given_volume_name()
        delete_snapshot_and_clone( vol_type, ignore_error=True )
        create_new_backup_clone( vol_type )

    elif action == 'shutdown':
        shutdown_nodes()

    elif action == 'reboot':
        reboot_nodes()


if __name__ == '__main__':


    try:
        main()
    except KeyboardInterrupt:
        print_with_timestamp( 'Interrupted             ')
        sys.exit(0)

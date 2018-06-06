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
2018-04-23  add set_host  --host --server --description
2018-04-23  add network
2018-04-23  add info
2018-05-05  add network info
2018-05-06  add pools info
2018-05-28  add set_time
2018-06-06  fix spelling

"""
    
from __future__ import print_function
import sys
import time
import datetime
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

def get(endpoint):
    global node
    api=interface(node)
    return api.driver.get(endpoint)['data']

def put(endpoint,data):
    global node
    api=interface(node)
    return api.driver.put(endpoint,data)

def post(endpoint,data):
    global node
    api=interface(node)
    return api.driver.post(endpoint,data)
    
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

 11. Set Timezone and with NTP-time with default NTP servers.

      %(prog)s set_time --timezone=America/New_York 192.168.0.220
      %(prog)s set_time --timezone=America/Chicago 192.168.0.220
      %(prog)s set_time --timezone=America/Los_Angeles 192.168.0.220
      %(prog)s set_time --timezone=Europe/Berlin 192.168.0.220

 12. Set new IP settings for eth0 and set gateway-IP and set eth0 as default gateway.
      Missing netmask option will set default 255.255.255.0 

      %(prog)s network --nic=eth0 --new_ip=192.168.0.80 --new_gw=192.168.0.1 192.168.0.220

 13. Print system info 

      %(prog)s info 192.168.0.220
    ''')

    parser.add_argument(
        'cmd',
        metavar='command',
        choices=['clone', 'create_pool', 'delete_clone', 'set_host', 'set_time', 'network',
                 'info', 'shutdown', 'reboot'],
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
        '--timezone',
        metavar='zone',
        default=None,
        help='Enter timezone'
    )
    parser.add_argument(
        '--ntp',
        metavar='ON|OFF',
        default='ON',
        help='Enter "ON" to enable, "OFF to disable NTP'
    )
    parser.add_argument(
        '--ntp_servers',
        metavar='servers',
        default='0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org',
        help='Enter NTP servers(s)'
    )
    parser.add_argument(
        '--nic',
        metavar='eth#',
        default=None,
        help='Enter NIC name. Example: eth0, eth1, bond0, bond1, etc.'
    )
    parser.add_argument(
        '--new_ip',
        metavar='addr',
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
        metavar='addr',
        default=None,
        help='Enter new gateway for selected NIC'
    )
    parser.add_argument(
        '--new_dns',
        metavar='addr',
        default=None,   # default None, empty str will clear dns
        help='Enter new dns address or coma separated list'
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
    global nic_name, new_ip_addr, new_mask, new_gw, new_dns
    global host_name, server_name, server_description, timezone, ntp, ntp_servers

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
    timezone                = args.timezone
    ntp                     = args.ntp
    ntp_servers             = args.ntp_servers

    nic_name                = args.nic
    new_ip_addr             = args.new_ip
    new_mask                = args.new_mask
    new_gw                  = args.new_gw
    new_dns                 = args.new_dns

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


def new_dns_convert_to_list(new_dns):
    if new_dns is None:
        return None
    if new_dns is '':
        return []
    for sep in ',;':
        if sep in new_dns:
            new_dns=new_dns.split(sep)
    if type(new_dns) is str:
        new_dns=new_dns.split() #no separator, single item new_dns list
    return new_dns


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
    global node
    for node in nodes :
        repeat = 100
        counter = 0
        while True:
            try:
                get('/conn_test')
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
    global node
    display_delay('Shutdown')
    for node in nodes:
        post('/power/shutdown',dict(force=True))
        print_with_timestamp( 'Shutdown: {}'.format(node))


def reboot_nodes() :
    global node
    display_delay('Reboot')
    for node in nodes:
        post('/power/reboot', dict(force=True))
        print_with_timestamp( 'Reboot: {}'.format(node))


def set_host_server_name(host_name=None, server_name=None, server_description=None):

    data = dict()
    if host_name:
        data["host_name"] = host_name
    if server_name:
        data["server_name"] = server_name
    if server_description:
        data["server_description"] = server_description

    put('/product',data)

    if host_name:
        print_with_timestamp( 'Set Host Name: {}'.format(host_name))
    if server_name:
        print_with_timestamp( 'Set Server Name: {}'.format(server_name))        
    if server_description:
        print_with_timestamp( 'Set Server Description: {}'.format(server_description))


def set_time(timezone=None, ntp=None, ntp_servers=None):

    data = dict()
    if timezone:
        data["timezone"] = timezone
    if ntp.upper() == "OFF":
        data["daemon"] = False    
    else:
        data["daemon"] = True     
    if ntp_servers:
        data["servers"] = ntp_servers.split(",")

    put('/time',data)

    if timezone:
        print_with_timestamp( 'Set Timezone: {}'.format(timezone))
    if ntp:
        print_with_timestamp( 'Set time from NTP: {}'.format("Yes"))        
    if ntp_servers:
        print_with_timestamp( 'Set NTP Servers: {}'.format(ntp_servers))


###
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
        print('\tNo imported/active pools found ')

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


###
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

        
def network(nic_name, new_ip_addr, new_mask, new_gw, new_dns):
    global node
    error = ''
    timeouted = False
    
    if new_ip_addr is None:
        sys_exit( 'Error: Expected, but not specified --new_ip for {}'.format(nic_name))
    # list_of_ip
    dns = new_dns_convert_to_list(new_dns)
    for ip in [new_ip_addr, new_mask, new_gw] + dns if dns else []:
        if ip:
            if not valid_ip(ip):
                sys_exit( 'IP address {} is invalid'.format(new_ip_addr))
    endpoint = '/network/interfaces/{INTERFACE}'.format(
                   INTERFACE=nic_name)
    data = dict(configuration="static", address=new_ip_addr, netmask=new_mask)
    if new_gw:
        data["gateway"]=new_gw
    try:
        put(endpoint,data)
    except Exception as e:
        error = str(e)
        # in case the node-ip-address changed, the RESTapi request cannot complete as the connection is lost due to IP change
        # e : HTTPSConnectionPool(host='192.168.0.80', port=82): Read timed out. (read timeout=30)
        timeouted = ("HTTPSConnectionPool" in error) and (node in error) and ("timeout" in error)
        if timeouted:
            node = new_ip_addr  #the node ip was changed
        time.sleep(1)
    
    ## set default gateway
    if new_gw:
        endpoint = '/network/default-gateway'
        data = dict(interface=nic_name)
        put(endpoint,data)
    if dns is not None:
        endpoint = '/network/dns'
        data = dict(servers=dns)
        put(endpoint,data)
    if timeouted:
        sys_exit( 'The accces NIC changed to {}'.format(new_ip_addr))
    

def info():
    global node
    for node in nodes:
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

        key_name={"strg":"Storage Extension Key",
                  "ha_rd":"Advanced HA Metro Cluster",
                  "ha_aa":"Standard HA Cluster"}

        extensions = get('/licenses/extensions')
        print_out_licence_keys = []
        for lic_key in extensions.keys():
            licence_type = key_name[ extensions[lic_key]['type']]
            licence_storage =  extensions[lic_key]['value']
            licence_storage = '' if licence_storage in 'None' else ' {}TB'.format(licence_storage)
            licence_description = '{:>30}:'.format( licence_type + licence_storage) 
            print_out_licence_keys.append('{}\t{}'.format( licence_description , lic_key ))
        print_out_licence_keys.sort(reverse=True)
        
        print()
        print('{:>30}:\t{}'.format("NODE", node))
        print('{:>30}:\t{}'.format("System Time",system_time))
        print('{:>30}:\t{}'.format("Time Zone",time_zone))
        print('{:>30}:\t{}'.format("Time from NTP",ntp_status))
        print('{:>30}:\t{}'.format("Software Version",version))
        print('{:>30}:\t{}'.format("Serial Number",serial_number))
        print('{:>30}:\t{} TB'.format("Licensed Storage Capacity",storage_capacity))
        print('{:>30}:\t{}'.format("Product Key", product_key))

        for key in print_out_licence_keys :
            print(key)

        print('{:>30}:\t{}'.format("Server Name",server_name))
        print('{:>30}:\t{}'.format("Host Name",host_name))
        print('{:>30}:\t{}'.format("DNS",', '.join([str(ip_addr) for ip_addr in dns])))
        print('{:>30}:\t{}'.format("Default Gateway",default_gateway))
        

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
    jbod = []
    global metro
    metro = False
    
    api = interface(node)
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

    elif action == 'set_time':
        c = count_provided_args(timezone, ntp, ntp_servers)   ## if all provided (not None), c must be equal 3 set_host 
        if c not in (1,2,3):
            sys_exit_with_timestamp( 'Error: set_host command expects at least 1 of arguments: --timezone, --ntp, --ntp_servers')
        set_time(timezone, ntp, ntp_servers)

    elif action == 'network':
        c = count_provided_args(nic_name, new_ip_addr, new_mask, new_gw, new_dns)   ## if all provided (not None), c must be equal 5 set_host 
        if c not in (1,2,3,4,5):
            sys_exit_with_timestamp( 'Error: network command expects at least 2 of arguments: --nic, --new_ip, --new_mask, --new_gw --new_dns or just --new_dns')
        network(nic_name, new_ip_addr, new_mask, new_gw, new_dns)

    elif action == 'info':
        info()

    elif action == 'shutdown':
        shutdown_nodes()

    elif action == 'reboot':
        reboot_nodes()


if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        sys_exit('Interrupted             ')

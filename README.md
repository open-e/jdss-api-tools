
# jdss-api-tools

<b>Remotely execute given JovianDSS command. Clone and iSCSI export and other commands to control JovianDSS remotely</b>
<br>Note:
Please enable the REST access in GUI :
System Settings -> Administration -> REST access
<br>

Show help:
	jdss-api-tools.exe --help

EXAMPLES:

<br>1. Create clone of iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.
    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the target exports most recent data every run.
    The example is using default password and port.
    Tools automatically recognize the volume type. If given volume is iSCSI volume,
    the clone of the iSCSI volume will be attached to iSCSI target.
    If given volume is NAS dataset, the created clone will be exported via network share
    as shown in the next example.

     jdss-api-tools.exe clone --pool=Pool-0 --volume=zvol00 192.168.0.220


<br>2. Create clone of NAS volume vol00 from Pool-0 and share via new created SMB share.
    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the share exports most recent data every run. The share is invisible by default.
    The example is using default password and port and make the share visible with default share name.

     jdss-api-tools.exe clone --pool=Pool-0 --volume=vol00 --visible 192.168.0.220

    The examples are using default password and port and make the shares invisible.

     jdss-api-tools.exe clone --pool=Pool-0 --volume=vol00 --share_name=vol00_backup 192.168.0.220
     jdss-api-tools.exe clone --pool=Pool-0 --volume=vol01 --share_name=vol01_backup 192.168.0.220


<br>3. Delete clone of iSCSI volume zvol00 from Pool-0 (it deletes the snapshot as well).

     jdss-api-tools.exe delete_clone --pool=Pool-0 --volume=zvol00 192.168.0.220


<br>4. Delete clone of NAS volume vol00 from Pool-0 (it deletes the snapshot as well).

     jdss-api-tools.exe delete_clone --pool=Pool-0 --volume=vol00 192.168.0.220


<br>5. Create clone of existing snapshot on iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.
    The example is using password 12345 and default port.

     jdss-api-tools.exe clone_existing_snapshot --pool=Pool-0 --volume=zvol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 --pswd 12345


<br>6. Create clone of existing snapshot on NAS volume vol00 from Pool-0 and share via new created SMB share.
    The example is using password 12345 and default port.

     jdss-api-tools.exe clone_existing_snapshot --pool=Pool-0 --volume=vol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 --pswd 12345


<br>7. Delete clone of existing snapshot on iSCSI volume zvol00 from Pool-0.
    The example is using password 12345 and default port.

     jdss-api-tools.exe delete_clone_existing_snapshot --pool=Pool-0 --volume=zvol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 --pswd 12345


<br>8. Delete clone of existing snapshot on NAS volume vol00 from Pool-0.
    The example is using password 12345 and default port.

     jdss-api-tools.exe delete_clone_existing_snapshot --pool=Pool-0 --volume=vol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 --pswd 12345


<br>9. Create pool on single node or cluster with single JBOD:
	Pool-0 with 2 * raidz1(3 disks) total 6 disks

     jdss-api-tools.exe create_pool --pool=Pool-0 --vdevs=2 --vdev=raidz1 --vdev_disks=3 192.168.0.220


<br>10. Create pool on Metro Cluster with single JBOD with 4-way mirrors:
	Pool-0 with 2 * mirrors(4 disks) total 8 disks

     jdss-api-tools.exe create_pool --pool=Pool-0 --vdevs=2 --vdev=mirror --vdev_disks=4 192.168.0.220


<br>11. Create pool with raidz2(4 disks each) over 4 JBODs with 60 HDD each.
	Every raidz2 vdev consists of disks from all 4 JBODs. An interactive menu will be started.
	In order to read disks, POWER-ON single JBOD only. Read disks selecting "0" for the first JBOD.
	Next, POWER-OFF the first JBOD and POWER-ON the second one. Read disks of the second JBOD selecting "1".
	Repeat the procedure until all JBODs disk are read. Finally, create the pool selecting "c" from the menu.

     jdss-api-tools.exe create_pool --pool=Pool-0 --jbods=4 --vdevs=60 --vdev=raidz2 --vdev_disks=4 192.168.0.220


<br>12. Shutdown three JovianDSS servers using default port but non default password.

     jdss-api-tools.exe --pswd password shutdown 192.168.0.220 192.168.0.221 192.168.0.222

    or with IP range syntax ".."

     jdss-api-tools.exe --pswd password shutdown 192.168.0.220..222


<br>13. Reboot single DSS server.

     jdss-api-tools.exe reboot 192.168.0.220


<br>14. Set host name to "node220", server name to "server220" and server description to "jdss220".

     jdss-api-tools.exe set_host --host=node220 --server=server220 --description=jdss220 192.168.0.220


<br>15. Set timezone and with NTP-time with default NTP servers.

     jdss-api-tools.exe set_time --timezone=America/New_York 192.168.0.220
     jdss-api-tools.exe set_time --timezone=America/Chicago 192.168.0.220
     jdss-api-tools.exe set_time --timezone=America/Los_Angeles 192.168.0.220
     jdss-api-tools.exe set_time --timezone=Europe/Berlin 192.168.0.220


<br>16. Set new IP settings for eth0 and set gateway-IP and set eth0 as default gateway. Missing netmask option will set default 255.255.255.0.

     jdss-api-tools.exe network --nic=eth0 --new_ip=192.168.0.80 --new_gw=192.168.0.1 192.168.0.220

    Setting new DNS only.

     jdss-api-tools.exe network --new_dns=192.168.0.1 192.168.0.220

    Setting new gateway only. The default gateway will be set automatically.

     jdss-api-tools.exe network --nic=eth0 --new_gw=192.168.0.1 192.168.0.220


<br>17. Create bond examples. Bond types: balance-rr, active-backup, balance-xor, broadcast, 802.3ad, balance-tlb, balance-alb.
	Default = active-backup.

     jdss-api-tools.exe create_bond --bond_nics=eth0,eth1 --new_ip=192.168.0.80 192.168.0.80
     jdss-api-tools.exe create_bond --bond_nics=eth0,eth1 --new_ip=192.168.0.80 --new_gw=192.168.0.1 192.168.0.80
     jdss-api-tools.exe create_bond --bond_nics=eth0,eth1 --bond_type=active-backup --new_ip=192.168.0.80 --new_gw=192.168.0.1 192.168.0.80


<br>18. Delete bond.

     jdss-api-tools.exe delete_bond --nic=bond0 192.168.0.80


<br>19. Bind cluster. Bind node-b: 192.168.0.81 with node-a: 192.168.0.80
    RESTapi user = admin, RESTapi password = password, node-b GUI password = admin

     jdss-api-tools.exe bind_cluster --user=admin --pswd=password --bind_node_password=admin 192.168.0.80 192.168.0.81


<br>20. Set HA-cluster ping nodes. First IP = access node IP, next IPs are new ping nodes
    RESTapi user = administrator, RESTapi password = password, netmask = 255.255.0.0

     jdss-api-tools.exe set_ping_nodes --user=administrator --pswd=password --netmask=255.255.0.0 192.168.0.80 192.168.0.240 192.168.0.241 192.168.0.242

    Same, but with defaults: user = admin, password = admin and netmask = 255.255.255.0

     jdss-api-tools.exe set_ping_nodes 192.168.0.80 192.168.0.240 192.168.0.241 192.168.0.242


<br>21. Set HA-cluster mirror path. Please enter comma separated NICs, the first NIC must be from the same node as the specified access IP.

     jdss-api-tools.exe set_mirror_path --mirror_nics=eth4,eth4 192.168.0.82


<br>22. Create VIP (Virtual IP) examples.

	If cluster is configured both vip_nics must be provided.
	With single node (no cluster) only first vip_nic specified will be used.
	The second vip_nic (if specified) will be ignored.
	Default vip_mask = 255.255.255.0

	 jdss-api-tools.exe create_vip --pool=Pool-0 --vip_name=vip21 --vip_nics=eth2,eth2 --vip_ip=192.168.21.100 --vip_mask=255.255.0.0 192.168.0.80

	 jdss-api-tools.exe create_vip --pool=Pool-0 --vip_name=vip31 --vip_nics=eth2 --vip_ip=192.168.31.100 192.168.0.80


<br>23. Start HA-cluster. Please enter first node IP address only.

     jdss-api-tools.exe start_cluster 192.168.0.82


<br>24. Move (failover) given pool.
    The current active node of given pool will be found and pool will be moved to passive node.

     jdss-api-tools.exe move --pool=Pool-0 192.168.0.82


<br>25. <b>Create storage resource</b>. Creates iSCSI target with volume or SMB share with dataset. iSCSI target with volume

    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=iscsi --volume=zvol00 --target_name=iqn.2018-08:ha-00.target0 --size=1TB --provisioning=thin 192.168.0.220

with defaults: size=1TB, provisioning=thin volume=auto target_name=auto
if target_name=auto(default), the cluster name "ha-00" will be used in the auto-target_name. In this example target name will be: iqn.2018-09:ha-00.target000
if iqn.2018-09:ha-00.target000 and zvol000 allreday exist program will use next one: if iqn.2018-09:ha-00.target1 and zvol001

    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=iscsi --cluster=ha-00 192.168.0.220

   with missing --cluster=ha-00, it will produce same result as "ha-00" is default cluster name.

    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=iscsi 192.168.0.220
       
    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=smb --volume=vol000 --share_name=data  192.168.0.220

   with defaults: volume=auto share_name=auto

    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=smb  192.168.0.220

   and multi-resource with --quantity option, starting consecutive number from zero (default)

    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=iscsi --quantity=5  192.168.0.220

   and multi-resource with --quantity option, but starting consecutive number from 5 (--start_with=10)
    
    %(prog)s create_storage_resource --pool=Pool-0 --storage_type=iscsi --quantity=5 --start_with=10  192.168.0.220
    

<br>26. Scrub all pools. If the node belongs to cluster, scrub all pools in cluster.

    %(prog)s scrub 192.168.0.220

   Scrub specified pools only.
   
    %(prog)s scrub --pool=Pool-0 192.168.0.220
    %(prog)s scrub --pool=Pool-0 --pool=Pool-1 --pool=Pool-2 192.168.0.220
    
   Stop of runnning scrub on all pools.
   
    %(prog)s scrub --action=stop 192.168.0.220
 

<br>27. Print system info.

     jdss-api-tools.exe info 192.168.0.220

#########################################<br>
After any modifications of source jdss-tools.py, run pyinstaller to create new jdss-tools.exe:

	C:\Python27\Scripts>pyinstaller.exe --onefile jdss-api-tools.py

And try it:

	C:\Python27>dist\jdss-api-tools.exe -h

Missing Python modules need to be installed with pip, e.g.:

	C:\Python27\Scripts>pip install ipcalc


NOTE:
In case of error: "msvcr100.dll missing...",
download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe

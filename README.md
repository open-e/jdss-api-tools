 ![Project Icon](JovianDSS-Logo.png)
# jdss-api-tools


<b>Execute single or batch commands for automated setup or to control JovianDSS remotely.</b>


<b>Commands:</b>

 <pre>clone                         	clone_existing_snapshot       	create_pool
scrub                         	set_scrub_scheduler           	create_storage_resource
modify_volume                 	attach_volume_to_iscsi_target 	detach_volume_from_iscsi_target
detach_disk_from_pool         	delete_clone                  	delete_clones
delete_snapshots              	delete_clone_existing_snapshot	set_host
set_time                      	network                       	create_bond
delete_bond                   	bind_cluster                  	set_ping_nodes
set_mirror_path               	create_vip                    	start_cluster
move                          	info                          	list_snapshots
shutdown                      	reboot                        	batch_setup
create_factory_setup_files    	activate                      	import
</pre>

<b>Commands description:</b>

 1. <b>Create clone</b> of iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.

    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the target exports most recent data every run.
    The example is using default password and port.
    Tools automatically recognize the volume type. If given volume is iSCSI volume,
    the clone of the iSCSI volume will be attached to iSCSI target.
    If given volume is NAS dataset, the created clone will be exported via network share.
    The example is using default password and port.

        jdss-api-tools.exe clone --pool Pool-0 --volume zvol00 --node 192.168.0.220

    By default primarycache and secondarycache is set to all. It can be disabled or set to cache metadata only:
        jdss-api-tools.exe clone --pool Pool-0 --volume zvol00 --primarycache none --secondarycache none --node 192.168.0.220
        jdss-api-tools.exe clone --pool Pool-0 --volume zvol00 --primarycache metadata --secondarycache none --node 192.168.0.220

    <b>Create clone</b> of NAS volume vol00 from Pool-0 and share via new created SMB share.

    Every time it runs, it will delete the clone created last run and re-create new one.
    So, the share exports most recent data every run. The share is invisible by default.
    The example is using default password and port and makes the share <b>visible</b> with default share name
    and primarycache set to metadata only.

        jdss-api-tools.exe clone --pool Pool-0 --volume vol00 --visible --primarycache metadata --node 192.168.0.220
    
    The following examples are using default password and port and make the shares <b>invisible</b>.

        jdss-api-tools.exe clone --pool Pool-0 --volume vol00 --share_name vol00_backup --node 192.168.0.220
        jdss-api-tools.exe clone --pool Pool-0 --volume vol01 --share_name vol01_backup --node 192.168.0.220


    <b>Create clone</b> of existing snapshot on iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.

    The example is using password 12345 and default port.

        jdss-api-tools.exe clone_existing_snapshot --pool Pool-0 --volume zvol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345


    <b>Create clone</b> of existing snapshot on NAS volume vol00 from Pool-0 and share via new created SMB share.

    The example is using password 12345 and default port.

        jdss-api-tools.exe clone_existing_snapshot --pool Pool-0 --volume vol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345



 2. <b>Delete clone</b> of iSCSI volume zvol00 from Pool-0.

        jdss-api-tools.exe delete_clone --pool Pool-0 --volume zvol00 --node 192.168.0.220


    <b>Delete clone</b> of NAS volume vol00 from Pool-0.

        jdss-api-tools.exe delete_clone --pool Pool-0 --volume vol00 --node 192.168.0.220


    <b>Delete clone</b> of existing snapshot on iSCSI volume zvol00 from Pool-0.

    The example is using password 12345 and default port.

        jdss-api-tools.exe delete_clone_existing_snapshot --pool Pool-0 --volume zvol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345


    <b>Delete clone</b> of existing snapshot on NAS volume vol00 from Pool-0.

    The example is using password 12345 and default port.

        jdss-api-tools.exe delete_clone_existing_snapshot --pool Pool-0 --volume vol00 --snapshot autosnap_2018-06-07-080000 --node 192.168.0.220 --pswd 12345


 3. <b>Delete clones</b> (time-based).

    Delete clones of provided volume and pool with creation date older than provided time period.

    This example deletes clones of iSCSI zvol00 from Pool-0 with 5 seconds prompted delay, older than 2 months and 15 days.

        jdss-api-tools.exe delete_clones --pool Pool-0 --volume zvol00 --older_than 2months 15days --delay 5 --node 192.168.0.220

    The older_than option is human readable clone age written with or without spaces with following units:
    year(s),y   month(s),m   week(s),w   day(s),d   hour(s),h   minute(s),min   second(s),sec,s
    Examples:  2m15d  -> two and a half months
               3w1d12h -> three weeks, one day and twelf hours
               2hours30min -> two and a half hours
               2hours 30min -> two and a half hours (with space between)

    <b>Delete all (older_than 0 seconds) clones</b> of NAS volume vol00 from Pool-0.

        jdss-api-tools.exe delete_clones --pool Pool-0 --volume vol00 --older_than 0seconds --delay 1 --node 192.168.0.220

    In order to delete all clones, the older_than must be zero.
    If the older_than option is missing, nothing will be deleted.


 4. <b>Delete snapshots</b> (time-based).

    Delete snapshots of provided volume and pool with creation date older than provided time period.

    This example deletes snapshots of iSCSI zvol00 from Pool-0 with 1 seconds prompted delay, older than 2 months and 15 days.

        jdss-api-tools.exe delete_snapshots --pool Pool-0 --volume zvol00 --older_than 2months 15days --delay 1 --node 192.168.0.220

    The older_than option is human readable clone age written with or without spaces with following units:
    year(s),y   month(s),m   week(s),w   day(s),d   hour(s),h   minute(s),min   second(s),sec,s
    Examples:  2m15d  -> two and a half months
               3w1d12h -> three weeks, one day and twelf hours
               2hours30min -> two and a half hours
               2hours 30min -> two and a half hours (with space between)

    <b>Delete all (older_than 0 seconds) snapshots</b> of NAS volume vol00 from Pool-0.

        jdss-api-tools.exe delete_snapshots --pool Pool-0 --volume vol00 --older_than 0seconds --delay 1 --node 192.168.0.220

    In order to delete all snapshots, the older_than must be zero.
    If the older_than option is missing, nothing will be deleted.


 5. <b>Create pool</b> on single node or cluster with single JBOD:

    Pool-0 with 2 * raidz1 (3 disks) total 6 disks.

    Command create_pool creates data-groups only and use disks within provided disk_size_range,

        jdss-api-tools.exe create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --disk_size_range 900GB 2TB --node 192.168.0.220

    if disk_size_range is omitted it takes disks with size near to avarage-disks-size. Default size difference is 5GB.

        jdss-api-tools.exe create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --node 192.168.0.220

    The default size difference of 5GB can be changed with tolerance option.

        jdss-api-tools.exe create_pool --pool Pool-0 --vdevs 2 --vdev raidz1 --vdev_disks 3 --tolerance 50GB --node 192.168.0.220


    <b>Create pool</b> on Metro Cluster with single JBOD with 4-way mirrors:

    Pool-0 with 2 * mirrors (4 disks) total 8 disks.

        jdss-api-tools.exe create_pool --pool Pool-0 --vdevs 2 --vdev mirror --vdev_disks 4 --node 192.168.0.220


    <b>Create pool</b> with raidz2 (4 disks each) over 4 JBODs with 60 HDD each.

    Every raidz2 vdev consists of disks from all 4 JBODs. An interactive menu will be started.
    In order to read disks, POWER-ON single JBOD only. Read disks selecting "0" for the first JBOD.
    Next, POWER-OFF the first JBOD and POWER-ON the second one. Read disks of the second JBOD selecting "1".
    Repeat the procedure until all disks from all JBODs are read. Finally, create the pool selecting "c" from the menu.

        jdss-api-tools.exe create_pool --pool Pool-0 --jbods 4 --vdevs 60 --vdev raidz2 --vdev_disks 4 --node 192.168.0.220


 6. <b>Import pool</b>:

    Get list of pools available for import:

        jdss-api-tools.exe import --node 192.168.0.220

    Import pool Pool-0:

        jdss-api-tools.exe import --pool Pool-0 --node 192.168.0.220

    Import pool Pool-0 with force option.
    Forces import, even if the pool appears to be potentially active.

        jdss-api-tools.exe import --pool Pool-0 --force --node 192.168.0.220

    Forced import of Pool-0 with missing write-log device.

        jdss-api-tools.exe import --pool Pool-0 --force --ignore_missing_write_log --node 192.168.0.220

    Forced import of Pool-0 in recovery mode for a non-importable pool.
    Attempt to return the pool to an importable state by discarding the last few transactions.
    Not all damaged pools can be recovered by using this option.
    If successful, the data from the discarded transactions is irretrievably lost.

        jdss-api-tools.exe import --pool Pool-0 --force --recovery_import --node 192.168.0.220

    Forced import of Pool-0 in recovery mode and missing write-log device.

        jdss-api-tools.exe import --pool Pool-0 --force --recovery_import --ignore_missing_write_log --node 192.168.0.220

    Forced import of Pool-0 in recovery mode and ignore unfinished resilver.

        jdss-api-tools.exe import --pool Pool-0 --force --recovery_import --ignore_unfinished_resilver --node 192.168.0.220


 7. <b>Shutdown</b> three JovianDSS servers using default port but non default password,

        jdss-api-tools.exe --pswd password shutdown --nodes 192.168.0.220 192.168.0.221 192.168.0.222

    or with IP range syntax "..".

        jdss-api-tools.exe --pswd password shutdown --node 192.168.0.220..222


 8. <b>Reboot</b> single JovianDSS server.

        jdss-api-tools.exe reboot --node 192.168.0.220


 9. <b>Set host name</b> to "node220", server name to "server220" and server description to "jdss220".

        jdss-api-tools.exe set_host --host node220 --server server220 --description jdss220 --node 192.168.0.220


10. <b>Set timezone and NTP-time</b> with default NTP servers.

        jdss-api-tools.exe set_time --timezone America/New_York --node 192.168.0.220
        jdss-api-tools.exe set_time --timezone America/Chicago --node 192.168.0.220
        jdss-api-tools.exe set_time --timezone America/Los_Angeles --node 192.168.0.220
        jdss-api-tools.exe set_time --timezone Asia/Tokyo --node 192.168.0.220
        jdss-api-tools.exe set_time --timezone Europe/Berlin --node 192.168.0.220

    Set NTP servers only.

        jdss-api-tools.exe set_time --ntp_servers 0.pool.ntp.org 1.pool.ntp.org --node 192.168.0.220


11. <b>Set new IP settings</b> for eth0 and set gateway-IP and set eth0 as default gateway.

    Missing netmask option will set default 255.255.255.0.

        jdss-api-tools.exe network --nic eth0 --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.220

    Setting new DNS only,

        jdss-api-tools.exe network --new_dns 192.168.0.1 --node 192.168.0.220

    or with 2 DNS servers.

        jdss-api-tools.exe network --new_dns 192.168.0.1 192.168.100.254 --node 192.168.0.220

    Setting new gateway only. The default gateway will be set automatically.

        jdss-api-tools.exe network --nic eth0 --new_gw 192.168.0.1 --node 192.168.0.220


12. <b>Create bond</b> examples. Bond types: balance-rr, active-backup.

    Default = active-backup.

        jdss-api-tools.exe create_bond --bond_nics eth0 eth1 --new_ip 192.168.0.80 --node 192.168.0.80
        jdss-api-tools.exe create_bond --bond_nics eth0 eth1 --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.80
        jdss-api-tools.exe create_bond --bond_nics eth0 eth1 --bond_type active-backup --new_ip 192.168.0.80 --new_gw 192.168.0.1 --node 192.168.0.80


13. <b>Delete bond</b>.

        jdss-api-tools.exe delete_bond --nic bond0 --node 192.168.0.80


14. <b>Bind cluster</b>. Bind node-b (192.168.0.81) with node-a (192.168.0.80).

    RESTapi user = admin, RESTapi password = password, node-b GUI password = admin.

        jdss-api-tools.exe bind_cluster --user admin --pswd password --bind_node_password admin --node 192.168.0.80 192.168.0.81


15. <b>Set HA-cluster ping nodes</b>.

    RESTapi user = administrator, RESTapi password = password, netmask = 255.255.0.0.

        jdss-api-tools.exe set_ping_nodes --user administrator --pswd password --netmask 255.255.0.0 --ping_nodes 192.168.0.240 192.168.0.241 192.168.0.242 --node 192.168.0.80

    Same, but with defaults: user = admin, password = admin and netmask = 255.255.255.0.

        jdss-api-tools.exe set_ping_nodes --ping_nodes 192.168.0.240 192.168.0.241 192.168.0.242 --node 192.168.0.80


16. <b>Set HA-cluster mirror path</b>. Please enter space separated NICs, the first NIC must be from the same node as the specified access IP.

        jdss-api-tools.exe set_mirror_path --mirror_nics eth4 eth4 --node 192.168.0.82


17. <b>Create VIP (Virtual IP)</b> examples.

        jdss-api-tools.exe create_vip --pool Pool-0 --vip_name vip21 --vip_nics eth2 eth2 --vip_ip 192.168.21.100 --vip_mask 255.255.0.0 --node 192.168.0.80
        jdss-api-tools.exe create_vip --pool Pool-0 --vip_name vip31 --vip_nics eth2 --vip_ip 192.168.31.100 --node 192.168.0.80

    If cluster is configured both vip_nics must be provided.
    With single node (no cluster) only first vip_nic specified will be used.
    The second vip_nic (if specified) will be ignored.
    Default vip_mask = 255.255.255.0.


18. <b>Start HA-cluster</b>. Please enter first node IP address only.

        jdss-api-tools.exe start_cluster --node 192.168.0.82


19. <b>Move (failover)</b> given pool.

    The current active node of given pool will be found and pool will be moved to passive node
    with optional delay in seconds.

        jdss-api-tools.exe move --pool Pool-0 --delay 120 --node 192.168.0.82


20. <b>Create storage resource</b>. Creates iSCSI target with volume (zvol) or SMB/NFS share with dataset.

    Defaults are: size = 1TB, blocksize = 128KB, recordsize = 1MB, provisioning = thin, volume = auto, target = auto, share_name = auto.
    The blocksize or recordsize can be: 4KB, 8KB, 16KB, 32KB, 64KB, 128KB, 256KB, 512KB, 1MB.

    Example for iSCSI target with specified volume, target, size, blocksize and provisioning.

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --volume zvol00 --target iqn.2018-09:target0 --size 1TB --blocksize 64KB --provisioning thin --node 192.168.0.220

    If cluster name is specified, it will be used in the target name. Next examples will create both the same target name.

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --cluster ha-00 --node 192.168.0.220
        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --volume zvol00 --target iqn.2018-09:target0 --cluster ha-00 --node 192.168.0.220

    With missing --target argument, it will produce auto-target name based on the host name.

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --node 192.168.0.220

    If sync (Write Cache sync requests) is not provided the default is set, which is "always" for zvols and "standard" for datasets. Here the sync is set to "disabled".

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --sync disabled --cluster ha-00 --node 192.168.0.220

    Example for SMB share with dataset, using defaults (volume = auto, share_name = auto, sync = standard).

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type smb --node 192.168.0.220

    Example for SMB share with dataset, using specified volume, recordsize, sync and share_name.

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type smb --volume vol00 --recordsize 128KB --sync always --share_name data --node 192.168.0.220

    Example with specified quota and reservation.

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type smb --quota 100GB --reservation 50GB --node 192.168.0.220

    Example for multi-resource with --quantity option, starting consecutive number from zero (default),

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 5 --node 192.168.0.220
        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type smb nfs --quantity 5 --node 192.168.0.220

    and multi-resource with --quantity option, but starting consecutive number with 50 and increment 10.

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 5 --start_with 10 --increment 10 --node 192.168.0.220
        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type smb nfs --quantity 5 --start_with 10 --increment 10 --node 192.168.0.220

    To attach more than single zvol to a target, use --zvols_per_target option.
    This example will create 3 targets with 2 zvols each with following auto-numbering:
    (vol 10,target 10),(vol 11,target 10),(vol 12,target 11),(vol 13,target 11),(vol 14,target 12),(vol 15,target 12).

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 3 --start_with 10 --zvols_per_target 2 --node 192.168.0.220

    This example will create 2 targets with 4 volumes each with following auto-numbering:
    (vol 100,target 100),(vol 101,target 100),(vol 102,target 100),(vol 103,target 100),
    (vol 200,target 200),(vol 201,target 200),(vol 202,target 200),(vol 203,target 200).

        jdss-api-tools.exe create_storage_resource --pool Pool-0 --storage_type iscsi --quantity 2 --start_with 100 --increment 100 --zvols_per_target 4 --node 192.168.0.220


21. <b>Modify volumes settings</b>. Modifiy volume (SAN) or dataset (NAS) setting.

    Current version modify only: Write cache logging (sync) settings.

        jdss-api-tools.exe modify_volume --pool Pool-0 --volume zvol00 --sync always --node 192.168.0.220
        jdss-api-tools.exe modify_volume --pool Pool-0 --volume zvol00 --sync disabled --node 192.168.0.220

        jdss-api-tools.exe modify_volume --pool Pool-0 --volume vol00 --sync always --node 192.168.0.220
        jdss-api-tools.exe modify_volume --pool Pool-0 --volume vol00 --sync standard --node 192.168.0.220
        jdss-api-tools.exe modify_volume --pool Pool-0 --volume vol00 --sync disabled --node 192.168.0.220

    Modify quota and reservation.

        jdss-api-tools.exe modify_volume --pool Pool-0 --volume vol00 --quota 200GB --reservation 80GB --node 192.168.0.220


22. <b>Attach volume to iSCSI target</b>.

        jdss-api-tools.exe attach_volume_to_iscsi_target --pool Pool-0 --volume zvol00 --target iqn.2019-06:ha-00.target0 --node 192.168.0.220


23. <b>Detach volume form iSCSI target</b>.

        jdss-api-tools.exe detach_volume_from_iscsi_target --pool Pool-0 --volume zvol00 --target iqn.2019-06:ha-00.target0 --node 192.168.0.220


24. <b>Detach disk form pool</b>.

    Detach disk from pool works with mirrored vdevs
    or with disks in raidz vdevs which are during or stopped replace process.

        jdss-api-tools.exe detach_disk_from_pool --pool Pool-0 --disk_wwn wwn-0x5000c5008574a736 --node 192.168.0.220


25. <b>Scrub</b> start|stop|status.

    Scrub all pools. If the node belongs to cluster, scrub all pools in cluster.

        jdss-api-tools.exe scrub --node 192.168.0.220

    Scrub on specified pools only.

        jdss-api-tools.exe scrub --pool Pool-0 --node 192.168.0.220
        jdss-api-tools.exe scrub --pool Pool-0 Pool-1 Pool-2 --node 192.168.0.220

    Stop scrub on all pools.

        jdss-api-tools.exe scrub --action stop --node 192.168.0.220

    Scrub status on all pools.

        jdss-api-tools.exe scrub --action status --node 192.168.0.220


26. <b>Set scrub scheduler</b>.

    By default the command searches all pools on node or cluster (if configured) and set default schedule: every month at 0:15 AM.
    Every pool will be set on different month day.

        jdss-api-tools.exe set_scrub_scheduler --node 192.168.0.220

    Set default schedule on Pool-0 and Pool-1 only.

        jdss-api-tools.exe set_scrub_scheduler --pool Pool-0 Pool-1 --node 192.168.0.220

    Set schedule every week on Monday at 1:10 AM on Pool-0 only.

        jdss-api-tools.exe set_scrub_scheduler --pool Pool-0 --day_of_the_month * --day_of_the_week 1 --hour 1 --minute 10 --node 192.168.0.220

    Set schedule every day at 2:30 AM on Pool-0 only.

        jdss-api-tools.exe set_scrub_scheduler --pool Pool-0 --day_of_the_month * --hour 2 --minute 30 --node 192.168.0.220

    Set schedule every second day at 21:00 (9:00 PM) on Pool-0 only.

        jdss-api-tools.exe set_scrub_scheduler --pool Pool-0 --day_of_the_month */2 --hour 21 --minute 0 --node 192.168.0.220

    <b>TIP:</b>
    Quick schedule params check via browser on <b>Pool-0</b> on <b>192.168.0.220</b>:

     <b>https:</b>//<b>192.168.0.220</b>:82/api/v3/pools/<b>Pool-0</b>/scrub/scheduler


27. <b>Generate factory setup files for batch setup</b>.

    It creates and overwrites (if previously created) batch setup files.
    Setup files need to be edited and changed to required setup accordingly.
    For single node setup single node ip address can be specified.
    For cluster, both cluster nodes ip addresses, so it will create setup file for every node.

        jdss-api-tools.exe create_factory_setup_files --nodes 192.168.0.80 192.168.0.81
        jdss-api-tools.exe create_factory_setup_files --nodes 192.168.0.80 192.168.0.81 --ping_nodes 192.168.0.30 192.168.0.40 --mirror_nics bond1 bond1
        jdss-api-tools.exe create_factory_setup_files --nodes 192.168.0.80..81 --ping_nodes 192.168.0.30 192.168.0.40 --mirror_nics eth4 eth4 --new_gw 192.168.0.1 --new_dns 192.168.0.1


28. <b>Execute factory setup files for batch setup</b>.

    This example runs setup for nodes 192.168.0.80 and 192.168.0.81.
    Both nodes need to be fresh rebooted with factory defaults: eth0 = 192.168.0.220.
    First only one node must be started. Once booted, the RESTapi must be enabled via GUI.
    The batch setup will start to configure first node.
    Now, the second node can be booted.
    Once the second node is up, the RESTapi must also be enabled via GUI.

        jdss-api-tools.exe batch_setup --setup_files api_setup_single_node_80.txt api_setup_single_node_81.txt api_setup_cluster_80.txt
        jdss-api-tools.exe batch_setup --setup_files api_test_cluster_80.txt


29. <b>Product activation</b>.

        jdss-api-tools.exe activate --online --node 192.168.0.220

    Sends online Product Activation request.
	On-line activation requires an internet connection.
    Note: The off-line activation is not implemented yet.


30. <b>Print system info</b>.

        jdss-api-tools.exe info --node 192.168.0.220

    The info command lists system information together with only the most recent snapshots.
    In order to list all snapshots use --all_snapshots option,

        jdss-api-tools.exe info --all_snapshots --node 192.168.0.220

    or just --all.

        jdss-api-tools.exe info --all --node 192.168.0.220


31. <b>Print only snapshot info</b>.

        jdss-api-tools.exe list_snapshots --node 192.168.0.220

    The list_snapshots command lists only the most recent snapshots.
    In order to list all snapshots use --all_snapshots option,

        jdss-api-tools.exe list_snapshots --all_snapshots --node 192.168.0.220

    or just --all.

        jdss-api-tools.exe list_snapshots --all --node 192.168.0.220


    Note: If you want complete system information, please use the info command instead.


#############################################################################################
After any modifications of source jdss-api-tools.py, run pyinstaller to create new jdss-api-tools.exe:

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
#############################################################################################

<b>Get help:</b>

         jdss-api-tools.exe -h

<b>Get help for a single command:</b>

         jdss-api-tools.exe create_factory_setup_files
         jdss-api-tools.exe batch_setup
         jdss-api-tools.exe create_pool
      ...

<b>Commands:</b>

 <pre>clone                         	clone_existing_snapshot       	create_pool
scrub                         	set_scrub_scheduler           	create_storage_resource
modify_volume                 	attach_volume_to_iscsi_target 	detach_volume_from_iscsi_target
detach_disk_from_pool         	delete_clone                  	delete_clones
delete_snapshots              	delete_clone_existing_snapshot	set_host
set_time                      	network                       	create_bond
delete_bond                   	bind_cluster                  	set_ping_nodes
set_mirror_path               	create_vip                    	start_cluster
move                          	info                          	list_snapshots
shutdown                      	reboot                        	batch_setup
create_factory_setup_files    	activate                      	import
</pre>
 
 

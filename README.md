
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
    So, the share exports most recent data every run. The share is unvisible by default.
    The example is using default password and port and make the share visible with default share name.

	jdss-api-tools.exe clone --pool=Pool-0 --volume=vol00 --visible 192.168.0.220

	The example is using default password and port and make the share "my_backup_share" unvisible.

  jdss-api-tools.exe clone --pool=Pool-0 --volume=vol00 --share_name=my_backup_share 192.168.0.220



<br>3. Delete clone of iSCSI volume zvol00 from Pool-0 (it deletes the snapshot as well).

	jdss-api-tools.exe delete_clone --pool=Pool-0 --volume=zvol00 192.168.0.220


<br>4. Delete clone of NAS volume vol00 from Pool-0 (it deletes the snapshot as well).

	jdss-api-tools.exe delete_clone --pool=Pool-0 --volume=vol00 192.168.0.220


<br>5. Create clone of existing snapshot on iSCSI volume zvol00 from Pool-0 and attach to iSCSI target.
    The example is using password 12345 and default port.

	jdss-api-tools.exe clone_existing_snapshot --pool=Pool-0 --volume=zvol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 -pswd 12345


<br>6. Create clone of existing snapshot on NAS volume vol00 from Pool-0 and share via new created SMB share.
    The example is using password 12345 and default port.

	jdss-api-tools.exe clone_existing_snapshot --pool=Pool-0 --volume=vol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 -pswd 12345


<br>7. Delete clone of existing snapshot on iSCSI volume zvol00 from Pool-0.
    The example is using password 12345 and default port.

	jdss-api-tools.exe delete_clone_existing_snapshot --pool=Pool-0 --volume=zvol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 -pswd 12345


<br>8. Delete clone of existing snapshot on NAS volume vol00 from Pool-0.
    The example is using password 12345 and default port.

	jdss-api-tools.exe delete_clone_existing_snapshot --pool=Pool-0 --volume=vol00 --snapshot=autosnap_2018-06-07-080000 192.168.0.220 -pswd 12345


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


<br>17. Print system info.

	jdss-api-tools.exe info 192.168.0.220

#
#After any modifications of source jdss-tools.py, run pyinstaller to create new jdss-tools.exe:

	C:\Python27>Scripts\pyinstaller.exe --onefile jdss-api-tools.py
#
And try it:

	C:\Python27>dist\jdss-api-tools.exe -h

NOTE:
In case of error: "msvcr100.dll missing...",
download and install "Microsoft Visual C++ 2010 Redistributable Package (x86)": vcredist_x86.exe

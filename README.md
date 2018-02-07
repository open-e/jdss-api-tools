
# jdss-api-tools

<b>Remotely execute given JovianDSS command. Clone and iSCSI export and other commands to control JovianDSS remotely</b>
<br>Note:
Please enable the REST access in GUI :
Setup -> Administrator setting -> REST access
<br>

Show help:
	jdss-api-tools.exe --help

EXAMPLES:

<br>1. Create Clone of iSCSI volume zvol00 from Pool-0 and attach to iSCSI target. Every time it runs, it will delete the clone created last run and re-create new one. So, the target exports most recent data every run.  The example is using default password and port. Tools automatically recognize the volume type. If given volume is iSCSI volume, the clone of the iSCSI volume will be attached to iSCSI target. If given volume is NAS dataset, the crated clone will be exported via network share as shown in the next example. 

	jdss-api-tools.exe  clone Pool-0 zvol00  192.168.0.220

<br>2. Create Clone of NAS volume vol00 from Pool-0 and share via new created SMB share. Every  time it runs, it will delete the clone created last run and re-create new one. So, the share  exports most recent data every run.  The example is using default password and port.

		jdss-api-tools.exe  clone Pool-0 vol00  192.168.0.220

<br>3. Shutdown three JovianDSS servers using default port but non default password

	jdss-api-tools.exe  --pswd password shutdown 192.168.0.220 192.168.0.221 192.168.0.222
<br>4. Reboot single DSS server

	jdss-api-tools.exe  reboot 192.168.0.220

#
#After any modifications of source jdss-tools.py, run pyinstaller to create new jdss-tools.exe:

	C:\Python27>Scripts\pyinstaller.exe --onefile jdss-api-tools.py
#
And try it:

	C:\Python27>dist\jdss-api-tools.exe -h
NOTE:
In case of error: "msvcr100.dll missing ...",
download and install: Microsoft Visual C++ 2010 Redistributable Package (x86) vcredist_x86.exe

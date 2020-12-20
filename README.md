# TFTPy3
Author: Michael P. Soulier <msoulier@digitaltorque.ca>, Josh Carswell<br/>
Copyright, Michael P. Soulier, 2010.

TFTPy3 is a TFTP library for the Python programming language. It includes
client and server classes, with sample implementations. Hooks are included for
easy inclusion in a UI for populating progress indicators. It supports RFCs
1350, 2347, 2348 and the tsize option from RFC 2349.

If you are moving from Michaels orginal code to this please see the migration notes

## Basic Usage
### Server
By default a server will listen on 127.0.0.1 if an listenip is not specified. 
The default port is 69 and path is ./tftpboot
```
import tftpy

server = tftpy.TftpServer(tftproot='/tmp',listneip='0.0.0.0')
server.listen() # This will loop until the server is killed
```
### Client
#### Uploads
1. Initalize the client with the server details
2. Specify the destination file for the server and the source file
```
import tftpy

client = tftpy.TftpClient(127.0.0.1)
client.Upload('server/dest_file','local/src_file')
```
#### Download
1. Initalize the client with the server details
2. Specify the source file to retrive and the where to save it. 
+
It's not currently possible to use the source file name as the destination file name
```
import tftpy

client = tftpy.TftpClient(127.0.0.1)
client.Download('src_file','dest_file')
```
#### Examples
Additional examples can be found in the examples folder include with this project

## Migrating
With the code rewrite for version 0.9 there are major breaking changes.<br>
For basic usages using only the TftpServer

**Before**
```
import tftpy

server = tftpy.TftpServer('/tmp')
server.listen() #if you were listening globally/using defaults
server.listen('127.0.0.1',1234) #if you were specifing the listening ip and port
```
**After**
```
import tftpy

server = tftpy.TftpServer('/tmp',listenip='0.0.0.0',listenport=69)
server.listen()
```

If you were not using the base TftpServer or TftpClient classes
1. Imports: Only TftpServer, TftpClient and TftpException are imported by default<br/>
2. Modules are now:
   - TftpContexts -> context: Server, Upload, Download
   - TftpPacketFactory -> packet.factory: Factory
   - TftpPacketTypes -> packet.types: ReadRQ, WriteRQ, Ack, OptionAck, Data, Error
   - TftpStates -> states: Start, ReceiveWriteRQ, ReceiveReadRQ, ExpectAck, SentWriteRQ, SentReadRQ, ExpexctData
   - TftpShared Exceptions -> exceptions: TftpException, TftpOptionsError, TftpTimeout, TftpFileNotFoundError
   - TftpShared -> shared
3. Context Changes Download and Upload:
   *Before* - All flags were handled in the child class instead of the parent class
   ``` 
   Download = TftpContextClientDownload(host,port,filename,output,options,packethook,timeout,localip="")
   Upload = TftpContextClientUpload(host,port,filename,input,options,packethook,timeout,localip="")
   ```
   *After* - Args are parsed in the same order as the partent class and only unique arguments are unnamed
   ```
   Download = context.Download(host,port,timeout,output)
   Upload = context.Upload(host,port,timeout,input)
   ```
   Context class arguments are now
   - filename - Server side file name<br/>
     valid: context.Upload, context.Download
   - options - Client Options<br/>
     valid: context.Upload, context.Download
   - packethook - A function call to recieve a copy of all packet Data
     valid: context.Upload, context.Download, context.Server
   - mode - Set the operating mode. Note that only octet is currently supported
     valid: context.Upload, context.Download, context.Server

## Dependencies:
Python 3.6+

## Trifles (Forked):
Project Page: https://github.com/jcarswell/tftpy

### Original Project
Home page: http://tftpy.sf.net/<br/>
Project page: http://sourceforge.net/projects/tftpy/

## License
License is the MIT License

See COPYING in this distribution.

## Limitations:
- Only 'octet' mode is supported.
- The only options supported are blksize and tsize.

## Contributors:
Josh Carswell

## Releases:
### TFTPy 0.9.0 -> TFTPy3 0.1.0:
Major re-write of the code base removing support for python 2. All classes got broken out
into independant modules for increased readability, support and imporateability. All names
should follow the PEP8 naming convention and code likewise generally folloes with the PEP8
standards. All non-byte strings are now using f-string formatting. And the exceptions
should be easier to catch. Additionally so minor bugfixes and enhancements we completed

TODOs:
- Update Documentation and release on RTD
- Fix unittest which appear to be looping infinetly

### 0.8.0:
This version introduces Python 3.X support.
And there was much rejoicing.

### 0.7.0:
Various bugfixes and refactoring for improved logging.
Now requiring python 2.7+ and tightening syntax in
preparation for supporting python 3.

### 0.6.2:
Maintenance release to fix a couple of reported issues.

### 0.6.1:
Maintenance release to fix several reported problems, including a rollover
at 2^16 blocks, and some contributed work on dynamic file objects.

### 0.6.0:
Maintenance update to fix several reported issues, including proper
retransmits on timeouts, and further expansion of unit tests.

### 0.5.1:
Maintenance update to fix a bug in the server, overhaul the documentation for
the website, fix a typo in the unit tests, fix a failure to set default
blocksize, and a divide by zero error in speed calculations for very short
transfers.

Also, this release adds support for input/output in client as stdin/stdout

### 0.5.0:
Complete rewrite of the state machine.
Now fully implements downloading and uploading.

### 0.4.6:
Feature release to add the tsize option. 
Thanks to Kuba Kończyk for the patch.

### 0.4.5:
Bugfix release for compatability issues on Win32, among other small issues.

### 0.4.4:
Bugfix release for poor tolerance of unsupported options in the server.

### 0.4.3:
Bugfix release for an issue with the server's detection of the end of the file
during a download.

### 0.4.2:
Bugfix release for some small installation issues with earlier Python
releases.

### 0.4.1:
Bugfix release to fix the installation path, with some restructuring into a
tftpy package from the single module used previously.

### 0.4:
This release adds a TftpServer class with a sample implementation in bin.
The server uses a single thread with multiple handlers and a select() loop to
handle multiple clients simultaneously.

Only downloads are supported at this time.

### 0.3:
This release fixes a major RFC 1350 compliance problem with the remote TID.

### 0.2:
This release adds variable block sizes, and general option support,
implementing RFCs 2347 and 2348. This is accessible in the TftpClient class
via the options dict, or in the sample client via the --blocksize option.

### 0.1:
This is an initial release in the spirit of "release early, release often".
Currently the sample client works, supporting RFC 1350. The server is not yet
implemented, and RFC 2347 and 2348 support (variable block sizes) is underway,
planned for 0.2.

# Tftpy
Author: Michael P. Soulier <msoulier@digitaltorque.ca>
Copyright, Michael P. Soulier, 2010.

Tftpy is a TFTP library for the Python programming language. It includes
client and server classes, with sample implementations. Hooks are included for
easy inclusion in a UI for populating progress indicators. It supports RFCs
1350, 2347, 2348 and the tsize option from RFC 2349.

## Dependencies:
Python 3.6+

## Trifles (Forked):
Project Page: https://github.com/jcarswell/tftpy

### Original Project
Home page: http://tftpy.sf.net/
Project page: http://sourceforge.net/projects/tftpy/

License is the MIT License

See COPYING in this distribution.

## Limitations:
- Only 'octet' mode is supported.
- The only options supported are blksize and tsize.

## Contributors:
Josh Carswell


## Change Log:

### 0.9.0:
Major re-write of the code base removing support for python 2
Converted all non-byte strings to f-string formatting
Rewrote tests - not working yet
All naming should follow PEP8 conventions
Minor bugfixes and enhancements

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

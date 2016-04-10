Rigserve Developer Notes
v 0.21 2/1/2007
(c) 2006-2007 Martin Ewing AA6E

These programs were developed on a Fedora Core 5 Linux machine running
Python 2.4.3 under Linux kernel 2.6.17.  The only external package
used is pyserial version 2.2 (pyserial.sf.net).  Rigserve should
work on Windows and a variety of other Unix-like systems.

The Rigserve concept is an offshoot of the Hamlib Project, 
www.hamlib.org.  Hamlib is a C-coded library with extensive cross-
language support and many defined and/or supported rigs.  I am
grateful for the long hours of work and discussion that have gone
into Hamlib.

Components

Rigserve.py - Interprets basic commands (open, get, put, etc.) and
listens for TCP connections on a designated port (14652).  An 'open'
command creates a rig object which is an instance of a rig class.  Rig
classes are imported as modules with their own namespaces permitting
any number of rigs of the same or different types to exist at one time.
Assignment of one class definition to one module is also a convenience
for managing files.

Rigserve translates rig commands are translated into calls to rig object
methods. 

Limitations of the current server: No security or user authentication
and no support for multiple simultaneous sessions.  I recommend SSH
port tunneling for remote access over an untrusted network.

The 'Backend' Class

The Backend class, based on 'object', defines the skeleton of Rigserve's
rig support.  Every defined rig interface method should appear in a
dummy form in Backend.  This helps to maintain compatibility among
rig classes, and also helps client programs deal with rigs of different
capabilities without too much detailed reconfiguration.  

Rigserve's "test" command allows the client to probe to find out whether
a particular command is supported at all, and if so, in which class the
method is handled.  If the method is only handled in 'Backend', it is
probably not functional for the current rig.

Rig Family Class, e.g., Tentec.

If there is a family of different rigs that share interface properties,
we can create a "family class" that abstracts those common properties.
A particular rig class would be based on the rig family, which in turn
is based on 'Backend'.  

The Tentec class, for example, at present contains the serial I/O
methods which are probably common to most Ten-Tec rigs.  We have
only implemented the Ten-Tec Orion as a rig class (TT_orion).  When
other Ten-Tec rigs are supported, it is possible that more functions
will be recognized that can be placed in the family class.

The Rig Class in General

Each distinct rig type gets its own distinct rig class.  Actually,
the same hardware rig might need multiple classes to account for
differences in firmware versions.  We have TT_orion_v1 and TT_orion_v2
for version 1 and version 2 of the Orion firmware. 

The major capabilities of the rig, such as modes supported, operating
frequencies, VFO and receiver combinations, etc. are expressed in
upper-case variables at the beginning of the rig class.  These
parameters are generally copied into instance variables defined in
the 'Backend' class.

At the end of a rig class file, we generally provide the typical
Python test for main program status.  If we are executing the module
directly (as the main program), the test code at the end will be run.
This is convenient for development and testing without involving the 
whole Rigserve framework.

The TT_orion Class

While the Ten-Tec Orion and Orion II (models 565 and 566) are basically
similar, there is enough variability in behavior, especially with
different firmware versions, that we may eventually need to have 
multiple Orion-like classes, based on the "ideal" TT_orion.
Nevertheless, for now a single class will be enough.

The Orion is a complicated software-defined radio with dual VFOs, a main
receiver and a subreceiver, and multiple antenna connections.  We have 
tried to capture much of this in the Backend and TT_orion classes.  
We do not want to tailor the architecture to the Orion, however, because 
we may need to deal with other complex rigs that have different 
architectures.  We will probably always have to compromise and not 
provide full access to all possible rig operating configurations.

The Orion has had particular problems servicing serial port requests,
especially with version 1 firmware.  There is a fairly high "misfire"
rate, with commands timing out if they are issued too rapidly or if
they occur at "unlucky" times when the Orion CPU is engaged elsewhere.
Numerous calls to time.sleep seem to help, but they will reduce the
responsiveness.  Users may want to reduce these delay settings depending
on their particular operating environments.

The Orion's memory channel stores mode and bandwidth information along
with VFO frequency.  Furthermore, its data path always goes through one
of the VFOs.  So there are quite a few side effects to using the memory
system, which are not expressed in Rigserve.

The firmware version subclasses TT_orion_v1 and TT_orion_v2 allow us to
express the "personality" differences between the Orion with v1 and v2
firmware.  Note that all Orion II (566) rigs must use v2 firmware.

The IC_r8500 Class

Icom rigs probably should have one or more family classes, but I have
implemented the R8500 entirely in a single class.  This imports
a module designed for another application where the detailed rig
protocols are coded.  (Modules do sometimes get reused!)

This receiver is naturally much simpler than the Orion, but it has
features that are hard to implement.  The scanner-like functions and
the memory "package" that contains much more than a VFO frequency have
not been implemented at this point.

Availability & Participation

Rigserve is now hosted on Sourceforge.net.  Periodic releases will be
available http://sourceforge.net/projects/rigserve.  You may use the
latest SVN repository sources by following the Sourceforge instructions
for anonymous access.  Users may ask for help on the Rigserve support
forums on Sourceforge.

I encourage any and all Python coders who to help extend
Rigserve, especially to implement more rig backend classes.  You need
to get a personal Sourceforge account and then email me for developer
access.

73,
Martin Ewing AA6E
ewing @@ alum.mit.edu

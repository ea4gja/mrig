Backend information
v 0.31 4/29/08
(c) 2006-2008 Martin Ewing AA6E

The Backend class defines the structure for all backends, including
all the methods that will be available to rigserve.

At this time, the following subclasses are defined:

TT_orion, which is based on Tentec, which is based on Backend.

TT_orion_v1, based on TT_orion, with S-meter calibration derived for 
version 1.xxx firmware.

TT_orion_v2, based on TT_orion, with firmware version 2 - specific 
functions, specifically the S-meter calibration.

Tentec (based on Backend) provides generic methods that may someday 
support other rigs from the Ten-Tec company.  Only the Orion (model 
565/566) is currently developed.

IC_r8500 is based on Icom.  Icom may eventually support other Icom
rigs.

IC_r8500 uses the module IC_r8500_basic, which was developed in an
earlier project.  In the future, some parts of IC_r8500 may be
abstracted into an Icom general class.

IC_r75 is similar to IC_r8500.

TT_omni6, is based on Icom_trx, because the Ten-Tec Omni VI / VI-Plus 
control interface is based on Icom -- the Icom 735, specifically.

IC_765 based on Icom_trx.  Like the Omni VI, it has a relatively simple
remote command interface.

CAPABILITIES

In v. 0.31, a "capabilities" mechanism is introduced to facilitate "families"
of rigs, especially the Icom family.  Capabilities allow certain features
of the underlying family to be supported for a given rig type.  Capabilities
are needed because rigs in a given family are likely to support different
subsets of the family's class definition.  Within a family (at least the
Icom family) there is no simple class-like inheritance of features, so
OOP subclassing doesn't work very well.  Each rig type can provide an
arbitrary subset of the family methods.



# Run debootstrap through ansible

This role will allow you to bootstrap a system over SSH using ansible. Typical
applications include remote installing via bootable thumb drive or PXE boot or
installing virtual machines using the host system. The author personally uses
this for all his Debian installation needs.

## Features
* **Your own partition layout**: You can choose your own partition layout
* **Encryption**: Encrypt partitions and hard drives with a pre-shared key (it
is strongly suggested you use ansible-vault here)
* **ZFS** is supported, even/especially as a root device

## Limitations
* You can't have the same names for ZFS pools and crypto devices
* no MD RAID / LVM
* requires a /boot and BIOS boot partition for encrypted / ZFS

## Supported distributions
* Debian
  * Stretch
  * Buster (untested)
* Ubuntu
  * bionic (18.04 LTS)
  * cosmic (18.10)
  * disco (19.04)

Minor modifications will likely make it possible to install newer and perhaps
older versions as well, or even other Debian based distributions. There are
some sanity checks executed, depending on lists in vars/main.yml, so you would
need to add the distribution codename there. Pull requests welcome.

## Host system caveats

This will make a few modifications to the system that is being used as install
medium. This includes installing a few packages, otherwise everything should
be cleaned up afterwards.

* It will install the eatmydata and debootstrap package
* It will install cryptsetup for encrypted targets
* It will install ZFS tools when using ZFS

Normally it is assumed that a some sort of PXE or USB rescue system is used,
some caveats apply otherwise with regards to device names. As an example, you
can't use the same name for any device mapper devices (luks encryption) or ZFS
pools. 

# Configuration
## Global variables
`release`: The release codename (**required**, example: *cosmic*)  
`tgt_hostname`: Hostname of the target (**required**)  
`root_password`: Hashed, Salted root password, you can use mkpasswd to create
one (Example: `$1$sfQaZkVR$Vo/0pjmJaljzakEQFCr7Q/`, obviously **don't use this
one ;) )**  
`use_serial`: Serial device to use for console / grub  
`use_tmpfs`: Bootstrap to tmpfs, it's quicker and may reduce wear on flash
(**default**: *yes*)  
`use_efi`: In case if a system supports UEFI, "grub-efi" will be installed on a target system otherwise "grub-pc" (**default**: *yes*)  
`kernel_cmdline`: Anything you need/want to pass to the kernel (**default**:
provided by distro)  
`layout`: Dictionary of partitions / devices (**required**, see below)  
`md`: List of DM-RAID devices (see below)  
`lvm`: List of LVM volumes (see below)  
`install_ppa`: PPAs to install (**Ubuntu Only**, see below)  
`install_packages`: List of packages to install  
`zfs_pool`: ZFS pool (see ZFS section)  
`zfs_fs`: ZFS filesystems (see ZFS section)  
`zfs_root`: ZFS devices to use as root  
`wipe`: Set to to string "ABSOLUTELY" if you wish to wipe the disk, this will
remove any disklabels present as well as issue a TRIM/UNMAP for the device.
Useful when you want to overwrite a target. **Please use extreme caution**  

## Debootstrap user options
`dbstrp_user`:  
  `name`: A name of debootstrap user (**default**: *debootstrap*)  
  `uid`: UID of debootstrap user (**default**: *65533*)  
  `group`: A group name of debootstrap user (**default**: *name of debootstrap user*)  
  `gid`: GID of debootstrap user (**default**: *uid of debootstrap user*)  
  `password`: A hashed password of debootstrap user (**default**: *\**)  
  `non_unique`: Ability to create non unique user (**default**: *yes*)  

## Partition Layout `layout`
Layout is a list of dictionaries, every dictionary representing a target
device. The dictionary contains the device names, as well as another list of
dictionaries representing partitions (as you can see, I like my complex data
structures).

Elements in the device dictionary:  
`device`: Path to the device  
`partitions`: List of partition dictionary  
`skip_grub`: *boolean* set to yes if you want to skip installing grub on this
device (**default** *False*)  

### Partition dictionary
`num`: Ascending number, a limitation here, just make sure it increments with
every element  
`size`: size with qualifier (M for Megabytes etc.), leave empty for the rest
of available space  
`type`: GTID typecode, for example 8200 for linux, see table below for common
type codes  
`fs`: Target filesystem (**optional**, for example ext4, xfs, not needed for
zfs)  
`mount`: Where to mount this device (**optional**, example */boot*)  
`encrypt`: Set to yes if you want encryption  
`target`: Target name for device mapper (**required** when using encryption,
for example *cryptroot*)  
`label` filesystem label to use  
`partlabel` partition label to use, defaults to `label` if defined, otherwise
no label will be set.  

| Type code | Description |
|---|---|
| 8200 | Linux Filesystem |
| 8300 | Linux Swap |
| ef02 | BIOS Boot partition (for grub)|
| fd00 | Linux RAID |
| 8e00 | Linux LVM |

### DM-RAID devices
Within the `md` list you can set up DM RAID devices. List items are
dictionaries supporting the following keys:

`level`: RAID level to be used (one of 0, 1, 4, 5, 6, 10) **required**  
`chunk_size`: RAID chunk size (required for all RAID levels except 1)  
`name`: Device name **required**  
`members`: List of devices to add to RAID  

Encryption and mount options are supported here. Please note that the order is
1. RAID, 2. Encryption, 3. LVM, so it is currently not possible to create a
RAID of two LUKS devices or encrypt an LVM volume. 

### Encryption Options
`passphrase`: Passphrase for encryption, use ansible-vault here please.
(**required** when using encryption)  
`cipher`: Encryption cipher (**default** *aes-xts-plain64*)  
`hash`: Hash type for LUKS (**default** *sha512*)  
`iter-time`: Time to spend on passphrase processing (**default** *5000*)
`key-size`: Encryption key size (**default** *256*, values depend on cipher, for AES *128*, *256*, *512*)  
`luks-type`: LUKS metadata type (**Default** *luks2*)  
`luks-sector-size`: Sector size for LUKS encryption (**default** *512*, possible values: *512*, *4096*)   
`target`: Device name to be used (**required**)  

### LVM configuration
LVM pvs can be created on disks, partitions as well as encrypted devices (use
/dev/mapper/`target` for LUKS). This is a list of dictionaries, dictionary keys
from partition dictionary can be used (except encryption) like `mount`, `fs`
etc. 

`lvm`: Dictionary of lvol options, these are passed to the [lvol noduule](https://docs.ansible.com/ansible/latest/modules/lvol_module.html)
as such, all options available to that module can be used. 

#### Example device with partitions:
```
layout:
  - device: '/dev/sdb'
    partitions:
      - num: 1
        size: 1M
        type: ef02
      - num: 2
        size: 253M
        type: 8200
        fs: ext4
        mount: /boot
      - num: 3 # Notice absence of size here, will use full disk
        type: 8200
        fs: ext4
        mount: /
```

## PPA to install, for Ubuntu `install_ppa`
Simple list of PPA to use, example:
```
install_ppa:
  - ppa:nils-nm/zfs-linux-unofficial
```

## ZFS configuration
### Pool definition `zfs_pool`
This defines the devices to use for the ZFS pool, you can use devices and
targets defined in `layout`. A list of dictionaries with the following
elements:

`poolname`: name of the ZFS pool (**required**, example *rpool*)  
`devices`: List of devices, you can insert key words like mirror, raidz etc.
like you would when using zpool create. (**required**, example below)  
`options`: List of options for the pool  
`fs_options`: Options for all filesystems in that pool  

### ZFS Filesystems / Datasets to create `zfs_fs`
This looks a lot like the pool definition above, again a list of dictionaries
(they call me the one trick pony). Dictionary definition:

`path`: Path of the dataset, make sure that they are in the correct order,
(**required**, example: *rpool/root*)  
`options`: List of filesystem options, see examples

### Set the root / boot fs for ZFS `zfs_root`
This is used when you want to use ZFS as your root filesystem. Set it to the
dataset which you want to use as root, example: *rpool/ROOT/Ubuntu*

#### ZFS example:
This example is plucked from my own configuration, it will create a lot of
datasets with different options and should give you a good overview over
the possibilities.

```
zfs_pool:
  - poolname: rpool
    devices:
    - /dev/mapper/cryptroot
    options:
    - ashift=12
    fs_options:
    - canmount=off
    - mountpoint=/
    - compression=lz4
    - atime=off
    - normalization=formD

zfs_fs:
  - path: 'rpool/ROOT'
    options:
    - canmount=off
    - mountpoint=none
  - path: 'rpool/ROOT/ubuntu'
    options:
    - mountpoint=/
  - path: 'rpool/home'
    options:
    - setuid=off
  - path: 'rpool/home/root'
    options:
    - mountpoint=/root
  - path: 'rpool/var'
    options:
    - exec=off
    - setuid=off
    - mountpoint=legacy
    mount: /var
  - path: 'rpool/var/cache'
    options:
    - 'com.sun:auto-snapshot=false'
    - mountpoint=legacy
    mount: /var/cache
  - path: 'rpool/var/log'
    optons:
    - mountpoint=legacy
    mount: /var/log
  - path: 'rpool/var/spool'
    optons:
    - mountpoint=legacy
    mount: /var/spool
  - path: 'rpool/var/tmp'
    optons:
    - mountpoint=legacy
    mount: /var/tmp
  - path: 'rpool/var/lib'
    optons:
    - mountpoint=legacy
    mount: /var/lib
  - path: 'rpool/var/lib/dpkg'
    options:
    - exec=on
    - mountpoint=legacy
    mount: /var/lib/dpkg
  - path: 'rpool/srv'

zfs_root: 'rpool/ROOT/ubuntu'
```

## Test playbook for vagrant
The directory meta/tests contains a test playbook, inventories and Vagrantfile for
local testing. The vagrant box by default contains three devices, one for the
source vagrant box and target devices for your install (/dev/sdb, /dev/sdc). To
test your new installation you would have to switch boot devices in the SeaBIOS
boot menu (easily achieved via the VirtualBox GUI). **Currently, only
VirtualBox is supported**.

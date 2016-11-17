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
* Pre-select packages to be installed, also supports using PPA on linux
* Place SSH keys for your users
* Will create new, stronger SSH Keys

## Limitations
* You can't have the same names for ZFS pools and crypto devices
* currently no UEFI support (grub only)
* no MD RAID / LVM
* requires a /boot and BIOS boot partition for encrypted / ZFS

## Supported distributions
* Debian
  * Jessie
* Ubuntu
  * xenial
  * yakkety

Minor modifications will likely make it possible to install newer and perhaps
older versions as well.

## Host system caveats

This will make a few modifications to the system that is being used as install
medium. This includes installing a few packages, otherwise everything should 
be cleaned up afterwards. 

* It will install the eatmydata and debootstrap package
* It will install cryptsetup for encrypted targets
* It will install ZFS tools when using ZFS

As a result, the host system **must** be encrypted. 

# Configuration 
## Global variables
`release`: The release codename (**required**, example: *yakkety*)  
`tgt_hostname`: Hostname of the target (**required**)
`root_password`: Hashed, Salted root password, you can use mkpasswd to create 
one (Example: `$1$sfQaZkVR$Vo/0pjmJaljzakEQFCr7Q/`, obviously **don't use this
one ;) )**  
`use_serial`: Serial device to use for console / grub  
`use_tmpfs`: Bootstrap to tmpfs, it's quicker and may reduce wear on flash 
(**default**: *yes*)  
`kernel_cmdline`: Anything you need/want to pass to the kernel (**default**: 
provided by distro)  
`layout`: Dictionary of partitions / devices (**required**, see below)  
`install_ppa`: PPAs to install (**Ubuntu Only**, see below)  
`install_packages`: List of packages to install  
`network`: Network configuration (**required**, see below)  
`users`: User setup (**required**, see below)  
`zfs_pool`: ZFS pool (see ZFS section)  
`zfs_fs`: ZFS filesystems (see ZFS section)  
`zfs_root`: ZFS devices to use as root

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
`passphrase`: Passphrase for encryption, use ansible-vault here please.
(**required** when using encryption)  
`target`: Target name for device mapper (**required** when using encryption,
for example *cryptroot*)  

| Type code | Description |
|---|---|
| 8200 | Linux Filesystem |
| 8300 | Linux Swap |
| ef02 | BIOS Boot partition (for grub)|
| fd00 | Linux RAID |
| 8e00 | Linux LVM | 


### Example device with partitions:
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

## Network Settings, `network`
This is a list of networks, this supports simple IPv4 config and dhcp, as well
as specifying your own configuration. 

Network dictionary structure:
`interface`: Device name of the interface (**required**, example `eth0`, `ens3`)  
`ipv4`: dict of IPv4 settings (optional)
`manual`: Manual configuration, see *interfaces*(5) man page for syntax. 

ipv4 dictionary structure:
`address`: IP Address/Netmask of the interface or *dhcp* for using dhcp,
(**required**, example: *192.0.2.56/24*)  
`gateway`: Default Gateway, (**optional**, example: *192.0.2.1*)  

### Examples
```
network:
  - interface: eth0
      address: dhcp
```

```
network:
  - interface: br0
    manual: > 
      auto br0
      iface br0 inet static
      address: 192.0.2.2/24
      bridge_ports en01 en02
      bridge_waitport 0
      bridge_fd 0
      bridge_stp off 
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

### ZFS example: 
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
  - path: 'rpool/ROOT/{{ release }}'
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
  - path: 'rpool/var/cache'
    options:
    - 'com.sun:auto-snapshot=false'
  - path: 'rpool/var/log'
  - path: 'rpool/var/spool'
  - path: 'rpool/var/tmp'
  - path: 'rpool/var/lib'
  - path: 'rpool/var/lib/dpkg'
    options:
    - exec=on
  - path: 'rpool/srv'

zfs_root: 'rpool/ROOT/{{ release }}'
```
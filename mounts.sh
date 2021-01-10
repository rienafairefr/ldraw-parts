#!/usr/bin/env bash

# hack to write inside a
# FAT32 partition for case-insensitiveness

dd if=/dev/zero of=loopbackfile.img bs=120M count=10
sudo losetup -fP loopbackfile.img
mkfs.vfat loopbackfile.img

mkdir -p repo

loop=`losetup -j loopbackfile.img | awk '{sub(/:/,"",$1); print $1}'`
uid=`id -u`
gid=`id -g`
sudo mount -o loop -o rw,uid=$uid,gid=$gid $loop fs

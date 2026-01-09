#!/bin/bash
APPDIR=~/squashfs-root
$APPDIR/runtime/default/lib64/ld-linux-x86-64.so.2 \
  --library-path $APPDIR:$APPDIR/usr/lib/x86_64-linux-gnu \
  $APPDIR/CuraEngine "$@"

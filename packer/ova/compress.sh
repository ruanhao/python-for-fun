
#!/bin/bash

set -e -x

staging_dir=$1

# round-trip through vdi format to get rid of deflate compression in vmdk
for f in ${staging_dir}/*.vmdk; do
  VBoxManage clonehd --format vdi $f $f.vdi
  VBoxManage closemedium disk --delete $f
  VBoxManage modifyhd --compact $f.vdi
  VBoxManage clonehd --format vmdk $f.vdi $f
  VBoxManage closemedium disk --delete $f.vdi
  VBoxManage closemedium disk $f
done


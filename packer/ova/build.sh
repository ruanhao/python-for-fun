#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
set -x
set -e

_SCRIPT_NAME=$(basename $0)
_SCRIPT_DIR=$(cd $(dirname $0); pwd)

. ${_SCRIPT_DIR}/scripts/common/defaults.sh
. ${_SCRIPT_DIR}/scripts/common/functions.sh

image_name="my-linux"
os_id=ubuntu
os_code=focal
os_version=16.04


while getopts ":t:o:d:v:f:b:c:i:p:" opt; do
    case ${opt} in
    c)
        os_code=${OPTARG}
        ;;
    \?)
        echo "Invalid option: -$OPTARG" >&2
        exit 1
    esac
done


DATE=`TZ="Asia/Shanghai" date +%Y%m%d`
VERSION_TAG=v1.0.0.${DATE}

cpus=1
memory=512
swap_size=256
disk_size=5000

cp -f ./http/ubuntu/preseed.cfg.template ./http/ubuntu/preseed.cfg
sed -i -e "s/SWAP_SIZE/${swap_size}/g" ./http/ubuntu/preseed.cfg

staging_dir=${_SCRIPT_DIR}/${image_name}-$os_code-output
rm -rf $staging_dir

packer build -force -var os_code=$os_code -var output_dir=${staging_dir} -var image_name=${image_name} -var vm_version=${VERSION_TAG} -var headless=true -var disk_size=${disk_size} -var cpus=${cpus} -var memory=${memory} build-$os_code.json

rm -f ${staging_dir}/*.vdi
./compress.sh ${staging_dir}

# generating image from VMDK
source_vmdk_file=${staging_dir}/${image_name}-${VERSION_TAG}-disk001.vmdk
${_SCRIPT_DIR}/scripts/vm-image/generate_ova.sh ${image_name} ${VERSION_TAG} ${source_vmdk_file} templates/${image_name}.ovf ${staging_dir}

final_artifact="${staging_dir}/${image_name}-${VERSION_TAG}-$os_code.ova"
mv ${staging_dir}/${image_name}-${VERSION_TAG}.ova $final_artifact
PRIVATE_BUILD_FOLDER="/home/nexus/nexus/sonatype-work/nexus/storage/snapshots/private_build/"
NS_SNAPSHOT_PRIVATE_BUILD_FOLDER="${ARTIFACT_SERVER_USER}@${ARTIFACT_SERVER}:$PRIVATE_BUILD_FOLDER"
remotelyDelete ${ARTIFACT_SERVER_USER}@${ARTIFACT_SERVER} ${ARTIFACT_SERVER_PWD} "${PRIVATE_BUILD_FOLDER}" "${image_name}*" 1
remotelyCopy $final_artifact ${NS_SNAPSHOT_PRIVATE_BUILD_FOLDER} ${ARTIFACT_SERVER_PWD}
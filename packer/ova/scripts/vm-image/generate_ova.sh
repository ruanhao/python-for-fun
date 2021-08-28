#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
set -x
set -e

filename=$1
version=$2
source_vmdk=$3
ovf_file=$4
working_dir=$5

readonly _SCRIPT_NAME=$(basename $0)
readonly _SCRIPT_DIR=$(cd $(dirname $0); pwd)

target_ova=${filename}-${version}.ova
ova_file=${working_dir}/${target_ova}
ovf_file=${_SCRIPT_DIR}/${ovf_file}

internal_ovf_file="${filename}.ovf"
internal_mf_file="${filename}.mf"
internal_vmdk_file="${filename}-disk1.vmdk"


#perpare working directory
#copy files to working directory
cp ${ovf_file} "${working_dir}/${internal_ovf_file}" || exit 1
cp ${source_vmdk} "${working_dir}/${internal_vmdk_file}" || exit 1

#switch to working directory
pushd `dirname "$0"`
cd "${working_dir}"

#generate ova
rm -f ${ova_file} || true
ovftool --shaAlgorithm=SHA1 ${internal_ovf_file} ${ova_file} || exit 1
rm -f ${working_dir}/${internal_ovf_file}

popd

echo "generated ova: ${ova_file}"


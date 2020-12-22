#!/bin/bash
kubectl wait --for=condition=ready --all node --timeout=180s

bash /vagrant/glusterfs_deploy/gk-deploy -gvy --admin-key=abc --user-key=abc /vagrant/glusterfs_deploy/topology.json

cat <<EOF | kubectl create -f -
apiVersion: storage.k8s.io/v1beta1
kind: StorageClass
metadata:
  name: my-gfs-storage
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: kubernetes.io/glusterfs
parameters:
  resturl: $(kubectl get svc/heketi --template 'http://{{.spec.clusterIP}}:{{(index .spec.ports 0).port}}')
  restuser: "admin"
  restuserkey: "abc"
reclaimPolicy: Delete
volumeBindingMode: Immediate
EOF

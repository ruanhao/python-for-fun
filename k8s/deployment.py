#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# minikube start
# kubectl run hello-minikube --image=k8s.gcr.io/echoserver:1.10 --port=8080
# kubectl expose deployment hello-minikube --type=NodePort

import unittest
import kubernetes
from kubernetes import client, config, watch
from pprint import pprint
import yaml



_config = config.load_kube_config()
api_instance = client.AppsV1Api(client.ApiClient(_config))

DEPLOYMENT_NAME = "nginx-deployment"


def run_script(script, echo=True):
  """Returns (stdout, stderr), raises error on non-zero return code"""
  import subprocess
  # Note: by using a list here (['bash', ...]) you avoid quoting issues, as the
  # arguments are passed in exactly this order (spaces, quotes, and newlines won't
  # cause problems):
  proc = subprocess.Popen(['bash', '-c', script],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.PIPE)
  stdout, stderr = proc.communicate()
  if proc.returncode:
    raise Exception('exit code %s (%s)' % (proc.returncode, stderr))
  if echo is True:
    print(f"====== {script} ======")
    print(stdout.decode('utf-8'))

def _remove_none(obj):
  if isinstance(obj, (list, tuple, set)):
    return type(obj)(_remove_none(x) for x in obj if x is not None)
  elif isinstance(obj, dict):
    return type(obj)((_remove_none(k), _remove_none(v))
      for k, v in obj.items() if k is not None and v is not None)
  else:
    return obj

def _print_yaml(obj):
  yaml_def = yaml.dump(_remove_none(obj.to_dict()), default_flow_style=False)
  print(yaml_def)



class UnitTest(unittest.TestCase):

    def tearDown(self):
      run_script('kubectl delete deploy nginx-deployment', False)

    def test_create_deploy(self):
      print()

      # Create container
      container = client.V1Container(
        name="nginx",
        image="nginx:1.7.9",
        ports=[client.V1ContainerPort(container_port=80)])

      # Create and configurate a spec section
      template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "nginx"}),
        spec=client.V1PodSpec(containers=[container]))

      # Create the specification of deployment
      spec = client.ExtensionsV1beta1DeploymentSpec(replicas=3, template=template)

      # Instantiate the deployment object
      deployment = client.ExtensionsV1beta1Deployment(
        api_version="extensions/v1beta1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME),
        spec=spec)

      client.ExtensionsV1beta1Api().create_namespaced_deployment(body=deployment, namespace='default')
      _print_yaml(deployment)
      run_script('kubectl get deploy')
      run_script('kubectl get rs')
      run_script('kubectl get pods --show-labels')


    def test_update_deploy(self):
      self.test_create_deploy()

      # 默认情况下，带有参数 --record 的命令都会被 kubernetes 记录到 etcd 进行持久化
      # 这会占用资源，上生产环境时，通过设置 Deployment.spec.revisionHistoryLimit 来限制最大保留的 revision number
      run_script('kubectl set image deployment/nginx-deployment nginx=nginx:1.9.1 --record')  # also: kubectl edit deployment/nginx-deployment
      run_script('kubectl rollout status deployment/nginx-deployment')

      # 通过创建一个新的 Replica Set 并扩容了 3 个 replica ，同时将原来的 Replica Set 缩容到了 0 个 replica
      run_script('kubectl get rs')

      run_script('kubectl set image deployment/nginx-deployment nginx=nginx:1.10.3 --record')
      run_script('kubectl rollout status deployment/nginx-deployment')
      # 返回 Deployment 的所有 record 记录
      run_script('kubectl rollout history deployment/nginx-deployment')
      # 回滚
      run_script('kubectl rollout undo deployment/nginx-deployment --to-revision=2')
      run_script('kubectl describe deploy nginx-deployment')






if __name__ == '__main__':
    unittest.main(verbosity=2)

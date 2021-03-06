#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import random
from k8s_utils import run
from k8s_utils import ensure_pod_phase
from k8s_utils import ensure_deploy_ready
from k8s_utils import ensure_namespace_phase
from k8s_utils import ensure_replicas
from k8s_utils import get_pod_phase
from k8s_utils import init_test_env
import time
import subprocess

NAME_SPACE = "pod-test"
NS = NAME_SPACE


class UnitTest(unittest.TestCase):

    def test_utils(self):
        run('kubectl explain pods')
        run('kubectl explain pods.spec.containers.image')


    def test_create(self):
        '''
        Please run this testcase at first
        '''
        run('kubectl create -f kubia-manual.yaml')
        run('kubectl create -f kubia-manual-with-labels.yaml')

    def test_log(self):
        # Container logs are automatically rotated daily and every time the log file reaches 10MB in size.
        # The kubectl logs command only shows the log entries from the last rotation.
        run('kubectl logs kubia-manual')
        # specify container name
        run('kubectl logs kubia-manual -c kubia')

    def test_forword_local_port(self):
        p = subprocess.Popen('kubectl port-forward kubia-manual 8888:8080', shell=True)
        time.sleep(1)
        run('curl -Ss localhost:8888')
        p.terminate()

    def test_annotation(self):
        # It’s a good idea to use this format for annotation keys to prevent key collisions.
        run('kubectl annotate pod kubia-manual mycompany.com/someannotation="foo bar"')
        run('kubectl describe pod kubia-manual | grep Annotations')

    def test_liveness_probe(self):
        if get_pod_phase('kubia-liveness') != 'Running':
            run('kubectl delete po kubia-liveness', True)
            ensure_pod_phase('kubia-liveness', 'Deleted')
            run('kubectl create -f kubia-liveness-probe.yaml', True)
            ensure_pod_phase('kubia-liveness')




    def test_namespace(self):
        run('kubectl get po -n kube-system')
        with self.subTest("Creating ns"):
            run('kubectl delete namespace custom-namespace', True)
            ensure_namespace_phase('custom-namespace', 'Deleted')
            run('kubectl create -f custom-namespace.yaml')  # also: kubectl create namespace <your-namespace>
            run('kubectl get ns')

        with self.subTest("Creating pod in other namespace"):
            run('kubectl create -f kubia-manual.yaml -n custom-namespace')
            run('kubectl get po -n custom-namespace')




    def test_labels(self):
        run('kubectl get po --show-labels')
        # only interested in certain labels
        run('kubectl get po -L creation_method,env')

        with self.subTest("Modifying labels"):
            # modify labels of existing pods
            # need to use the --overwrite option when changing existing labels.
            run('kubectl label po kubia-manual creation_method=manual --overwrite')
            run('kubectl label po kubia-manual-v2 env=debug --overwrite')
            run('kubectl get po -L creation_method,env')

        with self.subTest('Listing pods using a label selector'):
            run('kubectl get po -l creation_method=manual --show-labels')
            # list all pods that include the 'env' label
            run('kubectl get po -l env --show-labels')
            # list those that don’t have the 'env' label
            run("kubectl get po -l '!env' --show-labels")
            # select pods with the 'creation_method' label with any value other than 'manual'
            run("kubectl get po -l 'creation_method!=manual' --show-labels")
            # select pods with the 'env' label set to either 'debug' or 'devel'
            run('kubectl get po -l "env in (debug,devel)" --show-labels')
            # select pods with the 'env' label not set to either 'prod' or 'devel'
            run('kubectl get po -l "env notin (prod,devel)" --show-labels')

        with self.subTest('Scheduling pods to specific nodes'):
            run('kubectl delete pod kubia-gpu', True)  # cleanup first
            ensure_pod_phase('kubia-gpu', 'Deleted')

            time.sleep(10)
            run('kubectl label node minikube gpu=true --overwrite')
            run('kubectl get node -L gpu')
            run('kubectl create -f kubia-gpu.yaml')


    def test_using_host_node_namespaces(self):
        init_test_env(NAME_SPACE)

        with self.subTest("Using node network namespace"):
            run(f'kubectl create -f pod-with-host-network.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-with-host-network', 'Running', NAME_SPACE)
            stdout = run(f'kubectl exec pod-with-host-network -n {NAME_SPACE} -- ifconfig')
            self.assertIn('docker0', stdout)


        with self.subTest("Binding host port without using host network namespace"):
            run(f'kubectl create -f kubia-hostport.yaml -n {NAME_SPACE}')
            ensure_pod_phase('kubia-hostport', "Running", NAME_SPACE)
            minikube_ip = run('minikube ip', True)
            run(f'curl -s http://{minikube_ip}:9000/')


        with self.subTest("Using node PID and IPC namespaces"):
            run(f'kubectl create -f pod-with-host-pid-and-ipc.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-with-host-pid-and-ipc', 'Running', NAME_SPACE)
            run(f'kubectl exec pod-with-host-pid-and-ipc -n {NAME_SPACE} -- ps aux')


    def test_configuring_container_security_context(self):
        init_test_env(NAME_SPACE)
        run(f'kubectl run pod-with-defaults --image alpine --restart Never --namespace {NAME_SPACE} -- /bin/sleep 999999')
        ensure_pod_phase("pod-with-defaults", 'Running', NAME_SPACE)

        with self.subTest("Running a container as a specific user"):
            run(f'kubectl create -f pod-as-user-guest.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-as-user-guest', 'Running', NAME_SPACE)
            stdout = run(f'kubectl exec pod-as-user-guest -n {NAME_SPACE} -- id -u')
            self.assertEqual(stdout, '405')

        with self.subTest("Running container in privileged mode"):
            run(f'kubectl create -f pod-privileged.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-privileged', 'Running', NAME_SPACE)
            stdout1 = run(f'kubectl exec pod-with-defaults -n {NAME_SPACE} -- ls /dev')
            stdout2 = run(f'kubectl exec pod-privileged -n {NAME_SPACE} -- ls /dev')
            # the privileged container sees all the host node's devices. This means it can use any device freely.
            self.assertGreater(len(stdout2.split()), len(stdout1.split()))

        with self.subTest("Adding individual kernel capabilities to a container"):
            stdout = run(f'kubectl exec pod-with-defaults -n {NAME_SPACE} -- date -s "12:00:00" 2>&1')
            self.assertIn("can't", stdout)
            run(f'kubectl create -f pod-add-settime-capability.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-add-settime-capability', 'Running', NAME_SPACE)
            run(f'kubectl exec pod-add-settime-capability -n {NAME_SPACE} -- date +%T -s "12:00:00"')
            stdout = run(f'kubectl exec pod-add-settime-capability -n {NAME_SPACE} -- date +%T')
            self.assertIn('12:00:0', stdout)
            run('minikube ssh date')  # node date will be changed, but it can be changed back quickly due to NTP.

        with self.subTest('Dropping capabilities from a container'):
            run(f'kubectl create -f pod-drop-chown-capability.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-drop-chown-capability', 'Running', NAME_SPACE)
            stdout = run(f'kubectl exec pod-drop-chown-capability -n {NAME_SPACE} -- chown guest /tmp 2>&1', True)
            self.assertIn('Operation not permitted', stdout)


        with self.subTest("Preventing processes from writing to the container's filesystem"):
            run(f'kubectl create -f pod-with-readonly-filesystem.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-with-readonly-filesystem', 'Running', NAME_SPACE)
            stdout = run(f'kubectl exec pod-with-readonly-filesystem -n {NAME_SPACE} -- touch /newfile 2>&1', True)
            self.assertIn('Read-only', stdout)
            run(f'kubectl exec pod-with-readonly-filesystem -n {NAME_SPACE} -- touch /volume/newfile')
            stdout = run(f'kubectl exec pod-with-readonly-filesystem -n {NAME_SPACE} -- ls -l /volume')
            self.assertIn('newfile', stdout)

        with self.subTest("Sharing volumes when containers run as different users"):
            run(f'kubectl create -f pod-with-shared-volume-fsgroup.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-with-shared-volume-fsgroup', 'Running', NAME_SPACE)
            run(f'kubectl exec pod-with-shared-volume-fsgroup -n {NAME_SPACE} -c first -- id')
            stdout = run(f'kubectl exec pod-with-shared-volume-fsgroup -n {NAME_SPACE} -c first -- id -G', True)
            self.assertEqual(stdout.split(), ['0', '555', '666', '777'])
            stdout = run(f'kubectl exec pod-with-shared-volume-fsgroup -n {NAME_SPACE} -c first -- ls -l / | grep volume')
            self.assertIn('555', stdout)
            # fsGroup security context property is used when the process cre- ates files IN A VOLUME
            run(f'kubectl exec pod-with-shared-volume-fsgroup -n {NAME_SPACE} -c first -- touch /tmp/foo')
            stdout = run(f'kubectl exec pod-with-shared-volume-fsgroup -n {NAME_SPACE} -c first -- ls -l /tmp/')
            self.assertNotIn('555', stdout)

    def test_auto_scaling_based_on_cpu(self):
        init_test_env(NS)

        # create deployment first
        run(f'kubectl create -f deployment.yaml -n {NS}')
        ensure_deploy_ready('kubia', NS)
        ensure_replicas('kubia', 3, 'deploy', NS)

        # create HPA (have to enable Heapster and metrics-server:)
        # minikube addons enable heapster
        # minikube addons enable metrics-server
        run(f'kubectl autoscale deployment kubia --cpu-percent=30 --min=1 --max=5 -n {NS}')

        # show HPA
        run(f'kubectl get hpa kubia -o yaml -n {NS}')

        # Because you're running three pods that are currently receiving no requests,
        # which means their CPU usage should be close to zero,
        # you should expect the Autoscaler to scale them down to a single pod.
        ensure_replicas('kubia', 1, 'deploy', NS)

        # expose pod to service
        run(f'kubectl expose deployment kubia --port=80 --target-port=8080 -n {NS}')

        # create loadgenerator pod
        run(f'kubectl run --restart=Never loadgenerator --image=busybox -n {NS} -- sh -c "while true; do wget -O - -q http://kubia.{NS}; done"')
        ensure_pod_phase('loadgenerator', 'Running', NS)

        # autoscaler increase the number of replicas.
        ensure_replicas('kubia', 4, 'deploy', NS)
        run(f'kubectl top pod -n {NS}')
        run(f'kubectl get hpa -n {NS}')
        cpu_util_percent = int(run(f"kubectl get hpa kubia -n {NS} -o jsonpath='{{.status.currentCPUUtilizationPercentage}}'"))
        self.assertLessEqual(cpu_util_percent/4, 30)


    def test_auto_scaling_down_with_pod_disruption_budget(self):
        init_test_env(NS)

        run(f"kubectl create pdb kubia-pdb --selector=app=kubia --min-available=2 -n {NS}")
        run(f"kubectl get pdb kubia-pdb -o yaml -n {NS}")

        # create deployment
        run(f'kubectl create -f deployment.yaml -n {NS}')
        ensure_deploy_ready('kubia', NS)
        ensure_replicas('kubia', 3, 'deploy', NS)

        # create hpa
        run(f'kubectl autoscale deployment kubia --cpu-percent=30 --min=1 --max=5 -n {NS}')
        # pdb has nothing to do with hpa
        ensure_replicas('kubia', 1, 'deploy', NS)


    def test_init_container(self):
        init_test_env(NS)

        run(f'kubectl create -f fortune-client.yaml -n {NS}')
        # The STATUS column shows that zero of one init containers have finished.
        run(f'kubectl get pod -n {NS}')
        run(f'kubectl create -f fortune-server.yaml -n {NS}')
        ensure_pod_phase('fortune-server', 'Running', NS)
        run(f'kubectl get pod fortune-client -n {NS}')
        ensure_pod_phase('fortune-client', 'Running', NS)

    def test_post_start_hook(self):
        init_test_env(NS)
        with self.subTest("Using an command hook handler"):
            run(f'kubectl create -f post-start-hook.yaml -n {NS}')
            ensure_pod_phase('pod-with-poststart-hook', 'Pending', NS)
            time.sleep(60)
            run(f'kubectl describe pod pod-with-poststart-hook -n {NS}')
            run(f'kubectl get pod pod-with-poststart-hook -n {NS}')

        with self.subTest("Using an HTTP GET hook handler"):
            run(f'kubectl create -f post-start-hook-httpget.yaml -n {NS}')
            ensure_pod_phase('pod-with-poststart-http-hook', 'Pending', NS)
            time.sleep(60)
            run(f'kubectl describe pod pod-with-poststart-http-hook -n {NS}')
            run(f'kubectl get pod pod-with-poststart-http-hook -n {NS}')


    def test_pre_stop_hook(self):
        init_test_env(NS)
        with self.subTest("Using an command hook handler"):
            run(f'kubectl create -f pre-stop-hook-command.yaml -n {NS}')
            ensure_pod_phase('pod-with-prestop-hook', 'Running', NS)
            time.sleep(60)
            run(f'kubectl describe pod pod-with-prestop-hook -n {NS}')
            run(f'kubectl get pod pod-with-prestop-hook -n {NS}')

        with self.subTest("Using an HTTP GET hook handler"):
            run(f'kubectl create -f pre-stop-hook-httpget.yaml -n {NS}')
            ensure_pod_phase('pod-with-prestop-http-hook', 'Running', NS)
            time.sleep(60)
            run(f'kubectl describe pod pod-with-prestop-http-hook -n {NS}')
            run(f'kubectl get pod pod-with-prestop-http-hook -n {NS}')

    def test_providing_information_on_process_terminated(self):
        '''
        Show the reason why a container terminated in the pod's status.
        You do this by having the process write a termination message to a specific file in the container's filesystem.
        The default file the process needs to write the message to is /dev/termination-log,
        but it can be changed by setting the `terminationMessagePath` field in the container definition in the pod spec.
        '''
        init_test_env(NS)

        with self.subTest("Terminating unsuccessfully"):
            run(f'kubectl create -f termination-message.yaml -n {NS}')
            ensure_pod_phase('pod-with-termination-message', 'Running', NS)
            stdout = run(f'kubectl describe po pod-with-termination-message -n {NS} | grep -C5 "Message:"')
            self.assertIn("I've had enough", stdout)

        with self.subTest("Terminating successfully"):
            run(f'kubectl create -f termination-message-success.yaml -n {NS}')
            ensure_pod_phase('successful-pod-with-termination-message', 'Succeeded', NS)
            stdout = run(f'kubectl describe po successful-pod-with-termination-message -n {NS} | grep -C5 "Message:"')
            self.assertIn("I've completed my task", stdout)


    def test_node_affinity(self):
        '''
        Run this testcase under EKS with at least 2 worker nodes
        '''
        init_test_env(NS)
        nodes = run(f"kubectl get node -o jsonpath='{{.items[*].metadata.name}}'", True).split()
        for node in nodes:
            run(f'kubectl label node {node} gpu-', True)  # delete label first
            run(f'kubectl label node {node} availability-zone-', True)
            run(f'kubectl label node {node} share-type-', True)

        with self.subTest("Specifying hard node affinity rules"):
            node = random.choice(nodes)
            run(f'kubectl label node {node} gpu=true')
            run(f'kubectl create -f kubia-gpu-nodeaffinity.yaml -n {NS}')
            ensure_pod_phase('kubia-gpu', 'Running', NS)
            stdout = run(f'kubectl get pod kubia-gpu -o wide -n {NS}')
            self.assertIn(node, stdout)

        with self.subTest("Prioritizing nodes when scheduling a pod"):
            node1 = nodes[0]
            node2 = nodes[1]
            run(f'kubectl label node {node1} availability-zone=zone1', True)
            run(f'kubectl label node {node1} share-type=dedicated', True)
            run(f'kubectl label node {node2} availability-zone=zone2', True)
            run(f'kubectl label node {node2} share-type=shared', True)
            run(f'kubectl get node -L availability-zone -L share-type')
            run(f'kubectl create -f preferred-deployment.yaml -n {NS}')
            ensure_deploy_ready('pref', NS)
            # Nodes whose 'availability-zone' and 'share-type' labels match the pod's node affinity are ranked the highest.
            # Next come the 'shared' nodes in 'zone1', then come the 'dedicated' nodes in the other zones,
            # and at the lowest priority are all the other nodes.
            run(f'kubectl get po -l app=pref -o wide -n {NS}')
            node1_num = int(run(f'kubectl get po -l app=pref -o wide -n {NS} | grep {node1} | wc -l', True))
            node2_num = int(run(f'kubectl get po -l app=pref -o wide -n {NS} | grep {node2} | wc -l', True))
            self.assertGreater(node1_num, node2_num)


    def test_pod_affinity(self):
        '''
        Run this testcase under EKS with at least 2 worker nodes
        '''
        init_test_env(NS)
        # First, deploy the backend pod
        run(f'kubectl run backend -l app=backend --image busybox -n {NS} -- sleep 999999')
        ensure_deploy_ready('backend', NS)

        with self.subTest("Using inter-pod affinity to deploy pods on the same node"):
            '''
            Deploy a backend pod and five frontend pod replicas with pod affinity configured
            so that they're all deployed on the same node as the backend pod.
            '''
            run(f'kubectl create -f frontend-podaffinity-host.yaml -n {NS}')
            ensure_deploy_ready('frontend', NS)
            run(f'kubectl get po -o wide -n {NS}')

            backend_node = run(f"kubectl get po -l app=backend -n {NS} -o jsonpath='{{.items[*].spec.nodeName}}'", True)
            frontend_nodes = run(f"kubectl get po -l app=frontend -n {NS} -o jsonpath='{{.items[*].spec.nodeName}}'", True).split()
            self.assertEqual(len(set(frontend_nodes)), 1)
            self.assertEqual(frontend_nodes[0], backend_node)

            # If you now delete the backend pod, the Scheduler will schedule the pod to origin node.
            # You can confirm the Scheduler takes other pods' pod affinity rules INTO ACCOUNT.
            old_backend_pod = run(f"kubectl get po -l app=backend -n {NS} -o jsonpath='{{.items[*].metadata.name}}'", True)
            run(f"kubectl delete pod -l app=backend -n {NS}")
            ensure_pod_phase(old_backend_pod, 'Deleted', NS)
            new_backend_node = run(f"kubectl get po -l app=backend -n {NS} -o jsonpath='{{.items[*].spec.nodeName}}'", True)
            self.assertEqual(backend_node, new_backend_node)

        with self.subTest("Expressing pod affinity preferences"):
            run(f'kubectl create -f frontend-podaffinity-preferred-host.yaml -n {NS}')
            ensure_deploy_ready('frontend-pref', NS)
            run(f"kubectl get pod -l app=frontend-pref -o wide -n {NS}")
            frontend_pref_nodes = run(f"kubectl get po -l app=frontend-pref -n {NS} -o jsonpath='{{.items[*].spec.nodeName}}'", True).split()
            backend_node_num = frontend_pref_nodes.count(backend_node)
            other_node_num = len(frontend_pref_nodes) - backend_node_num
            # Scheduler will prefer backend_node for frontend-pref pods,
            # but may schedule pods to other nodes as well.
            self.assertGreater(backend_node_num, other_node_num)


        with self.subTest("Using anti-affinity to spread apart pods of the same deployment"):
            init_test_env(NS)   # remove test history first
            run(f'kubectl create -f frontend-podantiaffinity-host.yaml -n {NS}')
            ensure_replicas('frontend-anti', 3, 'deploy', NS)

            running_pods = run(f"""kubectl get pod -n {NS} -o jsonpath='{{.items[?(@.status.phase=="Running")].metadata.name}}'""", True).split()
            pending_pods = run(f"""kubectl get pod -n {NS} -o jsonpath='{{.items[?(@.status.phase=="Pending")].metadata.name}}'""", True).split()
            run(f'kubectl get pod -n {NS} -o wide')
            node_num = len(run(f"kubectl get node -o jsonpath='{{.items[*].metadata.name}}'", True).split())
            # Every node has only one pod, remaining pods are all Pending,
            # because the Scheduler isn't allowed to schedule them to the same nodes.
            self.assertEqual(len(running_pods), node_num)
            self.assertEqual(len(pending_pods), 5-node_num)

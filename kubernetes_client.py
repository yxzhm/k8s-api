import uuid

import time
from kubernetes import client, config

config.load_kube_config()
v1 = client.CoreV1Api()


class ReleaseData:
    def __init__(self, release_id):
        self.release_id = release_id
        self.namespace_list = []


class NamespaceData:
    def __init__(self, namespace_name):
        self.namespace_name = namespace_name
        self.pod_list = []

    def print_msg(self):
        for pod in self.pod_list:
            pod.print_msg()

    def read_status(self):
        pods_from_k8s = v1.list_namespaced_pod(namespace)
        for pod in self.pod_list:
            if not pod.is_destroyed:
                pod_info_k8s = self.find_pod_from_k8s(pod.pod_name, pods_from_k8s)
                if pod_info_k8s:
                    pod.read_status(pod_info_k8s)
                else:
                    pod.is_updated = True
                    pod.is_destroyed = True
                    pod.status='Destroyed'

        for pod_from_k8s in pods_from_k8s.items:
            if self.find_pod_from_pod_list(pod_from_k8s.metadata.name) is None:
                pod = PodData(pod_from_k8s.metadata.name)
                pod.read_status(pod_from_k8s)
                self.pod_list.append(pod)

    def find_pod_from_pod_list(self, pod_name):
        for pod in self.pod_list:
            if pod.pod_name == pod_name:
                return pod
        return None

    @staticmethod
    def find_pod_from_k8s(pod_name, pods_from_k8s):
        for pod in pods_from_k8s.items:
            if pod.metadata.name == pod_name:
                return pod
        return None


class PodData:
    def __init__(self, pod_name):
        self.pod_name = pod_name
        self.status = None
        self.is_ready = False
        self.is_updated = True
        self.is_destroyed = False
        self.image_list = []

    def print_msg(self):
        if self.is_updated:
            image_msg = ''
            for image in self.image_list:
                image_msg = image_msg+image.image_name
            print(self.pod_name+' '+self.status+' '+str(self.is_ready)+' '+str(self.is_destroyed)+' '+image_msg)
        self.is_updated=False

    def read_status(self, data):
        # Check the status
        if self.status != data.status.phase:
            self.status = data.status.phase
            self.is_updated = True

        # Check is ready
        current_is_ready = True
        for container_status in data.status.container_statuses:
            if not container_status.ready:
                current_is_ready = False
                break
        if current_is_ready != self.is_ready:
            self.is_ready = current_is_ready
            self.is_updated = True

        # Check the images
        if not self.is_image_list_same(data.spec.containers):
            self.image_list.clear()
            self.is_updated = True
            for container in data.spec.containers:
                image_data = ImageData(container.image)
                self.image_list.append(image_data)

    def is_image_list_same(self, containers):
        if len(self.image_list) != len(containers):
            return False

        for image in self.image_list:
            if not self.image_existed(image.image_name, containers):
                return False
        return True

    @staticmethod
    def image_existed(image_name, containers):
        for container in containers:
            if image_name == container.image:
                return True
        return False


class ImageData:
    def __init__(self, image_name):
        self.image_name = image_name


if __name__ == '__main__':
    release_id = str(uuid.uuid1())
    namespace_names = ['yxzhm1']

    release_data = ReleaseData(release_id)
    for namespace in namespace_names:
        namespace_data = NamespaceData(namespace)
        release_data.namespace_list.append(namespace_data)

    while True:
        for namespace_data in release_data.namespace_list:
            namespace_data.read_status()
            namespace_data.print_msg()

        time.sleep(1)

import uuid
from influxdb import InfluxDBClient
from kubernetes import client, config, watch

config.load_kube_config()
v1 = client.CoreV1Api()
w = watch.Watch()


class PodData:

    def __init__(self, namespace):
        self.pod_name = ""
        self.namespace = namespace
        self.event_type = ""
        self.container_status = ""
        self.pod_status = ""

    @staticmethod
    def get_header():
        return "Pod Name\t Event type\t Pod type\t Container type"

    def get_msg(self):
        return self.pod_name + "\t " + self.event_type + "\t " + self.pod_status + "\t " + self.container_status

    def read_events(self, data):
        self.pod_name = data['object'].metadata.name
        self.event_type = data['type']
        self.pod_status = data['object'].status.phase
        self.read_container_type(data)

    def read_container_type(self, data):
        if data['object'].status and data['object'].status.container_statuses:
            for container in data['object'].status.container_statuses:
                state = container.state
                if state and state.waiting and state.waiting.reason:
                    self.append_container_type("waiting:" + state.waiting.reason)
                    break

                if state and state.terminated and state.terminated.reason:
                    self.append_container_type("terminated:" + state.terminated.reason)
                    break

                if state and state.running:
                    self.append_container_type("start at: " + str(state.running.started_at))

    def append_container_type(self, reason):
        if self.container_status is "":
            self.container_status = reason
        else:
            self.container_status = self.container_status + ',' + reason


class RCData:

    def __init__(self, rc):
        self.name = None
        self.generation = 0
        self.ready_replicas = 0
        self.replicas = 0
        self.update_rc(rc)
        self.terminated = False

    def update_rc(self, rc):
        self.name = rc.metadata.name
        self.generation = rc.metadata.generation
        self.ready_replicas = rc.status.ready_replicas
        self.replicas = rc.status.replicas
        if self.replicas == 0:
            self.terminated = True

    def get_msg(self):
        msgs = []
        msgs.append("Name: %s" % self.name)
        msgs.append("Generation: %d" % self.generation)
        if self.ready_replicas:
            msgs.append("Ready Replicas: %d" % self.ready_replicas)
        else:
            msgs.append("Ready Replicas: None")
        msgs.append("Replicas: %d" % self.replicas)
        msgs.append("Terminated: %s" % self.terminated)
        return msgs


class Log:
    @staticmethod
    def print_msg(msg):
        print("################")
        print(msg)
        print("################")
        print("")

    @staticmethod
    def print_msgs(msgs):
        print("################")
        for msg in msgs:
            print(msg)
        print("################")
        print("")


if __name__ == '__main__':

    current_namespace = 'zhm'
    legacy_rc_list = []
    new_rc_list = []

    for item in v1.list_namespaced_replication_controller(current_namespace).items:
        rc = RCData(item)
        legacy_rc_list.append(rc)

    Log.print_msg("Current RC info")
    for rc in legacy_rc_list:
        Log.print_msg(rc.get_msg())

    for event in w.stream(v1.list_namespaced_pod, current_namespace):
        Log.print_msg("Start to rolling update")
        pod = PodData(current_namespace)
        pod.read_events(event)
        pod_header = PodData.get_header()
        pod_msg = pod.get_msg()

        for item in v1.list_namespaced_replication_controller(current_namespace).items:
            found = False
            for old_rc in legacy_rc_list:
                if old_rc.name == item.metadata.name:
                    found = True
                    old_rc.update_rc(item)
            for new_rc in new_rc_list:
                if new_rc.name == item.metadata.name:
                    found = True
                    new_rc.update_rc(item)
            if not found:
                rc = RCData(item)
                new_rc_list.append(rc)

        all_msgs = []
        for rc in legacy_rc_list:
            all_msgs.append(rc.get_msg())
        all_msgs.append("")
        for rc in new_rc_list:
            all_msgs.append(rc.get_msg())
        all_msgs.append("")
        all_msgs.append(pod_header)
        all_msgs.append(pod_msg)
        Log.print_msg(all_msgs)

        if len(legacy_rc_list) == len(new_rc_list):
            update_done = True
            for rc in legacy_rc_list:
                if not rc.terminated:
                    update_done = False
                    break
            if update_done:
                Log.print_msg("Rolling Update Done")
                w.stop()
    # for event in w.stream(v1.list_namespaced_pod, current_namespace):
    #     pod = PodData(current_namespace)
    #     pod.read_events(event)
    #     pod.print_msg()
    #
    #     print("################")
    #     for item in v1.list_namespaced_replication_controller(current_namespace).items:
    #         print("Generation: " + str(item.metadata.generation))
    #         print("Ready Replicas:" + str(item.status.ready_replicas))
    #         print("Replicas:" + str(item.status.replicas))
    #     print("################")

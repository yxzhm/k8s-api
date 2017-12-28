from kubernetes import client, config

config.load_kube_config()

v1=client.CoreV1Api()
print("Listing pods with their IPs:")
abc = v1.list_namespaced_pod('mix-cd-core')
for i in abc.items:
    print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))

ret = v1.list_namespaced_event('yxzhm',pretty=True)
for i in ret.items:
    print(i)

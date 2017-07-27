

from riseml.client import AdminApi, ApiClient

def add_cluster_parser(subparsers):
    parser = subparsers.add_parser('cluster', help="show cluster info")
    parser.set_defaults(run=run)

def run(args):
    api_client = ApiClient(host=api_url)
    client = AdminApi(api_client)
    nodes = client.get_nodes()
    print("RiseML cluster nodes:\n")
    print("{:<18}  {:>6} {:>9} {:>4}".format('Hostname', 'CPUs', 'MEM(GiB)', 'GPUs'))
    width = 18 + 6 + 9 + 2 + 6
    total_cpus = 0
    total_mem = 0
    total_gpus = 0
    print('-' * width)
    for n in nodes:
        print(
        "{:<18}  {:>6} {:>9} {:>4}".format(n.hostname, n.cpus, "%.1f" % (float(n.mem) * (10 ** 6) / (1024 ** 3)),
                                           n.gpus))
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += n.gpus
    print('-' * width)
    print(
    "{:<18}  {:>6} {:>9} {:>4}".format('Total', total_cpus, "%.1f" % (float(total_mem) * (10 ** 6) / (1024 ** 3)),
                                       total_gpus))
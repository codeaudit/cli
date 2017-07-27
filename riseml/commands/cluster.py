from riseml.client import AdminApi, ApiClient
from riseml.consts import API_URL
from riseml.util import mb_to_gib


def add_cluster_parser(subparsers):
    parser = subparsers.add_parser('cluster', help="show cluster info")
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
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
        print("{:<18}  {:>6} {:>9} {:>4}".format(n.hostname, n.cpus,  mb_to_gib(n.mem), n.gpus))
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += n.gpus

    print('-' * width)
    print("{:<18}  {:>6} {:>9} {:>4}".format('Total', total_cpus, mb_to_gib(total_mem), total_gpus))
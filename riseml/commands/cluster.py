from riseml.client import AdminApi, ApiClient
from riseml.consts import API_URL
from riseml.util import mb_to_gib, print_table, TableRowDelimiter


def add_cluster_parser(subparsers):
    parser = subparsers.add_parser('cluster', help="show cluster info")
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    nodes = client.get_nodes()

    rows = []
    total_cpus = 0
    total_mem = 0
    total_gpus = 0

    for n in nodes:
        rows.append([n.hostname, n.cpus,  mb_to_gib(n.mem), n.gpus])
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += n.gpus

    rows.append(TableRowDelimiter('-'))
    rows.append(['Total', total_cpus, mb_to_gib(total_mem), total_gpus])

    print("RiseML cluster nodes:")

    print_table(
        header=['Hostname', 'CPUs', 'MEM (GiB)', 'GPUs'],
        min_widths=[18, 6, 9, 4],
        rows=rows
    )
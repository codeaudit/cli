from collections import Counter
from riseml.client import AdminApi, ApiClient
from riseml.consts import API_URL
from riseml.util import bytes_to_gib, print_table, TableRowDelimiter, call_api


def add_system_info_parser(subparsers):
    parser = subparsers.add_parser('info', help="show cluster info")
    parser.add_argument('-l', '--long', help="display long version", action="store_const", const=True)
    parser.set_defaults(run=run)


def display_short(nodes):
    rows = []
    nodes = filter(lambda n: n.role != 'master', nodes)
    total_cpus = 0
    total_mem = 0
    total_gpus = 0

    for n in nodes:
        rows.append([n.hostname, n.cpus,  '%.1f' % bytes_to_gib(n.mem), n.gpus_allocatable])
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += n.gpus_allocatable

    rows.append(TableRowDelimiter('-'))
    rows.append(['Total', total_cpus, '%.1f' % bytes_to_gib(total_mem), total_gpus])

    print("RiseML Cluster Nodes:")

    print_table(
        header=['Hostname', 'CPUs', 'MEM (GiB)', 'GPUs'],
        min_widths=[18, 6, 9, 4],
        rows=rows
    )

def display_long(nodes):
    rows = []
    nodes = filter(lambda n: n.role != 'master', nodes)
    total_cpus = 0
    total_mem = 0
    total_gpus = 0
    total_gpu_mem = 0

    def gpus_column(gpus):
        gpus_counted = Counter(gpus)
        s = []
        for (name, mem), count in gpus_counted.items():
            s.append('%s x %s (%.1f)' % (count, name, mem))
        if not s:
            s = '-'
        return ', '.join(s)

    for n in nodes:
        gpus = gpus_column([(gpu.name, bytes_to_gib(gpu.mem)) for gpu in n.gpus])
        rows.append([n.hostname, n.cpus, n.cpu_model, '%.1f' % bytes_to_gib(n.mem),
                     gpus, n.nvidia_driver, n.kubelet_version, n.docker_version])
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += len(n.gpus)
        total_gpu_mem += sum([gpu.mem for gpu in n.gpus])


    rows.append(TableRowDelimiter('-'))
    rows.append(['Total', total_cpus, '-', '%.1f' % bytes_to_gib(total_mem), 
                 '%s (%s)' % (total_gpus, '%.1f' % bytes_to_gib(total_gpu_mem)),
                  '-', '-', '-'])

    print("RiseML cluster nodes:")

    print_table(
        header=['Hostname', 'CPUs', 'CPU Type', 'MEM (GB)', 'GPUs (GB)', 'Nvidia Driver', 'Kubelet Version', 'Docker Version '],
        min_widths=[18, 6, 9, 4, 5, 5, 5, 5],
        rows=rows
    )    

def display_clusterinfos(clusterinfos):
    clusterinfos = {e.key: e.value for e in clusterinfos}
    k8s_version = clusterinfos.get('k8s_version', 'N/A')
    k8s_build_date = clusterinfos.get('k8s_build_date', 'N/A')
    k8s_git_commit = clusterinfos.get('k8s_git_commit', 'N/A')
    print('Kubernetes Version %s (Build Date: %s)' % (k8s_version, k8s_build_date))


def run(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    nodes = call_api(lambda: client.get_nodes())
    clusterinfos = call_api(lambda: client.get_cluster_infos())    
    display_clusterinfos(clusterinfos)
    print('')
    if args.long:
        display_long(nodes)
    else:
        display_short(nodes)

from collections import Counter
from riseml.client import AdminApi, ApiClient
from riseml.consts import VERSION
from riseml.util import bytes_to_gib, print_table, TableRowDelimiter, call_api, format_float


def add_system_info_parser(subparsers):
    parser = subparsers.add_parser('info', help="show cluster info")
    parser.add_argument('-l', '--long', help="display long version", action="store_const", const=True)
    parser.add_argument('-g', '--gpus', help="display gpu info", action="store_const", const=True)
    parser.set_defaults(run=run)


def display_gpus(nodes):

    #nodes = filter(lambda n: n.role != 'master', nodes)

    def get_device_id(device_name):
        if device_name.startswith('/dev/nvidia'):
            return int(device_name[len('/dev/nvidia'):])

    rows = []
    for n in nodes:
        gpus = 0
        # consistent reporting of GPUs
        if n.gpus_allocatable == len(n.gpus):
            gpus = len(n.gpus)
            gpu_mem = sum([gpu.mem for gpu in n.gpus])
        if not gpus:
            continue
        sorted_gpus = sorted(n.gpus, key=lambda x: get_device_id(x.device))
        for i, gpu in enumerate(sorted_gpus):
            rows.append([n.hostname if i == 0 else '', 
                         n.nvidia_driver if i == 0 else '', 
                         gpu.name, 
                         get_device_id(gpu.device), '%.1f' % bytes_to_gib(gpu.mem), 
                         gpu.serial])

    print_table(
        header=['NODE', 'DRIVER', 'NAME', 'ID', 'MEM', 'SERIAL'],
        min_widths=[2, 3, 3, 2, 3, 3],
        rows=rows,
        column_spaces=2,
    )


def format_float(f):
    return "%d" % f if f.is_integer() else "%.1f" %f


def display_short(nodes):
    rows = []
    #nodes = filter(lambda n: n.role != 'master', nodes)
    total_cpus = 0
    total_mem = 0
    total_gpus = 0
    total_gpu_mem = 0

    for n in nodes:
        gpus = 0
        gpu_mem = 0
        # consistent reporting of GPUs
        if n.gpus_allocatable == len(n.gpus):
            gpus = len(n.gpus)
            gpu_mem = sum([gpu.mem for gpu in n.gpus])
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += n.gpus_allocatable
        total_gpu_mem += gpu_mem
        rows.append([n.hostname, n.cpus,  '%.1f' % bytes_to_gib(n.mem), gpus,
                     format_float(bytes_to_gib(gpu_mem))])        

    rows.append(TableRowDelimiter('-'))
    rows.append(['Total', total_cpus, format_float(bytes_to_gib(total_mem)),
                 total_gpus, '%.1f' % bytes_to_gib(total_gpu_mem)])

    print_table(
        header=['NODE', 'CPU', 'MEM', 'GPU', 'GPU MEM'],
        min_widths=[18, 3, 3, 3, 7],
        rows=rows,
        column_spaces=2,
    )

def display_long(nodes):

    rows = []
    #nodes = filter(lambda n: n.role != 'master', nodes)
    total_cpus = 0
    total_mem = 0
    total_gpus = 0
    total_gpu_mem = 0    

    for n in nodes:
        gpus = 0
        gpu_mem = 0
        # consistent reporting of GPUs
        if n.gpus_allocatable == len(n.gpus):
            gpus = len(n.gpus)
            gpu_mem = sum([gpu.mem for gpu in n.gpus])
            
        total_cpus += n.cpus
        total_mem += n.mem
        total_gpus += gpus
        total_gpu_mem += gpu_mem
        
        rows.append([n.hostname, n.cpus,  format_float(bytes_to_gib(n.mem)), gpus,
                     format_float(bytes_to_gib(gpu_mem)),
                     n.nvidia_driver if n.nvidia_driver != 'NOT FOUND' else '-', 
                     n.kubelet_version.lstrip('v'), n.docker_version])        
    rows.append(TableRowDelimiter('-'))

    rows.append(['Total', total_cpus, format_float(bytes_to_gib(total_mem)),
                 total_gpus, format_float(bytes_to_gib(total_gpu_mem)), '', '', ''])
                    

    print_table(
        header=['NODE', 'CPU', 'MEM', 'GPU', 'GPU MEM', 
                'NVIDIA DRIVER', 'KUBELET VERSION', 'DOCKER VERSION'],
        min_widths=[18, 3, 3, 3, 7, 3, 3, 3],
        rows=rows,
        column_spaces=2,
    )


def display_clusterinfos(clusterinfos):
    clusterinfos = {e.key: e.value for e in clusterinfos}
    server_version = clusterinfos.get('server_version', 'N/A')
    k8s_version = clusterinfos.get('k8s_version', 'N/A')
    k8s_build_date = clusterinfos.get('k8s_build_date', 'N/A')
    k8s_git_commit = clusterinfos.get('k8s_git_commit', 'N/A')
    cluster_id = clusterinfos.get('cluster_id', 'N/A')
    print('RiseML Client/Server Version: {}/{}'.format(VERSION, server_version))
    print('RiseML Cluster ID: {}'.format(cluster_id))
    print('Kubernetes Version %s (Build Date: %s)' % (k8s_version, k8s_build_date))


def run(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    nodes = call_api(lambda: client.get_nodes())
    if args.long:
        display_long(nodes)
    elif args.gpus:
        display_gpus(nodes)
    else:
        clusterinfos = call_api(lambda: client.get_cluster_infos())
        display_clusterinfos(clusterinfos)
        print('')
        display_short(nodes)

from .jobs.deploy import add_deploy_parser
from .jobs.execute import add_exec_parser
from .jobs.logs import add_logs_parser
from .jobs.train import add_train_parser

from .cluster import add_cluster_parser
from .kill import add_kill_parser
from .register import add_register_parser
from .status import add_status_parser
from .whoami import add_whoami_parser
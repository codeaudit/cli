project_template = """project: {project_name}
"""

project_init_template = """project: {project_name}
train:
  framework: tensorflow
  install:
    - apt-get -y update
    - apt-get -y install git
    - git clone https://github.com/tensorflow/models
  resources:
    gpus: 0
    cpus: 1
    mem: 512
  run: 
  - python models/tutorials/image/imagenet/classify_image.py
"""
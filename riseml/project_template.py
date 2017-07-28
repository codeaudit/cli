project_template = """repository: {0}
train:
  framework: tensorflow
  image:
    name: riseml/base:latest-squashed
    install:
    - apt-get -y update
  tensorflow:
    distributed: true
    ps-count: 1
    worker-count: 2
    tensorboard: true
  resources:
    master:
      gpus: 1
      cpus: 4
      mem: 1024
    worker:
      gpus: 2
  run: 
  - echo "It works"
  
# Add params if you want to do a hyperparameter search.
# params:
#   alpha:
#   - 0.5
#   - 0.7
#   beta:
#     range:
#       min: 0
#       max: 1
#       step: 0.5"""
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
    tensorboard: some/directory/with/summaries
  resources:
    master:
      gpus: 1
      cpus: 4
      mem: 1024
    worker:
      gpus: 2
  run: 
  - echo "It works"
  - echo {{alpha}} {{beta}}
  params:
    alpha: 0.1
    beta:
      range:
        min: 0
        max: 1
        step: 0.5"""
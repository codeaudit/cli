import sys
import os

import yaml


class ConfigException(Exception): pass

class Config(object):
    deploy = None

    @classmethod
    def parse(cls, obj):
        config = cls()
        config.deploy = Deploy.parse(obj.get('deploy'))
        return config

    def to_dict(self):
        return {'deploy': self.deploy.to_dict()}

class Image(object):
    name = None
    install = []

    @classmethod
    def parse(cls, obj):
        image = cls()
        image.name = parse_value(parse_one(obj.get('name')))
        image.install = parse_list(obj.get('install'))
        return image

    def to_dict(self):
        return {
            'name': self.name,
            'install': self.install}

class Deploy(object):
    image = None
    run = []
    input = []
    output = []
    parameters = []
    demo = None

    @classmethod
    def parse(cls, obj):
        deploy = cls()
        deploy.image = Image.parse(obj.get('image'))
        deploy.run = parse_list(obj.get('run'))
        deploy.input = parse_list(obj.get('input'))
        deploy.output = parse_list(obj.get('output'))
        deploy.parameters = parse_list(obj.get('parameters'), cls=Parameter.parse)
        deploy.demo = Demo.parse(obj.get('demo'))
        return deploy

    def to_dict(self):
        return {
            'image': self.image.to_dict(),
            'run': self.run,
            'input': self.input,
            'output': self.output,
            'parameters': [v.to_dict() for v in self.parameters or []],
            'demo': self.demo.to_dict()}

class Parameter(object):
    name = None
    type = None
    display_name = None
    default = None

    @classmethod
    def parse(cls, obj):
        parameter = cls()
        parameter.name = parse_value(obj.get('name'))
        parameter.type = parse_value(obj.get('type'))
        parameter.display_name = parse_value(obj.get('display_name'))
        parameter.default = parse_value(obj.get('default'))
        return parameter

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'display_name': self.display_name,
            'default': self.default}

class Demo(object):
    title = None
    description = None
    samples = []

    @classmethod
    def parse(cls, obj):
        demo = cls()
        demo.title = obj.get('title')
        demo.description = obj.get('description')
        demo.samples = parse_list(obj.get('samples'))
        return demo

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'samples': self.samples}

def parse_value(v):
    if isinstance(v, list) or isinstance(v, dict):
        raise ConfigException('value must be str: %s' % v)
    return v

def parse_list(l, cls=lambda x:x):
    if l is None:
        return
    if isinstance(l, list):
        return [cls(v) for v in l]
    return [cls(l)]

def parse_one(record):
    return parse_list(record)[0]

def parse_text(text):
    return Config.parse(yaml.load(text))

def parse(f):
    return parse_text(f.read())

def parse_file(filename):
    with open(filename) as f:
        return parse(f)

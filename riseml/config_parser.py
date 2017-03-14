import sys
import os

import yaml


class ConfigException(Exception): pass

class Base(object):
    @classmethod
    def parse(cls, obj):
        if not obj:
            raise ConfigException('missing section: %s' % cls.__name__.lower())
        if not isinstance(obj, dict):
            raise ConfigException('section must be a dict: %s' % cls.__name__.lower())
        return cls._parse(obj)

class Config(Base):
    deploy = None

    @classmethod
    def _parse(cls, obj):
        config = cls()
        config.deploy = Deploy.parse(obj.get('deploy'))
        return config

    def to_dict(self):
        return {'deploy': self.deploy.to_dict()}

class Image(Base):
    name = None
    install = []

    @classmethod
    def _parse(cls, obj):
        image = cls()
        image.name = parse_value(parse_one(obj.get('name')))
        image.install = parse_list(obj.get('install'))

        if not image.name:
            raise ConfigException('missing field: image')
        return image

    def to_dict(self):
        res = {
            'name': self.name}
        if self.install:
            res['install'] = self.install
        return res

class Deploy(Base):
    image = None
    run = []
    input = []
    output = []
    parameters = []
    demo = None

    @classmethod
    def _parse(cls, obj):
        deploy = cls()

        image_dict = obj.get('image')
        if not isinstance(image_dict, dict):
            image_dict = dict(name=image_dict)

        deploy.image = Image.parse(image_dict)
        deploy.run = parse_list(obj.get('run'))
        deploy.input = parse_list(obj.get('input'))
        deploy.output = parse_list(obj.get('output'))
        deploy.parameters = parse_list(obj.get('parameters'), cls=Parameter.parse)
        demo = obj.get('demo')
        if demo:
            deploy.demo = Demo.parse(obj.get('demo'))
        if not deploy.run:
            raise ConfigException('missing field: run')
        return deploy

    def to_dict(self):
        res = {
            'image': self.image.to_dict(),
            'run': self.run}
        if self.input:
            res['input'] = self.input
        if self.output:
            res['output'] = self.output
        if self.parameters:
            res['parameters'] = [v.to_dict() for v in self.parameters or []]
        if self.demo:
            res['demo'] = self.demo.to_dict()
        return res

class Parameter(Base):
    name = None
    type = None
    display_name = None
    default = None

    @classmethod
    def _parse(cls, obj):
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

class Demo(Base):
    title = None
    description = None
    samples = []

    @classmethod
    def _parse(cls, obj):
        demo = cls()
        demo.title = obj.get('title')
        demo.description = obj.get('description')
        demo.samples = parse_list(obj.get('samples'))
        return demo

    def to_dict(self):
        res = {}
        if self.title:
            res['title'] = self.title
        if self.description:
            res['description'] = self.description
        if self.samples:
            res['samples'] = self.samples
        return res

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
    res = parse_list(record)
    if res:
        return res[0]

def parse_text(text):
    return Config.parse(yaml.load(text))

def parse(f):
    return parse_text(f.read())

def parse_file(filename):
    with open(filename) as f:
        return parse(f)

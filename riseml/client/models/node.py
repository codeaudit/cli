# coding: utf-8

"""
    RiseML API

    No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)

    OpenAPI spec version: 1.1.0
    Contact: contact@riseml.com
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""

from pprint import pformat
from six import iteritems
import re


class Node(object):
    """
    NOTE: This class is auto generated by the swagger code generator program.
    Do not edit the class manually.
    """
    def __init__(self, id=None, hostname=None, name=None, role=None, cpu_model=None, nvidia_driver=None, cpus=None, mem=None, gpus_allocatable=None, gpus=None):
        """
        Node - a model defined in Swagger

        :param dict swaggerTypes: The key is attribute name
                                  and the value is attribute type.
        :param dict attributeMap: The key is attribute name
                                  and the value is json key in definition.
        """
        self.swagger_types = {
            'id': 'str',
            'hostname': 'str',
            'name': 'str',
            'role': 'str',
            'cpu_model': 'str',
            'nvidia_driver': 'str',
            'cpus': 'int',
            'mem': 'int',
            'gpus_allocatable': 'int',
            'gpus': 'list[GPU]'
        }

        self.attribute_map = {
            'id': 'id',
            'hostname': 'hostname',
            'name': 'name',
            'role': 'role',
            'cpu_model': 'cpu_model',
            'nvidia_driver': 'nvidia_driver',
            'cpus': 'cpus',
            'mem': 'mem',
            'gpus_allocatable': 'gpus_allocatable',
            'gpus': 'gpus'
        }

        self._id = id
        self._hostname = hostname
        self._name = name
        self._role = role
        self._cpu_model = cpu_model
        self._nvidia_driver = nvidia_driver
        self._cpus = cpus
        self._mem = mem
        self._gpus_allocatable = gpus_allocatable
        self._gpus = gpus


    @property
    def id(self):
        """
        Gets the id of this Node.


        :return: The id of this Node.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """
        Sets the id of this Node.


        :param id: The id of this Node.
        :type: str
        """

        self._id = id

    @property
    def hostname(self):
        """
        Gets the hostname of this Node.


        :return: The hostname of this Node.
        :rtype: str
        """
        return self._hostname

    @hostname.setter
    def hostname(self, hostname):
        """
        Sets the hostname of this Node.


        :param hostname: The hostname of this Node.
        :type: str
        """

        self._hostname = hostname

    @property
    def name(self):
        """
        Gets the name of this Node.


        :return: The name of this Node.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Sets the name of this Node.


        :param name: The name of this Node.
        :type: str
        """

        self._name = name

    @property
    def role(self):
        """
        Gets the role of this Node.


        :return: The role of this Node.
        :rtype: str
        """
        return self._role

    @role.setter
    def role(self, role):
        """
        Sets the role of this Node.


        :param role: The role of this Node.
        :type: str
        """

        self._role = role

    @property
    def cpu_model(self):
        """
        Gets the cpu_model of this Node.


        :return: The cpu_model of this Node.
        :rtype: str
        """
        return self._cpu_model

    @cpu_model.setter
    def cpu_model(self, cpu_model):
        """
        Sets the cpu_model of this Node.


        :param cpu_model: The cpu_model of this Node.
        :type: str
        """

        self._cpu_model = cpu_model

    @property
    def nvidia_driver(self):
        """
        Gets the nvidia_driver of this Node.


        :return: The nvidia_driver of this Node.
        :rtype: str
        """
        return self._nvidia_driver

    @nvidia_driver.setter
    def nvidia_driver(self, nvidia_driver):
        """
        Sets the nvidia_driver of this Node.


        :param nvidia_driver: The nvidia_driver of this Node.
        :type: str
        """

        self._nvidia_driver = nvidia_driver

    @property
    def cpus(self):
        """
        Gets the cpus of this Node.


        :return: The cpus of this Node.
        :rtype: int
        """
        return self._cpus

    @cpus.setter
    def cpus(self, cpus):
        """
        Sets the cpus of this Node.


        :param cpus: The cpus of this Node.
        :type: int
        """

        self._cpus = cpus

    @property
    def mem(self):
        """
        Gets the mem of this Node.


        :return: The mem of this Node.
        :rtype: int
        """
        return self._mem

    @mem.setter
    def mem(self, mem):
        """
        Sets the mem of this Node.


        :param mem: The mem of this Node.
        :type: int
        """

        self._mem = mem

    @property
    def gpus_allocatable(self):
        """
        Gets the gpus_allocatable of this Node.


        :return: The gpus_allocatable of this Node.
        :rtype: int
        """
        return self._gpus_allocatable

    @gpus_allocatable.setter
    def gpus_allocatable(self, gpus_allocatable):
        """
        Sets the gpus_allocatable of this Node.


        :param gpus_allocatable: The gpus_allocatable of this Node.
        :type: int
        """

        self._gpus_allocatable = gpus_allocatable

    @property
    def gpus(self):
        """
        Gets the gpus of this Node.


        :return: The gpus of this Node.
        :rtype: list[GPU]
        """
        return self._gpus

    @gpus.setter
    def gpus(self, gpus):
        """
        Sets the gpus of this Node.


        :param gpus: The gpus of this Node.
        :type: list[GPU]
        """

        self._gpus = gpus

    def to_dict(self):
        """
        Returns the model properties as a dict
        """
        result = {}

        for attr, _ in iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value

        return result

    def to_str(self):
        """
        Returns the string representation of the model
        """
        return pformat(self.to_dict())

    def __repr__(self):
        """
        For `print` and `pprint`
        """
        return self.to_str()

    def __eq__(self, other):
        """
        Returns true if both objects are equal
        """
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """
        Returns true if both objects are not equal
        """
        return not self == other

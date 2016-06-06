"""Handle the concept of a container."""

import os
import shutil

import docker

from control.dclient import dclient
from control.shittylogging import log
from control.options import options
from control.exceptions import (
    ContainerAlreadyExists, ContainerDoesNotExist,
    VolumePseudoExists, InvalidVolumeName,
    TransientVolumeCreation
)


class Container:
    """
    Container is a data structure for a container. Controlfiles that specify
    containers will be read into this structure and have defaults applied where
    a default has not been explicitly overriden.
    """

    expected_timeout = 10
    conf = {
        'name': '',
        'image': '',
        'hostname': None,
    }

    def __init__(self, image, conf):
        try:
            self.expected_timeout = conf.pop('expected_timeout')
        except KeyError:
            pass
        try:
            if 'hostname' not in conf:
                conf['hostname'] = conf['name']
        except KeyError:
            pass
        self.conf.update(conf)
        self.conf['image'] = image

    def get_container_options(self):
        conf_copy = self.conf.copy()
        host_config = {}
        try:
            host_config['binds'] = conf_copy.pop('volumes')
        except KeyError:
            pass
        # This calling create_host_config probably doesn't change the dict
        conf_copy['host_config'] = dclient.create_host_config(**host_config)
        return conf_copy

    def create(self):
        log(self.conf, level='debug')
        try:
            return CreatedContainer(
                dclient.create_container(**self.get_container_options()),
                self.conf)
        except docker.errors.NotFound as e:
            if 'chown' in e.explanation.decode('utf-8'):
                raise VolumePseudoExists(e.explanation.decode('utf-8'))
            elif 'volume not found' in e.explanation.decode('utf-8'):
                raise TransientVolumeCreation(e.explanation.decode('utf-8'))
            log(e, level='debug')
            log(e.response, level='debug')
            log(e.explanation.decode('utf-8'), level='debug')
            raise
        except docker.errors.APIError as e:
            if 'volume name invalid' in e.explanation.decode('utf-8'):
                raise InvalidVolumeName(e.explanation.decode('utf-8'))
            elif 'is already in use by container' in e.explanation.decode('utf-8'):
                raise ContainerAlreadyExists(e.explanation.decode('utf-8'))
            log(e, level='debug')
            log(e.response, level='debug')
            log(e.explanation.decode('utf-8'), level='debug')
            raise


class CreatedContainer(Container):
    inspect = {}

    def __init__(self, name, conf={}):
        try:
            self.inspect = dclient.inspect_container(name)
            super().__init__(self.inspect['Image'], conf)
        except docker.errors.NotFound as e:
            log(e, level='debug')
            raise ContainerDoesNotExist(name)

    def start(self):
        try:
            dclient.start(self.inspect['Id'])
        except docker.errors.NotFound as e:
            if e.explanation.decode('utf-8') == 'get: volume not found':
                raise InvalidVolumeName('volume not found')
            raise
        else:
            self.inspect = dclient.inspect_container(self.inspect['Id'])
        return self.inspect['State']['Running']

    def stop(self):
        dclient.stop(self.inspect['Id'], timeout=self.expected_timeout)
        self.inspect = dclient.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def kill(self):
        dclient.kill(self.inspect['Id'])
        self.inspect = dclient.inspect_container(self.inspect['Id'])
        return not self.inspect['State']['Running']

    def remove(self):
        dclient.remove_container(self.inspect['Id'], v=True)
        try:
            dclient.inspect_container(self.inspect['Id'])
            return False
        except docker.errors.NotFound:
            return True

    def remove_volumes(self):
        if options.debug:
            log('Docker has removed these volumes:', level='debug')
            for v in (v['Source'] for v in self.inspect['Mounts'] if not os.path.isdir(v['Source'])):
                log('  {}'.format(v), level='debug')
            log('Attempting to remove these volume locations:', level='debug')
            for v in (v['Source'] for v in self.inspect['Mounts'] if os.path.isdir(v['Source'])):
                log('  {}'.format(v), level='debug')
        for vol in self.inspect['Mounts']:
            if vol['Source'].startswith('/var/lib/docker/volumes'):
                log('having docker remove {}'.format(vol['Source']), level='debug')
                try:
                    dclient.remove_volume(vol['Name'])
                except docker.errors.APIError as e:
                    if 'no such volume' in e.explanation.decode('utf-8'):
                        continue
                    log('cannot remove volume: {}'.format(e.explanation.decode('utf-8'), level='info'))
            elif os.path.isdir(vol['Source']):
                log('removing {}'.format(vol['Source']), level='debug')
                try:
                    shutil.rmtree(vol['Source'])
                except PermissionError as e:
                    print('Cannot remove directory {}: {}'.format(vol['Source'], e))
            else:
                log('docker removed volume {}'.format(vol['Source']), level='debug')

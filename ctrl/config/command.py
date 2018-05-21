
import os
from configparser import RawConfigParser

from zope import component, interface

import yaml

from ctrl.config.interfaces import ICtrlConfig
from ctrl.command.interfaces import ISubcommand


class M(dict):

    def __setitem__(self, key, value):
        if key in self:
            items = self[key]
            if isinstance(items, str):
                items = [items]
            items.append(value)
            value = items
        super(M, self).__setitem__(key, value)

    def items(self):
        items = super(M, self).items()
        _items = []
        for k, v in items:
            if isinstance(v, list):
                for _v in v:
                    _items.append((k, _v))
            else:
                _items.append((k, v))
        return tuple(_items)


@interface.implementer(ISubcommand)
class ConfigSubcommand(object):

    def __init__(self, context):
        self.context = context

    async def handle(self, *args, **kwargs):
        print('Running config subcommand!')
        self.clear_service_files()
        self.update_systemd()

    @property
    def clients(self):
        sections = [
            s for s
            in self.config.sections()
            if s.startswith('client:')]
        for section in sections:
            yield section[7:]

    @property
    def config(self):
        return component.getUtility(ICtrlConfig).config

    @property
    def services(self):
        sections = [
            s for s
            in self.config.sections()
            if s.startswith('service:')]
        for section in sections:
            yield section[8:]

    @property
    def var_path(self):
        var_path = self.config.get('controller', 'var_path')
        if not os.path.exists(var_path):
            os.makedirs(var_path)
        return var_path

    def append_touch_files(self, name):
        idle_files = self.config.get(
            "service:%s" % name,
            'idle-files').split('\n')
        with open(os.path.join(self.var_path, 'idle-files'), 'a') as f:
            f.write('%s %s' % (name, ' '.join(idle_files)))

    def clear_service_files(self):
        files = [
            x for x
            in os.listdir('/etc/systemd/system')
            if x.startswith('controller-')]
        for f in files:
            os.unlink('/etc/systemd/system/%s' % f)

    def generate_compose_file(self, name):
        var_path = os.path.join(self.var_path, name)
        if not os.path.exists(var_path):
            os.makedirs(var_path)
        config = component.getUtility(ICtrlConfig, 'compose').config

        new_config = dict(services={}, volumes={}, networks={})
        extra_services = []
        for service in self.get_services(name):
            if not config['services'].get(service):
                continue
            new_config['services'][service] = dict(config['services'][service])
            for volume in new_config['services'][service].get('volumes', []):
                if volume.startswith('/'):
                    continue
                new_config['volumes'][volume.split(':')[0]] = {}
            has_extra_services = config['services'][service].get(
                'network_mode', '').startswith('service:')
            if has_extra_services:
                extra_services.append(
                    config['services'][service]['network_mode'][8:])
            networks = new_config['services'][service].get(
                'networks', [])
            for network in networks:
                if network.startswith('/'):
                    continue
                new_config['networks'][network.split(':')[0]] = {}
        for service in extra_services:
            new_config['services'][service] = dict(
                config['services'][service])
        new_config['version'] = config['version']
        yaml.dump(
            new_config,
            open(os.path.join(var_path, 'docker-compose.yml'), 'w'),
            default_flow_style=False)

    def generate_daemon_compose_file(self, config, startup_config):
        daemons = [
            d for d
            in self.config.get('controller', 'daemons').split('\n')
            if d]
        if not daemons:
            return
        extra_services = []
        for daemon in daemons:
            if not config['services'].get(daemon):
                print('No config for daemon: %s' % daemon)
                continue
            startup_config['services'][daemon] = dict(
                config['services'][daemon])
            has_extra_services = config['services'][daemon].get(
                'network_mode', '').startswith('service:')
            if has_extra_services:
                extra_services.append(
                    config['services'][daemon]['network_mode'][8:])
        for service in extra_services:
            startup_config['services'][service] = dict(
                config['services'][service])

        startup_config['volumes'] = dict(config.get('volumes', {}))
        startup_config['networks'] = dict(config.get('networks', {}))
        if startup_config['networks'].get('default'):
            subnet = startup_config[
                'networks']['default'][
                    'ipam']['config'][0]['subnet'].split('.')
            subnet[2] = '100'
            startup_config[
                'networks']['default'][
                    'ipam']['config'][0]['subnet'] = '.'.join(subnet)

    def generate_client_compose_file(self, config, startup_config):
        print(config)
        for client in self.clients:
            startup_config['services'][client] = dict(
                config['services'].get(client, {}))

    def generate_system_compose_file(self):
        var_path = self.var_path
        compose_config = component.getUtility(
            ICtrlConfig, 'compose').config
        startup_config = dict(
            services={}, volumes={}, networks={})
        self.generate_daemon_compose_file(
            compose_config, startup_config)
        self.generate_client_compose_file(
            compose_config, startup_config)
        startup_config['version'] = compose_config['version']
        yaml.dump(
            startup_config,
            open(os.path.join(var_path, 'docker-compose.yml'), 'w'),
            default_flow_style=False)

    def generate_service_files(self, name):
        context = self.config.get('controller', 'context')
        app = self.config.get(
            'controller', 'name') or os.path.basename(context)
        listen = self.config.get(
            "service:%s" % name, 'listen')
        description = self.config.get(
            "service:%s" % name, 'description')
        socket = self.config.get(
            "service:%s" % name, 'socket') or ("/sockets/%s.sock" % name)
        service = self.get_service(name)
        services = self.get_services(name)
        env = ''

        socket_config = RawConfigParser(dict_type=M)
        socket_config.optionxform = str
        socket_config.add_section('Socket')
        socket_config.set('Socket', 'ListenStream', listen)
        socket_config.add_section('Install')
        socket_config.set('Install', 'WantedBy', 'sockets.target')
        socket_config.write(
            open('/etc/systemd/system/controller-%s--proxy.socket'
                 % name,
                 'w'))

        service_config = RawConfigParser(dict_type=M)
        service_config.optionxform = str
        service_config.add_section('Unit')
        service_config.set(
            'Unit',
            'Requires',
            'controller-%s.service' % name)
        service_config.set(
            'Unit',
            'After',
            'controller-%s.service' % name)
        service_config.add_section('Service')
        service_config.set(
            'Service',
            'ExecStart',
            '/usr/local/bin/start-proxy %s' % socket)
        service_config.set('Service', 'PrivateTmp', 'yes')
        service_config.set(
            'Service',
            'PrivateNetwork',
            ('yes' if socket.startswith('/') else 'no'))
        service_config.write(
            open('/etc/systemd/system/controller-%s--proxy.service'
                 % name,
                 'w'))

        upstream_config = RawConfigParser(dict_type=M)
        upstream_config.optionxform = str
        upstream_config.add_section('Unit')
        upstream_config.set('Unit', 'Description', description)
        upstream_config.set('Unit', 'Requires', 'idle.timer')
        upstream_config.set('Unit', 'After', 'idle.timer')
        upstream_config.add_section('Service')
        upstream_config.set(
            'Service',
            'ExecStart',
            '%s/usr/local/bin/start-service %s %s %s %s %s'
            % (env, app, name, socket, service, " ".join(services)))
        upstream_config.set(
            'Service',
            'ExecStartPost',
            "%s/usr/local/bin/wait-for-service %s %s %s %s"
            % (env, app, name, socket, service))
        upstream_config.set(
            'Service',
            'ExecStop',
            '%s/usr/local/bin/stop-service %s %s %s %s'
            % (env, app, name, socket, service))
        upstream_config.set('Service', 'PrivateTmp', 'true')
        with open('/var/lib/controller/env') as f:
            for line in f.readlines():
                upstream_config.set('Service', 'Environment', line.strip())
        upstream_config.set('Service', 'RemainAfterExit', 'true')
        upstream_config.write(
            open('/etc/systemd/system/controller-%s.service' % name, 'w'))

    def get_services(self, name):
        return [
            ("%s-%s" % (s, name))
            for s
            in self.config.get("service:%s" % name, 'services').split(" ")
            if s] or [self.get_service(name)]

    def get_service(self, name):
        service = self.config.get("service:%s" % name, 'service')
        return (
            "%s-%s" % (service, name)
            if service
            else name)

    def set_timeout_file(self):
        with open(os.path.join(self.var_path, 'idle-timeout'), 'w') as f:
            f.write(self.config.get('controller', 'idle-timeout'))

    def setup_zmq_pipe(self):
        with open('/var/lib/controller/env') as f:
            env = dict(
                line.strip().split('=')
                for line
                in f.readlines())
        if env.get('LISTEN_ZMQ') or env.get('PUBLISH_ZMQ'):
            print("Creating ZMQ pipe")
            self.generate_service_files('zmq')

    def create_env_file(self):
        if not self.config.has_section('controller'):
            return
        print('Creating env file')
        env = (
            'COMPOSE_CONTEXT=%s\nDOCKER_HOST=%s'
            % (self.config.get('controller', 'context'),
               'unix:///fat/docker.sock'))
        open('/etc/controller.env', 'w').write(env)

    def update_systemd(self):
        self.create_env_file()
        self.generate_system_compose_file()
        self.set_timeout_file()
        self.setup_zmq_pipe()
        for name in self.services:
            self.generate_service_files(name)
            self.generate_compose_file(name)
            self.append_touch_files(name)

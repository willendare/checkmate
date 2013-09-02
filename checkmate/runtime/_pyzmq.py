import copy
import time
import pickle
import random
import threading

import zmq
import socket

import zope.interface

import checkmate.runtime._threading
import checkmate.runtime.interfaces


POLLING_TIMOUT_MS = 1000


@zope.interface.implementer(checkmate.runtime.interfaces.IConnection)
class Client(checkmate.runtime._threading.Thread):
    """"""
    def __init__(self, name=None):
        super(Client, self).__init__(name=name)
        self.received_lock = threading.Lock()
        self.request_lock = threading.Lock()
        self.in_buffer = []
        self.out_buffer = []
        self.name = name
        self.ports = []
        self.poller = zmq.Poller()
        self.context = zmq.Context()
        self.request_ports()
        self.connect_ports()

    def request_ports(self):
        socket = self.context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:%i"%self._initport)
        while len(self.ports) == 0:
            msg = "client1 request for ports"
            socket.send(pickle.dumps((self._name, msg)))
            self.ports.extend(pickle.loads(socket.recv()))
        socket.close()

    def connect_ports(self):
        if len(self.ports) == 2:
            self.request_lock.acquire()
            self.sender = self.context.socket(zmq.PUSH)
            self.sender.bind("tcp://127.0.0.1:%i"%self.ports[1])
            self.request_lock.release()
            self.receiver = self.context.socket(zmq.PULL)
            self.receiver.connect("tcp://127.0.0.1:%i"%self.ports[0])
            self.poller.register(self.receiver, zmq.POLLIN)

    def close_ports(self):
        self.request_lock.acquire()
        self.sender.close()
        self.request_lock.release()
        self.receiver.close()

    def run(self):
        """"""
        while True:
            if self.check_for_stop():
                self.close_ports()
                break
            self.process_receive()

    def send(self, exchange):
        """"""
        self.request_lock.acquire()
        destination = exchange.destination
        msg = pickle.dumps(exchange)
        self.sender.send(pickle.dumps((destination, msg)))
        self.request_lock.release()

    def read(self):
        self.received_lock.acquire()
        _local_copy = copy.deepcopy(self.in_buffer)
        self.in_buffer = []
        self.received_lock.release()
        return _local_copy

    def received(self, exchange):
        time.sleep(0.1)
        result = False
        self.received_lock.acquire()
        _local_copy = copy.deepcopy(self.in_buffer)
        self.received_lock.release()
        if exchange in _local_copy:
            result = True
            self.received_lock.acquire()
            self.in_buffer.remove(exchange)
            self.received_lock.release()
        return result
            
    def process_receive(self):
        incoming_list = []
        socks = dict(self.poller.poll(POLLING_TIMOUT_MS))
        if self.receiver in socks:
            self.received_lock.acquire()
            self.in_buffer.append(pickle.loads(self.receiver.recv()))
            self.received_lock.release()


class Registry(checkmate.runtime._threading.Thread):
    """"""
    def __init__(self, name=None):
        """"""
        super(Registry, self).__init__(name=name)
        self.comp_sender = {}
        self.poller = zmq.Poller()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.get_assign_port_lock = threading.Lock()
        self.get_assign_port_lock.acquire()
        self._initport = self.pickfreeport()
        self.socket.bind("tcp://127.0.0.1:%i"%self._initport)
        self.get_assign_port_lock.release()
        self.poller.register(self.socket, zmq.POLLIN)

    def run(self):
        """"""
        while True:
            if self.check_for_stop():
                break
            socks = dict(self.poller.poll(POLLING_TIMOUT_MS))
            for sock in iter(socks):
                if sock == self.socket:
                    receiver = self.assign_ports()
                    self.poller.register(receiver, zmq.POLLIN)
                else:
                    self.forward_incoming(sock)

    def assign_ports(self):
        """""" 
        msg = pickle.loads(self.socket.recv())
        name = msg[0]
        sender = self.context.socket(zmq.PUSH)
        receiver = self.context.socket(zmq.PULL)
        self.get_assign_port_lock.acquire()
        port_out = self.pickfreeport()
        sender.bind("tcp://127.0.0.1:%i"%port_out)
        self.get_assign_port_lock.release()
        self.comp_sender[name] = sender
        self.get_assign_port_lock.acquire()
        port_in = self.pickfreeport()
        receiver.connect("tcp://127.0.0.1:%i"%port_in)
        self.get_assign_port_lock.release()
        self.socket.send(pickle.dumps([port_out, port_in]))
        return receiver

    def forward_incoming(self, socket):
        msg = pickle.loads(socket.recv())
        try:
            sender = self.comp_sender[msg[0]]
        except:
            print("no client registried " + msg[0])
            return
        sender.send(msg[1])

    def pickfreeport(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        addr, port = s.getsockname()
        s.close()
        return port

@zope.interface.implementer(checkmate.runtime.interfaces.IProtocol)
class Communication(object):
    """
        >>> import checkmate.runtime._pyzmq
        >>> import checkmate.runtime._runtime
        >>> import checkmate.test_data
        >>> import checkmate.runtime
        >>> import checkmate.component
        >>> a = checkmate.test_data.App()
        >>> c = checkmate.runtime._pyzmq.Communication()
        >>> r = checkmate.runtime._runtime.Runtime(a, c)
        >>> r.setup_environment(['C3'])
        >>> r.start_test()
        >>> import checkmate.runtime.registry
        >>> c2_stub = checkmate.runtime.registry.global_registry.getUtility(checkmate.component.IComponent, 'C2')
        >>> c1_stub = checkmate.runtime.registry.global_registry.getUtility(checkmate.component.IComponent, 'C1')
        >>> simulated_exchange = a.components['C2'].state_machine.transitions[0].outgoing[0].factory()
        >>> simulated_exchange.origin_destination('C2', 'C1')
        >>> o = c2_stub.simulate(simulated_exchange)
        >>> c1_stub.validate(o[0])
        True
        >>> r.stop_test()

    """
    connection_handler = Client

    def initialize(self):
        """"""
        self.registry = Registry()
        Client._initport = self.registry._initport
        self.registry.start()

    def close(self):
        self.registry.stop()


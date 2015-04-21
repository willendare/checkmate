# This code is part of the checkmate project.
# Copyright (C) 2013-2015 The checkmate project contributors
#
# This program is free software under the terms of the GNU GPL, either
# version 3 of the License, or (at your option) any later version.


import checkmate.parser.yaml_visitor
import checkmate.partition_declarator


class Engine(object):
    def __init__(self, data_structure_module, exchange_module,
                 state_module, source_filenames):
        declarator = checkmate.partition_declarator.Declarator(
            data_structure_module,
            exchange_module=exchange_module,
            state_module=state_module)
        define_data = ''
        for _f in source_filenames:
            with open(_f, 'r') as _file:
                define_data += _file.read()
        data_source = checkmate.parser.yaml_visitor.call_visitor(define_data)
        declarator.new_definitions(data_source)
        declarator_output = declarator.get_output()
        self.states = declarator_output['states']
        self.transitions = declarator_output['transitions']
        self.services = {}
        self.service_classes = []
        self.communication_list = set()
        for _t in self.transitions:
            for _i in _t.incoming:
                _ex = _i.factory()
                if _i.code not in self.services:
                    self.services[_i.code] = _ex
                if _i.partition_class not in self.service_classes:
                    self.service_classes.append(_i.partition_class)
                self.communication_list.add(_ex.communication)
            for _o in _t.outgoing:
                _ex = _o.factory()
                self.communication_list.add(_ex.communication)

    def block_by_name(self, name):
        for _t in self.transitions:
            if _t.name == name:
                return _t

    def set_owner(self, name):
        for _tr in self.transitions:
            _tr.owner = name

    def get_blocks_by_input(self, exchange, states):
        block_list = []
        for _t in self.transitions:
            if (_t.is_matching_incoming(exchange, states) and
                    _t.is_matching_initial(states)):
                block_list.append(_t)
        return block_list

    def get_blocks_by_output(self, exchange, states):
        for _t in self.transitions:
            if (_t.is_matching_outgoing(exchange) and
                    _t.is_matching_initial(states)):
                return _t
        return None

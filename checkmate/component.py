import os

import zope.interface

import checkmate.state_machine
import checkmate.parser.doctree

import checkmate._utils


class Component(object):
    def __init__(self, matrix='', state_module=None, exchange_module=None):
        self.states = []
        try:
            partitions_output = checkmate.parser.doctree.load_partitions(matrix, state_module)
            transitions_output = checkmate.parser.doctree.load_transitions(matrix, state_module=state_module,
                                                                exchange_module=exchange_module)
            self.state_machine = checkmate.state_machine.StateMachine(partitions_output['states'],
                                                                      transitions_output['state_machine'])
        except:
            self.state_machine = checkmate.state_machine.StateMachine()

    def get_transition_by_input(self, exchange):
        """
        >>> import checkmate.test.data_exchange
        >>> import checkmate.test.data_component
        >>> a = checkmate.test.data_component.Abs()
        >>> r_tm = checkmate.test.data_exchange.AbsControlAction('TM()')
        >>> a.get_transition_by_input(r_tm) == a.transitions[0]
        True
        """
        for _t in self.state_machine.transitions:
            if (_t.is_matching_initial(self.states) and
                _t.is_matching_incoming(exchange)):
                return _t
        return None

            
    def start(self):
        for state in self.state_machine.states:
            try:
                if hasattr(state, 'append'):
                    self.states.append(state([]))
                else:
                    self.states.append(state(state._valid_values[0]))
            except IndexError:
                self.states.append(state())

    
def execute(_component, _exchange):
    """
    """
    _transition = _component.get_transition_by_input(_exchange)
    if _transition is None:
        return None
    return _transition.process(_component.states, _exchange)


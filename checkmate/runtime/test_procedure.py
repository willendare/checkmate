import os, re
import pickle
import checkmate._tree
import checkmate.test_data
import checkmate.service_registry
import checkmate.runtime.procedure

class TestProcedure(checkmate.runtime.procedure.Procedure):
    """"""
    def __init__(self, test=None):
        """
            >>> import checkmate.test_data
            >>> import checkmate.runtime._runtime
            >>> import checkmate.runtime.communication
            >>> a = checkmate.test_data.App()
            >>> r = checkmate.runtime._runtime.Runtime(a, checkmate.runtime.communication.Communication())
            >>> r.setup_environment(['C1'])
            >>> r.start_test()
            >>> proc = TestProcedure()
            >>> proc.exchanges.root.action
            'AC'
            >>> proc.exchanges.root.origin
            'C2'
            >>> proc.exchanges.root.destination
            'C1'
            >>> proc.exchanges.nodes[0].root.action
            'RE'
            >>> proc.exchanges.nodes[0].root.origin
            'C1'
            >>> proc.exchanges.nodes[0].root.destination
            'C3'
            >>> proc(result=None, system_under_test=['C1'])
            Traceback (most recent call last):
            ...
            Exception: No exchange 'RE' received by component 'C3'
        """
        super(TestProcedure, self).__init__(test)
        a = checkmate.test_data.App()
        c1 = a.components['C1']
        c2 = a.components['C2']
        c3 = a.components['C3']
        a.start()
        transition = c2.state_machine.transitions[0]
        self.exchanges = checkmate._tree.Tree(c2.process(transition.generic_incoming(c2.states))[0], [])
        for _e in c1.process([self.exchanges.root]):
            self.exchanges.add_node(checkmate._tree.Tree(_e, []))


class TestProcedureThreaded(checkmate.runtime.procedure.Procedure):
    """"""
    def __init__(self, test=None):
        """
            >>> import checkmate.test_data
            >>> import checkmate.runtime._runtime
            >>> import checkmate.runtime.communication
            >>> a = checkmate.test_data.App()
            >>> r = checkmate.runtime._runtime.Runtime(a, checkmate.runtime.communication.Communication())
            >>> r.setup_environment(['C1'])
            >>> r.start_test()
            >>> proc = TestProcedureThreaded()
            >>> proc.exchanges.nodes[1].root.action
            'ARE'
            >>> proc.exchanges.nodes[1].nodes[0].root.action
            'AP'
            >>> proc.exchanges.nodes[1].nodes[0].nodes[0].root.action
            'RL'
            >>> proc.exchanges.nodes[1].nodes[0].nodes[0].nodes[0].root.action
            'PP'
            >>> proc.exchanges.nodes[1].nodes[0].nodes[0].nodes[0].nodes[1].root.action
            'PA'
        """
        super(TestProcedureThreaded, self).__init__(test)
        a = checkmate.test_data.App()
        c1 = a.components['C1']
        c2 = a.components['C2']
        c3 = a.components['C3']
        a.start()
        transition = c2.state_machine.transitions[0]
        self.exchanges = checkmate._tree.Tree(c2.process(transition.generic_incoming(c2.states))[0], [])
        for _e in c1.process([self.exchanges.root]):
            self.exchanges.add_node(checkmate._tree.Tree(_e, []))
        for _e in c3.process([self.exchanges.nodes[0].root]):
            self.exchanges.nodes[0].add_node(checkmate._tree.Tree(_e, []))
        for _e in c2.process([self.exchanges.nodes[1].root]):
            self.exchanges.nodes[1].add_node(checkmate._tree.Tree(_e, []))
        for _e in c1.process([self.exchanges.nodes[1].nodes[0].root]):
            self.exchanges.nodes[1].nodes[0].add_node(checkmate._tree.Tree(_e, []))
        for _e in c3.process([self.exchanges.nodes[1].nodes[0].nodes[0].root]):
            self.exchanges.nodes[1].nodes[0].nodes[0].add_node(checkmate._tree.Tree(_e, []))
        for _e in c1.process([self.exchanges.nodes[1].nodes[0].nodes[0].nodes[0].root]):
            self.exchanges.nodes[1].nodes[0].nodes[0].nodes[0].add_node(checkmate._tree.Tree(_e, []))

def build_procedure(exchanges, output):
    class TestProc(checkmate.runtime.procedure.Procedure):
        """"""
            
    proc = TestProc()
    setattr(proc, 'exchanges', checkmate._tree.Tree(exchanges[0], [checkmate._tree.Tree(_o, []) for _o in output]))
    return proc

def TestProcedureGenerator(application_class=checkmate.test_data.App):
    a = application_class()
    c1 = a.components['C1']
    c2 = a.components['C2']
    c3 = a.components['C3']
    a.start()
    #Skip the last transition as no outgoing sent to 'C1'
    for _t in range(len(c2.state_machine.transitions)-1):
        transition = c2.state_machine.transitions[_t]
        _i = c2.process(transition.generic_incoming(c2.states))
        _o = c1.process(_i)
        yield build_procedure(_i, _o), c2.name, _i[0].action

def read_log(_f):
    class TestProc(checkmate.runtime.procedure.Procedure):
        """"""
            
    _e = pickle.load(_f)
    proc = TestProc()
    setattr(proc, 'exchanges', checkmate._tree.Tree(_e, []))
    _n = proc.exchanges
    try:
        while True:
            _e = pickle.load(_f)
            _n.add_node(checkmate._tree.Tree(_e, []))
            _n = _n.nodes[0]
    except EOFError:
        pass
    return proc

def TestLogProcedureGenerator(application_class=checkmate.test_data.App):
    a = application_class()
    for dirpath, dirnames, filenames in os.walk(os.getenv('CHECKMATE_LOG', './')):
        for _filename in [_f for _f in filenames if re.match('exchange-.*\.log', _f) is not None]:
            try:
                _f = open(os.path.join(dirpath, _filename), 'rb')
                yield read_log(_f), _filename
                _f.close()
            except FileNotFoundError:
                continue
            except EOFError:
                continue

def get_origin_component(exchange, components):
    for _c in components:
        if exchange.action in _c.outgoings:
            return _c

def TestProcedureInitialGenerator(application_class=checkmate.test_data.App):
    a = application_class()
    c1 = a.components['C1']
    c2 = a.components['C2']
    c3 = a.components['C3']
    a.start()
    a.get_initial_transitions()
    _incoming = a.initial_transitions[0].incoming[0].factory()
    origin = get_origin_component(_incoming, [c1,c2,c3])
    for _e in checkmate.service_registry.global_registry.server_exchanges(_incoming, origin):
        _o = a.components[_e.destination].process([_e])
        yield build_procedure([_e], _o), origin.name, _e.action, _e.destination


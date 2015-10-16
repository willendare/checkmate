# This code is part of the checkmate project.
# Copyright (C) 2013-2015 The checkmate project contributors
#
# This program is free software under the terms of the GNU GPL, either
# version 3 of the License, or (at your option) any later version.

import numpy
import random

import checkmate._tree
import checkmate._visual
import checkmate.sandbox
import checkmate.exception
import checkmate.pathfinder
import checkmate.tymata.transition


class Run(checkmate._tree.Tree):
    def __init__(self, block, nodes=None, states=None, exchanges=None):
        assert isinstance(block, checkmate.tymata.transition.Block)
        if nodes is None:
            nodes = []
        if states is None:
            states = ()
        if exchanges is None:
            exchanges = ()
        super(Run, self).__init__(block, nodes)
        self.exchanges = exchanges
        self._initial = None
        self._final = None
        self.itp_run = None
        self._collected_box = None
        self.itp_final = []
        self.change_states = []
        self.validate_items = (tuple(exchanges), tuple(states))
        self._collected_run = None
        for f in block.final:
            for s in states:
                if isinstance(s, f.partition_class):
                    self.change_states.append((type(s).__name__, s._dump()))
                    break

    @property
    def collected_run(self):
        if self._collected_run is None and self._collected_box is not None:
            for _r in self._collected_box.application.run_collection():
                if _r.compare_initial(self._collected_box.application) and \
                    set(self.walk()).issubset(set(_r.walk())):
                    self._collected_run = _r
                    break
        return self._collected_run
 
    @checkmate.fix_issue(
        'checkmate/issues/sandbox_call_notfound_transition.rst')
    def get_block_by_input_states(self, exchanges, component):
        for _b in self.walk():
            if (_b in component.engine.blocks and
                _b.is_matching_incoming(exchanges, component.states) and
                    _b.is_matching_initial(component.states)):
                return _b

    def get_validate_items_by_input(self, exchanges):
        items = []
        for run in self.breadthWalk():
            for _e in exchanges:
                if _e not in run.exchanges:
                    break
            else:
                items.append(run.validate_items)
        return items

    def get_states(self):
        if self._initial is None or self._final is None:
            initial_dict = dict()
            final_dict = dict()
            for run in self.breadthWalk():
                for index, _initial in enumerate(run.root.initial):
                    if _initial.partition_class not in initial_dict:
                        initial_dict[_initial.partition_class] = _initial
                    final_dict[_initial.partition_class] = _initial
                for index, _final in enumerate(run.root.final):
                    final_dict[_final.partition_class] = _final
            self._initial = set(initial_dict.values())
            self._final = set(final_dict.values())
            if len(self.itp_final):
                self._final = set(self.itp_final)

    def compare_initial(self, application):
        """"""
        box = checkmate.sandbox.Sandbox(type(application), application)
        if self.collected_run is not None:
            exchanges = self.collected_run.exchanges
        else:
            exchanges = self.exchanges
        return box(exchanges) and \
                set(self.walk()).issubset(set(box.blocks.walk()))

    @checkmate.fix_issue('checkmate/issues/compare_final.rst')
    @checkmate.fix_issue('checkmate/issues/sandbox_final.rst')
    @checkmate.fix_issue('checkmate/issues/validated_compare_states.rst')
    @checkmate.fix_issue("checkmate/issues/application_compare_states.rst")
    def compare_final(self, application):
        """"""
        final = {}
        for run in self.breadthWalk():
            for state in run.validate_items[1]:
                final[type(state)] = state
        matched = 0
        for state in final.values():
            for c in application.components.values():
                if state in c.states:
                    matched += 1
                    break
        if matched == len(final):
            return True
        return False

    def copy(self):
        _run = super().copy()
        _run.exchanges = self.exchanges
        _run.validate_items = self.validate_items
        return _run

    def add_node(self, tree):
        self._initial = None
        self._final = None
        super().add_node(tree)

    def visual_dump_initial(self):
        """
            >>> import checkmate.runs
            >>> import sample_app.application
            >>> src = sample_app.application.TestData.run_collection()
            >>> states = src[0].visual_dump_initial()
            >>> states['C1']['State']['value']
            True
            >>> states['C3']['Acknowledge']['value']
            False
        """
        state_dict = {}
        for run in self.breadthWalk():
            for _s in run.root.initial:
                if run.root.owner not in state_dict:
                    state_dict[run.root.owner] = {}
                state = _s.factory()
                cls_name = type(state).__name__
                if cls_name not in state_dict:
                    state_dict[run.root.owner][cls_name] = state._dump()
        return state_dict

    def visual_dump_final(self):
        """
            >>> import checkmate.runs
            >>> import sample_app.application
            >>> src = sample_app.application.TestData.run_collection()
            >>> states = src[0].visual_dump_final()
            >>> states['C1']['State']['value']
            False
            >>> states['C3']['Acknowledge']['value']
            True
        """
        state_dict = {}
        for run in self.breadthWalk():
            for state in run.change_states:
                if run.root.owner not in state_dict:
                    state_dict[run.root.owner] = {}
                state_dict[run.root.owner][state[0]] = state[1]
        return state_dict

    def visual_dump_steps(self):
        dump_dict = {}
        dump_dict['root'] = self.root.name
        dump_dict['incoming'] = [i.origin_code for i in self.root.incoming]
        dump_dict['outgoing'] = [o.origin_code for o in self.root.outgoing]
        dump_dict['states'] = {self.root.owner: dict(self.change_states)}
        dump_dict['nodes'] = []
        for element in self.nodes:
            dump_dict['nodes'].append(element.visual_dump_steps())
        return dump_dict

    @property
    def initial(self):
        self.get_states()
        return self._initial

    @property
    def final(self):
        self.get_states()
        return self._final


@checkmate.fix_issue('checkmate/issues/collected_run_in_itp_run.rst')
def get_runs_from_transition(application, transition, itp_transition=False):
    runs = []
    exchanges = []
    _class = type(application)
    box = checkmate.sandbox.Sandbox(_class, application, [transition])
    _incoming = transition.generic_incoming(box.application.state_list())
    origin = ''
    destination = []
    for _c in box.application.components.values():
        if _c.get_blocks_by_output(_incoming) is not None:
            origin = _c.name
        if len(_c.get_blocks_by_input(_incoming)) > 0:
            if _c.name not in destination:
                destination.append(_c.name)
    for _exchange in _incoming: 
        _exchange.origin_destination(origin, destination)
        exchanges.append(_exchange)
    assert box(exchanges)
    _run = box.blocks
    initial = checkmate.sandbox.Sandbox(_class, application, [transition])
    if itp_transition:
        _run.itp_final = transition.final
        _run._collected_box = initial
    runs.append(_run)
    return runs


def get_origin_exchanges(application_class):
    """
        >>> import sample_app.application
        >>> import checkmate.runs
        >>> cls = sample_app.application.TestData
        >>> exchanges = checkmate.runs.get_origin_exchanges(cls)
        >>> [_e.value for _e in exchanges]
        ['PBAC', 'PBRL', 'PBPP']
    """
    incomings = []
    outgoings = []
    origin_exchanges = []
    application = application_class()
    application.start()
    for _component in application.components.values():
        for _block in _component.engine.blocks:
            incomings.extend([_i for _i in _block.incoming
                                if _i not in incomings])
            outgoings.extend([_o for _o in _block.outgoing
                                if _o not in outgoings])
    for _incoming in incomings:
        for _o in outgoings:
            if _incoming.partition_class == _o.partition_class:
                break
        else:
            _i = _incoming.factory(**_incoming.resolve())
            if _i in origin_exchanges:
                continue
            for _e in _component.exchange_destination(_i):
                origin_exchanges.append(_e)
    return origin_exchanges


@checkmate.fix_issue('checkmate/issues/pathfinding_from_safe_runs.rst')
def followed_runs(application, exchanges, current_run=None):
    """
    3 conditions:
        1. we find next runs by matrix
        2. current_run is None, find next runs by exchanges
        3. find next runs by exchanges and update matrix
    >>> import sample_app.application
    >>> import checkmate.runs
    >>> import checkmate.sandbox
    >>> app = sample_app.application.TestData
    >>> exchanges = app.origin_exchanges()
    >>> box = checkmate.sandbox.Sandbox(app)
    >>> next_runs = [_r for _r in checkmate.runs.followed_runs(
    ...     box.application, exchanges, None)]
    >>> next_runs[0].validate_items[0][0].value
    'PBAC'
    >>> box(next_runs[0].exchanges)
    True
    >>> next_runs = [_r for _r in checkmate.runs.followed_runs(
    ...     box.application, exchanges, next_runs[0])]
    >>> next_runs[0].validate_items[0][0].value
    'PBRL'
    """
    _class = type(application)
    runs = application._matrix_runs
    next_runs = []
    if current_run is not None:
        if current_run in runs:
            _index = runs.index(current_run)
            if application._runs_found[_index]:
                for i in application._matrix[_index].nonzero()[1].tolist()[0]:
                    if runs[i] not in next_runs:
                        next_runs.append(runs[i])
                    yield runs[i]
    box = checkmate.sandbox.Sandbox(_class, application)
    transform_runs = []
    for _exchange in exchanges:
        if _exchange in [_r.exchanges[0] for _r in next_runs]:
            continue
        box.restart()
        if box([_exchange]):
            _run = box.blocks
            if _run not in next_runs:
                next_runs.append(_run)
                application.update_matrix([_run], current_run)
                return_path = transform_path(application, _run)
                _unsafe_runs = []
                if current_run is None or\
                    current_run not in _class._unsafe_runs:
                    if return_path is not None:
                        if (_run, return_path) not in _class._safe_runs:
                            _class._safe_runs.append((_run, return_path))
                    else:
                        _unsafe_runs.append(_run)
                else:
                    _unsafe_runs.append(_run)
                    if return_path is not None:
                        _unsafe_runs.extend(return_path)
                _class._unsafe_runs.extend([_r for _r in _unsafe_runs
                    if _r not in _class._unsafe_runs])
                if return_path is not None:
                    _current_run = _run
                    for _r in return_path:
                        application.update_matrix([_r], _current_run)
                        _current_run = _r
                    transform_runs.append(_current_run)
                for _r in transform_runs:
                    application.update_matrix(next_runs, _r)
                yield _run


def transform_path(application, run):
    """
    run are safe only when there is one-step way found
    that can use to transform to initial states
        >>> import checkmate.runs
        >>> import checkmate.sandbox
        >>> import sample_app.application
        >>> app = sample_app.application.TestData()
        >>> box = checkmate.sandbox.Sandbox(type(app), app)
        >>> box2 = checkmate.sandbox.Sandbox(type(app), app)
        >>> exchanges = app.origin_exchanges()
        >>> pbac = [ex for ex in exchanges if ex.value == 'PBAC'][0]
        >>> pbrl = [ex for ex in exchanges if ex.value == 'PBRL'][0]
        >>> box([pbac]), box2([pbac])
        (True, True)
        >>> box2([pbrl])
        True
        >>> run_pbac_ok = box.blocks
        >>> run_pbrl = box2.blocks
        >>> path = checkmate.runs.transform_path(box.application, run_pbac_ok)
        >>> path is not None
        False
        >>> path = checkmate.runs.transform_path(box.application, run_pbrl)
        >>> path is not None
        True
        >>> box([pbrl]), box2([pbac])
        (True, True)
        >>> run_pbac_er = box2.blocks
        >>> run_pbac_er.compare_initial(box.application)
        True
        >>> path = checkmate.runs.transform_path(box.application, run_pbac_er)
        >>> path is not None
        True
    """
    return_path = None
    if run.compare_initial(application):
        _cls = type(application)
        box = checkmate.sandbox.Sandbox(_cls, application)
        _states0 = application.copy_states()
        box(run.exchanges)
        _states1 = box.application.copy_states()
        if _states0 == _states1:
            return_path = []
        else:
            exchanges = box.application.origin_exchanges()
            for _ex in exchanges[:]:
                sandbox = checkmate.sandbox.Sandbox(_cls, box.application)
                if sandbox([_ex]):
                    tmp_run = sandbox.blocks
                    _states2 = sandbox.application.copy_states()
                    if  _states0 == _states2:
                        return_path = [tmp_run]
                        break
    return return_path


@checkmate.report_issue('checkmate/issues/run_collect_multi_instances.rst')
@checkmate.fix_issue('checkmate/issues/match_R2_in_runs.rst')
@checkmate.fix_issue('checkmate/issues/get_runs_from_failed_simulate.rst')
@checkmate.report_issue('checkmate/issues/execute_AP_R_AP_R2.rst',
                            failed=3)
def origin_runs_generator(application, randomized=False):
    """
        >>> import checkmate.runs
        >>> import sample_app.application
        >>> app = sample_app.application.TestData()
        >>> origin_runs = [_r for _r in
        ...     checkmate.runs.origin_runs_generator(app)]
        >>> len(origin_runs)
        4
    """
    _cls = type(application)
    if hasattr(_cls, _cls._run_collection_attribute):
        runs = _cls.run_collection()
        if randomized:
            runs = random.sample(runs, len(runs))
        for _r in runs:
            yield _r
        return
    exchanges = application.origin_exchanges()
    current_run=None
    yielded_runs = []
    unyielded_runs = []
    box = checkmate.sandbox.Sandbox(_cls, application)
    while True:
        _path = []
        gen = followed_runs(box.application, exchanges, current_run)
        next_runs = [r for r in gen]
        new_next_runs = [_r for _r in next_runs if _r not in yielded_runs]
        if len(new_next_runs) > 0:
            unyielded_runs.extend([_r for _r in new_next_runs
                                        if _r not in unyielded_runs])
            current_run = new_next_runs[0]
        else:
            if len(unyielded_runs) == 0:
                break
            current_run, _path = checkmate.pathfinder.find_path(\
                box.application, unyielded_runs, exchanges, current_run)
        if current_run in unyielded_runs:
            unyielded_runs.remove(current_run)
        for _r in _path + [current_run]:
            box(_r.exchanges)
        current_run = box.blocks
        yielded_runs.append(current_run)
        yield current_run


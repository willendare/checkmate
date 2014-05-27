import copy
import collections

import zope.interface

import checkmate._exec_tools
import checkmate._module


def _build_resolve_logic(transition, type, data):
    """
        >>> import sample_app.application
        >>> import sample_app.exchanges
        >>> import checkmate._storage
        >>> a = sample_app.application.TestData()
        >>> t = a.components['C1'].state_machine.transitions[1]
        >>> checkmate._storage._build_resolve_logic(t, 'final', t.final[0])
        {'R': ('incoming', <InterfaceClass sample_app.exchanges.IAction>)}
    """
    resolved_arguments = {}
    entry = getattr(transition, type)
    arguments = list(entry[entry.index(data)].arguments['attribute_values'].keys()) + list(entry[entry.index(data)].arguments['values'])
    for arg in arguments:
        found = False
        if type in ['final', 'incoming']:
            for item in transition.initial:
                if arg == item.code:
                    resolved_arguments[arg] = ('initial', item.interface)
                    found = True
                    break
        if ((not found) and len(transition.incoming) != 0):
            if type in ['final', 'outgoing']:
                for item in transition.incoming:
                    if arg in list(item.arguments['attribute_values'].keys()):
                        resolved_arguments[arg] = ('incoming', item.interface)
                        found = True
                        break
        if not found:
            if type in ['outgoing']:
                for item in transition.final:
                    if arg == item.code:
                        resolved_arguments[arg] = ('final', item.interface)
                        found = True
                        break
    return resolved_arguments


def store(type, interface, name, description=None):
    """
        >>> import checkmate._storage
        >>> import sample_app.exchanges
        >>> import sample_app.application
        >>> import sample_app.component.component_1_states
        >>> a = sample_app.application.TestData()
        >>> acr = sample_app.data_structure.ActionRequest()
        >>> acr.value
        'NORM'
        >>> st = checkmate._storage.store('states', sample_app.component.component_1_states.IAnotherState, 'Q0()')
        >>> state = st.factory()
        >>> print(state.value)
        None
        >>> st = checkmate._storage.store('exchanges', sample_app.exchanges.IAction, 'AP(R)')
        >>> ex = st.factory({'R': 'HIGH'})
        >>> (ex.action, ex.R) # doctest: +ELLIPSIS
        ('AP', <sample_app.data_structure.ActionRequest object at ...
    """
    if checkmate._exec_tools.method_unbound(name) or type == 'exchanges':
        code = checkmate._exec_tools.get_method_basename(name)
        if type == 'exchanges':
            try:
                return checkmate._storage.InternalStorage(interface, name, description, getattr(checkmate._module.get_module_defining(interface), code))
            except AttributeError:
                raise AttributeError(checkmate._module.get_module_defining(interface).__name__ + " has no function defined: " + code)
        else:
            try:
                return checkmate._storage.InternalStorage(interface, name, description, getattr(checkmate._module.get_class_implementing(interface), code))
            except AttributeError:
                raise AttributeError(checkmate._module.get_class_implementing(interface).__name__ + ' has no function defined: ' + code)
    else:
        return checkmate._storage.InternalStorage(interface, name, description)


class Data(object):
    def __init__(self, type, interface, codes, full_description=None):
        self.type = type
        self.interface = interface
        self.codes = codes
        self.full_description = full_description

    @property
    def storage(self):
        _list = []
        for code in self.codes:
            try:
                code_description = self.full_description[code]
            except:
                code_description = (None, None, None)
            _storage = store(self.type, self.interface, code, code_description)
            _list.append(_storage)
        if self.codes is None or len(self.codes) == 0:
            _list.append(store(self.type, self.interface, ''))
        return _list

    def get_description(self, item):
        """ Return description corresponding to item """
        for stored_item in list(self.storage):
            if item == stored_item.factory():
                return stored_item.description
        return (None, None, None)


class TransitionData(collections.OrderedDict):
    def __init__(self, initial, incoming, final, outgoing):
        assert type(final) == list
        assert type(initial) == list
        assert type(incoming) == list
        assert type(outgoing) == list

        for item in initial + final + incoming + outgoing:
            assert isinstance(item, Data)

        super(TransitionData, self).__init__()
        # OrderedDict to keep order ('initial', 'incoming', 'final', 'outgoing')
        self['initial'] = initial
        self['incoming'] = incoming
        self['final'] = final
        self['outgoing'] = outgoing


class PartitionStorage(Data):
    """"""


class TransitionStorage(object):
    def __init__(self, transition):
        """ Build the list of InternalStorage
        """
        assert isinstance(transition, TransitionData)
        for key in iter(transition):
            _list = []
            for item in transition[key]:
                _list.append(item.storage[0])
            setattr(self, key, _list)

        for _attribute in ('incoming', 'final', 'outgoing'):
            for item in getattr(self, _attribute):
                item.resolve_logic = _build_resolve_logic(self, _attribute, item)


class IStorage(zope.interface.Interface):
    """"""
    def factory(self, args=[], kwargs={}):
        """"""


@zope.interface.implementer(IStorage)
class InternalStorage(object):
    """Support local storage of data (status or data_structure) information in transition"""
    def __init__(self, interface, name, description, function=None):
        """
            >>> import sample_app.application
            >>> import sample_app.data_structure
            >>> ds_ap = sample_app.data_structure.ActionRequest('HIGH')
            >>> ds_ap.value
            'HIGH'
        """
        self.code = checkmate._exec_tools.get_method_basename(name)
        self.description = description
        self.interface = interface
        self._class = checkmate._module.get_class_implementing(interface)
        if function is None:
            self.function = self._class
        else:
            self.function = function

        self.arguments = checkmate._exec_tools.method_arguments(name, interface)
        self.resolve_logic = {}

    def factory(self, args=[], kwargs={}):
        """
            >>> 'Q0.append(R)'
            'Q0.append(R)'

            >>> import sample_app.application
            >>> import sample_app.data_structure
            >>> a = sample_app.application.TestData()
            >>> r1 = sample_app.data_structure.ActionRequest('HIGH')
            >>> r1.value
            'HIGH'
        """
        def wrapper(func, param, kwparam):
            if type(args) == list and self.interface.implementedBy(self.function):
                if len(self.arguments['values']) > 0 and len(args) > 0:
                    func = self.function.__init__
                    state = args[0]
                    value = self.arguments['values'][0]
                    return func(state, value)
            else:
                return func(*param, **kwparam)

        if len(args) == 0:
            args = self.arguments['values']
        if len(kwargs) == 0:
            kwargs = self.arguments['attribute_values']
        else:
            _local_kwargs = copy.deepcopy(self.arguments['attribute_values'])
            _local_kwargs.update(kwargs)
            kwargs = _local_kwargs
        return wrapper(self.function, args, kwargs)

    def resolve(self, arg, states=[], exchanges=[]):
        """
            >>> import sample_app.application
            >>> import sample_app.exchanges
            >>> a = sample_app.application.TestData()
            >>> t = a.components['C1'].state_machine.transitions[1]
            >>> inc = t.incoming[0].factory()
            >>> states = [t.initial[0].factory()]
            >>> t.final[0].resolve('R', states=[states])
            Traceback (most recent call last):
            ...
            AttributeError
            >>> t.final[0].resolve('R', exchanges=[inc]) # doctest: +ELLIPSIS
            {'R': <sample_app.data_structure.ActionRequest object at ...
            >>> inc = t.incoming[0].factory(kwargs={'R': 1})
            >>> (inc.action, inc.R)  # doctest: +ELLIPSIS
            ('AP', 1)
            >>> t.final[0].resolve('R', exchanges=[inc])  # doctest: +ELLIPSIS
            {'R': 1}
        """
        if arg in self.resolve_logic.keys():
            (_type, _interface) = self.resolve_logic[arg]
            if _type in ['initial', 'final']:
                for _state in states:
                    if _interface.providedBy(_state):
                        return {arg: _state.value}
                raise AttributeError
            else:
                for _exchange in [_e for _e in exchanges if _interface.providedBy(_e)]:
                    try:
                        return {arg: getattr(_exchange, arg)}
                    except AttributeError:
                        raise AttributeError
                raise AttributeError
        raise AttributeError

    def match(self, target_copy):
        for _target in [_t for _t in target_copy if self.interface.providedBy(_t)]:
            if _target == self.factory():
                target_copy.remove(_target)
                break
        return target_copy

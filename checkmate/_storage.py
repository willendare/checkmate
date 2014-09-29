import copy
import collections

import zope.interface

import checkmate._module
import checkmate._exec_tools


def _to_interface(_classname):
    return 'I' + _classname

def name_to_interface(name, modules):
    for _m in modules:
        if hasattr(_m, _to_interface(name)):
            interface = getattr(_m, _to_interface(name))
            break
    else:
        raise AttributeError(_m.__name__+' has no interface defined:'+_to_interface(name))
    return interface

def _build_resolve_logic(transition, type, data):
    """Build logic to resolve kwargs in TransitionStorage

        >>> import sample_app.application
        >>> import sample_app.exchanges
        >>> import checkmate._storage
        >>> a = sample_app.application.TestData()
        >>> t = a.components['C1'].state_machine.transitions[1]
        >>> t.final[0].resolve_logic
        {'R': ('incoming', <InterfaceClass sample_app.exchanges.IAction>)}
    """
    resolved_arguments = {}
    entry = transition[type]
    arguments = list(entry[entry.index(data)].arguments['attribute_values'].keys()) + list(entry[entry.index(data)].arguments['values'])
    for arg in arguments:
        found = False
        if type in ['final', 'incoming']:
            for item in transition['initial']:
                if arg == item.code:
                    resolved_arguments[arg] = ('initial', item.interface)
                    found = True
                    break
        if ((not found) and len(transition['incoming']) != 0):
            if type in ['final', 'outgoing']:
                for item in transition['incoming']:
                    if arg in list(item.arguments['attribute_values'].keys()):
                        resolved_arguments[arg] = ('incoming', item.interface)
                        found = True
                        break
        if not found:
            if type in ['outgoing']:
                for item in transition['final']:
                    if arg == item.code:
                        resolved_arguments[arg] = ('final', item.interface)
                        found = True
                        break
    return resolved_arguments


def store(type, interface, code, value, description=None):
    """
        >>> import checkmate._storage
        >>> import sample_app.application
        >>> import sample_app.exchanges
        >>> import sample_app.component.component_1_states
        >>> a = sample_app.application.TestData()
        >>> acr = sample_app.data_structure.ActionRequest()
        >>> acr
        ['AT1', 'NORM']
        >>> st = checkmate._storage.store('states', sample_app.component.component_1_states.IAnotherState, 'Q0()', 'Q0()')
        >>> state = st.factory()
        >>> print(state.value)
        None
        >>> st = checkmate._storage.store('exchanges', sample_app.exchanges.IAction, 'AP(R)', 'AP(R)')
        >>> ex = st.factory(kwargs={'R': 'HIGH'})
        >>> (ex.action, ex.R)
        ('AP', 'HIGH')
    """
    name = checkmate._exec_tools.get_method_basename(code)
    if type == 'exchanges':
        try:
            return InternalStorage(interface, code, description, getattr(checkmate._module.get_module_defining(interface), name))
        except AttributeError:
            raise AttributeError(checkmate._module.get_module_defining(interface).__name__ + " has no function defined: " + name)
    elif checkmate._exec_tools.method_unbound(code, interface):
        try:
            return InternalStorage(interface, code, description, getattr(checkmate._module.get_class_implementing(interface), name))
        except AttributeError:
            raise AttributeError(checkmate._module.get_class_implementing(interface).__name__ + ' has no function defined: ' + name)
    else:
        return checkmate._storage.InternalStorage(interface, value, description, checkmate._module.get_class_implementing(interface))


class Data(object):
    def __init__(self, type, interface, code_value_list, full_description=None):
        self.type = type
        self.interface = interface
        self.full_description = full_description

        self.storage = []
        #n items for PartitionStorage and 1 item for TransitionStorage
        for data in code_value_list:
            code = data[0]
            value = data[1]
            try:
                code_description = self.full_description[code]
            except:
                code_description = (None, None)
            _storage = store(self.type, self.interface, code, value, code_description)
            self.storage.append(_storage)
        if not self.storage:
            self.storage = [store(self.type, self.interface, '')]

    def get_description(self, item):
        """ Return description corresponding to item """
        for stored_item in list(self.storage):
            if item == stored_item.factory():
                return stored_item.description
        return (None, None)


class PartitionStorage(Data):
    """"""


class TransitionStorage(collections.defaultdict):
    def __init__(self, items, module_dict):
        super(TransitionStorage, self).__init__(list)

        for _k, _v in items.items():
            if _k == 'initial' or _k == 'final':
                module_type = 'states'
            elif _k == 'incoming' or _k == 'outgoing':
                module_type = 'exchanges'
            elif _k == 'name':
                continue
            for each_item in _v:
                for _name, _data in each_item.items():
                    interface = name_to_interface(_name, module_dict[module_type])
                    storage_data = Data(module_type, interface, [(_data, _data)])
                    if _k == 'initial':
                        self['initial'].append(storage_data.storage[0])
                    elif _k == 'final':
                        if interface.implementedBy(storage_data.storage[0].function):
                            storage_data.storage[0].function = storage_data.storage[0].function.__init__
                        self['final'].append(storage_data.storage[0])
                    elif _k == 'incoming':
                        self['incoming'].append(storage_data.storage[0])
                    elif _k == 'outgoing':
                        self['outgoing'].append(storage_data.storage[0])

        for _attribute in ('incoming', 'final', 'outgoing'):
            for item in self[_attribute]:
                item.resolve_logic = _build_resolve_logic(self, _attribute, item)


class IStorage(zope.interface.Interface):
    """"""
    def factory(self, args=[], kwargs={}):
        """"""


@zope.interface.implementer(IStorage)
class InternalStorage(object):
    """Support local storage of data (status or data_structure) information in transition"""
    def __init__(self, interface, name, description, function):
        """
            >>> import sample_app.application
            >>> import sample_app.exchanges
            >>> st = InternalStorage(sample_app.exchanges.IAction, "AP(R)", None, sample_app.exchanges.Action)
            >>> st.arguments['values'], st.arguments['attribute_values']
            ((), {'R': None})
            >>> dir(st.factory())
            ['R']
            >>> st.factory().R
            ['AT1', 'NORM']
        """
        self.code = checkmate._exec_tools.get_method_basename(name)
        self.description = description
        self.interface = interface
        self.function = function

        self.arguments = checkmate._exec_tools.method_arguments(name, interface)
        self.resolve_logic = {}

    @checkmate.report_issue('checkmate/issues/init_with_arg.rst')
    def factory(self, args=None, kwargs=None):
        """
            >>> import sample_app.application
            >>> import sample_app.data_structure
            >>> import checkmate._storage
            >>> st = checkmate._storage.InternalStorage(sample_app.exchanges.IAction, "AP(R)", None, sample_app.exchanges.Action)
            >>> st.arguments['values'], st.arguments['attribute_values']
            ((), {'R': None})
            >>> dir(st.factory())
            ['R']
            >>> st.factory().R
            ['AT1', 'NORM']
            >>> st.factory(kwargs={'R':['AT2', 'HIGH']}).R
            ['AT2', 'HIGH']

            >>> import sample_app.application
            >>> a = sample_app.application.TestData()
            >>> c = a.components['C1']   
            >>> a.start()
            >>> i = sample_app.exchanges.AP()
            >>> c.process([i]) # doctest: +ELLIPSIS
            [<sample_app.exchanges.ThirdAction object at ...
            >>> i = sample_app.exchanges.AC()
            >>> c.process([i]) # doctest: +ELLIPSIS
            [<sample_app.exchanges.Reaction object at ...
            >>> c.states[1].value
            [{'R': ['AT1', 'NORM']}]
            >>> t = c.state_machine.transitions[2]
            >>> i = t.incoming[0].factory(); i.action
            'PP'
            >>> t.final[1].function # doctest: +ELLIPSIS
            <function State.pop at ...
            >>> t.final[1].factory([c.states[1]]) # doctest: +ELLIPSIS
            <sample_app.component.component_1_states.AnotherState object at ...
            >>> c.states[1].value
            []
        """
        def wrapper(func, param, kwparam):
            if len(param) > 0 and self.interface.providedBy(param[0]):
                state = param[0]
                try:
                    value = self.arguments['values'][0]
                except IndexError:
                    value = None
                func(state, value, **kwparam)
                return state
            else:
                return func(*param, **kwparam)

        if args is None:
            args = self.arguments['values']
        if kwargs is None:
            kwargs = self.arguments['attribute_values']
        else:
            _local_kwargs = copy.deepcopy(self.arguments['attribute_values'])
            _local_kwargs.update(kwargs)
            kwargs = _local_kwargs
        return wrapper(self.function, args, kwargs)

    def resolve(self, _type, states=None, exchanges=None):
        """
            >>> import sample_app.application
            >>> import sample_app.exchanges
            >>> a = sample_app.application.TestData()
            >>> t = a.components['C1'].state_machine.transitions[1]
            >>> inc = t.incoming[0].factory()
            >>> states = [t.initial[0].factory()]
            >>> t.final[0].resolve('final', states=[states])
            {}
            >>> t.final[0].resolve('final', exchanges=[inc])
            {'R': ['AT1', 'NORM']}
            >>> inc = t.incoming[0].factory(kwargs={'R': 1})
            >>> (inc.action, inc.R)  # doctest: +ELLIPSIS
            ('AP', 1)
            >>> t.final[0].resolve('final', exchanges=[inc])  # doctest: +ELLIPSIS
            {'R': 1}
        """
        resolved_arguments = {}
        arguments = list(self.arguments['attribute_values'].keys()) + list(self.arguments['values'])
        for arg in arguments:
            try:
                if arg in self.resolve_logic.keys():
                    (_type, _interface) = self.resolve_logic[arg]
                    if _type in ['initial', 'final'] and states is not None:
                        for _state in states:
                            if _interface.providedBy(_state):
                                resolved_arguments.update({arg: _state.value})
                                break
                    elif exchanges is not None:
                        for _exchange in [_e for _e in exchanges if _interface.providedBy(_e)]:
                            try:
                                resolved_arguments.update({arg: getattr(_exchange, arg)})
                                break
                            except AttributeError:
                                continue
            except AttributeError:
                continue
        return resolved_arguments

    def match(self, target_copy, reference=None, incoming_list=None):
        """
            >>> import checkmate.runtime._runtime
            >>> import checkmate.runtime.test_plan
            >>> import sample_app.application
            >>> import sample_app.component.component_1_states
            >>> import sample_app.component.component_3_states
            >>> gen = checkmate.runtime.test_plan.TestProcedureInitialGenerator(sample_app.application.TestData)
            >>> proc = [p[0] for p in gen][0]
            >>> app = sample_app.application.TestData()
            >>> app.start()
            >>> saved = app.state_list()
            >>> c1 = app.components['C1']
            >>> c3 = app.components['C3']

            >>> final = [_f for _f in proc.final if _f.interface == sample_app.component.component_1_states.IState][0]
            >>> t1 = c1.state_machine.transitions[0]
            >>> c1.simulate(t1) #doctest: +ELLIPSIS
            [<sample_app.exchanges.Reaction object at ...
            >>> len(final.match(app.state_list(), saved)) != len(saved)
            True

            >>> final = [_f for _f in proc.final if _f.interface == sample_app.component.component_3_states.IAcknowledge][0]
            >>> t3 = c3.state_machine.transitions[0]
            >>> c3.simulate(t3)
            []
            >>> len(proc.final[1].match(app.state_list(), saved)) != len(saved)
            True
        """
        for _target in [_t for _t in target_copy if self.interface.providedBy(_t)]:
            _initial = None
            resolved_arguments = None
            if reference is not None:
                _initial = [_i for _i in reference if self.interface.providedBy(_i)]
                resolved_arguments = self.resolve('final', _initial, incoming_list)
            
            if _target == self.factory(_initial, kwargs=resolved_arguments):
                target_copy.remove(_target)
                break
        return target_copy

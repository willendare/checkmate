import collections

import checkmate._storage
import checkmate._exec_tools
import checkmate.parser.yaml_visitor


def make_transition(items, exchanges, state_modules):
    module_dict = {'states': state_modules,
                   'exchanges': exchanges}
    try:
        tran_name = items['name']
    except KeyError:
        tran_name = 'unknown'
    ts = checkmate._storage.TransitionStorage(items, module_dict)
    return ts.factory()


class Declarator(object):
    """"""
    data_value = {}

    def __init__(self, data_module, exchange_module,
                 state_module=None, transition_module=None, data_value=None):
        self.module = {}
        self.module['data_structure'] = data_module
        self.module['states'] = state_module
        self.module['exchanges'] = exchange_module
        if data_value is not None:
            self.__class__.data_value = data_value

        self.output = {
            'data_structure': [],
            'states': [],
            'exchanges': [],
            'transitions': []}

    @checkmate.fix_issue("checkmate/issues/new_partition_in_doctest.rst")
    def new_partition(self,
                      partition_type,
                      signature,
                      codes_list,
                      values_list,
                      full_description=None,
                      attributes={},
                      define_attributes={}):
        """
        >>> import collections
        >>> import checkmate._module
        >>> import checkmate.application
        >>> import checkmate.data_structure
        >>> import checkmate.partition_declarator
        >>> state_module = checkmate._module.get_module(
        ...                    'checkmate.application', 'states')
        >>> exchange_module = checkmate._module.get_module(
        ...                       'checkmate.application', 'exchanges')
        >>> data_structure_module = checkmate._module.get_module(
        ...                             'checkmate.application', 'data')
        >>> de = checkmate.partition_declarator.Declarator(
        ...         data_structure_module,
        ...         exchange_module,
        ...         state_module=state_module)
        >>> de.new_partition(
        ...     'data_structure',
        ...     "TestActionRequest",
        ...     codes_list=['TestActionRequestNORM'],
        ...     values_list=['NORM'],
        ...     full_description=collections.OrderedDict(
        ...                         [('TestActionRequestNORM',
        ...                             ('D-PRIO-01',
        ...                              'NORM valid value',
        ...                              'NORM priority value'))]))
        >>> output = de.get_output()
        >>> ds = output['data_structure']
        >>> ds[0][0]
        <InterfaceClass checkmate.data.ITestActionRequest>
        >>> ds[0][1].get_description(
        ...             checkmate.data.TestActionRequest('NORM'))
        ('D-PRIO-01', 'NORM valid value', 'NORM priority value')
        >>> de.new_partition('states',
        ...                  "TestState",
        ...                   codes_list=['TestStateTrue'],
        ...                   values_list=[True])
        >>> dst = de.get_output()['states']
        >>> dst[0][0]
        <InterfaceClass checkmate.states.ITestState>
        >>> de.new_partition('exchanges',
        ...                  'TestAction(R:TestActionRequest)',
        ...                   codes_list=['AP(R)'],
        ...                   values_list=['AP'],
        ...                   attributes={'communication':'test_comm'})
        >>> dee = de.get_output()['exchanges']
        >>> dee[0][0]
        <InterfaceClass checkmate.exchanges.ITestAction>
        >>> dee[0][-1].storage[0].factory().R._valid_values
        ['NORM']
        >>> dee[0][-1].storage[0].factory().communication
        'test_comm'
        """
        _module = self.module[partition_type]
        defined_class, defined_interface =\
            checkmate._exec_tools.exec_class_definition(
                self.module['data_structure'],
                partition_type,
                _module,
                signature,
                values_list,
                attributes)
        code_arguments = collections.OrderedDict()
        for code, value in zip(codes_list, values_list):
            code_arguments[code] = {'value': value}
        if defined_class.__name__ in self.__class__.data_value:
            code_arguments.update(
                self.__class__.data_value[defined_class.__name__])
        partition_storage = checkmate._storage.PartitionStorage(
                                partition_type, defined_interface,
                                code_arguments, full_description)
        setattr(defined_class, 'define_attributes', define_attributes)
        setattr(defined_class, 'partition_storage', partition_storage)
        self.output[partition_type].append((defined_interface, partition_storage))

    def new_transition(self, item):
        """
        >>> import checkmate._module
        >>> import checkmate.application
        >>> import checkmate.data_structure
        >>> import checkmate.partition_declarator
        >>> state_module = checkmate._module.get_module(
        ...                    'checkmate.application', 'states')
        >>> exchange_module = checkmate._module.get_module(
        ...                       'checkmate.application', 'exchanges')
        >>> data_structure_module = checkmate._module.get_module(
        ...                             'checkmate.application', 'data')
        >>> de = checkmate.partition_declarator.Declarator(
        ...         data_structure_module,
        ...         exchange_module,
        ...         state_module=state_module)
        >>> de.new_partition('data_structure',
        ...                  "TestActionRequest",
        ...                   codes_list=['TestActionRequestNORM'],
        ...                   values_list=['NORM'],
        ...                   full_description=None)
        >>> de.new_partition('states',
        ...                  "TestState",
        ...                   codes_list=['TestStateTrue()',
        ...                   'TestStateFalse()'],
        ...                   values_list=[True, False])
        >>> de.new_partition('exchanges',
        ...                  'TestAction(R:TestActionRequest)',
        ...                   codes_list=['AP(R)'],
        ...                   values_list=['AP'])
        >>> de.new_partition('exchanges', 'TestReturn()',
        ...                   codes_list=['DA()'], values_list=['DA'])
        >>> item = {'name': 'Toggle TestState tran01',
        ...         'initial': [{'TestState': 'TestStateTrue'}],
        ...         'outgoing': [{'TestReturn': 'DA()'}],
        ...         'incoming': [{'TestAction': 'AP(R)'}],
        ...         'final': [{'TestState': 'TestStateFalse'}]}
        >>> de.new_transition(item)
        >>> de.get_output()['transitions'] # doctest: +ELLIPSIS
        [<checkmate.transition.Transition object at ...
        """
        self.output['transitions'].append(
            make_transition(item, [self.module['exchanges']],
            [self.module['states']]))

    def new_definitions(self, data_source):
        """
        >>> import collections
        >>> import checkmate._module
        >>> import checkmate.application
        >>> import checkmate.data_structure
        >>> import checkmate.partition_declarator
        >>> state_module = checkmate._module.get_module(
        ...                    'checkmate.application', 'states')
        >>> exchange_module = checkmate._module.get_module(
        ...                       'checkmate.application', 'exchanges')
        >>> data_structure_module = checkmate._module.get_module(
        ...                             'checkmate.application', 'data')
        >>> data_source = collections.OrderedDict([
        ... ('data_structure',[{
        ...     'clsname': 'TestActionRequest',
        ...     'codes_list': ['TestActionRequestNORM'],
        ...     'values_list': ['NORM'],
        ...     'full_desc': None,
        ...     'attributes': {},
        ...     'define_attributes': {}}]),
        ... ('states', [{
        ...    'clsname': 'TestState',
        ...    'codes_list': ['TestStateTrue'],
        ...    'values_list': [True],
        ...    'full_desc': None,
        ...    'attributes': {},
        ...    'define_attributes': {}}]),
        ... ('exchanges', [{
        ...    'clsname': 'TestAction(R:TestActionRequest)',
        ...    'codes_list': ['AP(R)'],
        ...    'values_list': ['AP'],
        ...    'full_desc': None,
        ...    'attributes': {},
        ...    'define_attributes': {}}])
        ... ])
        >>> de = checkmate.partition_declarator.Declarator(
        ...          data_structure_module,
        ...          exchange_module,
        ...          state_module=state_module)
        >>> de.new_definitions(data_source)
        >>> output = de.get_output()
        >>> output['data_structure'][0][0]
        <InterfaceClass checkmate.data.ITestActionRequest>
        >>> output['states'][0][0]
        <InterfaceClass checkmate.states.ITestState>
        >>> output['exchanges'][0][0]
        <InterfaceClass checkmate.exchanges.ITestAction>
        >>> output['transitions']
        []
        """
        for partition_type, chunk in data_source.items():
            for data in chunk:
                if partition_type == 'transitions':
                    self.new_transition(data)
                else:
                    self.new_partition(partition_type,
                                       data['clsname'],
                                       data['codes_list'],
                                       data['values_list'],
                                       data['full_desc'],
                                       data['attributes'],
                                       data['define_attributes'])

    def get_output(self):
        return self.output

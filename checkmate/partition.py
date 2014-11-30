class Partition(object):
    """"""
    partition_attribute = tuple()

    @classmethod
    def method_arguments(cls, signature):
        """
            >>> import sample_app.application
            >>> import sample_app.exchanges
            >>> action = sample_app.exchanges.Action()
            >>> action.method_arguments("PP('AT1')")
            OrderedDict([('R', 'AT1')])
            >>> action.method_arguments("Action('R')")
            OrderedDict()
            >>> action.method_arguments("AP('R2')")['R'].C.value, action.method_arguments("AP('R2')")['R'].P.value
            ('AT2', 'HIGH')
        """
        arguments = {}
        found_label = signature.find('(')
        parameters = signature[found_label:][1:-1].split(', ')
        args = tuple([_p.strip("'") for _p in parameters if (_p != '' and
                      _p.strip("'") not in cls._sig.parameters.keys())])
        arguments = cls._sig.bind_partial(*args).arguments
        for attr, value in arguments.items():
            data_cls = cls._construct_values[attr]
            if hasattr(data_cls, value):
                arguments[attr] = data_cls(**getattr(data_cls, value))
            else:
                for _s in data_cls.partition_storage.storage:
                    if _s.code == value:
                        arguments[attr] = _s.factory()
                        break
        return arguments

    def __init__(self, value=None, *args, default=True, **kwargs):
        """
        The arguments are of str type, the values are stored in parameter dict.
            >>> e = Partition('CA', 'AUTO')
            >>> e.value
            'CA'

        If the partition defines an attribute as implementing IStorage, the factory() is called to instantiate the attribute.
            >>> import zope.interface
            >>> import checkmate._storage
            >>> def factory(self): print("In factory")
            >>> A = type('A', (object,), {'factory': factory})
            >>> _impl = zope.interface.implementer(checkmate._storage.IStorage)
            >>> A = _impl(A)
            >>> setattr(Partition, 'A', A())
            >>> Partition.partition_attribute = ('A',)
            >>> ds = Partition('AT1')
            >>> delattr(Partition, 'A')
            >>> Partition.partition_attribute = tuple()

        Partition will be given a default value if none is provided.
        The default value is from definition in yaml:
            >>> import sample_app.application
            >>> re = sample_app.data_structure.ActionRequest()
            >>> re.C.value, re.P.value
            ('AT1', 'NORM')

        The default keyword only argument allow to use None as default:
            >>> import sample_app.application
            >>> re = sample_app.data_structure.ActionRequest(default=False)
            >>> re.C.value, re.P.value
            (None, None)
        """
        if type(value) == list:
            self.value = list(value)
        elif value == 'None':
            self.value = None
        else:
            self.value = value
            if value is None and default and hasattr(self, '_valid_values'):
                try:
                    self.value = self._valid_values[0]
                    if self.value == 'None':
                        self.value = None
                except:
                    pass
        for _k, _v in kwargs.items():
            setattr(self, _k, _v)

    def __dir__(self):
        return self.partition_attribute

    def __eq__(self, other):
        """
            >>> import sample_app.application
            >>> import sample_app.component.component_1_states
            >>> a = sample_app.application.TestData()
            >>> r1 = sample_app.exchanges.Action()
            >>> r2 = sample_app.exchanges.Action()
            >>> r1 == r2
            True
            >>> r1.value = ['HIGH']
            >>> r1 == r2
            False
            >>> s1 = sample_app.component.component_1_states.State()
            >>> s2 = sample_app.component.component_1_states.State()
            >>> s1.value, s2.value
            ('True', 'True')
            >>> s1 == s2
            True
            >>> s1.value = 'False'
            >>> s1 == s2
            False
        """
        if type(self) != type(other):
            return False
        if self.value is None:
            if len(dir(self)) == 0:
                return True
        elif other.value is None:
            if len(dir(other)) == 0:
                return True
        elif self.value == other.value:
            if (len(dir(self)) == 0 or len(dir(other)) == 0):
                return True
        else:
            return False
        if (len(dir(self)) == len(dir(other))):
            for key in iter(dir(self)):
                if key not in iter(dir(other)):
                    return False
                if (getattr(self, key) is not None and
                    getattr(other, key) is not None and
                    getattr(self, key) != getattr(other, key)):
                    return False
            return True
        return False

    def _dump(self):
        """
            >>> import sample_app.application
            >>> ac =sample_app.exchanges.Action('AC')
            >>> dump_dict = ac._dump()
            >>> dump_dict['value']
            'AC'
            >>> dump_dict['R']['C']['value']
            'AT1'
        """
        dump_dict = {}
        dump_dict['value'] = self.value
        for attr in dir(self):
            dump_dict[attr] = getattr(self, attr)._dump()
        return dump_dict

    def description(self):
        try:
            return (self.partition_storage.get_description(self))
        except AttributeError:
            return (None, None)

    def attribute_list(self, keyset=None):
        if keyset is None:
            return dict(map(lambda x:(x, getattr(self, x)), self.partition_attribute))
        else:
            return dict(map(lambda x:(x, getattr(self, x)), keyset.intersection(self.partition_attribute)))

    @property
    def partition_id(self):
        return self.description()[0]


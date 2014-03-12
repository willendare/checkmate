import copy
import zope.interface

import checkmate.path_transition

def get_transition(application_class, exchanges, initial, transitions=None):
    """
        >>> import sample_app.exchanges
        >>> import sample_app.application
        >>> import checkmate.run_transition
        >>> a = sample_app.application.TestData()
        >>> a.start()
        >>> exchanges = [sample_app.exchanges.AC(), sample_app.exchanges.RE(), sample_app.exchanges.ARE(), sample_app.exchanges.AP(), sample_app.exchanges.DA()]
        >>> states = []
        >>> for name in ['C1', 'C2', 'C3']:
        ...     states.extend(a.components[name].states)
        >>> transition = checkmate.run_transition.get_transition(sample_app.application.TestData, exchanges, states, [])
        >>> transition.incoming[0].action
        'AC'
    """
    a = application_class()
    a.start()
    states = []
    return_transitions = []
    for component in list(a.components.values()):
        states.extend(component.states)
    init_states = []
    for state in initial:
        if type(state) == checkmate._storage.InternalStorage:
            init_states.append(state.factory())
        else:
            init_states.append(state)
    if not compare_states(a, init_states):
        #transform to initial
        if transitions is None:
            return None
        path = find_path_to_initial(transitions, states, init_states)
        if path is not None and len(path) > 0:
            for i in range(len(path)):
                simulate_exchange(a, path[i].incoming[0])
    #verify the exchange list
    if compare_states(a, init_states):
        copy_states = copy.deepcopy(states)
        simulate_exchange(a, exchanges[0], exchanges, validate=True)
        path_transition = checkmate.path_transition.Path_Transition(initial=copy_states, incoming=exchanges, final=states, outgoing=[])
        if transitions is not None:
            for _t in transitions:
                if path_transition.is_matching_initial(_t.final):
                    path_transition.previous_transitions.append(_t)
                if path_transition.is_matching_final(_t.initial):
                    path_transition.next_transitions.append(_t)
        return path_transition
    else:
        return None
                
def find_path_to_initial(transitions, initial, target):
    path = []
    current = target
    for i in (range(-1, -1-len(transitions), -1)):
        transition = transitions[i]
        if transition.is_matching_final(current):
            path.insert(0, transition)
            current = transition.initial
            if transition.is_matching_initial(initial):
                return path
        else:
            continue
    return None

def simulate_exchange(application, exchange, exchanges=None, validate=False):
    for component in list(application.components.values()):
        if exchange.action in component.outgoings:
            for output in component.simulate(exchange):
                if validate and (output not in exchanges):
                    raise ValueError("outgoing %s is not as expected" %output.action) 
                run(application, output, exchanges, validate)

def run(application, incoming, exchanges=None, validate=False):
    try:
        component = application.components[incoming.destination]
    except AttributeError as e:
        raise e("no component %s found in application" %incoming.destination)
    for output in component.process([incoming]):
        if validate and (output not in exchanges):
            raise ValueError("outgoing %s is not as expected" %output.action)
        run(application, output, exchanges, validate)
            
def compare_states(application, target):
        """"""
        matching = 0
        for _target in target:
            _interface = zope.interface.implementedBy(_target.__class__)
            for _component in list(application.components.values()):
                try:
                    #Assume at most one state of component implements interface
                    _state = [_s for _s in _component.states if _interface.providedBy(_s)].pop(0)
                    if _state == _target:
                        matching += 1
                        break
                    else:
                        break
                except IndexError:
                    continue
        return matching == len(target)

# This code is part of the checkmate project.
# Copyright (C) 2013-2015 The checkmate project contributors
# 
# This program is free software under the terms of the GNU GPL, either
# version 3 of the License, or (at your option) any later version.

import checkmate.runs
import checkmate.sandbox


class TestProcedureRun1Threaded(checkmate.runs.Run):
    """"""
    def __init__(self, application_class):
        """
            >>> import sample_app.application
            >>> import checkmate.runtime._pyzmq
            >>> import checkmate.runtime._runtime
            >>> import sample_app.runtime.test_procedure
            >>> r = checkmate.runtime._runtime.Runtime(sample_app.application.TestData, checkmate.runtime._pyzmq.Communication, True)
            >>> r.setup_environment(['C1'])
            >>> r.start_test()
            >>> run = sample_app.runtime.test_procedure.TestProcedureRun1Threaded(sample_app.application.TestData)
            >>> run.nodes[0].nodes[0].nodes[2].root.incoming[0].code
            'ARE'
            >>> run.nodes[0].nodes[0].nodes[2].nodes[0].root.incoming[0].code
            'AP'
            >>> run.nodes[0].nodes[0].nodes[2].nodes[0].nodes[1].root.incoming[0].code
            'DA'
            >>> r.execute(run)
            >>> r.stop_test()
        """
        application = application_class()
        c2 = application.components['C2']
        runs = checkmate.runs.get_runs_from_transition(application, c2.state_machine.transitions[0])
        super(TestProcedureRun1Threaded, self).__init__(runs[0].root, runs[0].nodes)

    def __call__(self):
        pass


class TestProcedureRun2Threaded(checkmate.runs.Run):
    """"""
    def __init__(self, application_class):
        """
            >>> import checkmate.runtime._runtime
            >>> import checkmate.runtime.communication
            >>> import sample_app.application
            >>> import sample_app.runtime.test_procedure
            >>> r = checkmate.runtime._runtime.Runtime(sample_app.application.TestData, checkmate.runtime._pyzmq.Communication, True)
            >>> r.setup_environment(['C1'])
            >>> r.start_test()
            >>> run = sample_app.runtime.test_procedure.TestProcedureRun2Threaded(sample_app.application.TestData)
            >>> run.root.outgoing[0].code
            'PBRL'
            >>> run.nodes[0].root.incoming[0].code
            'PBRL'
            >>> run.nodes[0].nodes[0].nodes[0].root.incoming[0].code
            'DR'
            >>> r.execute(run, transform=True)
            >>> r.stop_test()
        """
        application = application_class()
        c2 = application.components['C2']
        run_pbac = checkmate.runs.get_runs_from_transition(application, c2.state_machine.transitions[0])[0]
        box = checkmate.sandbox.Sandbox(application_class)
        box(run_pbac)
        transition_rl_index = [_t for _t in c2.state_machine.transitions
                               if _t.outgoing and _t.outgoing[0].code == 'RL']
        run_pbrl = checkmate.runs.get_runs_from_transition(box.application, transition_rl_index[0])[0]
        super(TestProcedureRun2Threaded, self).__init__(run_pbrl.root, run_pbrl.nodes)

    def __call__(self):
        pass


def TestProcedureGenerator(application_class):
    """
            >>> import sample_app.application
            >>> import sample_app.runtime.test_procedure
            >>> import checkmate.runtime._pyzmq
            >>> import checkmate.runtime._runtime
            >>> r = checkmate.runtime._runtime.Runtime(sample_app.application.TestData, checkmate.runtime._pyzmq.Communication, threaded=True)
            >>> r.setup_environment(['C1'])
            >>> r.start_test()
            >>> for g in sample_app.runtime.test_procedure.TestProcedureGenerator(sample_app.application.TestData):
            ...     r.execute(g[0])
            >>> r.stop_test()
    """
    application = application_class()
    c2 = application.components['C2']
    run_pbac = checkmate.runs.get_runs_from_transition(application, c2.state_machine.transitions[0])[0]
    yield run_pbac, run_pbac.root.name

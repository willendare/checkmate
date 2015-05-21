# This code is part of the checkmate project.
# Copyright (C) 2014-2015 The checkmate project contributors
#
# This program is free software under the terms of the GNU GPL, either
# version 3 of the License, or (at your option) any later version.

import time

import checkmate.runs
import checkmate.sandbox


@checkmate.fix_issue("checkmate/issues/pathfinder_find_runs.rst")
@checkmate.fix_issue("checkmate/issues/get_path_from_pathfinder.rst")
@checkmate.fix_issue("checkmate/issues/pathfinder_find_AC-OK_path.rst")
def _find_runs(application, target, origin):
    """"""
    if target.collected_run is not None:
        target = target.collected_run
    if origin.collected_run is not None:
        origin = origin.collected_run
    used_runs = []
    checkmate.pathfinder.get_runs(used_runs, application, origin, target)
    return used_runs


class Timer():
    def __init__(self, limit):
        self.start = 0
        self.limit = limit

    def reset(self):
        self.start = time.time()

    def check(self):
        return (time.time() < self.start + self.limit)

timer = Timer(5)


def fail_fast(depth):
    global timer
    if depth == 0:
        timer.reset()
        return False
    else:
        return not timer.check()


def get_runs(runs, app, ori_run, nr, diff_set=None, depth=0):
    """
    >>> import checkmate.runs
    >>> import checkmate.sandbox
    >>> import checkmate.pathfinder
    >>> import sample_app.application
    >>> app = sample_app.application.TestData()
    >>> app.start()
    >>> runs  = app.run_collection()
    >>> r0 = runs[3]
    >>> nr = runs[1]
    >>> path_runs = []
    >>> checkmate.pathfinder.get_runs(path_runs, app, r0, nr)
    True
    >>> [_r.root.name for _r in path_runs]
    ["Press C2's Button AC", "Press C2's Button RL"]
    """
    if fail_fast(depth):
        return False

    if diff_set is None:
        diff_set = set()
        for _state in app.state_list():
            for _store in _state.partition_storage.storage:
                if _state.value == _store.value:
                    diff_set.add(_store)
                    break

    if depth == app.path_finder_depth:
        return False
    next_runs = checkmate.runs.followed_runs(app, ori_run)
    for run1 in next_runs[:]:
        # Modify to support sample_app, diff_set hasn't RequestState
        if (not diff_set.issuperset(run1.initial) and not
           run1.initial.issuperset(diff_set)):
            next_runs.remove(run1)
            continue
        if run1 == nr:
            return True
        if run1 == ori_run or run1 in runs:
            next_runs.pop(next_runs.index(run1))
            continue

    nr_classes = [s.partition_class for s in nr.initial.difference(diff_set)]
    next_runs_1 = filter(lambda r: len(nr.initial.intersection(
                    r.final.difference(diff_set))) > 0, next_runs)
    next_runs_2 = filter(lambda r: len(nr.initial.intersection(
                    r.final.difference(diff_set))) == 0, next_runs)
    sorted_list_1 = sorted(next_runs_1, key=lambda r: len(
                        nr.initial.intersection(r.final.difference(diff_set))),
                        reverse=True)
    sorted_list_2 = sorted(next_runs_2, key=lambda r: len([s for s in r.final
                        if s not in r.initial and
                        s.partition_class in nr_classes]), reverse=True)

    for run in sorted_list_1 + sorted_list_2:
        runs.append(run)
        diff_set1 = set(diff_set)
        select_partition_class = [_f.partition_class for _f in run.final]
        for di in diff_set:
            if di.partition_class in select_partition_class:
                diff_set1.remove(di)
        if (checkmate.pathfinder.get_runs(runs,
                app, run, nr, diff_set1.union(run.final_alike()), depth + 1)):
            return True
        else:
            runs.pop()
    return False

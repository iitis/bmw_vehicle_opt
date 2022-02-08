from bmw_solver_qprogmods.ip_utils import *
from itertools import product, combinations
from time import time, sleep


class TestConditionsScheduling:
    def __init__(self, car_no, tests, mode, days_no, eng_no, use_time_frames, use_groups) -> None:
        self.car_no = car_no
        assert all(t.count == 1 for t in tests)
        self.tests = tests
        self.mode = mode
        self.days_no = days_no
        self.eng_no = eng_no
        assert isinstance(use_time_frames, bool)
        self.timef = use_time_frames
        assert isinstance(use_groups, bool)
        self.use_groups = use_groups

        self.test_id_groups = dict()
        for ind, t in enumerate(self.tests):  # 38 (grouping - preprocessing)
            glob_id, _ = t.id.split("_")
            if glob_id not in self.test_id_groups.keys():
                self.test_id_groups[glob_id] = [ind]
            else:
                self.test_id_groups[glob_id].append(ind)

        self.groups = sorted(list({t.group: 0 for t in self.tests}))
        self.test_prior_group = {g: [] for g in self.groups}
        for ind, t in enumerate(self.tests):
            self.test_prior_group[t.group].append(ind)
        assert sum(len(g) for g in self.test_prior_group.values()) == sum(t.count for t in self.tests)

    def __iter__(self):
        cars = range(self.car_no)
        days = range(self.days_no)

        values = [1 for _ in range(self.car_no*self.days_no)]
        for t in self.tests:  # 36
            vars = [get_schedule_var(i, t.id, d)
                    for i, d in product(cars, days)]
            label = f"test_scheduling_test_{t.id}"
            yield EqConstraint(vars, values, 1, label)

        values = [1 for _ in self.tests]
        for i, d in product(cars, days):  # 40
            vars = [get_schedule_var(i, t.id, d) for t in self.tests]
            label = f"test_scheduling_car_{i}_day_{d}"
            yield IneqConstraint(vars, values, 1, label)

        values = [1 for _ in product(self.tests, cars)]
        for d in days:  # 39
            vars = [get_schedule_var(i, t.id, d)
                    for t, i in product(self.tests, cars)]
            label = f"test_scheduling_day_{d}"
            yield IneqConstraint(vars, values, self.eng_no, label)

        for _, test_group in self.test_id_groups.items():  # 38
            for i in cars:
                vars = [get_schedule_var(i, self.tests[ind].id, d)
                        for d, ind in product(days, test_group)]
                values = [1 for _ in vars]
                # only first for distinguishing needed
                id_first = self.tests[test_group[0]].id
                label = f"group_test_scheduling_{i}_test_{id_first}"
                yield EqConstraint(vars, values, 1, label)

        if self.timef:  # 37
            for t in self.tests:
                data = [(-d, get_schedule_var(i, t.id, d))
                        for i, d in product(cars, days)]
                values, vars = zip(*data)
                label = f"test_scheduling_timein_{t.id}"
                yield IneqConstraint(vars, values, -t.time_in, label)

                data = [(d, get_schedule_var(i, t.id, d))
                        for i, d in product(cars, days)]
                values, vars = zip(*data)
                label = f"test_scheduling_timeout_{t.id}"
                yield IneqConstraint(vars, values, t.time_out, label)

        if self.use_groups:
            for i in cars:  # 42
                tests_inds = self.test_prior_group[self.groups[0]]
                vars = [get_schedule_var(i, self.tests[ind].id, d)
                        for ind, d in product(tests_inds, days)]
                values = [1 for _ in vars]
                label = f"test_scheduling_crash_{i}"
                yield EqConstraint(vars, values, 1, label=label)

            for g1, g2 in combinations(self.groups, 2):  # 41 group order
                for ind1, ind2 in product(self.test_prior_group[g1], self.test_prior_group[g2]):
                    t1 = self.tests[ind1]
                    t2 = self.tests[ind2]
                    if self.mode == "pyqubo":
                        for i, (d1, d2) in product(cars, combinations(days, 2)):
                            b1 = pyqubo.Binary(get_schedule_var(i, t1.id, d2))
                            b2 = pyqubo.Binary(get_schedule_var(i, t2.id, d1))
                            yield b1*b2
                    else:
                        t = time()
                        for i, (d1, d2) in product(cars, combinations(days, 2)):
                            b1 = get_schedule_var(i, t1.id, d2)
                            b2 = get_schedule_var(i, t2.id, d1)
                            vars = [b1, b2]
                            label = f"test_scheduling_group_order_{ind1}_{ind2}_{i}_{d1}_{d2}"
                            yield IneqConstraint(vars, [1, 1], 1, label)
                        # print(time()-t)



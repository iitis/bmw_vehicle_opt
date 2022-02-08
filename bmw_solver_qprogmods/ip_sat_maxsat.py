from itertools import product

from pulp.constants import LpBinary
from pulp.pulp import LpVariable

from bmw_solver_qprogmods.ip_utils import *


class TestConditions:
    """
    Asserts car can be used for given test conditions (common for SAT and MAX-SAT problems)
    """

    def __init__(self, car_no, tests, mode) -> None:
        self.car_no = car_no
        self.tests = tests
        assert mode == "pyqubo" or mode == "dimod"
        self.mode = mode

    def _test_to_constraints(self, car_id, test):
        constraints = []
        for var_id, var in enumerate(test.test):
            label = f"test_constraint_{car_id}_{test.id}_{var_id}"
            if var[0] in [0, 1]:
                if self.mode == "pyqubo":
                    cartest = pyqubo.Binary(get_car_test_name(car_id, test.id))
                    carfeat = pyqubo.Binary(
                        get_car_feature_name(car_id, var[1]))
                    if var[0] == 0:
                        constraints += [(1-carfeat)*cartest]
                    else:  # var[0] == 1
                        constraints += [carfeat*cartest]
                else:

                    cartest = get_car_test_name(car_id, test.id)
                    carfeat = get_car_feature_name(car_id, var[1])
                    if var[0] == 0:
                        constraints += [IneqConstraint(
                            [carfeat, cartest], [-1, 1], 0, label)]
                    else:  # var[0] == 1
                        constraints += [IneqConstraint(
                            [carfeat, cartest], [1, 1], 1, label)]
            elif var[0] == 2:
                vars = [get_car_feature_name(car_id, v) for v in var[1]]
                vars += [get_car_test_name(car_id, test.id)]
                values = [-1 for _ in var[1]]
                values += [1]
                constraints += [IneqConstraint(vars, values, 0, label)]
            else:
                raise ValueError(f"incorrect test var {test} ({var})")
        return constraints

    def __iter__(self):
        constraints = []
        for car_id, test in product(range(self.car_no), self.tests):
            constraints += self._test_to_constraints(car_id, test)

        return constraints.__iter__()


class TestConditionsSAT:
    """
    Asserts the test was considered sufficiently many times (SAT only)
    """

    def __init__(self, car_no, tests) -> None:
        self.car_no = car_no
        self.tests = tests

    def __iter__(self):
        constraints = []
        values = [1 for _ in range(self.car_no)]
        for test in self.tests:
            vars = [get_car_test_name(i, test.id) for i in range(self.car_no)]
            constraints.append(EqConstraint(
                vars, values, test.count, f"test_sat_cond_{test.id}"))
        return constraints.__iter__()


class TestConditionsMAXSAT:
    """
    MAX-SAT only
    if consider_counts is True: asserts the test was not considered too many times. 
    if False: creates new variables equivalent to test was considered sufficiently many times
    """

    def __init__(self, car_no, tests, consider_counts) -> None:
        self.car_no = car_no
        self.tests = tests
        self.consider_counts = consider_counts

    def __iter__(self):
        constraints = []
        if self.consider_counts:
            values = [1 for _ in range(self.car_no)]
            for test in self.tests:
                vars = [get_car_test_name(i, test.id)
                        for i in range(self.car_no)]
                constraints.append(IneqConstraint(
                    vars, values, test.count, f"test_sat_cond_{test.id}"))
        else:
            for test in self.tests:
                values = [-1 for _ in range(self.car_no)]
                values.append(test.count)
                vars = [get_car_test_name(i, test.id)
                        for i in range(self.car_no)]
                vars.append(get_maxsat_test(test.id))
                constraints.append(IneqConstraint(
                    vars, values, 0, f"test_sat_cond_{test.id}"))
        return constraints.__iter__()


class TestObjectiveMAXSAT:
    """
    MAX-SAT only
    creates objective function for MAX-SAT Problem
    """

    def __init__(self, car_no, tests, mode, consider_counts, pulp_variables=None) -> None:
        self.car_no = car_no
        self.tests = tests
        self.mode = mode
        self.consider_counts = consider_counts
        assert mode != "pulp" or pulp_variables is not None
        self.pulp_variables = pulp_variables

    def get_var(self, label):
        if self.mode == "pyqubo":
            return pyqubo.Binary(label)
        elif self.mode == "dimod":
            return dimod.Binary(label)
        elif self.mode == "pulp":
            if label not in self.pulp_variables:
                self.pulp_variables[label] = LpVariable(label, cat=LpBinary)
            return self.pulp_variables[label]
        else:
            raise ValueError("Unknown mode {self.mode}")

    def _get_bin_t(self, test):
        label = get_maxsat_test(test.id)
        return self.get_var(label)

    def _get_bin_ct(self, car_id, test):
        label = get_car_test_name(car_id, test.id)
        return self.get_var(label)

    def get_objective(self):
        if self.consider_counts:
            iterator = product(range(self.car_no), self.tests)
            return -sum(test.weight*self._get_bin_ct(i, test) for i, test in iterator)
        else:
            for test in self.tests:
                return -sum(test.weight*self._get_bin_t(test) for test in self.tests)

from copy import deepcopy

from pulp import LpVariable, LpBinary
from pulp.pulp import LpProblem

from bmw_solver_qprogmods.bmw_parser import BMWProblem
from bmw_solver_qprogmods.general_ip_constraints import *
from bmw_solver_qprogmods.ip_sat_maxsat import *
from bmw_solver_qprogmods.ip_scheduling import *
from bmw_solver_qprogmods.ip_utils import *
from bmw_solver_qprogmods.ip_utils import _extend_bqm


class BMWIntegerProgram:
    def __init__(self, bmwproblem: BMWProblem, nv) -> None:
        assert nv > 0
        self.problem = bmwproblem
        self.car_no = nv

    def _add_pyqubo_part(self, iterator, strength=0):
        tmp_result = 0
        for constr in iterator:
            if isinstance(constr, EqConstraint) or isinstance(constr, IneqConstraint):
                tmp_result += constr.export("pyqubo")
            else:
                tmp_result += constr
        return tmp_result.compile(strength=strength).to_bqm()

    def _general_conditions_pyqubo(self, strength):
        result = BQMWithoutPenalty()
        types = self.problem.cartypes
        features = self.problem.features
        nv = self.car_no
        problem = self.problem

        tmp = self._add_pyqubo_part(SingleType(nv, types))
        result["single_type"] = tmp

        feat_per_type = FeatPerType(
            nv, types, features, problem.tvars, mode="pyqubo")
        tmp = self._add_pyqubo_part(feat_per_type)
        result["feat_per_type"] = tmp

        group_features = GroupFeatures(nv, problem.exclusion_vars)
        tmp = self._add_pyqubo_part(group_features)
        result["group_features"] = tmp

        rules_per_type = RulesPerType(
            1, types, problem.if_constraints, mode="pyqubo")
        tmp = self._add_pyqubo_part(rules_per_type, strength)
        result["rules_per_type"] = _extend_bqm(tmp, nv)

        # rules_per_type = RulesPerType(
        #     nv, types, problem.if_constraints, mode="pyqubo")
        # tmp = self._add_pyqubo_part(rules_per_type, strength)
        # extend_bqm(tmp, 2)
        # result["rules_per_type"] = tmp

        return result

    def _add_dimod_constr(self, result, constraints):
        for c in constraints:
            label = c.label
            c_export = c.export_dimod()
            result.add_constraint(c_export, label=label)

    def _refill_pulp_vars(self, c, vars):
        for var in c.vars:
            if var not in vars:
                vars[var] = LpVariable(var, cat=LpBinary)

    def _add_pulp_constr(self, result, constraints, vars):
        for c in constraints:
            self._refill_pulp_vars(c, vars)
            result += c.export_pulp(vars)

    def _general_conditions_dimod(self):
        types = self.problem.cartypes
        features = self.problem.features
        nv = self.car_no
        problem = self.problem

        result = dimod.ConstrainedQuadraticModel()

        self._add_dimod_constr(result, SingleType(nv, types))

        feat_per_type = FeatPerType(
            nv, types, features, problem.tvars, mode="dimod")
        self._add_dimod_constr(result, feat_per_type)

        group_features = GroupFeatures(nv, problem.exclusion_vars)
        self._add_dimod_constr(result, group_features)

        rules_per_type = RulesPerType(
            nv, types, problem.if_constraints, mode="dimod")
        self._add_dimod_constr(result, rules_per_type)
        return result

    def _general_conditions_pulp(self, vars):
        assert NotImplementedError()
        types = self.problem.cartypes
        features = self.problem.features
        nv = self.car_no
        problem = self.problem

        result = LpProblem()

        self._add_pulp_constr(result, SingleType(nv, types), vars)

        feat_per_type = FeatPerType(
            nv, types, features, problem.tvars, mode="dimod")
        self._add_pulp_constr(result, feat_per_type, vars)

        group_features = GroupFeatures(nv, problem.exclusion_vars)
        self._add_pulp_constr(result, group_features, vars)

        rules_per_type = RulesPerType(
            nv, types, problem.if_constraints, mode="dimod")
        self._add_pulp_constr(result, rules_per_type, vars)
        return result

    def export(self, mode, strength=None, penalty_dict=None):
        if mode == "pyqubo":
            return self.export_pyqubo(strength, penalty_dict)
        elif mode == "dimod":
            return self.export_dimod()
        elif mode == "pulp":
            return self.export_pulp()
        else:
            raise ValueError("Unknown mode, has to be 'pyqubo' or 'dimod'")


class BMWIntegerProgramSAT(BMWIntegerProgram):
    def export_pyqubo(self, strength, penalty_dict=None):
        nv = self.car_no
        problem = self.problem

        result = self._general_conditions_pyqubo(strength)

        test_constraints = TestConditions(nv, problem.tests, mode="pyqubo")
        tmp = self._add_pyqubo_part(test_constraints, strength)
        result["test_constraint"] = tmp

        test_constraints = TestConditionsSAT(nv, problem.tests)
        tmp = self._add_pyqubo_part(test_constraints)
        result["test_objective"] = tmp

        if penalty_dict == None:
            return result
        else:
            return result.to_bqm(penalty_dict)

    def export_dimod(self):
        nv = self.car_no
        problem = self.problem

        result = self._general_conditions_dimod()

        test_constraints = TestConditions(nv, problem.tests, mode="dimod")
        self._add_dimod_constr(result, test_constraints)

        test_constraints = TestConditionsSAT(nv, problem.tests)
        self._add_dimod_constr(result, test_constraints)

        y = dimod.Binary(result.variables[0])
        result.set_objective(y-y)
        return result

    def export_pulp(self):
        nv = self.car_no
        problem = self.problem

        vars = dict()
        result = self._general_conditions_pulp(vars)

        test_constraints = TestConditions(nv, problem.tests, mode="dimod")
        self._add_pulp_constr(result, test_constraints, vars)

        test_constraints = TestConditionsSAT(nv, problem.tests)
        self._add_pulp_constr(result, test_constraints, vars)

        return result


class BMWIntegerProgramMAXSAT(BMWIntegerProgram):
    def __init__(self, bmwproblem: BMWProblem, nv, consider_count=False) -> None:
        assert nv > 0
        self.problem = bmwproblem
        self.car_no = nv
        self.consider_count = consider_count

    def export_pyqubo(self, strength, penalty_dict=None):
        nv = self.car_no
        problem = self.problem
        ccount = self.consider_count

        result = self._general_conditions_pyqubo(strength)

        test_constraints = TestConditions(nv, problem.tests, mode="pyqubo")
        tmp1 = self._add_pyqubo_part(test_constraints)

        test_constraints = TestConditionsMAXSAT(nv, problem.tests, ccount)
        tmp2 = self._add_pyqubo_part(test_constraints)
        result["test_constraint"] = tmp1 + tmp2

        obj = TestObjectiveMAXSAT(nv, problem.tests, "pyqubo", ccount)
        result["test_objective"] = obj.get_objective().compile().to_bqm()

        if penalty_dict == None:
            return result
        else:
            return result.to_bqm(penalty_dict)

    def export_dimod(self):
        nv = self.car_no
        problem = self.problem
        ccount = self.consider_count

        result = self._general_conditions_dimod()

        test_constraints = TestConditions(nv, problem.tests, mode="dimod")
        self._add_dimod_constr(result, test_constraints)

        test_constraints = TestConditionsMAXSAT(nv, problem.tests, ccount)
        self._add_dimod_constr(result, test_constraints)

        obj = TestObjectiveMAXSAT(nv, problem.tests, "dimod", ccount)
        result.set_objective(obj.get_objective())
        return result

    def export_pulp(self):
        nv = self.car_no
        problem = self.problem
        ccount = self.consider_count

        vars = dict()
        result = self._general_conditions_pulp(vars)

        test_constraints = TestConditions(nv, problem.tests, mode="dimod")
        self._add_pulp_constr(result, test_constraints, vars)

        test_constraints = TestConditionsMAXSAT(nv, problem.tests, ccount)
        self._add_pulp_constr(result, test_constraints, vars)

        obj = TestObjectiveMAXSAT(nv, problem.tests, "pulp", ccount, vars)
        result += obj.get_objective()
        return result


class BMWIntegerProgramScheduling(BMWIntegerProgram):
    def __init__(self, bmwproblem: BMWProblem, nv, days_no, engineers_no, use_time_frames=False, use_groups=False) -> None:
        assert nv > 0
        self.problem = bmwproblem
        self.car_no = nv
        assert days_no > 0
        self.days_no = days_no
        assert engineers_no > 0
        self.engineers_no = engineers_no
        self._timef = use_time_frames
        self._groups = use_groups

        self.tests_unfolded = []
        for test in bmwproblem.tests:
            for i in range(test.count):
                t = deepcopy(test)
                t.id = f"{test.id}_{i}"
                t.count = 1
                self.tests_unfolded.append(t)

    def export_pyqubo(self, strength, penalty_dict=None):
        nv = self.car_no
        result = self._general_conditions_pyqubo(strength)

        test_constraints = TestConditionsScheduling(
            nv, self.tests_unfolded, "pyqubo", self.days_no, self.engineers_no, self._timef, self._groups)
        tmp = self._add_pyqubo_part(test_constraints)
        result["test_constraint"] = tmp

        if penalty_dict == None:
            return result
        else:
            return result.to_bqm(penalty_dict)

    def export_dimod(self):
        nv = self.car_no

        result = self._general_conditions_dimod()

        test_constraints = TestConditionsScheduling(
            nv, self.tests_unfolded, "dimod", self.days_no, self.engineers_no, self._timef, self._groups)
        self._add_dimod_constr(result, test_constraints)

        return result

    def export_pulp(self):
        nv = self.car_no

        vars = dict()
        result = self._general_conditions_pulp(vars)

        test_constraints = TestConditionsScheduling(
            nv, self.tests_unfolded, "dimod", self.days_no, self.engineers_no, self._timef, self._groups)
        self._add_pulp_constr(result, test_constraints, vars)

        return result

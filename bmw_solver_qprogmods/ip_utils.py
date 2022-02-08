import dimod
import pyqubo
# from dimod import Bin
from dimod import BinaryQuadraticModel
from pyqubo.integer.log_encoded_integer import LogEncInteger

################################################################
############### BQM up to penalty parameters ###################
################################################################


class BQMWithoutPenalty:
    def __init__(self) -> None:
        self.dicts = dict()

    def to_bqm(self, pdict):
        return sum(0 if pdict[k] == 0 else pdict[k] * self.dicts[k] for k in self.dicts)

    def __setitem__(self, k, bqm):
        assert isinstance(bqm, BinaryQuadraticModel), type(bqm)
        assert k not in self.dicts.keys()
        self.dicts[k] = bqm


################################################################
################### Constraint classes #########################
################################################################


class Constraint:
    '''
    Abstract class for constraints.
    '''

    def __init__(self, vars, values, offset, label) -> None:
        assert len(vars) == len(values)
        self.vars = vars
        self.values = values
        self.offset = offset
        self.label = label

    def export(self, mode, pulp_variables:dict=None):
        if mode == "pyqubo":
            return self.export_pyqubo()
        elif mode == "dimod":
            return self.export_dimod()
        elif mode == "pyqubo":
            return self.export_pulp(pulp_variables)
        else:
            raise ValueError("Unknown mode, has tobe 'pyqubo' or 'dimod'")


class EqConstraint(Constraint):
    '''
    This is for sum_{i} vars_i * names_i = offset
    '''

    def export_pyqubo(self):
        expr = sum(v*pyqubo.Binary(x) for v, x in zip(self.values, self.vars))
        return (expr-self.offset)**2

    def export_dimod(self):
        from time import time
        linear = {x: v for v, x in zip(self.values, self.vars)}
        quadratic = {}
        vartype = dimod.Vartype.BINARY
        expr = BinaryQuadraticModel(
            linear, quadratic, offset=-self.offset, vartype=vartype)
        return expr == 0

    def export_pulp(self, pulp_variables):
        assert pulp_variables is not None
        return sum(val*pulp_variables[var] for var, val in zip(self.vars, self.values)) == self.offset, self.label


class IneqConstraint(Constraint):
    """
    This is for sum_{i} vars_i * names_i <= offset
    """

    def _max_slack(self):
        return -(sum(filter(lambda x: x < 0, self.values)) - self.offset)

    def export_pyqubo(self):
        expr = sum(v*pyqubo.Binary(x) for v, x in zip(self.values, self.vars))
        slack_var = LogEncInteger(
            f"{self.label}_slack", (0, self._max_slack()))
        return (expr - self.offset + slack_var)**2

    def export_dimod(self):
        linear = {x: v for v, x in zip(self.values, self.vars)}
        quadratic = {}
        vartype = dimod.Vartype.BINARY
        expr = BinaryQuadraticModel(
            linear, quadratic, offset=-self.offset, vartype=vartype)
        return expr <= 0

    def export_pulp(self, pulp_variables):
        assert pulp_variables is not None
        return sum(val*pulp_variables[var] for var, val in zip(self.vars, self.values)) <= self.offset, self.label


################################################################
####### Functions for specifying names of variables ############
################################################################

def get_car_type_name(car_id, type_no):
    return f"t_{car_id}_{type_no}"


def get_car_feature_name(car_id, feature_no):
    return f"b_{car_id}_{feature_no}"


def get_car_test_name(car_id, test_no):
    return f"p_{car_id}_{test_no}"


def get_maxsat_test(test_id):
    return f"s_{test_id}"


def get_schedule_var(car_id, test_id, day):
    return f"p_{car_id}_{test_id}_{day}"


def _name_update(the_str, car_id):
    if the_str[:2] in ["t_", "b_"]:
        name, _, rest = the_str.split("_")
        return f"{name}_{car_id}_{rest}"
    elif the_str[:13] == "if_constraint":
        _, rest = the_str[14:].split("_", 1)
        return f"if_constraint_{car_id}_{rest}"
    elif "_" not in the_str:
        return f"{the_str}_{car_id}"
    else:
        raise ValueError(f"I can't consider this type of variable {the_str}")


def _extend_bqm(bqm_orig: BinaryQuadraticModel, cars_no):
    quadratic, offset = bqm_orig.to_qubo()
    for i in range(1, cars_no):
        new_quadratic = dict()
        for (var1, var2), val in quadratic.items():
            new_quadratic[_name_update(var1, i), _name_update(var2, i)] = val

        bqm = BinaryQuadraticModel.from_qubo(new_quadratic, offset)
        bqm_orig += bqm

    return bqm_orig

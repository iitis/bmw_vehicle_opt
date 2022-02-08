from bmw_solver_qprogmods.bmw_parser import (IfConstraintBMW,
                                             IfConstraintBMWBunch)
from bmw_solver_qprogmods.ip_utils import *


class SingleType():
    """
    Asserts each car is of exactly one type
    """

    def __init__(self, car_no, types_list) -> None:
        self.car_no = car_no
        self.index = 0
        self.types_list = types_list

    def __iter__(self):
        return self

    def __next__(self):
        if self.index == self.car_no:
            raise StopIteration
        vars = [get_car_type_name(self.index, t) for t in self.types_list]
        values = [1 for _ in self.types_list]
        self.index += 1
        return EqConstraint(vars, values, 1, f"single_type_{self.index}")


class FeatPerType():
    """
    Asserts car won't have forbiddent features
    """

    def __init__(self, car_no, types_list, features, tvars, mode) -> None:
        self.car_no = car_no
        self.forbidden_features = dict()
        assert mode == "pyqubo" or mode == "dimod"
        self.mode = mode
        features_set = set(features)
        for tvar in filter(lambda tvar: tvar.t in types_list, tvars):
            self.forbidden_features[tvar.t] = features_set.difference(
                tvar.vars)

    def __iter__(self):
        constraints = []
        for i in range(self.car_no):
            for (cartype, features) in self.forbidden_features.items():
                for f in features:
                    t = get_car_type_name(i, cartype)
                    b = get_car_feature_name(i, f)
                    if self.mode == "pyqubo":
                        constraints.append(
                            pyqubo.Binary(t)*pyqubo.Binary(b))
                    elif self.mode == "dimod":
                        label = f"feat_per_type_{i}_{cartype}_{f}"
                        ineq = IneqConstraint([t, b], [1, 1], 1, label)
                        constraints.append(ineq)
        return constraints.__iter__()


class GroupFeatures:
    """
    Asserts group features
    """

    def __init__(self, car_no, excl_vars) -> None:
        self.car_no = car_no
        self.excl_vars = excl_vars

    def __iter__(self):
        constraints = []
        for i in range(self.car_no):
            for (constr_id, constr) in enumerate(self.excl_vars):
                vars = [get_car_feature_name(i, feat) for feat in constr.vars]
                values = [1 for _ in constr.vars]
                constraints.append(IneqConstraint(
                    vars, values, 1, label=f"group_features_{i}_{constr_id}"))
        return constraints.__iter__()


class RulesPerType:
    """
    Assert Rules per type
    """

    def __init__(self, car_no, types_list, if_constraints, mode) -> None:
        self.car_no = car_no
        self.mode = mode
        self.constraints = if_constraints
        self.types_list = types_list

    def _constr_to_ineq(self, constr, car, constr_id):

        vars = [get_car_feature_name(car, f[1]) for f in constr.left_vars]
        vars += [get_car_feature_name(car, f[1]) for f in constr.right_vars]
        N = len(constr.right_vars)
        M = len(constr.left_vars)

        t = constr.t if isinstance(constr, IfConstraintBMW) else None

        if t != None:
            vars += [get_car_type_name(car, t)]

        constr_type = constr.get_type()
        values = []
        offset = 0
        if constr_type in ["0&0&", "0&01", "010&", "0101"]:
            values += [N for _ in constr.left_vars]
            values += [-1 for _ in constr.right_vars]
            offset = N*M-N
            if t != None:
                values += [N]
                offset += N
        elif constr_type in ["0&1&", "0111", "0&11", "011&"]:
            values += [N for _ in constr.left_vars]
            values += [1 for _ in constr.right_vars]
            offset = N*M
            if t != None:
                values += [N]
                offset += N
        elif constr_type in ["m&0|", "m&01", "1&0|", "110|", "1101"]:
            mu = sum(var[0] for var in constr.left_vars)
            M -= mu
            values += [1 if var[0] == 0 else -1 for var in constr.left_vars]
            values += [-1 for _ in constr.right_vars]
            offset = M-1
            if t != None:
                values += [1]
                offset += 1
        elif constr_type in ["m&11"]:
            mu = sum(var[0] for var in constr.left_vars)
            M -= mu
            values += [1 if var[0] == 0 else -1 for var in constr.left_vars]
            values += [1 for _ in constr.right_vars]
            offset = M
            if t != None:
                values += [1]
                offset += 1
        elif constr_type in ["0&0|", "010|"]:
            values += [1 for _ in constr.left_vars]
            values += [-1 for _ in constr.right_vars]
            offset = M-1
            if t != None:
                values += [1]
                offset += 1
        elif constr_type in ["0|0|", "0|01", "0101"]:
            values += [1 for _ in constr.left_vars]
            values += [-M for _ in constr.right_vars]
            if t != None:
                values += [M]
                offset = M
        elif constr_type in ["0|1&", "0|11"]:
            constraints = []
            if isinstance(constr, IfConstraintBMW):
                for var in constr.left_vars:
                    constr_new = IfConstraintBMW()
                    constr_new.left_vars = [var]
                    constr_new.left_op = "1"
                    constr_new.right_vars = constr.right_vars
                    constr_new.right_op = constr.right_op
                    constr_new.t = constr.t
                    new_constr_id = f"{constr_id}_case{var[1]}"
                    constraints += self._constr_to_ineq(
                        constr_new, car, new_constr_id)
                return constraints
            elif isinstance(constr, IfConstraintBMWBunch):
                for var in constr.left_vars:
                    constr_new = IfConstraintBMWBunch()
                    constr_new.left_vars = [var]
                    constr_new.left_op = "1"
                    constr_new.right_vars = constr.right_vars
                    constr_new.right_op = constr.right_op
                    constr_new.orig_types = constr.orig_types
                    constr_new.max_types = constr.max_types
                    constr_new.loaded = True
                    new_constr_id = f"{constr_id}_case{var[1]}"
                    constraints += self._constr_to_ineq(
                        constr_new, car, new_constr_id)
                return constraints
            else:
                # Hack, likely won't be run
                raise f"Something wrong {type(constr)}"
        elif constr_type in ["1&00"]:
            assert t != None
            values += [-1 for _ in constr.left_vars]
            values += [1]
            offset = 0
        elif constr_type in ["0100"]:
            assert t != None
            if self.mode == "pyqubo":
                var1 = pyqubo.Binary(get_car_type_name(car, t))
                feature = constr.left_vars[0][1]
                var2 = pyqubo.Binary(get_car_feature_name(car, feature))
                return [var1*var2]
            if self.mode == "dimod":
                values = [1, 1]
                offset = 1
        else:
            raise ValueError(f"{constr_type} not handled!")

        label = f"if_constraint_{car}_{constr_id}"
        if t != None:
            label = f"{label}_{t}"

        return [IneqConstraint(vars, values, offset, label=label)]

    def _global_constr_to_ineq(self, car_id, constr, constr_id):
        inequalities = self._constr_to_ineq(constr, car_id, constr_id)
        if len(self.types_list) - len(constr.max_types) == 1:
            outcomes = []
            for ineq in inequalities:
                assert self.mode == "pyqubo"
                ineq = ineq.export_pyqubo()
                the_type = set(self.types_list).difference(constr.max_types)
                the_type = list(the_type)[0]
                b = pyqubo.Binary(get_car_type_name(car_id, the_type))
                outcomes.append((1-b) * ineq)
            return outcomes
        else:
            return inequalities

    def _local_constr_to_ineq(self, car_id, constr, constr_id):
        constraints = []
        for cstr_local in constr.constr_simplified:
            constraints += self._constr_to_ineq(cstr_local, car_id, constr_id)
        return constraints

    def set_mode(self, mode):
        assert mode == "pyqubo" or mode == "dimod"
        self.mode = mode

    def __iter__(self):
        assert self.mode != None
        constraints = []

        for i in range(self.car_no):
            for cstr_id, cstr in enumerate(self.constraints):
                glob_condition = False
                glob_condition |= len(cstr.max_types) >= len(
                    self.types_list) - 1 and self.mode == "pyqubo"
                glob_condition |= len(cstr.max_types) == len(self.types_list)
                if glob_condition:
                    constraints += self._global_constr_to_ineq(
                        i, cstr, cstr_id)
                else:
                    constraints += self._local_constr_to_ineq(i, cstr, cstr_id)

        return constraints.__iter__()

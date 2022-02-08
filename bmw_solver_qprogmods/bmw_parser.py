import re
from copy import deepcopy


class IfConstraintBMWAbs:
    def __init__(self) -> None:
        pass

    def _get_var(self, s):
        if s[0] == "~":
            return 1, int(s[2:])
        else:
            return 0, int(s[1:])

    def _basic_splitter(self, constraint):
        constraint = "".join(constraint.split())
        argument, conclusion = constraint.split("=>")

        if "|" in argument:
            self.left_op = "|"
        elif "&" in argument:
            self.left_op = "&"
        else:
            self.left_op = "1"

        if "|" in conclusion:
            self.right_op = "|"
        elif "&" in conclusion:
            self.right_op = "&"
        else:
            self.right_op = "1"

        left_vars = []
        right_vars = []
        for var in re.split("[|&]", argument):
            left_vars.append(self._get_var(var))
        for var in re.split("[|&]", conclusion):
            right_vars.append(self._get_var(var))
        self.left_vars = left_vars
        self.right_vars = right_vars

    def _remove_lhs_rhs_repeat(self):
        if self.get_type() == "1&0|":  # only these occur for given file
            left_set_var = set(var for _, var in self.left_vars)
            right_set_var = set(var for _, var in self.right_vars)
            common_var = left_set_var.intersection(right_set_var)
            self.right_vars = [
                var for var in self.right_vars if var[1] not in common_var
            ]

    def _str_constraint(self):
        result = ""
        for neg, var in self.left_vars[:-1]:
            result += (" ~F" if neg == 1 else " F") + str(var)
            result += " " + self.left_op
        if len(self.left_vars) == 0:
            result += " 1"
        else:
            result += " ~F" if self.left_vars[-1][0] == 1 else " F"
            result += str(self.left_vars[-1][1])

        result += " =>"

        for neg, var in self.right_vars[:-1]:
            result += (" ~F" if neg == 1 else " F") + str(var)
            result += " " + self.right_op
        if len(self.right_vars) == 0:
            result += " 0"
        else:
            result += " ~F" if self.right_vars[-1][0] == 1 else " F"
            result += str(self.right_vars[-1][1])
        result += " "  # for compatibility
        return result[1:]

    def get_type(self):
        result = ""
        neg_set_left = set(el[0] for el in self.left_vars)
        neg_set_right = set(el[0] for el in self.right_vars)

        if len(neg_set_left) == 1:
            result += str(list(neg_set_left)[0])
        elif len(neg_set_left) == 0:
            result += "0"
        else:
            result += "m"

        result += self.left_op

        if len(neg_set_right) == 1:
            result += str(list(neg_set_right)[0])
        elif len(neg_set_right) == 0:
            result += "0"
        else:
            result += "m"

        result += self.right_op

        return result


class IfConstraintBMW(IfConstraintBMWAbs):
    def __init__(self, constraint: str=None, t=None, tvars=None) -> None:
        self.t = -1
        self.left_op = "N"
        self.right_op = "N"
        self.left_vars = []
        self.right_vars = []

        if constraint == None:
            return

        self.t = t
        self._basic_splitter(constraint)
        self._constraint_simplification(tvars)
        self._remove_lhs_rhs_repeat()

        assert len(self.left_vars) + len(self.right_vars) > 0

        if len(self.left_vars) <= 1:
            self.left_op = str(len(self.left_vars))
        if len(self.right_vars) <= 1:
            self.right_op = str(len(self.right_vars))

    def __str__(self) -> str:
        return "T" + str(self.t) + " : " + self._str_constraint()

    def _constraint_simplification(self, tvars):
        left_vars = self.left_vars
        right_vars = self.right_vars

        if self.left_op == "&":
            new_var = []
            for var in left_vars:
                if not (var[1] in tvars):
                    if var[0] == 1:
                        continue  # don't include it
                    else:
                        self.t = -1
                        return
                else:
                    new_var.append(var)
            left_vars = new_var

        if self.left_op == "|":
            new_var = []
            for var in left_vars:
                if not (var[1] in tvars):
                    if var[0] == 1:
                        raise ValueError("Error type |0")
                    else:
                        continue
                else:
                    new_var.append(var)
            left_vars = new_var
            if len(left_vars) == 0:
                self.t = -1
                return

        if self.right_op == "|":
            new_var = []
            for var in right_vars:
                if not (var[1] in tvars):
                    if var[0] == 1:
                        self.t = -1
                        return
                    else:
                        continue
                else:
                    new_var.append(var)
            right_vars = new_var

        if self.right_op == "&":
            new_var = []
            for var in right_vars:
                if not (var[1] in tvars):
                    if var[0] == 1:  # negation -> rest v True => True
                        continue
                    else:
                        raise ValueError("Error type &0")
                else:
                    new_var.append(var)
            right_vars = new_var
            if len(left_vars) == 0:
                self.t = -1
                return

        if self.right_op == "1":
            var = right_vars[0]
            if not (var[1] in tvars):
                if var[0] == 1:  # for example T11 : F87 => ~F298
                    self.t = -1
                    return
                else:  # for example F14 => F140
                    right_vars = []

        if self.left_op == "1":
            var = left_vars[0]
            if not (var[1] in tvars):
                if var[0] == 0:  # for example T11 : F87 => ~F298
                    self.t = -1
                    return
                else:
                    left_vars = []
        self.right_vars = right_vars
        self.left_vars = left_vars


class IfConstraintBMWBunch(IfConstraintBMWAbs):
    def __init__(self, constraint: str=None, cartypes=None, tvars_list=None) -> None:
        self.loaded = True
        self.left_op = "N"
        self.right_op = "N"
        self.left_vars = []
        self.right_vars = []
        self.orig_types = []
        self.max_types = []
        self.constr_simplified = []

        if constraint == None:
            self.loaded = False
            return

        self.orig_types = deepcopy(cartypes)

        self._basic_splitter(constraint)
        for t in self.orig_types:
            tvar = next(tvar for tvar in tvars_list if tvar.t == t).vars
            constr = IfConstraintBMW(constraint, t, tvar)
            if constr.t != -1:
                self.constr_simplified.append(constr)
        if len(self.constr_simplified) == 0:
            self.loaded = False
            return
        self._maximize_cartypes_set(tvars_list)

        if len(self.left_vars) <= 1:
            self.left_op = str(len(self.left_vars))
        if len(self.right_vars) <= 1:
            self.right_op = str(len(self.right_vars))

        self.orig_types = sorted(self.orig_types)
        self.max_types = sorted(self.max_types)

    def __str__(self) -> str:
        result = self._str_constraint()
        result += "\n"
        result += str(self.orig_types) + " "
        result += str(self.max_types)
        return result

    def _maximize_cartypes_set(self, tvars):
        cartypes = set(tvar.t for tvar in tvars)
        missing_cartypes = cartypes.difference(self.orig_types)
        self.max_types = deepcopy(self.orig_types)
        missing_tvars = list(filter(lambda tvar: tvar.t in missing_cartypes, tvars))
        if self.get_type()[1] in "1&":
            for neg, var in self.left_vars:
                if neg == 0:
                    for tvar in missing_tvars:
                        if var not in tvar.vars:
                            self.max_types.add(tvar.t)

        if self.get_type()[3] in "1|":
            for neg, var in self.right_vars:
                if neg == 1:
                    for tvar in missing_tvars:
                        if var not in tvar.vars:
                            self.max_types.add(tvar.t)
        self.max_types = sorted(self.max_types)

    def is_mergable(self, tvars):
        return {tvar.t for tvar in tvars} == set(self.max_types)

    def missing_types(self, tvars):
        return {tvar.t for tvar in tvars}.difference(self.max_types)


class TVars:
    def __init__(self, s: str = None) -> None:
        self.vars = []
        self.t = -1
        if s == None:
            return

        t_case, vars_str = s.split(":")
        self.t = int(t_case[1:])
        for var in vars_str.split():
            self.vars.append(int(var[1:]))

    def __str__(self) -> str:
        result = "T" + str(self.t) + " : "
        for v in self.vars:
            result += "F" + str(v) + " "
        return result


class ExlucionVars:
    def __init__(self, s: str = None) -> None:
        self.vars = []
        if s == None:
            return
        for var in s.split():
            self.vars.append(int(var[1:]))

    def __str__(self) -> str:
        result = ""
        for v in self.vars:
            result += "F" + str(v) + " "
        return result


class TestReq:
    def __init__(self, id, count: int, test_line: str = None) -> None:
        # this works only if there or of features, not literals
        self.test = []
        self.count = -1
        self.id = id
        self.weight = None
        self.group = None
        self.time_in = None
        self.time_out = None

        if test_line == None:
            return
        self.count = count
        test = test_line.split()

        ind = 0
        while ind < len(test):
            if test[ind][0] == "F":
                self.test.append((0, int(test[ind][1:])))  # variable
                ind += 1
                continue
            if test[ind][0] == "~":
                self.test.append((1, int(test[ind][2:])))  # not variable
                ind += 1
                continue
            if test[ind] == "(":
                ind += 1
                or_seq = []
                while test[ind] != ")":
                    if test[ind][0] == "F":
                        or_seq.append(int(test[ind][1:]))  # variable
                    elif test[ind][0] == "|":
                        pass
                    else:
                        raise ValueError(
                            "error when parsin test requirements, contact authors"
                        )
                    ind += 1
                ind += 1
                self.test.append((2, or_seq))

    def __str__(self) -> str:
        result = str(self.count) + " : "
        for mode, var in self.test:
            if mode == 0:
                result += "F" + str(var) + " "
            elif mode == 1:
                result += "~F" + str(var) + " "
            elif mode == 2:
                result += "( "
                str_vars = []
                for var_or in var:
                    str_vars += ["F" + str(var_or)]
                result += " | ".join(str_vars)
                result += " ) "
        return result


class BMWProblem:
    def __init__(self, build_filename: str = None, test_filename: str = None) -> None:
        self.cartypes = []
        self.cartypes_no = 0
        self.features = []
        self.features_no = 0
        self.tvars = []
        self.exclusion_vars = []
        self.if_constraints = []
        self.tests = []

        if build_filename == None and test_filename == None:
            return

        if build_filename == None or test_filename == None:
            raise ValueError("Only both or none filenames can be None")

        with open(build_filename) as file:
            lines = file.readlines()
            lines = [line.rstrip() for line in lines]
        self.cartypes_no = int(lines[1].split(":")[1])
        self.cartypes = list(range(self.cartypes_no))
        self.features_no = int(lines[2].split(":")[1])
        self.features = list(range(self.features_no))

        ind_mode = 4

        tvars = []
        for line in lines[ind_mode:]:
            if line == "Rules per typ:":
                break
            tvars.append(TVars(line))
            ind_mode += 1
        self.tvars = tvars

        ind_mode += 1
        if_lines = []
        for line in lines[ind_mode:]:
            if (
                line
                == "group features (only one of them can be active at the same time, each line a group):"
            ):
                break
            if_lines.append(line)
            ind_mode += 1
        stats = self._if_constraints_statistics(if_lines)
        for line, cartypes in stats.items():
            constraint = IfConstraintBMWBunch(line, cartypes, self.tvars)
            if constraint.loaded:
                self.if_constraints.append(constraint)

        ind_mode += 1
        for line in lines[ind_mode:]:
            self.exclusion_vars.append(ExlucionVars(line))

        lines = []
        with open(test_filename) as file:
            lines = file.readlines()
            lines = [line.rstrip() for line in lines]

        unique_tests = dict()
        for line in lines[2:]:
            q, rline = line.split(":")
            rline = rline.strip()
            if rline in unique_tests.keys():
                unique_tests[rline] += int(q)
            else:
                unique_tests[rline] = int(q)
        self.tests = [
            TestReq(id, unique_tests[k], k) for id, k in enumerate(unique_tests.keys())
        ]

    def _if_constraints_statistics(self, lines):
        lines = [line.split(" : ") for line in lines]
        statistics = dict()
        for cartype, constr in lines:
            if constr in statistics.keys():
                statistics[constr].add(int(cartype[1:]))
            else:
                statistics[constr] = {int(cartype[1:])}

        return statistics

from bmw_solver_qprogmods.bmw_parser import *
import os
from numpy.random import choice, rand
from copy import deepcopy
from bmw_solver_qprogmods.qubo_generate import *
import numpy as np

"""
    types_no can be list of types, or it's number
"""


def generate_partial_sample(problem: BMWProblem, types_no, p_test=1, seed=None):
    assert 0 <= p_test and p_test <= 1
    result = BMWProblem()

    if seed != None:
        np.random.seed(seed)
    # preparing selected cartypes

    if isinstance(types_no, list):
        result.cartypes_no = len(types_no)
        result.cartypes = deepcopy(types_no)
    else:
        result.cartypes_no = types_no
        result.cartypes = choice(problem.cartypes, size=types_no, replace=False)
        result.cartypes_no = sorted(result.cartypes)

    features = set()
    for ct in result.cartypes:
        features = features.union(problem.tvars[ct].vars)
    result.features_no = len(features)
    result.features = sorted(features)


    ### building filtered problem
    # filtering car-types
    for el in problem.tvars:
        if el.t in result.cartypes:
            result.tvars.append(deepcopy(el))

    # exclusion vars
    for el in problem.exclusion_vars:
        vars = set(el.vars).intersection(features)
        if len(vars) >= 2:
            constraint = ExlucionVars()
            constraint.vars = sorted(list(vars))
            result.exclusion_vars.append(constraint)

    # if constraints
    for el in problem.if_constraints:
        if el.t in result.cartypes:
            result.if_constraints.append(deepcopy(el))

    # test_const
    i = 0
    for tl in problem.tests:
        if rand() < p_test:  # randomly consider test
            i+=1
            new_test = []
            for var in tl.test:
                if var[0] == 0 and not (var[1] in features):
                    new_test = -1  # ignore the whole test
                    break
                elif var[0] == 0 and var[1] in features:
                    new_test.append((var[0], var[1]))
                elif var[0] == 1 and var[1] in features:
                    new_test.append((var[0], var[1]))
                elif var[0] == 1 and not (var[1] in features):
                    continue  # all cars satisfy this
                elif var[0] == 2:
                    or_vars = list(filter(lambda v: v in features, var[1]))
                    if len(or_vars) == 0:
                        new_test = -1
                        break
                    elif len(or_vars) == 1:
                        new_test.append((0, or_vars[0]))
                    else:
                        new_test.append((2, or_vars))
            if new_test != -1:
                t = TestReq(i, tl.count)
                t.test = new_test
                result.tests.append(t)
    print(result.tests[0].id)
    return result


if __name__ == "__main__":
    build_filename = os.path.join("vehicle_config", "buildability_constraints.txt")
    test_filename = os.path.join("vehicle_config", "test_requirements.txt")
    problem = BMWProblem(build_filename, test_filename)

    t_size = 6  # number of types allowed, can be a list of types
    seed = 10  # seed for randomize tests and types, can be None
    p_type = 0.5  # proportion of considerable types

    problem_new = generate_partial_sample(
        problem, types_no=t_size, p_test=p_type, seed=seed
    )

    nv = 20
    nt = len(problem_new.tvars)
    nf = problem_new.features_no
    data_group = [ev.vars for ev in problem_new.exclusion_vars]

    A, B, C, D = 20, 1, 5, 20
    T = 10
    qp, Q, of = generate_qubo(nv, nt, nf, data_group, problem, A, B, C, D, T)

    print(problem.features)

    print(len(problem_new.if_constraints))
    print(len(problem_new.tests))
    # for i in range(len(problem_new.if_constraints)):
    # print(problem_new.if_constraints[i].__dict__)

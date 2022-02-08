from collections import defaultdict
import itertools as it
import logging


def check_group_features(sample, nv, problem, log):
    fl = [ev.vars for ev in problem.exclusion_vars]
    violate = []
    for feat in fl:
        for i in range(nv):
            s = sum(sample[f"b_{i}_{j}"] for j in feat)
            if s > 1:
                vlist = []
                for j in feat:
                    if sample[f"b_{i}_{j}"] == 1:
                        vlist.append(j)
                violate.append([f"Car {i} has features {vlist}"])
    if log:
        logging.info(f"Group Features: {len(violate) == 0} {violate}")
    return len(violate) == 0, violate


def check_single_type(sample, nv, problem, log):
    violate = []
    for i in range(nv):
        s = sum(sample[f"t_{i}_{j.t}"] for j in problem.tvars)
        if s != 1:
            violate.append(i)
    if log:
        logging.info(f"Single Type: {len(violate)==0} {violate}")
    return len(violate) == 0


# Returns True if all 1
def check_all_1(vars, i, sample):
    for l in vars:
        if sample[f"b_{i}_{l[1]}"] == 0:
            return False
    return True


# Returns True if all 0
def check_all_0(vars, i, sample):
    for l in vars:
        if sample[f"b_{i}_{l[1]}"] == 1:
            return False
    return True


def check_type_features(sample, nv, problem, log):
    violate = []
    for i, el in it.product(range(nv), problem.if_constraints):
        type = el.get_type()
        tlist = el.orig_types
        for t in tlist:
            if type == "0&01" or type == "010&" or type == "0101":
                if (
                    sample[f"t_{i}_{t}"] == 1
                    and check_all_1(el.left_vars, i, sample)
                ) and not check_all_1(el.right_vars, i, sample):
                    violate.append(
                        [f"Car {i}", type, t, el.left_vars, el.right_vars]
                    )
            elif (
                type == "0&1&" or type == "0&11" or type == "011&" or type == "0111"
            ):
                if (
                    sample[f"t_{i}_{t}"] == 1
                    and check_all_1(el.left_vars, i, sample)
                ) and not check_all_0(el.right_vars, i, sample):
                    violate.append(
                        [f"Car {i}", type, t, el.left_vars, el.right_vars]
                    )
            elif type == "0&0|" or type == "010|":
                if (
                    sample[f"t_{i}_{t}"] == 1
                    and check_all_1(el.left_vars, i, sample)
                ) and check_all_0(el.right_vars, i, sample):
                    violate.append(
                        [f"Car {i}", type, t, el.left_vars, el.right_vars]
                    )
            elif (
                type == "m&0|"
                or type == "m&01"
                or type == "1&0|"
                or type == "110|"
                or type == "1101"
            ):
                neg_vars = []
                vars = []
                for j in el.left_vars:
                    if j[0] == 1:
                        neg_vars.append(j)
                    else:
                        vars.append(j)
                if (
                    sample[f"t_{i}_{t}"] == 1
                    and check_all_1(vars, i, sample)
                    and check_all_0(neg_vars, i, sample)
                ) and check_all_0(el.right_vars, i, sample):
                    violate.append(
                        [f"Car {i}", type, t, el.left_vars, el.right_vars]
                    )
            elif type == "0|01" or type == "0|0|":
                if (
                    sample[f"t_{i}_{t}"] == 1
                    and not check_all_0(el.left_vars, i, sample)
                ) and check_all_0(el.right_vars, i, sample):
                    violate.append(
                        [f"Car {i}", type, t, el.left_vars, el.right_vars]
                    )
            elif type == "0|1&" or type == "0|11":
                if (
                    sample[f"t_{i}_{t}"] == 1
                    and not check_all_0(el.left_vars, i, sample)
                ) and not check_all_0(el.right_vars, i, sample):
                    violate.append(
                        [f"Car {i}", type, t, el.left_vars, el.right_vars]
                    )
    if log:
        logging.info(f"Rules per type: {len(violate) == 0} {violate}")
    return len(violate) == 0


def check_allowed_features(sample, nv, problem, log):
    violate = []
    list_all_feat = set(problem.features)
    for i, tvars in it.product(range(nv), problem.tvars):
            result = list_all_feat.difference(tvars.vars)
            for j in result:
                if sample[f"t_{i}_{tvars.t}"] == 1 and sample[f"b_{i}_{j}"] == 1:
                    violate.append(
                        [f"Car {i} is type {tvars.t}, feature {j} not allowed"]
                    )
    if log:
        logging.info(f"Allowed features: {len(violate) == 0} {violate}")
    return len(violate) == 0


def check_test_reqs(sample, nv, tests):
    violate = []
    for vehicle, t in it.product(range(nv),tests):
        if sample[f"p_{vehicle}_{t.id}"] == 1:
            test_reqs = t.test
            for req in test_reqs:
                f = req[1]
                if type(f) == int:
                        if sample[f"b_{vehicle}_{f}"] == req[0]:
                            violate.append(
                                (
                                    f"Test {t.id}: p_{vehicle}_{t.id}=1, x_{vehicle}_{f} should be {req[0]}"
                                )
                            )
                else:
                    orlist = req[1]  # (0,1)
                    s = sum(sample[f"b_{vehicle}_{f}"] for f in orlist)
                    if s == 0:
                        violate.append(
                            (
                                f"Test {t.id}: vehicle {vehicle} should have one feature from {orlist}"
                            )
                        )
    if log:
        logging.info(f"Test constraints: {len(violate) == 0} {violate}")
    return len(violate) == 0


def count_passed_test(sample, nv, tests, log):
    passed_tests, pass_all = defaultdict(lambda: []), defaultdict(lambda: [])
    for i, t in it.product(range(nv), tests):
        test_reqs = t.test
        flag = True
        for req in test_reqs:
            feat = req[1]
            if type(feat) == int:
                flag &= sample[f"b_{i}_{feat}"] != req[0]
            else:
                flag &= sum(sample[f"b_{i}_{f}"] for f in feat) > 0
        if flag:
            passed_tests[t.id].append(i)

    for t in tests:
        if t.id in passed_tests and len(passed_tests[t.id]) >= t.count:
            pass_all[t.id] = passed_tests[t.id]
    if log:
        logging.info(f"Partially fulfilled tests: {len(passed_tests)}")
        logging.info(f"Fulfilled tests: {len(pass_all)}")
    return passed_tests


def sample_full_check(sample, nv, bmw_problem, energy, of, car_properties, log):
    for i in range(nv):
        type = car_properties[i]["type"]
        features = car_properties[i]["features"]
        if log:
            logging.info(f"Car {i} is type {type} has features {features}")
    if log:
        logging.info(f"Energy: {energy+of}")
    st = check_single_type(sample, nv, bmw_problem,log)
    df = check_group_features(sample, nv, bmw_problem,log)
    tf = check_type_features(sample, nv, bmw_problem,log)
    af = check_allowed_features(sample, nv, bmw_problem,log)
    return st and df and tf and af


def translate_sample(sample, nv, problem):
    car_properties = {}
    for i in range(nv):
        types = []
        for j in problem.tvars:
            if f"t_{i}_{j.t}" in sample.keys() and sample[f"t_{i}_{j.t}"] == 1:
                types.append(j.t)
        features = []
        for j in problem.features:
            if f"b_{i}_{j}" in sample.keys() and sample[f"b_{i}_{j}"] == 1:
                features.append(j)
        car_properties[i] = {"type": types, "features": features}
    return car_properties


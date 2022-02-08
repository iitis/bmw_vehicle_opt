import os
import pickle
from random import uniform

import dimod
from dwave.system.samplers.leap_hybrid_sampler import LeapHybridSampler
import neal
import pulp
from bmw_solver_qprogmods import (BMWIntegerProgramMAXSAT,
                                  BMWIntegerProgramSAT, BMWProblem)
from dwave.system import LeapHybridCQMSampler
import numpy as np


def anneal(bqm, ns, nr, anneal_type):
    if anneal_type == 's':
        s = neal.SimulatedAnnealingSampler()
        sampleset = s.sample(bqm, beta_range=(5, 100), num_sweeps=ns, num_reads=nr,
                             beta_schedule_type='geometric')
    elif anneal_type == 'h':
        s = LeapHybridSampler()
        sampleset = s.sample_qubo(bqm)

    results, energies = [], []

    for datum in sampleset.data(fields=["sample", "energy"]):
        energies.append(datum.energy)
        results.append(datum[0])
    return sampleset


def constrained_solver(cqm, time):
    sampler = LeapHybridCQMSampler()
    return sampler.sample_cqm(cqm,time_limit = time)


def get_bqm(bmw_ip, pdict):
    obj = bmw_ip.export_pyqubo(strength=1000)
    return obj.to_bqm(pdict)


def get_cqm(bmw_ip):
    return bmw_ip.export_dimod()


def get_lp(bmw_ip):
    return bmw_ip.export_pulp()


def get_bmw_problem(folder, build_file, test_file):
    build_filename = os.path.join(folder, build_file)
    test_filename = os.path.join(folder, test_file)
    return BMWProblem(build_filename, test_filename)


def get_sampleset(file_name, model):
    file = load_sampleset(file_name)
    if model == "pulp":
        return file
    sampleset = dimod.SampleSet.from_serializable(file)

    if model == "cqm":
        sampleset = sampleset.filter(lambda d: d.is_feasible)
    samples = [data.sample for data in sampleset.data()]
    energies = [data.energy for data in sampleset.data()]

    return samples, energies


def store_results(filename, sampleset):
    sdf = sampleset.to_serializable()
    with open(filename, 'wb') as handle:
        pickle.dump(sdf, handle)


def fill_weight_tests(bmwproblem, a=1, b=2, vec=None):
    if vec is None:
        for test in bmwproblem.tests:
            if test.weight == None:
                test.weight = uniform(a, b)
    else:
        assert len(vec) >= len(bmwproblem.tests)
        for val, test in zip(vec, bmwproblem.tests):
            if test.weight == None:
                test.weight = val


def generate_pulp_sampleset(lp):
    sampleset = {str(v): v.varValue for v in lp.variables()}
    obj = lp.objective.value() if lp.objective != None else 0
    return sampleset, obj


def store_pulp_sampleset(file, sampleset, obj, st, sct):
    solution = (sampleset, obj, st, sct)
    with open(file, 'wb') as handle:
        pickle.dump(solution, handle)


def load_sampleset(file):
    return pickle.load(open(file, "rb"))


def pulp_experiment(file, problem, nv, mode, bmw_problem, model):
    if mode == "run":
        if problem == "maxsat":
            bmw_ip = BMWIntegerProgramMAXSAT(bmw_problem, nv, consider_count=True)
        elif problem == "sat":
            bmw_ip = BMWIntegerProgramSAT(bmw_problem, nv)
        lp = get_lp(bmw_ip)
        if model == "pulp":
            lp.solve()
        elif model == "gurobi":
            solver = pulp.getSolver('GUROBI_CMD')
            lp.solve(solver)
        sampleset, obj = generate_pulp_sampleset(lp)
        store_pulp_sampleset(file, sampleset, obj, lp.solutionTime, lp.solutionCpuTime)
    elif mode == "load":
        sampleset, obj, st, sct = get_sampleset(file, "pulp")
    return [sampleset], [obj]


def cqm_experiment(file, problem, nv, mode, bmw_problem, time):
    if mode == "run":
        if problem == "maxsat":
            bmw_ip = BMWIntegerProgramMAXSAT(bmw_problem, nv, consider_count=True)
        elif problem == "sat":
            bmw_ip = BMWIntegerProgramSAT(bmw_problem, nv)
        cqm = get_cqm(bmw_ip)
        sampleset = constrained_solver(cqm, time)
        store_results(file, sampleset)
    return get_sampleset(file, "cqm")


def bqm_experiment(file, problem, nv, mode, bmw_problem, pdict, ns, nr, anneal_type):
    """ns == number of sweeps
       nr == number of reads"""

    if mode == "run":
        if problem == "maxsat":
            bmw_ip = BMWIntegerProgramMAXSAT(bmw_problem, nv, consider_count=True)
        elif problem == "sat":
            bmw_ip = BMWIntegerProgramSAT(bmw_problem, nv)
        bqm = get_bqm(bmw_ip, pdict)

        sampleset = anneal(bqm, ns, nr, anneal_type)
        store_results(file, sampleset)
    return get_sampleset(file, f"bqm+{anneal_type}")

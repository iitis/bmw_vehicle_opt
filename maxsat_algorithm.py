import argparse

from bmw_solve import *
from bmw_solver_qprogmods.helpers import *
import logging
from os.path import exists
import sys

def get_penalties():
    pdict = {}
    pdict["single_type"] = 1
    pdict["feat_per_type"] = 1
    pdict["group_features"] = 1
    pdict["rules_per_type"] = 1
    pdict["test_constraint"] = 1
    pdict["test_objective"] = 1
    pdict["penalty_strength"] = 100
    return pdict


def update_tests(passed_tests, bmw_problem):
    for t in bmw_problem.tests:
        t.count -= len(passed_tests[t.id])
    tids = [t.id for t in bmw_problem.tests if t.count <= 0]
    bmw_problem.tests = list(filter(lambda t: t.count > 0, bmw_problem.tests))
    return tids


def log_statistics(bmw_problem, removed_tests, car_properties):
    logging.info("--------------------Statistics----------------------")
    logging.info("Car properties")
    logging.info(car_properties)
    logging.info(f"Removed tests: {len(removed_tests)}")
    logging.info(removed_tests)
    logging.info(f"Remaining tests: {len(bmw_problem.tests)}")
    tids = [(t.id, t.count, t.__dict__) for t in bmw_problem.tests]
    logging.info(tids)


def initialize_experiment(model, problem, build, test, weighted):
    bmw_problem = get_bmw_problem("vehicle_config", build, test)
    weights = [1] * len(bmw_problem.tests)
    if weighted:
        logging.basicConfig(filename=f'results_{problem}_{model}_weighted.log', level=logging.INFO)
        for i, t in enumerate(bmw_problem.tests):
            weights[i] = len(t.test)
    else:
        logging.basicConfig(filename=f'results_{problem}_{model}.log', level=logging.INFO)
    fill_weight_tests(bmw_problem, vec=weights)
    folder = f"{problem}_results_weighted" if weighted else f"{problem}_results"
    return bmw_problem, folder

def experiment(repetitions, model, nv, time, max_iter, log):
    np.random.seed(99)
    problem = "maxsat"
    build = "buildability_constraints.txt"
    test = "test_requirements.txt"
    weighted = False

    for run in range(repetitions):
        bmw_problem, folder = initialize_experiment(model, problem, build, test, weighted)
        vehicles = {}
        logging.info(f"----------------------Run: {run}------------------------")
        remaining_tests = []
        iter = 1 # Initialization
        while iter < max_iter+1:
            if log: logging.info(f"----------------------Iteration: {iter}------------------------")

            car_properties, pfts = {}, {}  #Dictionaries to hold car properties, partially fulfilled tests at each iteration
            all_energies, all_samples, num_pfts = {}, {}, {} #Dictionaries to hold energies, samples, number of partially.f.t. at each iteration

            num_trials = 1 #Number of trials for each interation, this is increased in case feasible solution is not found
            trial = 0
            while (trial < num_trials):
                if log: logging.info(f"----------------------Trial: {trial}------------------------")

                #load or run the file
                if time == 5:
                    file = os.path.join(folder, f"{model}_{problem}_{nv}_{iter}_{trial}_{run}")
                else:
                    file = os.path.join(folder, f"{model}_{problem}_{nv}_{iter}_{trial}_{run}_{time}")
                mode = "load" if exists(file) else "run"

                #call the experiment
                if model == 'cqm':
                    samples, energies = cqm_experiment(file, problem, nv, mode, bmw_problem, time)
                elif model[:3] == 'bqm':
                    samples, energies = bqm_experiment(file, problem, nv, mode, bmw_problem, get_penalties(), 1000, 1000,
                                                       model.strip('bqm+'))
                elif model in ['pulp', 'gurobi']:
                    samples, energies = pulp_experiment(file, problem, nv, mode, bmw_problem, model)

                if samples != []: #This is empty in case cqm solver returns no feasible solution
                    sample, energy = samples[0], energies[0]
                    car_properties[trial] = translate_sample(sample, nv, bmw_problem) #get the car properties
                    feasible = sample_full_check(sample, nv, bmw_problem, energy, 0, car_properties[trial], log) #check if feasible
                    if feasible:
                        all_samples[trial] = sample #save the sample
                        pfts[trial] = count_passed_test(sample, nv, bmw_problem.tests, log) #save pfts for the trial
                        num_pfts[trial] = sum([len(satisfying_cars) for test_id, satisfying_cars in pfts[trial].items()]) #save num of pfts

                if len(num_pfts) == 0 and num_trials == 5:
                    logging.info("No feasible solution is found in 5 trials.")
                    quit()
                if len(num_pfts) == 0:  #If no pfts trial found, increase num_trial
                    num_trials += 1

                trial += 1

            iter += 1
            index = max(num_pfts, key=num_pfts.get) #Find the trial which satisfies max no of pfts
            vehicles[iter] = car_properties[index] #Save vehicle properties for iteration
            removed_tests = update_tests(pfts[index], bmw_problem) #Remove pfts from problem
            remaining_tests.append(len(bmw_problem.tests)) #Number of remaining tests

            if len(bmw_problem.tests) == 0:  # if all tests are satisfied, exit
                max_iter = iter
                break
            
            if log: log_statistics(bmw_problem, removed_tests, vehicles)

        logging.info("----------------------Results--------------------")
        if log:
            for iter in vehicles:
                logging.info(vehicles[iter])
        logging.info(remaining_tests)
        logging.info(max_iter)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=int,
                        help="Number of experiments.")
    parser.add_argument("model", type=str, choices=["pulp", "gurobi","cqm"],
                        help="Solver to be used. It should be either pulp, gurobi or cqm.")
    parser.add_argument("nv", type=int,
                        help="Number of vehicles.")
    parser.add_argument("-time", type=int, default=5,
                        help="Time limit for constrained solver. Default is 5s.")
    parser.add_argument("-it", type=int, default = 70,
                        help="The number of iterations. The default is 70. The program stops earlier if all tests are satisfied")
    parser.add_argument("-log", action="store_true", default=False,
                        help="Whether to generate a log for each iteration. Default is False.")
    args = parser.parse_args()

    experiment(args.runs, args.model, args.nv, args.time, args.it, args.log)

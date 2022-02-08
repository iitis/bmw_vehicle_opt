import pickle
import matplotlib.pyplot as plt
import numpy as np
import re  

def runtime_info_cqm():
    exp_no = 3
    model = 'cqm'
    overall_average_qpu_time = 0
    overall_run_time = 0
    for run in range(exp_no):
        qpu_run_time = 0
        run_time = 0
        for i in range(1, 66+1):
            file = f'maxsat_results/{model}_maxsat_1_{i}_0_{run}'
            x = pickle.load(open(file, "rb"))
            print(x.keys())
            print(x['sample_data'])
            qpu_run_time += x['info']['qpu_access_time']
            run_time += x['info']['run_time']

        overall_average_qpu_time += qpu_run_time
        overall_run_time += run_time

    qpu_total_time = overall_average_qpu_time/ exp_no
    overall_runtime = overall_run_time //exp_no
    ration_of_time = qpu_run_time / overall_runtime
    print(f'qpu time {qpu_total_time*1e-6}, runtime {overall_runtime*1e-6}, ratio {ration_of_time}')


def runtime_info_pulp_gurobi():
    exp_no = 60
    for model in ['pulp', 'gurobi']:
        if model == 'pulp':
            iter = 62
        else:
            iter = 64

        overall_run_time = 0
        for run in range(exp_no):
            run_time = 0
            for i in range(1, iter+1):
                file = f'maxsat_results/{model}_maxsat_1_{i}_0_{run}'
                x = pickle.load(open(file, "rb"))
                print(x[0])
                run_time += x[2]

            overall_run_time += run_time

        total_runtime = overall_run_time/ exp_no
        print(total_runtime, model)
    return 'The answer is above this text'

if __name__ == "__main__":
    print(runtime_info_pulp_gurobi())

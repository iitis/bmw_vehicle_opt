import pickle
import matplotlib.pyplot as plt
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.size": 12
})


def make_label(model_list):

    label_list = []
    for el in model_list:
        if el == 'gurobi':
            label_list.append('Gurobi')
        elif el == 'cqm':
            label_list.append('CQM')
        else:
            label_list.append('CBC')

    return label_list

def runtime_vs_iteration(model_list, total_exp_numb):

    label_list = make_label(model_list)
    line_type =  [ 'r-', 'b--', 'g-.']
    plt.figure(figsize=(4.2, 4))
    for model_no, model in enumerate(model_list):
        iter_list = []
        run_time_list = []
        remaining_test_list = []
        infile = f'results_maxsat_{model}_short.log'
        with open(infile) as f:
            f = f.readlines()
        remaining_test_list.append(eval(f[2][10: len(f[2])]))
        remaining_test_list = remaining_test_list[0]
        iterations = len(remaining_test_list)
        
        for i in range(1, iterations+1):
            run_time = 0
            if model == 'cqm':
                exp_numb = 1
            else:
                exp_numb = total_exp_numb       
            for run in range(exp_numb):      
                if model  == 'cqm':
                    file = f'maxsat_results/{model}_maxsat_1_{i}_0_0'
                    x = pickle.load(open(file, "rb"))
                    exp_run_time = x['info']['run_time']*1e-6 
                else:
                    file = f'maxsat_results/{model}_maxsat_1_{i}_0_{run}'
                    x = pickle.load(open(file, "rb"))
                    exp_run_time = x[2]
                run_time += exp_run_time
            run_time /= exp_numb
            run_time_list.append(run_time)
            iter_list.append(i)
        
        plt.semilogy(iter_list, run_time_list, line_type[model_no], label = f'{label_list[model_no]}')
    
    plt.xlabel('Iterations')
    plt.ylabel('Runtime (s)')
    plt.legend(bbox_to_anchor=(0.66, 1.02), loc=2, borderaxespad=0.5, prop={'size': 11})
    # plt.savefig('plot/averaged_runtime_vs_iteration.png', bbox_inches='tight')
    plt.savefig('plot/averaged_runtime_vs_iteration.pdf', bbox_inches='tight')


def remaining_test_vs_iterations(model_list, mode = None):

    label_list = make_label(model_list)
    plt.figure(figsize=(4.4, 4))
    line_type =  [ 'r-', 'b--', 'g-.']
    for model_no, model in enumerate(model_list):
        if model == 'cqm':
            infile = f'results_maxsat_{model}_short.log'
        else:
            infile = f'results_maxsat_{model}_short.log'
        with open(infile) as f:
            f = f.readlines()
        i = 0
        remaining_test_list = []
        if model == 'cqm':
            
            remaining_test_list.append(eval(f[i+2][10: len(f[i+2])]))
            remaining_test_list = remaining_test_list[0]
            iter_list = list(range(len(remaining_test_list)))
        else:
            remaining_test_list.append(eval(f[i+2][10: len(f[i+2])]))
            remaining_test_list = remaining_test_list[0]
            iter_list = list(range(len(remaining_test_list)))
            
        iteration_list = []
        for iter_el in iter_list:
            iteration_list.append(iter_el+1)
    
        plt.plot(iteration_list, remaining_test_list, line_type[model_no], label = f'{label_list[model_no]}')
        if model == 'cqm':
            plt.plot(iteration_list, [0]*len(remaining_test_list), 'k--')
    
    if mode == 'zoomed':
        
        plt.xlim(55,66)
        plt.ylim(-0.5,10)
        plt.xticks(fontsize = 18)
        plt.yticks(fontsize = 18)
        plt.savefig('plot/averaged_remaining-cars_vs_iterations_zoomed.png')
        plt.savefig('plot/averaged_remaining-cars_vs_iterations_zoomed.pdf')  
    else:
        plt.xlabel('Iterations')
        plt.ylabel('Number of remaining tests')
        plt.savefig('plot/averaged_remaining-cars_vs_iterations.png', bbox_inches='tight')
        plt.savefig('plot/averaged_remaining-cars_vs_iterations.pdf', bbox_inches='tight')


if __name__ == "__main__":

    model_list = ['cqm', 'gurobi', 'pulp']
    total_exp_numb = 60
    runtime_vs_iteration(model_list, total_exp_numb)
    # remaining_test_vs_iterations(model_list)

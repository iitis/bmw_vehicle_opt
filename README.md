# Source code for *Optimizing the Production of Test Vehicles using Hybrid Constrained Quantum Annealing*

The scripts necessary for generating the results provided in the "Optimizing the Production of Test Vehicles using Hybrid Constrained Quantum Annealing"

## Software installation

Anaconda distribution can be downloaded from https://www.anaconda.com/products/individual. To install

```
conda env create -f vehicle_env.yml
```

To activate this environment, use
```
conda activate vehicle_env
```
To deactivate an active environment, use
```
conda deactivate
```

## Reproducing the results

The code already contains data used in the publication. To run the experiments, follow the instructions below. Occasionally the code omits generating new data if old already exist. If you want to generate new data, please remove the old data.


## Data used in publication

The input files are located in `vehicle_config` folder which contains `buildability_constraints.txt` and `test_requirements.txt`. Data is stored in the format of `pickle` files inside folder `maxsat_results` named in the following format: `{name_of_solver}_maxsat_{number_of_vehicles}_{iteration_number}_{trial_number}_{experiment_number}`. `trial_number` is increased in case no feasible solution is found at an iteration and the other parameters will be explained below. If you want to reproduce the results, you can follow the steps below to run the experiments which will load the existing data. If you want to generate new data, please remove the related files.


## Running the experiment

To generate and save the outcomes from classical and quantum solvers you need to run the code

```
python maxsat_algorithm.py 60 cqm 1 -it=50 -time=10 -log
```
that generates data by running the `maxsat_algorithm.py` for `60` times, using CQM solver, optimizing `1` vehicle at each iteration. The rest of the commands are optional. The parameter `-it=50` limits the number of iterations to 50. `-time=10` is the time limit for CQM solver. `-log` should be used if you want to log the results of the experiment for each iteration. Hence the `.py` file takes 

- *number of experiments*, 
- *name of the solver*, 
    
    - `cqm` for constrained quantum solver (CQM) by D-Wave, 
    - `pulp` for CBC (Coin-or branch and cut) solver,
    - `gurobi` for Gurobi solver. 

- *number of vehicles*, 

- *number of iterations* (optional),
    - if not specified the experiment will terminate when no tests remain to be satisfied or running at most 70 iterations. If specified for an example `-it=N`, then the experiment will either terminate at `N` or earlier if all tests are satisfied.

- *time limit for CQM solver* (optional),
    - The CQM solver has a default time of `5` seconds and it is the lowest possible.

- *Whether to generate a log for each iteration* (optional),
    -  by default it is `False` i.e. does not generate `.log` file for each iterations

as the command line parameters. 

## Results analysis

To utilize the results obtained from the experiments, one can follow the following data extraction procedure and reproduce the plots in the publication. Let us consider the saved file name as `F`.

- **Runtime and qpu time** 
    - `For cqm:` As `F` is saved as a dictionary then the `runtime` and the `qpu access time` can be extracted using `F['info']['run_time']` and `F['info']['qpu_access_time']` respectively.

    - `For classical solvers:` One can extract the runtime using `F[2]`.

- **Sample data**
    - `For cqm:` One can find the sample data using the command `F['sample_data]`,
    - `For classical solvers:` To get sample data one can do `F[0]`.

- **Remaining number of tests**
    - In the default setting (i.e. `False`) the `.log` file simply contains a list of the number of remaining tests at each iteration.

To reproduce the plots in the publication one simply need to run the `plotter.py`. Finally to get the information about overall runtime (overaged over experiments) by the solvers you can run the `runtime_calculator.py` file.


## Additional notes

It should be noted that the subroutine of the algorithm is implemented in the following `.py` files

- `bmw_solve.py`
- `bmw_solver_qprogmods.py`

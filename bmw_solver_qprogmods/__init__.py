"""
bmw_solver_qprogmods
========
bmw_solver_qprogmods is a Python package which generates a QUBO and ConstraintQuadraticModel
for BMW Challenge "Optimizing the Production of Test Vehicles"

Organization: 
Institute of Theoretical and Applied Informatics, Polish Academy of Sciences

Authors:
Adam Glos, aglos@iitis.pl
Akash Kundu, akundu@iitis.pl
Ozlem Salehi Koken, osalehi@iitis.pl
"""

__version__ = "0.1"

from bmw_solver_qprogmods.bmw_parser import BMWProblem
from bmw_solver_qprogmods.ip_problems import (BMWIntegerProgramMAXSAT,
                                              BMWIntegerProgramSAT)
from bmw_solver_qprogmods.ip_utils import (get_car_feature_name,
                                           get_car_test_name,
                                           get_car_type_name, get_maxsat_test,
                                           get_schedule_var)

__all__ = [
    "BMWProblem",
    "BMWIntegerProgramMAXSAT",
    "BMWIntegerProgramSAT",
    "get_car_feature_name",
    "get_car_test_name",
    "get_car_type_name",
    "get_maxsat_test",
    "get_schedule_var"
]
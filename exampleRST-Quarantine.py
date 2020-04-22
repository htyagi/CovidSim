#This example runs the simulation using testing policy RST and intervention policy Quarantine
#The output is stored in example/SimulationResults/outputData
#Note that the output data is uncompressed and the size can be significantly reduced
# by compressing using, for instnace, gzip


#Dependencies
import numpy as np
import matplotlib.pyplot as plt
from functools import partial
import pickle
import random as random
import os

#CovidSim modules 
from evolution import simulate
from interventions import InterventionQuarantine
from tests import RandomSymptomaticTesting
from inoutfuncs import setupcitydata

#Read Bangalore data using function setupcitydata available in inoutfuncs
CD, CarProb=setupcitydata('example/InputData/city.geojson', 'example/InputData/car-prob.csv')


##Simulation configuration
## run multiple iterations and log data
## details of param settings for recording in file name

Days=100
Population=100000
Iterations=10
seed='uniform' #Uniformly distribute initial cases, see details below
TestingBudget=50 #tests per day
FalseNegative=0.0 #false nagative prob for each test 
LocationRepProb=np.ones(CD.shape[0]) #reporting probability per locality

##testing policy set to RandomSymptomaticTesting given in tests.py
testingPolicy=partial(RandomSymptomaticTesting, TestingBudget, FalseNegative, LocationRepProb)

##intervention policy set to InterventionQuarantine in interventions.py
interventionPolicy=InterventionQuarantine


#Model Parameters                                                                                                                                             
ModelParams = {\
    #Probability with which two persons who meet will transfer Covid                                                                                         
    "CovidInfectionRate":0.1, \

    #Covid [1/Average time to symptoms, 1/Average time to recovery]                                                                                           
    "CovidRateVector": [1, 1/8], \

    #Flu [S2I, 1/Average time with Flu symptoms]                                                                                                              
    "FluRateVector": [0.02, 1/8], \

    #Each person meets these many random people locally                                                                                                       
    "NeighborhoodContact": 1, \

    #Each person meets these many fixed people locally                                                                                                        
    "NeighborhoodContactFixed": 5, \

    #Each person meets these many random people at a hotspot                                                                                                  
    "HotspotContact": 2, \

    #Each person meets these many fixed people at a hotspot                                                                                                   
    "HotspotContactFixed": 10,}


#Directory for storing output data
OutputDirectory = "OutputData/"
SimulationDirectory="SimulationResults/"
ParentDirectory = "example/"

#Create simulation directory
path = os.path.join(ParentDirectory, SimulationDirectory)
if not os.path.exists(path):
    os.mkdir(path)
ParentDirectory+=SimulationDirectory
path = os.path.join(ParentDirectory, OutputDirectory) 
if not os.path.exists(path):
    os.mkdir(path)


##Initial infected (seed)
## Seeding type 1: Uniform seeding
## covid and flu infected distributed uniformly
InitFracLocalitiesCovid=0.1 # approx. fraction of localities with a single covid infection seed                                                               
InitFracLocalitiesFlu=0.1 # approx. fraction of localities with a single flu infection seed                                                                   
CovidMaxPerLocality= 5
FluMaxPerLocality= 20


## Seeding type 2: clustered seeding
## all covid infections placed in a single locality (locality_name="Cottonpete", locality_id=120)
## flu infection seeds randomly placed across localities
SeedLocalityID = 120
InitNumSeedsCovid=50 

if seed == 'uniform':
    initcovidcts = np.random.binomial(CovidMaxPerLocality, InitFracLocalitiesCovid, CD.shape[0]).tolist()
    initflucts = np.random.binomial(FluMaxPerLocality, InitFracLocalitiesFlu, CD.shape[0]).tolist()

elif seed == 'clustered':
    initcovidcts = np.zeros(CD.shape[0]).astype(int).tolist()
    initcovidcts[SeedLocalityID-1] = InitNumSeedsCovid
    initflucts = np.random.binomial(1, InitFracLocalitiesFlu, CD.shape[0]).tolist()

###Call to the simulate function in evolution.py
OutputFileNamePrefix=ParentDirectory+OutputDirectory+"RandomSymptomaticTesting_UniformSeed_InterventionQuarantine_TestingBudget50_FalseNegative0" 
for i in range(Iterations):
    CovidCases, TestingHistory,  Symptomatic, Localities = simulate(Days, Population, ModelParams, CD, CarProb, interventionPolicy, testingPolicy,\
                                                                    InitCovidCounts=initcovidcts, InitFluCounts=initflucts)    
    print("Iteration number:"+str(i))
    FileName = OutputFileNamePrefix + "_Iter_" + str(i) + ".pickle"
    with open(FileName, "wb") as f:
        pickle.dump((CovidCases, TestingHistory, Symptomatic, Localities), f)
        print("Results saved in " + FileName)

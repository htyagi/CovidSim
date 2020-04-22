import pandas as pd
import random
import numpy as np
from scipy.special import comb
import timeit
import multiprocessing as mp
import sys
from functools import partial
from interventions import InterventionRule 


#File containing functions for COVID simulation
#This code maintains two globally shared variables: CP and TestingHistory
#CP: the state of the city's population stored as a pandas frame
#TestingHistory: a numpy array storing the history of tests
#  of all people on all days:+1 indicates a positive test, -1 negative, 0 not tested

#Function to initialize the population matrix
#Inputs
# CD: city data in pandas
# CarProb: array of lists  

def Initialize(CD, CarProb, ModelParams, Population, randseed=0):
    random.seed(randseed)
    np.random.seed(randseed)
        
    column_names = ["id", "localityIndex", "locality", "CovidState", "FluState",\
                    "Visits", "neighborhood", "LocalContacts","VisitsContacts",\
                    "quarantine","quarantineDay","CovidPositive"]
    CP=pd.DataFrame(columns = column_names)

    localities=[CD.loc[i, 'locality_name'] for i in range(CD.shape[0]) \
                for j in range(int(Population*CD.loc[i,'locality_density']))]

    localitiesIndex=[CD.loc[i, 'locality_id']  for i in range(CD.shape[0]) \
                     for j in range(int(Population*CD.loc[i, 'locality_density']))]



    PopulationEffective= len(localities)

    idVector=[i for i in range(PopulationEffective)]

    InitialStateCovid=['S' for i in range(PopulationEffective)]
    InitialStateFlu=['S' for i in range(PopulationEffective)]
    
    # Setup The Place Each person visits
    Visits=[np.argmax(np.random.multinomial(1,CarProb[i])) for i in range(CD.shape[0]) \
            for j in range(int(Population*CD.loc[i,'locality_density']))]
    
    CP['id']=idVector
    CP['locality']=localities
    CP['localityIndex']=localitiesIndex
    CP['CovidState']=InitialStateCovid
    CP['FluState']=InitialStateFlu
    CP['Visits']=Visits
    CP['quarantine']=[0 for i in range(PopulationEffective)]
    CP['CovidPositive']= [0 for i in range(PopulationEffective)]
    CP['neighborhood']=[list(CD.loc[CD['locality_name']==CP.loc[i, 'locality']].locality_neighbors)[0] \
                           for i in range(PopulationEffective)]

    #Set up contact list for each person
    contactsLocal=[CP['id'].loc[CP['locality'].isin(CD.loc[i, 'locality_neighbors'].split(", "))].values \
              for i in range(CD.shape[0])]
    contactsHotspot=[CP['id'].loc[CP['Visits'] == i].values \
              for i in range(len(CarProb[0])-1)] 


    NumHotspotFixed = ModelParams["HotspotContactFixed"]
    NumLocalFixed = ModelParams["NeighborhoodContactFixed"]
    
    contactListLocal=[np.random.choice(contactsLocal[i], size=NumLocalFixed).tolist() for i in range(CD.shape[0])\
                 for j in range(int(Population*CD.loc[i, 'locality_density']))]

    random.seed(randseed+1)
    contactListHotspot = [[] for i in range(CP.shape[0])]
    for i in range(CP.shape[0]):
            hotspot = CP.loc[i, 'Visits']
            if hotspot<len(CarProb[0])-1:
                contactListHotspot[i]=np.random.choice(contactsHotspot[hotspot], size=NumHotspotFixed).tolist()
                
    CP['LocalContacts']=contactListLocal
    CP['VisitsContacts']=contactListHotspot

    print("City Population Data setup complete")
    
    return CP

#Function to Initialize infections to a prespecified value
#Inputs
# InfectionCountsCovid (list int): Location-wise number of people with COVID
# InfectionCountsFlu (list int): Location-wise number of people with flu

def InitInfection(InfectionCountsCovid, InfectionCountsFlu, CP, randseed=0):
    
    for i in range(len(InfectionCountsCovid)):
        if (CP.loc[CP['localityIndex']==i+1].shape[0]>=InfectionCountsCovid[i]) and\
           (CP.loc[CP['localityIndex']==i+1].shape[0]>=InfectionCountsFlu[i]):
            sampleIdsCovid=CP.loc[CP['localityIndex']==i+1].sample(n=InfectionCountsCovid[i], random_state=randseed).index.values
            sampleIdsFlu=CP.loc[CP['localityIndex']==i+1].sample(n=InfectionCountsFlu[i], random_state=randseed).index.values
            CP.loc[sampleIdsCovid, 'CovidState']='E'
            CP.loc[sampleIdsFlu, 'FluState']='I'
        else:
            print('Error: Population in locality ' +str(i+1)+' too small for sampling initially infected. Terminating simulation.')
            sys.exit(1)
            

#The main simulate function
#Inputs
# NumSteps: number of days (int)
# Population: population of city (int) [actually we will /
#                   simulate slightly fewer individuals due to round-off from densities]
# interventionPolicy: name of the interventionPolicy function
# testingPolicy: name of the testingPolicy function
# CD: city data in pandas; see the function Initialize() to see what columns are needed
# CarProb: list of car probabilities

def simulate(NumSteps, Population, ModelParamsInput, CD, CarProbInput, interventionPolicy, testingPolicy, InitCovidCounts=None, InitFluCounts=None):

    global ModelParams, TestingHistory, CP, CarProb, CovidPerHotspot, PeoplePerHotspot, CovidPerNeighborhood, PeoplePerNeighborhood
    ModelParams=ModelParamsInput
    CarProb=CarProbInput
    
    #Calling Initialize without randseed
    print('Initializing '+str(Population)+' agents...')
    CP=Initialize(CD, CarProb, ModelParams, Population)
    PopulationEffective = CP.shape[0]
    
    

    if not InitCovidCounts:
        #Infect a fixed number of people per ward
        InitialCovid = [np.mod(i,2) for i in range(CD.shape[0])]
    else:
        InitialCovid = InitCovidCounts

    if not InitFluCounts:
        #Infect a fixed number of people per ward
        InitialFlu = [0 for i in range(CD.shape[0])]
    else:
        InitialFlu = InitFluCounts

    InitInfection(InitialCovid, InitialFlu, CP)

    
    #Setting up variables to record simulation data
    CovidCases = np.zeros((CD.shape[0], NumSteps))
    TestingHistory=np.zeros((PopulationEffective, NumSteps))
    Symptomatic =np.zeros((CD.shape[0], NumSteps))

    initial_time=timeit.default_timer()

    PeoplePerNeighborhood=[CP.loc[CP['locality'].isin(CD.loc[CD['locality_id']==i+1].locality_neighbors.values[0].split(", "))].shape[0] \
                            for i in range(CD.shape[0])]
    CovidPerNeighborhood=[0 for i in range(CD.shape[0])]

    PeoplePerHotspot=[CP.loc[CP['Visits']==i].shape[0] for i in range(len(CarProb[0]))]
    CovidPerHotspot=[0 for i in range(len(CarProb[0]))]


    InterventionsHistory=[]
    print("Initialized random infection seed")
    
    for j in range(NumSteps):

        #Intervention policy function can use TestingHistory as observation
        day=j
        interventions=interventionPolicy(TestingHistory, InterventionsHistory, CP, day)
        InterventionsHistory.append(interventions)

        
        updateState_partial = partial(updateState, interventions,  day)
        updateCountNeighborhood_partial = partial(updateCountNeighborhood, CD)

        #SerialImplementation
        #for i in range(PopulationEffective):
        #    StateOut=updateState_partial(i)
        #    CP.loc[i, 'CovidState']=StateOut[0]
        #    CP.loc[i, 'FluState']=StateOut[1]

        
        #Parallel Implementation
        #Set pool
        pool = mp.Pool(8) # 8 state update "threads" for consistency across machines

        
        CovidPerNeighborhood= pool.map(updateCountNeighborhood_partial, [i for i in range(CD.shape[0])])
        CovidPerHotspot=pool.map(updateCountHotspot, [i for i in range(len(CarProb[0]))])
        
        ##### MAIN UPDATE ######
        StateOut=pool.map(updateState_partial, [i for i in range(PopulationEffective)])
        ########################
        
        
        #Close pool
        pool.close()
        pool.join()

        #Update states computed from the parallel pool
        df=pd.DataFrame(StateOut)
        CP['CovidState']=df[0]
        CP['FluState']=df[1]
                
        #Testing policy updates TestingHistory and can interact with the intervention policy
        testingPolicy(CP, TestingHistory, day)  

       #Update Ward-wise symptomatic and CovidCases
        for i in range(CD.shape[0]):
            Symptomatic[i][j]=CP.loc[((CP['CovidState']=='I') | (CP['FluState']=='I'))& (CP['localityIndex']==i+1)].shape[0]
            CovidCases[i][j]=CP.loc[(CP['CovidState']=='I') & (CP['localityIndex']==i+1)].shape[0]

        current_time=timeit.default_timer()
        print("Day:"+str(j)+" Cases:"+str(int(np.sum( CovidCases[:,j] )))+ \
              " PositiveTests:"+str(int(np.sum(  TestingHistory[ TestingHistory[:,j] >0  ,j]   )))+ \
              " TestsConducted:"+str(TestingHistory[ TestingHistory[:,j] !=0  ,j].shape[0] )+ \
              " Symptomatic:"+str(int(np.sum(Symptomatic[:,j]))) + \
              " Interventions:"+str(interventions)+ \
              " TimeTaken:{dt:.3f}s".format(dt=current_time-initial_time))   
        initial_time=current_time
        
    return CovidCases, TestingHistory,  Symptomatic, CP['locality']



#Main function to update state
#Global Variables ModelParams and CP used
#Accesses functions InterventionRule from the file interventions and InfectRate

def updateState(interventions, day, i):
    global CP, CarProb, ModelParams, CovidPerHotspot, PeoplePerHotspot, CovidPerNeighborhood, PeoplePerNeighborhood
    
    CovidState=CP.loc[i,'CovidState']
    FluState=CP.loc[i,'FluState']
    CovidStateOut=CovidState
    FluStateOut=FluState
    
    localspread, globalspread = InterventionRule(interventions, CP, i)
    

    if FluState=="S":
        if random.random()<ModelParams["FluRateVector"][0]:
            FluStateOut="I"
    else:
        if random.random()<ModelParams["FluRateVector"][1]:
            FluStateOut="S"
    
    if CovidState=="E":
        if random.random()<ModelParams["CovidRateVector"][0]:
            CovidStateOut="I"
    elif CovidState=="I":
        if random.random()<ModelParams["CovidRateVector"][1]:
            CovidStateOut="R"
        

            
    #LocalSpread
    if localspread:
         N= PeoplePerNeighborhood[CP.loc[i, 'localityIndex']-1]
         NI=CovidPerNeighborhood[CP.loc[i, 'localityIndex']-1]
         M=ModelParams["NeighborhoodContact"]
         p=ModelParams["CovidInfectionRate"]

         NeighborhoodRate=InfectRate(N, NI,M,p)
         if CovidState=="S":
             if random.random()<NeighborhoodRate:
                 CovidStateOut="E"
        
         for contactId in CP.loc[i,'LocalContacts']:
              if (CovidState=="I") and (CP.loc[contactId, 'CovidState'] =='S'):
                  if random.random()<ModelParams['CovidInfectionRate']:
                      CP.loc[contactId, 'CovidState'] ='E'


    #GlobalSpread
    if globalspread:
         hotspot=CP.loc[i, 'Visits']             
    
         if hotspot<len(CarProb[0])-1:
             N=PeoplePerHotspot[hotspot]
             NI=CovidPerHotspot[hotspot]
             M=ModelParams["HotspotContact"]
             p=ModelParams["CovidInfectionRate"]
         

             HotspotRate=InfectRate(N,NI,M,p)
             if CovidState=="S":
                 if random.random()<HotspotRate:
                      CovidStateOut="E"

             for contactId in CP.loc[i,'VisitsContacts']:
                 if (CovidState=="I") and (CP.loc[contactId, 'CovidState'] =='S'):
                     if random.random()<ModelParams['CovidInfectionRate']:
                         CP.loc[contactId, 'CovidState'] ='E'
                         
                         
    return [CovidStateOut, FluStateOut]


#This function computes random infection rate for a pool
#Input:
# N: number of people
# NI: number of infected
# M: random contacts number
# p: probability of infection on meeting
def InfectRate(N,NI, M, p):
    return NI*M*p/N


#This function updates the Covid Positive Counts for neighborhoods
def updateCountNeighborhood(CD, i):
    return CP.loc[(CP['locality'].isin(CD.loc[CD['locality_id']==i+1].locality_neighbors.values[0].split(", "))) & \
                                 (CP['CovidState']=='I') ].shape[0] 
        
#This function updates the Covid Positive Counts for hotspots
def updateCountHotspot(i):
        return CP.loc[(CP['Visits']==i) & (CP['CovidState']=='I')].shape[0]



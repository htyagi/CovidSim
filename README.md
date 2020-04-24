# CovidSim: An agent based simulator for COVID-19 testing and policy interventions

This library for Python 3 provides an agent based simulation for COVID-19 evolution in a city. The city is divided into various localities
and agents are distributed across localities in proportion to population densities. Each agent has a COVID state which evolves according to an SEIR model. There is also another Flu state corresponding to a flu with similar symptoms as COVID-19 which evolves according to an SI model. In addition, agents interact with other agents in their neighbourhood and across localities. When an agent in COVID state S meets another agent in  COVID state I, its COVID state updates to I with some probability, thereby infecting the former agent. In the current version, the interaction across localities is based a single OD matrix for traffic flow across the city. 

Along with state evolution for the health of the population, this simulator integrates testing policies (such as contact tracing) as well as policy interventions (such as Lockdown). A testing policy chooses which agent to test. It can use observable features such as if an agent is symptomatic or not, but, obviously, cannot rely on the COVID state of an agent. An intervention policy can rely on the entire testing history. 

**Dependencies**

- Python 3
- geopandas 
- pandas 
- scipy 
- numpy 
- pickle 
- sys 
- functools 
- multiprocessing 
- timeit 
- random


**Main modules**

1. evolution.py: This module contains functions governing the state evolution model.

2. tests.py: This module contains functions that enable testing and the testing policies that we have implemented.

3. interventions.py: This module contains functions enabling interventions and the intervention policies that we have implemented.

**How do we store the state of the city**

1. CP (short for City Population): This pandas dataframe maintains the entire state of the city, including health of each agent and its permanent list of contacts. It can be accessed by tests as well as intervention policies. A row of CP is an agent and a column is an attribute, e.g., "id". 

2. TestingHistory: This is a numpy array which maintain the test status of each agent (row) on each day (column). Agents that test positive on a day are marked +1, those that test negative are marked -1, and those that are not tested are marked 0.

3. InterventionHistory: This is a list which contains all the interventions applied till date.


**Some important functions**

1. simulate(): this is the main simulation function inside evolution.py. It calls updateState to evolve the state of each agent by one day, calls testingPolicy to apply tests on population, and calls interventionPolicy to obtain a list of interventions. 

2. updateState(): this function is inside evolution.py and updates the state of each agent by one day. It uses the list of interventions and accesses the function InterventionRule inside interventions.py to interpret the interventions active on that day. 


**A good starting point to understand the flow of code**

Execute the file exampleRST-Quarantine.py, which runs a simulation for 100 days for 100 000 people, to understand the flow of our code. We summarize the flow below:

1. It first uses setupcitydata() from inoutfuncs.py to read data from city.geojson and car-prob.csv. Then, it sets all the parameters of simulation and calls simulate() from evolution.py.

2. simulate() calls function Initialize() to initialize the population state CP. Then, it calls InitInfection() to infect an initial seed of agents. 

3. simulate() starts daily simulation and calls interventionPolicy() to determine the list of interventions active on that day.

3. simulate() calls updateState() for each agent using multiple cores, collects all the outputs, and updates CP.

4. simulate() calls testingPolicy() which applies tests to agents and records the results in TestingHistory.


**Making the code work for your own data with your own interventions and testing policies**

While the simulator has been designed for general purpose use, in its current form it is tied closely to our own data. If you would like to modify our code to handle your own data, note the following points.

1. The Initialize() function inside evolution.py is custom made for city.geojson. You should replace this function with your own version and output CP with the same column names. 

2. Testing policies are not allowed to use COVID state and Flu state, but we have made these states available to testing policies through CP. Care must be taken to not use this information -- only observable one can use is if an agent is infected with COVID or Flu. In a later version, we will limit the information available to testing policies to only the observables.

3. Intervention policies may need to maintain a state for the population. For instance, quarantine requires recording of the day on which a particular agent was put under quarantine. In this version, we store this status in the same data frame CP. Any other feature for agents that you need for your custom made intervention can be added to CP.

**!!A caution!!**

***Changing the number of cores used by multiprocessing.pool() in the simulate() function will change the dynamics of the simulation itself and will give very different results. For fair comparison, fix the number of cores across all your simulation runs.***


That's all you need. ENJOY!

Ah, one more thing. If you have queries, feel free to **contact us** at {aditya,htyagi}@iisc.ac.in.

**Contributors** 

- Aditya Gopalan (Indian Institute of Science)
- Himanshu Tyagi (Indian Institute of Science)

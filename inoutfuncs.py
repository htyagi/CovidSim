import geopandas as gpd
import pandas
import matplotlib.pyplot as plt
import csv
import numpy as np

#Read Bangalore data
def setupcitydata(citygeojson, trafficcsv):
    city=gpd.read_file(citygeojson)

    #Add Neigbors
    for index, row in city.iterrows():  
        neighbors = city[city.geometry.touches(row['geometry'])].wardName.tolist() 
        city.at[index, "locality_neighbors"] = ", ".join(neighbors)

    density = city['POP_TOTAL']/sum(city['POP_TOTAL'])
    city['locality_density']=density

    CD = city[['locality_density', 'geometry', 'locality_neighbors']]
    CD = CD.assign(locality_name=city['wardName'])
    CD = CD.assign(locality_id=city['wardNo'].astype(int))

    CD=CD.sort_values(by=['locality_id'], ignore_index=True)

    CarProb=[]

    with open(trafficcsv, 'r') as file:
        data =list(csv.reader(file, delimiter=','))

        CarProb = np.array(data[0:], dtype=np.float)

    print("City Data setup complete")

    return CD, CarProb





#Plotting function
#Input
# CovidCases:gives locality-wise spread of the population matrix, obtained as an output from simulation
# TestingHistory: Day-wise testing history with
#                 +1 for positive and -1 for negative, 0 for not tested
def plotresults(CovidCases, TestingHistory):
    NumSteps=TestingHistory.shape[1]
    evolutionCases = [sum(CovidCases.values())[j] for j in range(NumSteps)]
    evolutionTests = [np.sum(  TestingHistory[TestingHistory[:,j] > 0, j]  )    for j in range(NumSteps)]

    plt.plot(evolutionCases)
    plt.ylabel('Number of Covid Cases')
    plt.xlabel('Day number')
    plt.grid(True)
    
    plt.figure()
    plt.plot(evolutionTests)
    plt.ylabel('Number of Covid Positive Tests')
    plt.xlabel('Day number')
    plt.grid(True)
    plt.show()



#Intervention Policies
#Interventions allowed: None, LockAll, LockCommute

import numpy as np

#Interpretting the interventions for the updateState function
#Should be elaborating for every new intervention

def InterventionRule(interventions, CP, i):
    localspread=True
    globalspread=True
    QuarantineDuration=10
    if 'LockAll' in interventions:
        localspread=False
        globalspread=False
    elif 'LockCommute' in interventions:
        globalspread=False   
    elif ('Quarantine' in interventions) and (CP.loc[i,'quarantine']==1):
        if i<CP.loc[i,'quarantineDay']+QuarantineDuration:
            localspread=False
            globalspread=False

    return localspread, globalspread


#A simple intervention example: LockCommute on even days
def InterventionEvenOdd(TestingHistory, InterventionsHistory, CP, day):
    if np.mod(day,2)==0:
        return ['LockCommute']
    else:
        return ['None']
    
#LockCommute when the slope of positive tests goes over a threshold
def InterventionLockdown(TestingHistory, InterventionsHistory, CP, day):
    #Threshold the percentage change in the running window sum
    threshold = 0.5 #Slope 1/2
    changeTime=10
    window=8
    normalizedChange= sum([np.sum(TestingHistory[TestingHistory[:,day-j]>0, day-j]) \
                           -  np.sum(TestingHistory[TestingHistory[:,day-changeTime-j]>0, day-changeTime-j]) \
             for j in range(min(window, day+1-changeTime))])/(window*changeTime)
    print('Slope='+str(normalizedChange))

    if day>=1:
        if normalizedChange>threshold or ('LockAll' in InterventionsHistory[day-1]):
            return ['LockAll']
        else:
            return ['None']
    else:
        return ['None']

#LockCommute for a constant number of days when the slope of positive tests goes over a threshold
def InterventionLockdownFixed(TestingHistory, InterventionsHistory, CP, day):
    #Threshold the percentage change in the running window sum
    threshold = 0.5 #Slope 1/2
    changeTime=10
    window=8
    duration=14
    normalizedChange= sum([np.sum(TestingHistory[TestingHistory[:,day-j]>0, day-j]) \
                           -  np.sum(TestingHistory[TestingHistory[:,day-changeTime-j]>0, day-changeTime-j]) \
             for j in range(min(window, day+1-changeTime))])/(window*changeTime)
    print('Slope='+str(normalizedChange))

    flag=0
    startDate=100
    
    for i in range(day):
        if flag==0 and ('LockAll' in InterventionsHistory[i]):
          flag=1

    if flag==1:
        i=1
        while not (('LockAll' in InterventionsHistory[day-i]) and (not('LockAll' in InterventionsHistory[day-i-1]))):
            i=i+1
        startDate=day-i+1    
          
    if day>=1:
        if normalizedChange>threshold or ((day<=startDate+duration) and (flag==1)):
            return ['LockAll']
        else:
            return ['None']
    else:
        return ['None']

    
#No intervention
def InterventionNone(TestingHistory, InterventionsHistory, CP, day):
    return []
    
def InterventionQuarantine(TestingHistory, InterventionsHistory, CP, day):
        
    for i in range(TestingHistory.shape[0]):
        if TestingHistory[i,day]==1:
            QuarantineList= CP.loc[i,'LocalContacts']+CP.loc[i,'VisitsContacts']+[i]
            for j in QuarantineList:
                CP.loc[j, 'quarantine']=1
                CP.loc[j, 'quarantineDay']=day
            
    return ['Quarantine']


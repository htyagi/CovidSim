import pandas
import random
import numpy as np

# ===================================================================================
#The test function denoting individual tests
def test(CovidState, i,  FalseNegativeProb):
    if CovidState == 'I':
        if random.random()<(1-FalseNegativeProb):
            return 1
    else:
        return 0

# ===================================================================================    
# return a list of all symptomatic individuals in locality index locidx, thinned down by reportProb
def getSymptomatic(CP, locidx, reportProb=1.0):
    Symptomatic = CP.loc[ (CP["localityIndex"]==locidx) & \
    ((CP["CovidState"]=="I") | (CP["FluState"]=="I")) & (CP['CovidPositive']==0) ]
    return [i for i in Symptomatic["id"] if random.random() < reportProb]

# ===================================================================================
#Tests a constant fraction of people with symptoms chosen randomly
def RandomSymptomaticTesting(TestingBudget, FalseNegative, LocationRepProb, CP, TestingHistory, day):
    toTest=[]
    for i in range(len(LocationRepProb)):
        toTest+=getSymptomatic(CP, i+1, LocationRepProb[i])
    
    if TestingBudget<=len(toTest):
        finalList=random.sample(toTest, TestingBudget)
    else:
        finalList=toTest

    for i in finalList:        
        if test(CP.loc[i, "CovidState"], i, FalseNegative)==1:
            TestingHistory[i,day]=1
            CP.loc[i,'CovidPositive']=1
            CP.loc[i,'quarantine']=1
            CP.loc[i,'quarantineDay']=day
        else:
            TestingHistory[i,day]=-1


# ===================================================================================
#Contact tracing: Uses a part of testing budget for contact tracing
def ContactTracing( TestingBudget, FalseNegative, LocationRepProb, CP, TestingHistory, day):
    
    ContactList = []

    
    for i in range(TestingHistory.shape[0]):
        if TestingHistory[i, day-1]==1 or TestingHistory[i,day-2]==1:
            ContactList+= CP.loc[i, 'LocalContacts'] + CP.loc[i, 'VisitsContacts']
            #ContactList+= [CP.loc[j,'id'] for j in range(CP.shape[0]) if i in CP.loc[j, 'LocalContacts'] or i in CP.loc[j, 'VisitsContacts']]

    ContactsToTest= CP.loc[(CP.index.isin(ContactList)) & \
                          (((CP["CovidState"]=="I") | (CP["FluState"]=="I"))&(CP['CovidPositive']==0))]

    symptomatic=[]
    for i in range(len(LocationRepProb)):
        symptomatic+=getSymptomatic(CP, i+1, LocationRepProb[i])

    

    
    if ContactsToTest.shape[0]<TestingBudget: 
        if (TestingBudget- ContactsToTest.shape[0])< len(symptomatic):
            toTest = list(ContactsToTest['id'])+random.sample(symptomatic, TestingBudget-ContactsToTest.shape[0])                        
        else:
            toTest = list(ContactsToTest['id'])+symptomatic
    else:
        toTest = list(ContactsToTest.sample(n=TestingBudget)['id'])

    for i in toTest:
        if test(CP.loc[i, "CovidState"], i, FalseNegative)==1:
            TestingHistory[i,day]=1
            CP.loc[i,'CovidPositive']=1
            CP.loc[i,'quarantine']=1
            CP.loc[i,'quarantineDay']=day
        else:
            TestingHistory[i,day]=-1


# ===================================================================================
# LocBasedTesting: A testing policy with importance based on spatial location and place visited


# output a list of people who should be tested
def getTestTargets(TestingBudgetSymptomatic, TestingBudgetContact, ReportingProbs, \
    LocalityToVisitsRatio, CP, TestingHistory, visitinfeclevels, wardinfeclevels, Day, UniformSampling=False):
    FinalList = []
    # contact tracing part: test (symptomatic) neighbours of everyone who tested +ve in the previous round
    ContactTracedTargets = []
    if Day > 0:
        ContactTracedTargets=[]
        if TestingBudgetContact > 0:
            for i in range(TestingHistory.shape[0]):
                if TestingHistory[i][Day-1]==1:
                    ContactTracedTargets = ContactTracedTargets+ \
                    [contact for contact in CP.loc[i]["LocalContacts"] \
                     if ((CP.loc[contact]["CovidState"] == "I")|(CP.loc[contact]["FluState"] == "I") & (CP.loc[contact]['CovidPositive']==0) )\
                    ] 
            ContactTracedTargets = list(set(ContactTracedTargets))
            if TestingBudgetContact<len(ContactTracedTargets):
                ContactTracedTargets = np.random.choice(ContactTracedTargets, size=TestingBudgetContact, replace=False)

    # symptomatic testing part
    SymptomaticPeople = [item for sublist in [ getSymptomatic(CP, j+1, ReportingProbs[j]) \
    for j in range(len(ReportingProbs)) ]\
     for item in sublist]
    SymptomaticPeopleSelected = []
    if SymptomaticPeople:
        SelectionWeights = visitinfeclevels[CP.loc[SymptomaticPeople]["Visits"]] + LocalityToVisitsRatio * wardinfeclevels[CP.loc[SymptomaticPeople]["localityIndex"]-1]  
        if UniformSampling:
            SelectionWeights = np.ones(SelectionWeights.shape[0])

        if not np.any(SelectionWeights):
            SymptomaticPeopleSelected = list(np.random.permutation(SymptomaticPeople)[:TestingBudgetSymptomatic])
        else:
            ReqdSize = min(TestingBudgetSymptomatic, len(SelectionWeights))
            SupportSize = np.sum(SelectionWeights > 0)
            SymptomaticPeopleSelected = list(np.random.choice(SymptomaticPeople, size=min(ReqdSize, SupportSize), replace=False, p=SelectionWeights/np.sum(SelectionWeights)))  

    FinalList = list(set(ContactTracedTargets + SymptomaticPeopleSelected))
    return FinalList, len(ContactTracedTargets), len(SymptomaticPeopleSelected) 


# update "infectedness" of localities and visiting places
def getPlacesInfectedness(VisitingPlaceInfectiousnessPerPerson, \
        WardInfectiousnessPerPerson, Epsilon, CP, TestingHistory, Day):

    NumPlacesVisit = len(pandas.unique(CP["Visits"].values))
    NumLocations = len(pandas.unique(CP["localityIndex"].values))

    VisitingPlacesInfectedness = np.zeros(NumPlacesVisit)
    WardsInfectedness = np.zeros(NumLocations)

    for PrevDay in range(Day+1):
        CurrentVisitingPlacesInfectedness = np.zeros(NumPlacesVisit)
        CurrentWardsInfectedness = np.zeros(NumLocations) 
        FreshlyTestedPositive = []
        if PrevDay > 0:
            FreshlyTestedPositive = np.where(TestingHistory[:, PrevDay-1] > 0)
        for i in FreshlyTestedPositive:
            CurrentVisitingPlacesInfectedness[CP.loc[i]["Visits"]] += VisitingPlaceInfectiousnessPerPerson # CP.loc[i]["Visits"] takes values 0 ... NumPlacesVisit (last one is dummy)
            CurrentWardsInfectedness[CP.loc[i]["localityIndex"]-1] += WardInfectiousnessPerPerson # CP.loc[i]["localityIndex"] takes values 1 ... NumLocations    
        VisitingPlacesInfectedness = (1.0 + Epsilon)*VisitingPlacesInfectedness + CurrentVisitingPlacesInfectedness
        WardsInfectedness = (1.0 + Epsilon)*WardsInfectedness + CurrentWardsInfectedness
    
    # Visits = max value is a "dummy place", so zero out its infectiousness level
    VisitingPlacesInfectedness[-1] = 0.0

    return VisitingPlacesInfectedness, WardsInfectedness


def LocBasedTesting(TestingBudgetSymptomatic, TestingBudgetContact, ReportingProbs, \
    VisitingPlaceInfectiousnessPerPerson, WardInfectiousnessPerPerson, LocalityToVisitsRatio, Epsilon, \
        falsenegprob, CP, TestingHistory, day):    

    VisitPlacesInfecLevels, WardInfecLevels = getPlacesInfectedness(VisitingPlaceInfectiousnessPerPerson, \
        WardInfectiousnessPerPerson, Epsilon, CP, TestingHistory, day)
 
    toTest, numContactTrac, numSympt=getTestTargets(TestingBudgetSymptomatic, TestingBudgetContact, \
        ReportingProbs, LocalityToVisitsRatio, CP, TestingHistory, VisitPlacesInfecLevels, \
        WardInfecLevels, day)
    numPositive = 0
    WhoPositive = []
    for i in toTest:
        if test(CP.loc[i, "CovidState"], i, falsenegprob)==1:
            numPositive = numPositive + 1
            WhoPositive.append(i)
            TestingHistory[i,day]=1
            CP.loc[i,'CovidPositive']=1
            CP.loc[i,'quarantine']=1
            CP.loc[i,'quarantineDay']=day
        else:
            TestingHistory[i,day]=-1
    # debug:
    # print("LocBasedTesting: Tested: {cont:3d} contacts, {symp:3d} symptomatic, \
    #     {pos:3d} +ve with Visits=".format(cont=numContactTrac, symp=numSympt, pos=numPositive ) \
    #         + str([CP.loc[i, "Visits"] for i in WhoPositive ] )  )



# ===================================================================================

import numpy as np

class Apparatus:
    def __init__(self,name,type,station,time,stat,loc,fire_hr,ems_hr):
        self.name = name
        self.type = type
        self.station = station
        self.next_time = time
        self.status = stat
        self.location = loc
        self.fires_per_hr = fire_hr
        self.ems_per_hr = ems_hr
        self.incident = None
        self.history =[]
    def status_update(self,newstat):
        # set status of the apparatus
        self.status=newstat
        return self.status
    def next_update(self,cost):
        # set when next update will occur
        self.next_time = cost
        return self.next_time
    def next_loc(self,new_loc):
        #set next location
        self.location=new_loc
        return self.location
    def next_inc(self,new_inc):
        #set next incident
        self.incident = new_inc
        return self.incident
    def track(self):
        #track everything
        self.history.append([self.incident,self.next_time,self.status,self.location])
        return self.history

class Station:
    def __init__(self,station,loc):
        self.station = station
        self.location = loc
        self.apparatus = []
    def assign_apparatus(self,app):
        #assign apparatus to station
        self.apparatus.append(app)
        return self.apparatus

class Incident:
    ## 0-> unit not assigned/pending
    ## 1-> unit assigned
    def __init__(self,unique,inctype,utypes,needed,state,loc,time,unit):
        self.incino = unique
        self.code = inctype
        self.time_occurred = time
        self.units_types = np.array(utypes)
        self.number_needed = np.array(needed)
        self.status = state
        self.location = loc
        self.units_assigned = []
    def reduce(self,apptype):
        # reduce number of apparatus needed
        which = np.where(self.units_types==apptype)[0]
        self.number_needed[which]+= -1
    def increase(self,apptype):
        # increase number of apparatus needed
        which = np.where(self.units_types==apptype)[0]
        self.number_needed[which]+= 1
    def assign_unit(self,unit):
        self.units_assigned.append(unit)
        return self.units_assigned



#
# event = Incident('fire')

###########################
######### testing #########
# stop
# # coming from file
# units_name =['E1','E2','E3']
# units_type = ['eng','eng','eng']
# units_stat = ['S1','S2','S3']
# units_initloc =[1,2,3]
#
# #initialize units
# l1  = [[units_name[x],units_type[x],units_stat[x],1558621015,'available',units_initloc[x]] for x in range(len(units_name))]
# du   = {l1[x][0]:Apparatus(l1[x][0],l1[x][1],l1[x][2],l1[x][3],l1[x][4],l1[x][5]) for x in range(len(units_name))}
# #initialize stations
# ds = {units_stat[x]:Station(units_stat[x]) for x in range(len(units_stat))}
# for u in du:
#     for ss in ds:
#         if  du[u].station == ds[ss].station: ds[ss].assign_apparatus(du[u].name)
#
# ## start
# # global variables
# needfire = ['eng']
# needems = ['amb']
# nfires = 3
# nems = 1
# needtot = [x for x in needfire for n in range(nfires)] + [x for x in needems for n in range(nems)]
# for n in nfires:
#     inci_count += 1
#     inci_no = 'N'+inci_count
#
#
#



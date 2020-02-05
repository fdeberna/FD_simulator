import pandas as pd
import numpy as np
from scipy.stats import poisson as ps
from c_Apparatus import *
import random

def locations_details(locf,odmf):
    #read locations and OD cost matrix file
    locs = pd.read_csv(locf)
    odm = pd.read_csv(odmf)
    return locs,odm

def time_details(start_time,end_time):
    # start/end date of simulation in unix epoch
    start_hour = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
    start = start_time.value/1e9
    end   = end_time.value/1e9
    return start,end,start_hour

def incidents(lambdas):
    # return number of calls arriving per each lambdas
    return np.random.poisson(lam=lambdas)

#
# def incidents_cleared(loc,place):
#     # return probability of call cleared per each us
#     return np.random.random() < ps.pmf(1, loc[loc.locations == place].us)

def p_terminating(unit_name,tres):
    #probability of terminating service of 1 customer in the second, for given term_rate (aka us)
    inc_type = di[du[unit_name].incident].code
    term_rate=0.
    if inc_type=='rate_ems': term_rate = du[unit_name].ems_per_hr/3600
    if inc_type=='rate_fire': term_rate = du[unit_name].fires_per_hr/3600
    return np.random.random() <  (ps.pmf(1,term_rate*tres))#/(ps.pmf(0,loc[loc.locations == place].us*tres)+ps.pmf(1,loc[loc.locations == place].us*tres)))[0]

def search_radius(location,radius):
    # returns cost-matrix indices which are on given radius around given location
    if radius<cm[(cm.start==location)].cost.min():#radius<cm.cost.min():
        # if radius too small, didn't move
        sr = cm[(cm.start==location)*(cm.end==location)]
    else:
        sr= cm[(cm.start==location)*((cm.cost-radius)<=0)]
        #ValueError:
    return sr[sr.cost == max(sr.cost)].index.tolist()

def assign_units(du,this,now,units_engaged,enr_a=0,std_enr=0):
    type_needed = this.units_types[this.number_needed > 0]
    # loop on needed units
    for s in type_needed:
        #look for available units, if any
        ll = [t for t in du.keys() if du[t].type==s and (du[t].status=='available' or du[t].status=='available-in station')]
        # if the unit is just "available" find where it is:
        for u in ll:
            if du[u].status == 'available':
                radius_from_station = du[u].next_time-now
                radius_from_previousincident = now - du[u].history[-1][1]
                rad_stat = search_radius(ds[du[u].station].location,radius_from_station)
                rad_inc = search_radius(di[du[u].incident].location, radius_from_previousincident)
                intersect = [cm.loc[x].end for x in rad_stat for y in rad_inc if cm.loc[x].end == cm.loc[y].end]
                if intersect:
                    du[u].location = random.choice(intersect)
                else:
                    # in case of empty intersection, pick closest couple of points
                    # this is direction dependent: this goes from incident to station because station is the destination
                    candidates = [[x, cm[(cm.start == x) * (cm.end == ds[du[u].station].location)].cost.item()] for x in
                                  cm.loc[rad_inc].start.tolist()]
                    a_min = min(x[1] for x in candidates)
                    du[u].location = random.choice([x[0] for x in candidates if x[1] == a_min])
        # for units available or available-on scene, assign
        if len(ll)>0:
            while this.number_needed[this.units_types==s].sum() >0 and len(ll)>0:
                #look for closest unit available
                alldist = [cm[(cm.start == du[uu].location) * (cm.end == this.location)].cost.item() for uu in ll]
                # break ties by sending back first-due unit to its station if it's the case
                tie_breaker = [ll[x] for x in range(len(ll)) if (alldist[x]==np.sort(alldist)[0] and ds[du[ll[x]].station].location == this.location) ]
                t = 0 # zeroed to make sure it's not wrongly reassigned
                if len(tie_breaker)>0:
                    # print(tie_breaker,this.location)
                    t = tie_breaker[0]
                else:
                # else look for the unit whose station is closest to location
                    stat_dist = [cm[(cm.start == ds[du[uu].station].location) * (cm.end == this.location)].cost.item() for uu in ll]
                    t = ll[np.argsort(stat_dist)[0]]
                    # print(this.location,np.sort(stat_dist)[0])
                du[t].next_inc(this.incino)
                du[t].next_update(now)
                units_engaged.append(t)
                previous = du[t].status
                du[t].status_update('dispatched')
                du[t].track()
                this.assign_unit(t)
                if enr_a+std_enr !=0 and previous == 'available-in station':
                    du[t].next_update(now + round(np.random.normal(enr_a,std_enr)))
                else:
                    # print(t,'not in station - immediate enroute')
                    du[t].next_update(now + time_resol)
                # remove unit from available ones
                ll.remove(t)
                this.reduce(s)
                # du[ll[np.argsort(alldist)[0]]].next_loc(this.location)
                if this.number_needed.sum()==0: this.status = 1
    return this,units_engaged

def assign_pending_incidents(pending_inc):
    removed = []
    u_engaged = []
    for l in pending_inc:
        enroute_aver = 0.#loc[loc.locations == di[l].location].rate_enroute.item()
        enroute_stdev = 0.#loc[loc.locations == di[l].location].stdev_enroute.item()
        di[l], u_engaged = assign_units(du, di[l], time,u_engaged,enroute_aver,enroute_stdev)
        if di[l].status == 1: removed.append(l)
    for x in removed: pending_inc.remove(x)
    return pending_inc,u_engaged

def new_calls(calls,di,inci_count,this_time):
    u_engaged=[]
    index_shuffle = list(range(len(calls[0])))
    random.shuffle(index_shuffle)
    # assign calls, loop on types
    for t_index in range(len(calls)):
        # loop on location of incidents
        for loc_index in index_shuffle:#range(len(calls[t_index])):
            # loop on actual incidents
            newincs = 1
            while newincs <= calls[t_index][loc_index]:
                # print(newincs,calls[t_index][loc_index])
                inci_count += 1
                inci_no = 'I' + str(inci_count)
                # print(inci_no,inci_no, cols_rates[t_index], resp_mod[cols_rates[t_index]][0],resp_mod[cols_rates[t_index]][1], 0, all_locations[loc_index],[],this_time)
                this_inc = Incident(inci_no, cols_rates[t_index], resp_mod[cols_rates[t_index]][0],
                                    resp_mod[cols_rates[t_index]][1], 0, all_locations[loc_index],this_time,[])
                enroute_aver = loc[loc.locations==this_inc.location].rate_enroute.item()
                enroute_stdev = loc[loc.locations == this_inc.location].stdev_enroute.item()
                this_inc, u_engaged = assign_units(du, this_inc, time,u_engaged,enroute_aver,enroute_stdev)
                di.update({inci_no: this_inc})
                if this_inc.status == 0: pending_inc.append(inci_no)
                newincs += 1
    return pending_inc,u_engaged,di,inci_count

def unroller(dfn,incnum,unitid,rolledc,rolledatt):
# create temporaty id (unit ID + incident number)
    dfn['inc_temp'] = dfn[incnum] + dfn[unitid]
    rc = list(dfn[rolledc].unique())
    dfred = dfn[['inc_temp',rolledc,rolledatt]]
    dfcomp = dfn.drop([rolledc,rolledatt],axis=1)
    dfcomp = dfcomp.groupby('inc_temp').first().reset_index()
    a = dfred[dfred[rolledc] ==rc[0]].reset_index()
    for r in rc[1::]:
        b = dfred[dfred[rolledc] == r].reset_index()
        a = a.set_index('inc_temp').join(b[['inc_temp', rolledc, rolledatt]].set_index('inc_temp'), lsuffix=rc[0],rsuffix=r, how='outer')
        a = a.reset_index()
        if r != rc[0]: a = a.rename(columns={rolledatt: rolledatt + str(r)})
    a = a.set_index('inc_temp').join(dfcomp.set_index('inc_temp'),lsuffix=' ', rsuffix=' ', how='inner')
    a = a.reset_index()
    cr = [x for x in a.columns if x.startswith(rolledc)]
    try:
        remcol = cr + ['inc_temp','index']
        a = a.drop(remcol,axis=1)
    except:
        try : a.drop(['inc_temp','index'])
        except:
            pass
    return a


def cad_formatter(du):
    cad = []
    for unit in du.keys():
        if du[unit].history:
            for items in du[unit].history:
                cad.append([unit]+items+[items[3] if items[2]=='dispatched' else '-']+[di[items[0]].location]+[di[items[0]].code.replace('rate_','')])
    cad_file = pd.DataFrame.from_records(cad,columns=['Unit','Incident_ID','Time','Event','Location_aux','Unit_location_at_dispatch','Incident_location','Inc_type'])
    cad_standard_form = unroller(cad_file, 'Incident_ID', 'Unit', 'Event', 'Time')
    cad_standard_form = cad_standard_form[
        ['Incident_ID','Inc_type', 'Unit', 'Unit_location_at_dispatch','Incident_location', 'Timedispatched', 'Timeenroute', 'Timeonscene', 'Timeavailable',
         'Timeavailable-in station']]
    cad_standard_form['travel'] = cad_standard_form['Timeonscene'] - cad_standard_form['Timeenroute']
    cad_standard_form['dispatched_to_available'] = cad_standard_form['Timeavailable'] - cad_standard_form[
        'Timedispatched']
    cad_standard_form['dispatched_to_instation'] = cad_standard_form['Timeavailable-in station'] - cad_standard_form[
        'Timedispatched']
    cad_standard_form = cad_standard_form.rename(
        columns={'Timedispatched': 'dispatched', 'Timeenroute': 'enroute', 'Timeonscene': 'arrived',
                 'Timeavailable': 'available', 'Timeavailable-in station': 'in_station'})
    cad_standard_form['dispatched'] = cad_standard_form['dispatched'].apply(lambda x: pd.to_datetime(x * 1e9))
    cad_standard_form['enroute'] = cad_standard_form['enroute'].apply(lambda x: pd.to_datetime(x * 1e9))
    cad_standard_form['arrived'] = cad_standard_form['arrived'].apply(lambda x: pd.to_datetime(x * 1e9))
    cad_standard_form['available'] = cad_standard_form['available'].apply(lambda x: pd.to_datetime(x * 1e9))
    cad_standard_form['in_station'] = cad_standard_form['in_station'].apply(lambda x: pd.to_datetime(x * 1e9))
    cad_standard_form = cad_standard_form.sort_values(['dispatched','Incident_ID'])
    return cad_standard_form




def print_history(x):
    for l in du[x].history:
        print(l)

##### things to do
#- force check on lambda/us units
#- enable csv/excel
#- test multiple units and different unit types per station
#- enable varying lambda,us
#-expand Incident class
####
######
##### from input
f1= 'DC_real_cost_matrix.csv'#'simulated_inputs\\fake_cm_dc.csv'
f2 = 'DC_real_locations_rates.csv'#'simulated_inputs\\test_locations_DClike.csv'
ratesfile = 'daily_rates.csv'
response_model = 'response_model.csv'
ufile = 'Units_DC_real.csv'
s1 = '1/1/2018 12:00:00'
s2 = '1/1/2018 13:00:00'
cols_rates=['rate_ems','rate_fire']
min_travel_allowed = 30 # seconds

# time steps for simulation (seconds)
time_resol = 1

daily_rates = pd.read_csv(ratesfile)
units_read = pd.read_csv(ufile)
units_name = units_read.Unit.tolist()
units_type = units_read.Type.tolist()
units_stat = units_read.Station.tolist()
stat_loc = units_read.station_location.tolist()
units_initloc =units_read.initial_location.tolist()
fire_clear_perhr = [1./(x/3600) for x in units_read.average_time_on_service_fire_seconds]
ems_clear_perhr  = [1./(x/3600) for x in units_read.average_time_on_service_ems_seconds]
stats = units_read.Station.unique().tolist()

# dictionaries for daily fire and ems rates
# fire_rates_hr = dict([(x,daily_rates[daily_rates.hour==x]['rate_fire'].item()) for x in range(len(daily_rates))])
# ems_rates_hr = dict([(x,daily_rates[daily_rates.hour==x]['rate_ems'].item()) for x in range(len(daily_rates))])

# units_name =['E1','E2','E3','A1','A2','A3']
# units_type = ['eng','eng','eng','amb','amb','amb']
# units_stat = ['S1','S2','S3','S1','S2','S3']
#  [1,2,3,1,2,3]
# stats  = ['S1','S2','S3']


####
#######
##### ACTUAL START ########
# load locations, times, response model
loc,cm = locations_details(f2,f1)
all_locations = loc.locations.tolist()
start,end,start_hour = time_details(pd.to_datetime(s1),pd.to_datetime(s2))
t1 = start - start_hour

model = pd.read_csv(response_model)
#initialize units
l1  = [[units_name[x],units_type[x],units_stat[x],start,'available-in station',units_initloc[x],fire_clear_perhr[x],ems_clear_perhr[x]] for x in range(len(units_name))]
du   = {l1[x][0]:Apparatus(l1[x][0],l1[x][1],l1[x][2],l1[x][3],l1[x][4],l1[x][5],l1[x][6],l1[x][6]) for x in range(len(units_name))}
#initialize stations
ds = {units_stat[x]:Station(stats[x],stat_loc[x]) for x in range(len(stats))}
for u in du:
    for ss in ds:
        if  du[u].station == ds[ss].station:ds[ss].assign_apparatus(du[u].name)

#response model
resp_mod = {x:[list(np.unique(units_type)),[int(model[model.Incident_Type==x][y]) for y in np.unique(units_type)]] for x in model.Incident_Type}
# count type of calls
call_type = dict({int(x):cols_rates[x] for x in range(len(cols_rates))})
###### -----------------------------------------------------
####################################
# for testing only
# calls = [([0, 0, 1]), ([0, 0, 0])]
# inci_count = 0
# t_index = 0
# loc_index = 2
# inci_count+=1
# inci_no = 'I'+str(inci_count)
# this_inc = Incident(inci_no,cols_rates[t_index],resp_mod[cols_rates[t_index]][0],resp_mod[cols_rates[t_index]][1],0,all_locations[loc_index])
#------ assign units ------#
# now = time
# locs = all_locations[loc_index]
# type_needed = this_inc.units_types[this_inc.number_needed > 0]
# s = type_needed[0]
# this_inc.number_needed[this_inc.units_types==s].sum() >0
# ll = [t for t in du.keys() if du[t].type==s and du[t].status=='available']
# alldist = [cm[(cm.start == du[uu].location) * (cm.end == locs)].cost.item() for uu in ll]
# du[ll[np.argsort(alldist)[0]]].status_update('dispatched')
# du[ll[np.argsort(alldist)[0]]].next_update(now + cm.cost[np.argsort(alldist)[0]])
# this_inc.reduce(s)
# du[ll[np.argsort(alldist)[0]]].next_loc(locs)
# du[ll[np.argsort(alldist)[0]]].next_inc(this_inc.incino)
# du[ll[np.argsort(alldist)[0]]].track()
#######
######-----------------------END TESTING-----------


pending_inc = []
di={}
time = start
all_units_engaged = []
inci_count = 0
general_counter =0
#calls = [([0, 0, 1]), ([1, 0, 0])]
#main time loop
# du['E2'].status_update('OOS')
import timeit

print('Starting Time Loop')
start0 = timeit.default_timer()
while time < end:
    # print(pd.to_datetime(time*1e9),len(di))
    if general_counter == int((end-start)/time_resol*0.1): print('The time is: ',pd.to_datetime(time*1e9),'10% time interval completed. ',len(di),' Incidents reported.')
    if general_counter == int((end-start)/time_resol*0.3): print('The time is: ',pd.to_datetime(time*1e9),'30% time interval completed. ',len(di),' Incidents reported.')
    if general_counter == int((end-start)/time_resol*0.6): print('The time is: ',pd.to_datetime(time*1e9),'60% time interval completed. ',len(di),' Incidents reported.')
    if general_counter == int((end-start)/time_resol*0.9): print('The time is: ',pd.to_datetime(time*1e9),'90% time interval completed. ',len(di),' Incidents reported.')
    ### First, attempt to assign pending incidents
    # start = timeit.default_timer()
    #determine hour of day and rates
    days = int((time - t1) / 86400)
    hour = int((time - t1 - 86400 * days) / 3600)
    pending_inc,u_engaged = assign_pending_incidents(pending_inc)
    # print(len(di), timeit.default_timer() - start)
    if u_engaged: all_units_engaged = all_units_engaged + u_engaged
    ### Then deal with new calls arriving
    #print('hour',hour,daily_rates[daily_rates.hour==hour]['rate_ems'].item()*loc['rate_ems'][0]/loc['rate_ems'].sum()*time_resol)
    calls = [incidents(daily_rates[daily_rates.hour==hour][x].item()*loc[x]/loc[x].sum()*time_resol) for x in cols_rates]
    #calls = [incidents(loc[x] *daily_rates[daily_rates.hour==hour][x].item()/daily_rates[x].sum()* time_resol) for x in cols_rates]
    #calls = [incidents(loc[x]*time_resol) for x in cols_rates]
    # if time == start : calls = [([0, 1, 0]), ([0, 0, 0])]
    # if time == start+1 : calls = [([0, 0, 0]), ([0, 0, 0])]
    # print('----func1')
    # start = timeit.default_timer()
    pending_inc,u_engaged,di,inci_count  = new_calls(calls,di,inci_count,time)
    # print(len(di),timeit.default_timer()-start)
    if u_engaged: all_units_engaged = all_units_engaged + u_engaged
    ### Check on dispatched units
    to_remove=[]
    startl = timeit.default_timer()
    all_units_engaged = np.unique(all_units_engaged).tolist()
    for dispu in all_units_engaged:
        checker1=0
        checker2=0
        if du[dispu].status == 'onscene':
            if p_terminating(dispu,time_resol) and di[du[dispu].incident].status:
                # if this incident is cleared, then clear all units on it
                # potentially can add some stagger - future versions
                for u_on_inc in di[du[dispu].incident].units_assigned:
                    du[u_on_inc].status_update('available')
                    du[u_on_inc].next_inc(du[u_on_inc].incident)
                    du[u_on_inc].next_update(time)
                    du[u_on_inc].track()
                    # this is when it's expected to station
                    travel_to_stat = cm[(cm.start==du[u_on_inc].location)*(cm.end==ds[du[u_on_inc].station].location)].cost.item()
                    # du[u_on_inc].next_update(time+np.random.normal(travel_to_stat,0.5*travel_to_stat))
                    du[u_on_inc].next_update(time + max(min_travel_allowed,np.random.normal(travel_to_stat, daily_rates[daily_rates.hour==hour].st_to_mean.item()*travel_to_stat)))
        elif du[dispu].next_time <= time and checker1 ==0:
            checker1+=1
            if du[dispu].status == 'dispatched':
                du[dispu].status_update('enroute')
                du[dispu].next_update(time)
                du[dispu].track()
                travel_time = cm[(cm.start==du[dispu].location)*(cm.end==di[du[dispu].incident].location)].cost.item()
                du[dispu].next_update(time+max(min_travel_allowed,np.random.normal(travel_time,daily_rates[daily_rates.hour==hour].st_to_mean.item()*travel_time)))####!!!! HERE SCATTER TRAVEL
                du[dispu].next_loc(di[du[dispu].incident].location)
                # print(dispu, du[dispu].location,di[du[dispu].incident].location,du[dispu].next_time)
            elif du[dispu].status == 'available':
                du[dispu].next_loc(ds[du[dispu].station].location)
                du[dispu].status_update('available-in station')
                du[dispu].next_update(time)
                du[dispu].track()
                to_remove.append(du[dispu].name)
        if du[dispu].status == 'enroute' and du[dispu].next_time <= time and checker2==0:
            checker2+=1
            du[dispu].next_loc(di[du[dispu].incident].location)
            du[dispu].status_update('onscene')
            du[dispu].next_update(time)
            du[dispu].track()
    for x in to_remove: all_units_engaged.remove(x)
    # print(len(all_units_engaged), timeit.default_timer() - startl)
    time = time + time_resol
    general_counter +=1
            # HERE DO STUFF
print('\n globaltime ', timeit.default_timer() - start0,'\n')

mycad = cad_formatter(du)

mycad = mycad.sort_values(['dispatched','Incident_ID'])
# first arriving onlyt
stop
mycad = mycad.sort_values('arrived')
mycadf= mycad.drop_duplicates('Incident_ID',keep='first')
t = mycadf[mycadf.Inc_type=='ems'].travel.dropna().as_matrix()


#2158 20 minutes
# print('A1')
# print_history('A1')
# print('E1')
# print_history('E1')
# print('A2')
# print_history('A2')
# print('E2')
# print_history('E2')
# print('A3')
# print_history('A3')
# print('E3')
# print_history('E3')
stop
# du['A1'].status = 'available'
# du['A3'].status = 'available'
####
#### NEED to CHECK VALUE ERROR in search_radius####


# neeed to get clause for "and" "or" in response model--- not really needed?
# introduce enroute scatter
# allow mechanism for first-due dispatches ----6
# Insert mechanism to "loose" incident not addressed within X time
# TOD DO: INTRODUCE ALS//BLS//STRFIREs scale? ---- 3
# mapping of incidents in zone ----4
# test call rate by hr ----5
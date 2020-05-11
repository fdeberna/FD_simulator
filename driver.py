import pandas as pd
import numpy as np
from scipy.stats import poisson as ps
import sys
sys.path.insert(0,r'D:\Users\fdebernardis\Projects\Python Scripts\BigSimulator')
sys.path.insert(0,r'D:\Users\fdebernardis\Projects\CAD_app')
import cad
from c_Apparatus import *
import random

#python -m cProfile -o driver_SantaMonica.prof driver_SantaMonica.py
#snakeviz driver_SantaMonica.prof


def arrive_order(df,atscene,id):
    df['order'] = 0.
    dfs = df.sort_values([id, atscene])
    dfm,dc=cad.to_mat(dfs)
#     Here split -> select fires only and engines only and run the order function
#     Here split 2->select ems and check order for all units
    dfor = cad.first_arriving_s(dfm,dc,'order',atscene,id)
    dataf_or = pd.DataFrame(dfor, columns=df.columns)
    return dataf_or

def bb(dataframe,disp,cleared,unitname,iid):
    dataframe[disp] = pd.to_datetime(dataframe[disp])
    dataframe[cleared] = pd.to_datetime(dataframe[cleared])
    dsecs = cad.unixt(dataframe,[disp,cleared])
    dsecs['bb_time']=0.
   # dsecs['Serv_Time']=0.
    dsecs = dsecs.sort_values([disp,cleared])
    #dsecs = dsecs.loc[dsecs[disp].dropna().index]
    #dsecs = dsecs.loc[dsecs[cleared].dropna().index]
    dm,dc = cad.to_mat(dsecs)
    arr = cad.b2b(dm,dc,unitname,disp+'_seconds',cleared+'_seconds',iid,'bb_time')
    bbdf = pd.DataFrame(arr,columns=dsecs.columns)
    return bbdf



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
    term_rate = du[unit_name].cleared_per_hr[inc_type] / 3600
    # if inc_type=='rate_ems': term_rate = du[unit_name].ems_per_hr/3600
    # if inc_type=='rate_fire': term_rate = du[unit_name].fires_per_hr/3600
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

def assign_units(du,this,now,units_engaged,use_fd,enr_a=0,std_enr=0):
    type_needed = this.units_types[this.number_needed > 0]
    # loop on needed units
    ll = []
    for s in type_needed:
        #look for available units, if any - if incident is BLS and no BLS transport is found, then look for ALS transport
        if use_fd: ll = [t for t in du.keys() if du[t].first_due == this.first_due and ((du[t].type==s or (du[t].type_ems==s and du[t].type!='transport') or du[t].type+'_'+du[t].type_ems == s)
                  and (du[t].status=='available' or du[t].status=='available-in station'))]
        if not ll or not use_fd: ll = [t for t in du.keys() if (du[t].type == s or (du[t].type_ems == s and du[t].type != 'transport') or du[t].type + '_' + du[t].type_ems == s) and (du[t].status=='available' or du[t].status=='available-in station')]
        if s == 'transport_BLS' and not ll and EMS_hierarchy: ll = [t for t in du.keys()  if (du[t].type=='transport') ]
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
        if len(ll)>0 :
            while this.number_needed[this.units_types==s].sum() >0 and len(ll)>0:
                try:
                    alldist = [cm[(cm.start == du[uu].location) * (cm.end == this.location)].cost.item() for uu in ll]
                except:
                    alldist = [cm[(cm.end == du[uu].location) * (cm.start == this.location)].cost.item() for uu in ll]
                # break ties by sending back first-due unit to its station if it's the case
                if use_fd:
                    tie_breaker=[u for u in ll if du[u].first_due == this.first_due]
                else:
                    tie_breaker = [ll[x] for x in range(len(ll)) if (alldist[x]==np.sort(alldist)[0] and ds[du[ll[x]].station].location == this.location) ]
                t = 0 # zeroed to make sure it's not wrongly reassigned
                if len(tie_breaker)>0:
                    # print(tie_breaker,this.location)
                    t = tie_breaker[0]
                else:
                # else look for the unit whose station is closest to location
                    stat_dist = [cm[(cm.end == ds[du[uu].station].location) * (cm.start == this.location)].cost.item() for uu in ll]
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

def assign_pending_incidents(pending_inc,use_fd):
    removed = []
    u_engaged = []
    for l in pending_inc:
        enroute_aver = 0.#loc[loc.locations == di[l].location].rate_enroute.item()
        enroute_stdev = 0.#loc[loc.locations == di[l].location].stdev_enroute.item()
        di[l], u_engaged = assign_units(du, di[l], time,u_engaged,use_fd,enroute_aver,enroute_stdev)
        if di[l].status == 1: removed.append(l)
    for x in removed: pending_inc.remove(x)
    return pending_inc,u_engaged

def new_calls(calls,di,inci_count,this_time,use_fd):
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
                                    resp_mod[cols_rates[t_index]][1], 0, all_locations[loc_index],loc[loc.locations == all_locations[loc_index]].first_due.item(),this_time,[])
                enroute_aver = loc[loc.locations==this_inc.location].rate_enroute.item()
                enroute_stdev = loc[loc.locations == this_inc.location].stdev_enroute.item()
                this_inc, u_engaged = assign_units(du, this_inc, time,u_engaged,use_fd,enroute_aver,enroute_stdev)
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
                cad.append([unit]+items+[items[3] if items[2]=='dispatched' else '-']+[di[items[0]].location]+[di[items[0]].code.replace('rate_','')]+[di[items[0]].first_due]+[du[unit].first_due])
    cad_file = pd.DataFrame.from_records(cad,columns=['Unit','Incident_ID','Time','Event','Location_aux','Unit_location_at_dispatch','Incident_location','Inc_type','First-Due','Unit First-Due'])
    cad_standard_form = unroller(cad_file, 'Incident_ID', 'Unit', 'Event', 'Time')
    cad_standard_form = cad_standard_form[
        ['Incident_ID','Inc_type', 'Unit', 'First-Due','Unit First-Due', 'Timedispatched', 'Timeenroute', 'Timeonscene', 'Timeavailable',
         'Timeavailable-in station','Unit_location_at_dispatch','Incident_location']]
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


##### from input
f1= r'InputFiles_NOStat7\SM_real_cost_matrix.csv'
f2 = r'InputFiles_NOStat7\SM_realtypes_locations_rates_firstdue.csv'
ratesfile = r'InputFiles_NOStat7\SM_daily_rates.csv'
stations_file = r'InputFiles_NOStat7\SM_stations_locations_info_firstdue.csv'
response_model = r'InputFiles_NOStat7\SM_response_model.csv'
ufile = r'InputFiles_NOStat7\Units_Details_SM.csv'
#
#STAT 7
# f1= r'InputFiles\SM_real_cost_matrix.csv'
# f2 = r'InputFiles\SM_realtypes_locations_rates_firstdue.csv'
# ratesfile = r'InputFiles\SM_daily_rates.csv'
# stations_file = r'InputFiles\SM_stations_locations_info_firstdue.csv'
# response_model = r'InputFiles\SM_response_model.csv'
# ufile = r'InputFiles\Units_Details_SM.csv'
#
###E8 in S2
# f1= r'InputFiles_Stat7_E8inS2\SM_real_cost_matrix.csv'
# f2 = r'InputFiles_Stat7_E8inS2\SM_realtypes_locations_rates_firstdue.csv'
# ratesfile = r'InputFiles_Stat7_E8inS2\SM_daily_rates.csv'
# stations_file = r'InputFiles_Stat7_E8inS2\SM_stations_locations_info_firstdue.csv'
# response_model = r'InputFiles_Stat7_E8inS2\SM_response_model.csv'
# ufile = r'InputFiles_Stat7_E8inS2\Units_Details_SM.csv'

### E8 in S3
# f1= r'InputFiles_Stat7_E8inS3\SM_real_cost_matrix.csv'
# f2 = r'InputFiles_Stat7_E8inS3\SM_realtypes_locations_rates_firstdue.csv'
# ratesfile = r'InputFiles_Stat7_E8inS3\SM_daily_rates.csv'
# stations_file = r'InputFiles_Stat7_E8inS3\SM_stations_locations_info_firstdue.csv'
# response_model = r'InputFiles_Stat7_E8inS3\SM_response_model.csv'
# ufile = r'InputFiles_Stat7_E8inS3\Units_Details_SM.csv'

### E8 in S1
# f1= r'InputFiles_Stat7_E8inS1\SM_real_cost_matrix.csv'
# f2 = r'InputFiles_Stat7_E8inS1\SM_realtypes_locations_rates_firstdue.csv'
# ratesfile = r'InputFiles_Stat7_E8inS1\SM_daily_rates.csv'
# stations_file = r'InputFiles_Stat7_E8inS1\SM_stations_locations_info_firstdue.csv'
# response_model = r'InputFiles_Stat7_E8inS1\SM_response_model.csv'
# ufile = r'InputFiles_Stat7_E8inS1\Units_Details_SM.csv'

### E8 in S2 and E9 in S3
# f1= r'InputFiles_Stat7_E8inS2_E9inS3\SM_real_cost_matrix.csv'
# f2 = r'InputFiles_Stat7_E8inS2_E9inS3\SM_realtypes_locations_rates_firstdue.csv'
# ratesfile = r'InputFiles_Stat7_E8inS2_E9inS3\SM_daily_rates.csv'
# stations_file = r'InputFiles_Stat7_E8inS2_E9inS3\SM_stations_locations_info_firstdue.csv'
# response_model = r'InputFiles_Stat7_E8inS2_E9inS3\SM_response_model.csv'
# ufile = r'InputFiles_Stat7_E8inS2_E9inS3\Units_Details_SM.csv'

s1 = '1/1/2018 01:00:00'
s2 = '3/1/2018 01:00:00'
EMS_hierarchy = True

use_fd = False
min_travel_allowed = 30 # seconds

# time steps for simulation (seconds)
time_resol = 10

daily_rates = pd.read_csv(ratesfile)
cols_rates=list(daily_rates.columns[1:-1])
units_read = pd.read_csv(ufile)
stat_file = pd.read_csv(stations_file)
# joint to get first-due of units
if 'first_due' in stat_file.columns: units_read['first_due'] = units_read.Station.apply(lambda x: stat_file[stat_file['Station']==x].first_due.item())


units_name = units_read.Unit.tolist()
units_first_due = units_read.first_due.tolist()
units_type = units_read.Type.tolist()
units_type_ems = units_read.Type_EMS.tolist()
units_stat = units_read.Station.tolist()
stat_loc = units_read.station_location.tolist()
units_initloc =units_read.initial_location.tolist()



rates_clear = []
for c in cols_rates:
        rates_clear.append(  [1./(x/3600) for x in units_read['average_time_on_service_'+ c.replace('rate_','')]] )
# fire_clear_perhr = [1./(x/3600) for x in units_read.average_time_on_service_fire_seconds]
# ems_clear_perhr  = [1./(x/3600) for x in units_read.average_time_on_service_ems_seconds]


stats = units_read.Station.unique().tolist()

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
l1  = [[units_name[x],units_type[x],units_type_ems[x],units_stat[x],units_first_due[x],start,'available-in station',units_initloc[x],{cols_rates[c]:rates_clear[c][x] for c in range(len(rates_clear))}] for x in range(len(units_name))]
du   = {l1[x][0]:Apparatus(l1[x][0],l1[x][1],l1[x][2],l1[x][3],l1[x][4],l1[x][5],l1[x][6],l1[x][7],l1[x][8]) for x in range(len(units_name))}

#initialize stations
units_stat = units_read[['Station','station_location']].drop_duplicates('Station', keep='first').Station.to_list()
stat_loc   = units_read[['Station','station_location']].drop_duplicates('Station', keep='first').station_location.tolist()
ds = {units_stat[x]:Station(stats[x],stat_loc[x]) for x in range(len(stats))}
for u in du:
    for ss in ds:
        if  du[u].station == ds[ss].station:ds[ss].assign_apparatus(du[u].name)


#response model
# resp_mod = {x:[list(np.unique(units_type)),[int(model[model.Incident_Type==x][y]) for y in np.unique(units_type)]] for x in model.Incident_Type}
resp_mod = {x:[model.columns[1::].tolist(),[int(model[model.Incident_Type==x][y]) for y in model.columns[1::]]] for x in model.Incident_Type}
# count type of calls
call_type = dict({int(x):cols_rates[x] for x in range(len(cols_rates))})


###### -----------------------------------------------------
####################################
# for testing only
# calls = [([1, 0,0,0]), ([0, 0,0, 0])]
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
#transforming daily rates to array for optimization
daily_rates = daily_rates.fillna(1e-9)
loc = loc.fillna(1e-9)
locratesonly = loc[cols_rates]
locmat, locdc = cad.to_mat(locratesonly)
drmat,drdc = cad.to_mat(daily_rates)
while time < end:
    # print(time,end)
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
    pending_inc,u_engaged = assign_pending_incidents(pending_inc,use_fd)
    # print(len(di), timeit.default_timer() - start)
    if u_engaged: all_units_engaged = all_units_engaged + u_engaged
    ### Then deal with new calls arriving -  multiply by 24 hours then take the fraction in the hour
    calls = [incidents(( drmat[np.where(drmat[:,drdc['hour']]==hour),drdc[x]].item()* locmat[:,locdc[x]]*24. / drmat[:,drdc[x]].sum())* time_resol) for x in cols_rates]
    #calls = [incidents((daily_rates[daily_rates.hour == hour][x].item() * loc[x]*24. / daily_rates[x].sum()).fillna(0.) * time_resol) for x in cols_rates]
    #testing
    # calls[0]=calls[0]*0
    # calls[1] = calls[1] * 0
    # calls[2] = calls[2] * 0
    # calls[3] = calls[3] * 0
    # calls[0][169] = 1
    ## end testing
    #calls = [incidents(loc[x] *daily_rates[daily_rates.hour==hour][x].item()/daily_rates[x].sum()* time_resol) for x in cols_rates]
    #calls = [incidents(loc[x]*time_resol) for x in cols_rates]
    # if time == start : calls = [([0, 1, 0]), ([0, 0, 0])]
    # if time == start+1 : calls = [([0, 0, 0]), ([0, 0, 0])]
    # print('----func1')
    # start = timeit.default_timer()
    pending_inc,u_engaged,di,inci_count  = new_calls(calls,di,inci_count,time,use_fd)
    # if len(di)>=1: stop
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
                #might (or not) always wait for all the units to be on scene (this might be modified in the future)
                # print('Unit Available -2')
                count_on_scene =0
                for u in di[du[dispu].incident].units_assigned: count_on_scene += du[u].status == 'onscene'
                if count_on_scene >-100:# len(di[du[dispu].incident].units_assigned):
                    # print('Unit Available -3')
                    for u_on_inc in di[du[dispu].incident].units_assigned:
                        # print('Unit Available')
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
                try:
                    travel_time = cm[(cm.start==du[dispu].location)*(cm.end==di[du[dispu].incident].location)].cost.item()
                except:
                    travel_time = cm[(cm.end == du[dispu].location) * (cm.start == di[du[dispu].incident].location)].cost.item()
                du[dispu].next_update(time+max(min_travel_allowed,travel_time))
                #du[dispu].next_update(time+max(min_travel_allowed,np.random.normal(travel_time,daily_rates[daily_rates.hour==hour].st_to_mean.item()*travel_time)))####!!!! HERE SCATTER TRAVEL
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
# stop
mycadf = mycad.sort_values('arrived')
mycadf= mycadf.drop_duplicates('Incident_ID',keep='first')
t = mycadf[mycadf.Inc_type=='EMS'].travel.dropna().values
print('EMS 90th Percentile')
print(np.percentile(t,90))
mycad.to_csv('temp.csv')
stop
####
mycad = arrive_order(mycad,'arrived','Incident_ID')
mycad = bb(mycad,'dispatched','available','Unit','Incident_ID')
mycad = mycad.drop(['dispatched_seconds','available_seconds'],axis=1)
mycad.to_csv('twomonths_comparison_10sec_E8inS2_E9inS3.csv')
# #CHECK t1 and t2 in data_driver_SM - IS IT REALLY FOR 2019 only?

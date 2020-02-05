import pandas as pd
import numpy as np
import pylab as p
# set of functions and code to format data

def draw(y,z=None,x=None):
    if not z: z=y
    if x:
        p.plot(x,y);p.plot(x, z,'--');p.show()
    else:
        p.plot(y);p.plot(z);p.show()


def daily_variation(df,disp_col,inci_id):
    #seconds for 1 hour only
    all_seconds = (df[disp_col].max()-df[disp_col].min()).days*60*60.
    df = df.drop_duplicates(inci_id, keep='first')
    shape = [len([x for x in df[disp_col] if x.hour==y]) for y in np.arange(0,24,1)]
    #[34952, 29816, 25731, 21673, 19767, 23068, 31094, 42831, 51884, 57966, 61556, 62878, 64129, 64931, 64162, 64794, 66009, 65231, 64857, 62604, 58007, 52771, 46972, 40403]
    g = [(x,shape[x]/all_seconds) for x in range(len(shape))]
    d_counts = dict(g)
    return d_counts

def cost_matrix_format(cmdf,name,cost):
    #this assumes the cost is in minutes!!
    locs = [[cmdf[name].ix[x].split('-')[0].strip().split(' ')[1], cmdf[name].ix[x].split('-')[1].strip().split(' ')[1],cmdf[cost].ix[x]*60] for x in cmdf.index]
    return pd.DataFrame.from_records(locs,columns=['start','end','cost'])

def locations_format(df,clnames,cseconds):
    list_rec = [[df.loc[x][clnames].split(' ')[1],df.loc[x][cseconds],df.loc[x][cseconds]] for x in range(len(df))]
    loc_df = pd.DataFrame.from_records(list_rec,columns=['locations','rate_fire','rate_ems'])
    return loc_df


####### inputs
# units_file = 'simulated_files\\Units_DC.csv'
cmfile ='..\ODMatrix_DC_05miles.csv'
rates_file = 'arcgis_aux_files\\DC_location_preprocessing_file.csv'
cad = 'DC_2017_2019_edited_file_travel_order_b2b_withtypes_fixed.csv'
arcgis_stations='arcgis_aux_files\\arcgis_stations_locations.csv'

# for cost_matrix file cmfile
loc_names = 'Name'
ttcol     = 'Total_TravelTime'

# for station file arcgis_statios
stat_names = 'NAME'

# this for rates_file produced by the GIS
count_loc_names = 'Name'
counts = 'Point_Count'
t1 = '01/01/2017 00:00:00'
t2 = '07/31/2019 23:59:59'

# this for cad
code_col = 'Type_Fixed'
ems = 'EMS_all'
fire ='ALL_Fires'
disp = 'Dispatch'
unit_types = ''
inci_id='Num 1'
enroute = 'Enroute'
arrived = 'Arrived'
date = 'Date'
travel = 'Travel'
# clear = 'Available'
# service= None

# for units file
type ='Type'


####


### UNCOMMENT THIS PART FOR GIS
# stop
# #### read GIS files
# arcgis_cost = pd.read_csv(cmfile)
# arcgis_rates = pd.read_csv(rates_file)
# ######
#
# #### get cost matrix
# print('Formatting cost matrix...')
# cmf = cost_matrix_format(arcgis_cost,loc_names,ttcol)
# #fix cost 0 by setting it to up to one minute - this should be checked against data
# cmf.cost = [np.random.random()*40+20 if x==0. else x for x in cmf.cost ]
# #save things
# cmf.to_csv('DC_real_cost_matrix.csv',index=False)
#
# ##### get average counts per location and clear per type
# print('Preparing locations details...')
# t1t = pd.to_datetime(t1)
# t2t = pd.to_datetime(t2)
# no_of_days = t2t-t1t
# arcgis_rates['average_second'] = [x/(no_of_days.days*24*60*60) for x in arcgis_rates[counts]]
# locf = locations_format(arcgis_rates,count_loc_names,counts)
#
#
# locations_df = locations_format(arcgis_rates,count_loc_names,'average_second')
# locations_df['rate_enroute']=0
# locations_df['stdev_enroute']=0
# locations_df.to_csv('DC_real_locations_rates.csv',index=False)
#
# ##### get stations details
# stats = pd.read_csv(arcgis_stations)
# stats['loc_number'] = [stats.loc[x][loc_names].split(' ')[1] for x in range(len(stats))]
# sloc = stats[[stat_names,'loc_number']]
# sloc.to_csv('DC_stations_locations_info.csv',index=False)
# stop

####### get daily variation from CAD
print('Getting calls rate by hour...')
dd = pd.read_csv(cad)
dd[disp] =pd.to_datetime(dd[disp])#,format="%m/%d/%Y %I:%M:%S %p")# infer_datetime_format=True)#pd.to_datetime(dd[disp], format="%m/%d/%Y %H:%M:%S %p")

dd = dd.sort_values(disp)
dd=dd.head(10000)


idx = [x for x in dd.index if dd.loc[x][disp].year>2000]
dd=dd.loc[idx]
# travel time details
# tt_ems = dd[(dd.travel<7200)*(dd.travel>30)*(dd['Tycod (group)']==ems)*(dd.order==1)].travel.dropna().as_matrix()
# tt_fire = dd[(dd.travel<7200)*(dd.travel>30)*(dd['Tycod (group)']==fire)*(dd.order==1)].travel.dropna().as_matrix()
#
# std_tt_ems = np.std(tt_ems)
# std_tt_fire = np.std(tt_fire)

#global
tt = dd[(dd[travel]<7200)*(dd[travel]>30)][travel].dropna().as_matrix()
st = np.std(tt)

all_travels=[]
for thishour in np.arange(0,24,1):
    ix = [x for x in dd.index if dd.loc[x][disp].hour==thishour]
    if len(ix)>0:
        dd_bytime = dd.loc[ix]
        tt_time = dd_bytime[(dd_bytime[travel] < 7200) * (dd_bytime[travel] > 30)][travel].dropna().as_matrix()
        all_travels.append([tt_time.mean(),np.std(tt_time)])
    else:
        if all_travels:
            all_travels.append([all_travels[-1][0],all_travels[-1][1]])
        else:
            all_travels.append([tt,st])

#get st dev/mean ratio for travel time, by hour of day
st_hour = [x[1]/x[0] for x in all_travels]
stop

dems = dd[dd[code_col]==ems]
dfire = dd[dd[code_col]==fire]

counts_fire = daily_variation(dfire,disp,inci_id)
counts_ems = daily_variation(dems,disp,inci_id)
records = [[list(counts_fire.keys())[x],list(counts_fire.values())[x],list(counts_ems.values())[x],st_hour[x]] for x in range(len(counts_fire))]
daily_rates = pd.DataFrame.from_records(records,columns=['hour','rate_fire','rate_ems','st_to_mean'])
daily_rates.to_csv('daily_rates.csv',index=False)



#### TODo
# introduce more inci type


# # move this part to main driver
# t1 = pd.to_datetime('2001-01-01 11:29:59')
# t1 = pd.to_datetime(t1)
# start_hour = t1.hour*3600+t1.minute*60+t1.second
# t1 = t1.value/1e9-start_hour
# t2 = pd.to_datetime('2018-01-14 23:59:59').value/1e9
# t = t2
# days=int((t-t1)/86400)
# hour= int((t-t1-86400*days)/3600)

import pandas as pd
import random
from math import radians, degrees, sin, cos, asin, acos, sqrt
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt

def great_circle(lon1, lat1, lon2, lat2):
    # sic
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    return earth_radius_miles * (acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2)))

def scatterer(coord):
    # randomly scatter a point around given coord
    coord = coord + random.random()*2.*small_angle_approx-small_angle_approx
    return coord

def set_resolution(dfl,res):
    #find resolution of map (distance between centers of locations)
    if not res:
        dfl = dfl.sort_values(['Name'])
        resol = great_circle(dfl.loc[0].SnapX, dfl.loc[0].SnapY, dfl.loc[1].SnapX, dfl.loc[1].SnapY)
    else:
        resol = res
    return resol

def gislocation_to_coord(loc):
    #translate gis location names to coordinates
    long_c = dfl[dfl.Name == loc].SnapX.item()
    lat_c  = dfl[dfl.Name == loc].SnapY.item()
    return long_c,lat_c

def map_incidents(long,lat,color):
    #produce a map of long and lat with given color
    ax = plt.axes(projection=request.crs)
    ax.set_extent(extent, crs=ccrs.Geodetic())
    ax.plot(long, lat, marker='o', color=color, markersize=5, alpha=0.7, transform=ccrs.Geodetic())
    ax.add_image(request, 13)
    plt.tight_layout()
    plt.show()
    plt.pause(0.0001)

def cad_add_coords(dfc):
    #add coordingates to a CAD dataframe
    dfc = dfc.rename(columns={'Incident_location': 'Name'})
    dfj = dfc.set_index('Name').join(dfl[['Name', 'SnapX', 'SnapY']].set_index('Name'), on='Name', how='left').reset_index()
    dfj['Longitude_Inc'] = dfj.SnapX.apply(lambda x: scatterer(x))
    dfj['Latitude_Inc']  = dfj.SnapY.apply(lambda x: scatterer(x))
    dfj.drop(['SnapX', 'SnapY'], axis=1)
    dfj = dfj.rename(columns={'Name':'Incident_location'})
    return dfj

dfl = pd.read_csv(r'D:\Users\fdebernardis\Projects\Python Scripts\BigSimulator\SantaMonica\SantaMonica_AuxFiles\locations_geoinfo.csv')
dfl['Name'] = dfl['Name'].apply(lambda x: int(x.split(' ')[1]))



earth_radius_miles = 3958.8
# might be set by user, hard coded to None for now
res = None

resol = set_resolution(dfl,res)
small_angle_approx = resol/earth_radius_miles*57.2958 #degrees
plt.ion()
request = cimgt.OSM()

#move to driver
# dfc = pd.read_csv('stat7_2months_10sec.csv')
# dfc = dfc.rename(columns={'Incident_location':'Name'})
# dfl['Name'] = dfl['Name'].apply(lambda x: int(x.split(' ')[1]))
# dfj = dfc.set_index('Name').join(dfl[['Name','SnapX','SnapY']].set_index('Name'),on='Name',how='left').reset_index()



#

##### mapping ####
# extent = [-118.52, -118.47, 33.985, 34.05]

dfl.SnapX.max()*.5+dfl.SnapX.min()*.5
dfl.SnapY.max()*.5+dfl.SnapY.min()*.5

long_lim1  = dfl.SnapX.max()+small_angle_approx*2.5
long_lim2  = dfl.SnapX.min()-small_angle_approx*2.5

lat_lim1  = dfl.SnapY.max()+small_angle_approx*2.5
lat_lim2  = dfl.SnapY.min()-small_angle_approx*2.5
extent = [min(long_lim1,long_lim2), max(long_lim1,long_lim2), min(lat_lim1,lat_lim2),  max(lat_lim1,lat_lim2)]
# for x in range(len(long)):
#     map_incidents(long[x],lat[x])
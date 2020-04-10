import pyodbc
import pandas as pd
from geojson import LineString, Feature, FeatureCollection, dump
import folium 
import streamlit as st
import os
import time 
import glob

def getDatabaseConnection():
	return pyodbc.connect('DRIVER={SQL Server};SERVER=128.95.29.74;DATABASE=RealTimeLoopData;UID=starlab;PWD=star*lab1')

def GetSegmentGeo():
	# load geo
	geo = pd.read_csv('SegmentsGeo.csv')

	geo_key = []
	for i in range(len(geo)):
	    geo_key.append(str(geo['route'][i]) + '_' + geo['direct'][i].upper() + '_' + str(geo['mile_min'][i]) + '_' + str(geo['mile_max'][i]))
	geo['key'] = geo_key

	# st.write(geo)

	# load segments ids
	conn = getDatabaseConnection()
	SQL_Query = pd.read_sql_query(
	'''	SELECT *
		  FROM [RealTimeLoopData].[dbo].[Segments]''', conn)
	segmentIDs = pd.DataFrame(SQL_Query)

	segmentIDs['route'] = segmentIDs['route'].apply(lambda x: x.strip())

	seg_key = []
	for i in range(len(segmentIDs)):
	    seg_key.append(str(segmentIDs['route'][i]) + '_' + segmentIDs['mpdirection'][i].upper() + '_' + str(segmentIDs['milepost_small'][i]) + '_' + str(segmentIDs['milepost_large'][i]))
	segmentIDs['key'] = seg_key

	# st.write(segmentIDs)

	# merge
	segment = geo.merge(segmentIDs, on = ['key'], how = 'inner')

	# st.write(segment)

	return segment

def style_function(feature):
    value = feature['properties']['TrafficIndex_GP']
    #print(value)
    if value > 0.95:
        color = 'green'
    elif value > 0.90:
        color = 'yellow'
    else:
        color = 'red'
        
    return {
        'weight': 1,
        'color': color}


def GenerateGeo(TPS):

	# st.write(TPS)

	segment = GetSegmentGeo()
	# merge TPS with segment data
	data = segment.merge(TPS, on = ['segmentID'], how = 'left')
	data.fillna(1, inplace = True) # fill nan with zero, becuase Out of range float values are not JSON compliant: nan

	features = []
	for i in range(len(data)):
	    coordinates = []
	    if data['geometry'][i].split(' ')[0] != 'LINESTRING': # dropped multi-linestring
	        continue
	    geo_string = data['geometry'][i][12:-1]
	    temp = geo_string.split(',')
	    for item in temp:
	        lon, lat = item.strip().split(' ')
	        coordinates.append((float(lon), float(lat)))
	        
	    route=LineString(coordinates)
	    features.append(Feature(geometry = route, properties={"TrafficIndex_GP":float(data['TrafficIndex_GP'][i])}))
	feature_collection = FeatureCollection(features)

	with open('data.geojson', 'w') as f:
	   dump(feature_collection, f)

	m = folium.Map([47.673650, -122.260540], zoom_start=10, tiles="cartodbpositron")

	folium.GeoJson('./data.geojson', style_function= style_function).add_to(m)

	# STREAMLIT_STATIC_PATH = "/Users/meixin/anaconda3/lib/python3.7/site-packages/streamlit/static/"

	STREAMLIT_STATIC_PATH = 'C:\\Users\\Zhiyong\\Anaconda3\\Lib\\site-packages\\streamlit\\static\\'

	for filename in glob.glob(STREAMLIT_STATIC_PATH + 'map*'):
		os.remove(filename)

	filename_with_time = f'map_{time.time()}.html'
	map_path = STREAMLIT_STATIC_PATH + filename_with_time
	open(map_path, 'w').write(m._repr_html_())

	# st.markdown('Below is the traffic performance score by segments:' + dt_string)
	st.markdown(f'<iframe src="/{filename_with_time}" ; style="width:100%;height:600px;"> </iframe>', unsafe_allow_html=True)
	# return m
		




import pyodbc
import pandas as pd
from geojson import LineString, Feature, FeatureCollection, dump
import folium 
import streamlit as st
import os
import time 
import glob

import geopandas
import branca
from folium.features import GeoJson, GeoJsonTooltip
from folium import plugins
import fiona
import fiona.crs


from sys import platform 
if platform == "linux" or platform == "linux2":
    # linux
	SQL_DRIVER = 'SQL Server'
elif platform == "darwin":
    # OS X
	SQL_DRIVER = 'ODBC Driver 17 for SQL Server'

elif platform == "win32":
    # Windows...
	# SQL_DRIVER = 'ODBC Driver 17 for SQL Server'
	SQL_DRIVER = 'SQL Server'

def getDatabaseConnection():
	return pyodbc.connect(f'DRIVER={SQL_DRIVER};SERVER=128.95.29.74;DATABASE=RealTimeLoopData;UID=starlab;PWD=star*lab1')

def route_map_func(x):
    if x in [5, 90, 405]: 
        return 'I-' + str(x) 
    else: 
        return 'SR ' + str(x)

def name_map_func(x):
    return x['route_name'] + ' ' + x['direction_name'] + ' ' + str(int(x['milepost_small'])) + ' to ' + str(int(x['milepost_large']))

def GetSegmentGeo():
	# load geo
	geo = geopandas.read_file('geodata/step-2.shp')
	geo_csv = pd.read_csv('geodata/step-2.csv')
	geo_csv.drop(['geometry'], axis = 1, inplace = True)
	geo = pd.concat([geo_csv, geo['geometry']], axis = 1)

	geo_key = []
	for i in range(len(geo)):
	    geo_key.append(str(geo['route'][i]) + '_' + geo['direct'][i].upper() + '_' + str(geo['mile_min'][i]) + '_' + str(geo['mile_max'][i]))
	geo['key'] = geo_key

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
	segment = geo.merge(segmentIDs, on = ['key'], how = 'inner')
	# segment.fillna(0, inplace = True)
    
    # create name
	segment['route_name'] = segment['route_x'].apply(route_map_func) 
	segment['direction_name'] = segment['direction'].apply(lambda x: str(x) + 'B')
	segment['name'] = segment.apply(name_map_func, axis = 1)

	return segment

colormap = branca.colormap.LinearColormap(vmin = 60, 
                                        vmax= 100, 
                                        colors=['red','orange','yellow','lightgreen','green'],
                                       caption="Traffic Performance Score")

def style_func(feature):
    value = feature['properties']['TrafficIndex_GP']
    return {
        "color": colormap(value)
        if value is not None
        else "transparent"
    }

def style_func_HOV(feature):
    value = feature['properties']['TrafficIndex_HOV']
    return {
        "color": colormap(value)
        if value is not None
        else "transparent"
    }

def GenerateGeo(TPS):
	segment = GetSegmentGeo()
	# merge TPS with segment data
	segment.rename(columns={"segmentid": "segmentID"}, inplace = True)
	# st.write(segment[['segmentID', 'route_name', 'direction_name', 'name']])
	# st.write(TPS)
	# st.write(segment[['segmentID', 'route_name', 'direction_name', 'name']].merge(TPS, on = ['segmentID'], how = 'inner'))
	data = segment.merge(TPS, on = ['segmentID'], how = 'left')

	data['TrafficIndex_GP'].fillna(1, inplace = True) # fill nan with zero, becuase Out of range float values are not JSON compliant: nan
	data['TrafficIndex_HOV'].fillna(1, inplace = True) # fill nan with zero, becuase Out of range float values are not JSON compliant: nan

	scaled_data = data
	scaled_data['TrafficIndex_GP'] = data['TrafficIndex_GP']*100
	scaled_data['TrafficIndex_HOV'] = data['TrafficIndex_HOV']*100

	tooltip = GeoJsonTooltip(
		fields=["name", "TrafficIndex_GP", 'time'],
		aliases=["Road Segment", "Traffic Performance Score", 'Time'],
		localize=True,
		sticky=False,
		labels=True,
		style="""
			background-color: #F0EFEF;
			border: 2px solid black;
			border-radius: 3px;
			box-shadow: 3px;
		"""
	)

	tooltip_HOV = GeoJsonTooltip(
		fields=["name", "TrafficIndex_HOV", 'time'],
		aliases=["Road Segment", "Traffic Performance Score", 'Time'],
		localize=True,
		sticky=False,
		labels=True,
		style="""
			background-color: #F0EFEF;
			border: 2px solid black;
			border-radius: 3px;
			box-shadow: 3px;
		"""
	)

	data_gdf = geopandas.GeoDataFrame(scaled_data, crs=fiona.crs.from_epsg(4326))
	data_gdf['time'] = data_gdf['time'].apply(lambda x: x.isoformat())

	m = folium.Map([47.673650, -122.260540], zoom_start=10, tiles="cartodbpositron")

	folium.GeoJson(data_gdf, style_function= style_func, tooltip = tooltip, name = 'GP Lane').add_to(m)
	folium.GeoJson(data_gdf, style_function= style_func_HOV, tooltip = tooltip_HOV, name = 'HOV Lane', show = False).add_to(m)

	colormap.add_to(m)
	# full screen plugins
	plugins.Fullscreen(
		position='topright',
		title='Expand me',
		title_cancel='Exit me',
		force_separate_button=True
	).add_to(m)
	folium.LayerControl(collapsed=False).add_to(m)

	STREAMLIT_STATIC_PATH = os.path.join(os.path.dirname(st.__file__), 'static')

	# st.write(os.path.dirname(st.__file__) + '\\static')

	for filename in glob.glob(STREAMLIT_STATIC_PATH + 'map*'):
		os.remove(filename)

	filename_with_time = f'map_{time.time()}.html'
	map_path = os.path.join(STREAMLIT_STATIC_PATH, filename_with_time)
	open(map_path, 'w').write(m._repr_html_())

	# st.markdown('Below is the traffic performance score by segments:' + dt_string)
	st.markdown("Please use **Chrome** for best visualization quality.")
	st.markdown(f'<iframe src="/{filename_with_time}" ; style="width:100%; height:480px;"> </iframe>', unsafe_allow_html=True)


def	GenerateGeoAnimation(TPS):
	TPS.columns = ['time', 'segmentID', 'AVG_Spd_GP', 'AVG_Spd_HOV', 'AVG_Vol_GP', 'AVG_Vol_HOV', 'TrafficIndex_GP', 'TrafficIndex_HOV']
	
	segment = GetSegmentGeo()
	# merge TPS with segment data
	segment.rename(columns={"segmentid": "segmentID"}, inplace = True)
	data = segment.merge(TPS, on = ['segmentID'], how = 'left')
	
	data['TrafficIndex_GP'].fillna(1, inplace = True) # fill nan with zero, becuase Out of range float values are not JSON compliant: nan
	data['TrafficIndex_HOV'].fillna(1, inplace = True) # fill nan with zero, becuase Out of range float values are not JSON compliant: nan

	scaled_data = data
	scaled_data['TrafficIndex_GP'] = data['TrafficIndex_GP']*100
	scaled_data['TrafficIndex_HOV'] = data['TrafficIndex_HOV']*100

	temporal_data = segment.merge(TPS, on = ['segmentID'], how = 'left')
	temporal_data['TrafficIndex_GP'] = temporal_data['TrafficIndex_GP']*100
	temporal_data['TrafficIndex_HOV'] = temporal_data['TrafficIndex_HOV']*100

	features = []
	for _, line in temporal_data.iterrows():
	    route = line['geometry']
	    try:
	        features.append(Feature(geometry = route, properties={"TrafficIndex_GP":float(line['TrafficIndex_GP']), "name": line["name"], 
	                                                          "times":[line["time"].isoformat()]*len(line['geometry'].coords), "style":{"color": colormap(line['TrafficIndex_GP'])}}))
	    except:
	        continue

	m = folium.Map([47.673650, -122.260540], zoom_start=10, tiles="cartodbpositron")

	plugins.TimestampedGeoJson({
	    'type': 'FeatureCollection',
	    'features': features,
	}, period='PT1H', add_last_point= False, max_speed = 10, min_speed = 0.1, transition_time = 1000, loop_button = True, time_slider_drag_update=True).add_to(m)

	colormap.add_to(m)
	# full screen plugins
	plugins.Fullscreen(
		position='topright',
		title='Expand me',
		title_cancel='Exit me',
		force_separate_button=True
	).add_to(m)

	# folium.LayerControl(collapsed=False).add_to(m)

	STREAMLIT_STATIC_PATH = os.path.join(os.path.dirname(st.__file__), 'static')

	# st.write(os.path.dirname(st.__file__) + '\\static')

	for filename in glob.glob(STREAMLIT_STATIC_PATH + 'map*'):
		os.remove(filename)

	filename_with_time = f'map_{time.time()}.html'
	map_path = os.path.join(STREAMLIT_STATIC_PATH, filename_with_time)
	open(map_path, 'w').write(m._repr_html_())

	# st.markdown('Below is the traffic performance score by segments:' + dt_string)
	st.markdown("Please use **Chrome** for best visualization quality.")
	st.markdown(f'<iframe src="/{filename_with_time}" ; style="width:100%; height:480px;"> </iframe>', unsafe_allow_html=True)


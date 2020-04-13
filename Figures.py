import streamlit as st
import pandas as pd
import numpy as np
import time
import pypyodbc as pyodbc
import datetime
import pydeck as pdk
import pyodbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image

import geopandas
from geojson import LineString, Feature, FeatureCollection, dump
import fiona
import fiona.crs
import branca

import folium
from folium.features import GeoJson, GeoJsonTooltip
from folium import plugins

import os
import glob

from SQLquery import getDatabaseConnection
from SQLquery import getLoopDetectorLocation


def plotTPS(data, date_or_time = 'time', lw = 1):

    if date_or_time == 'date':
        (col_gp, col_hov) = ['daily_index_gp', 'daily_index_hov']
        xaxis_title = 'Date'
    elif date_or_time == 'time':
        (col_gp, col_hov) = ['trafficindex_gp', 'trafficindex_hov']
        xaxis_title = 'Time'
    else:
        return None

    # Create traces
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data[date_or_time], y=data[col_gp],
                             mode='lines', line=dict(dash='solid', width=lw),
                             name='Main lane'))

    fig.add_trace(go.Scatter(x=data[date_or_time], y=data[col_hov],
                             mode='lines', line=dict(dash='solid', width=lw),
                             name='HOV lane'))

    fig.update_layout(xaxis_title=xaxis_title, yaxis_title='Traffic Performance Score (%)',
                      legend=dict(x=.01, y=0.05),
                      margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width=700, height=450)

    return fig


def plotOtherMetrics(data, dataFields, lw = 2):

    fig = go.Figure()
    for item in dataFields:
        fig.add_trace(go.Scatter(x=data['date'], y=data[item],
                                 mode='lines', line=dict(dash='solid', width=lw),
                                 name=item))

    fig.update_layout(xaxis_title='Date', yaxis_title='Traffic Volume per Lane',
                      legend=dict(x=.01, y=0.05),
                      margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width=700, height=450)

    return fig


def plotCOVID19(data, lw = 2):

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces for axis-2
    fig.add_trace(go.Scatter(x=data['date'], y=data['daily_index_gp'],
                             mode='lines', line=dict(dash='dot', width=lw, color='#1f77b4'),
                             name='Index - GP',
                             legendgroup='group2'),
                    secondary_y=False)
    fig.add_trace(go.Scatter(x=data['date'], y=data['daily_index_hov'],
                             mode='lines', line=dict(dash='dot', width=lw, color='#2ca02c'),
                             name='Index - HOV',
                             legendgroup='group2'),
                    secondary_y=False)

    # Add traces for axis-1
    fig.add_trace(go.Scatter(x=data['date'], y=data['confirmed case'],
                             mode='lines+markers', line=dict(dash='solid', width=lw, color='red'),
                             name='Confirmed Cases',
                             legendgroup='group1'),
                    secondary_y=True)
    fig.add_trace(go.Scatter(x=data['date'], y=data['new case'],
                             mode='lines+markers', line=dict(dash='solid', width=lw, color='orange'),
                             name='New Cases',
                             legendgroup='group1'),
                    secondary_y=True)
    # fig.add_trace(go.Scatter(x=data['date'], y=data['total death'],
    # 						 mode='lines+markers', line=dict(dash='solid', width=lw, color='black'),
    # 						 name='Total Death',
    # 						 legendgroup='group1'),
    # 				secondary_y=True)

    confirmed_case_axis_max = data['confirmed case'].max() + 500

    fig.update_traces(textposition='top center')
    # Set x-axis title
    fig.update_xaxes(title_text="Date")
    # Set y-axes titles
    fig.update_yaxes(title_text="Daily Traffic Performance Score (%)",
                        range=[70, 100],
                        showline=True,
                        linecolor='rgb(204, 204, 204)',
                        linewidth=2,
                        showticklabels=True,
                        ticks='outside',
                        secondary_y=False)
    fig.update_yaxes(title_text="COVID-19 Case Amount",
                        range=[0, confirmed_case_axis_max],
                        showline=True,
                        linecolor='rgb(204, 204, 204)',
                        linewidth=2,
                        showticklabels=True,
                        ticks='outside',
                        secondary_y=True)
    fig.update_layout(xaxis=dict(
                            showline=True,
                            showgrid=False,
                            showticklabels=True,
                            linecolor='rgb(204, 204, 204)',
                            linewidth=2,
                            ticks='outside',
                            tickfont=dict(
                                family='Arial',
                                size=12,
                                color='rgb(82, 82, 82)',
                            ),
                        ),
                        legend=dict(x= 0.5, y=1.3, orientation="h"),
                        margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4),
                        width = 700,
                        height = 450,
                        plot_bgcolor='white')

    return fig


def showLoopDetectorMap():
    df_loop_location = getLoopDetectorLocation()

    st.pydeck_chart(pdk.Deck(
        # map_style='mapbox://styles/mapbox/dark-v9',
        map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
            latitude=47.59,
            longitude=-122.24,
            zoom=9,
            pitch=50,
        ),
        layers=[
            # pdk.Layer(
            #    'HexagonLayer',
            #    data=df_loop_location,
            #    get_position='[lon, lat]',
            #    radius=200,
            #    elevation_scale=4,
            #    elevation_range=[0, 1000],
            #    pickable=True,
            #    extruded=True,
            # ),
            pdk.Layer(
                'ScatterplotLayer',
                data=df_loop_location,
                get_position='[lon, lat]',
                get_color='[0, 160, 187, 160]',
                get_radius=300,
            ),
        ],
    ))

#####################################################
# segment-based visualization
#####################################################


def route_map_func(x):
    if x in [5, 90, 405]: 
        return 'I-' + str(x) 
    else: 
        return 'SR ' + str(x)

def name_map_func(x):
    return x['route_name'] + ' ' + x['direction_name'] + ' ' + str(int(x['milepost_small'])) + ' to ' + str(int(x['milepost_large']))

def GetSegmentGeo():
    # load geo
    geo = geopandas.read_file('./geo/segments.shp')
    geo_csv = pd.read_csv('./geo/segments.csv')
    geo_csv.drop(['geometry'], axis = 1, inplace = True)
    geo = pd.concat([geo_csv, geo['geometry']], axis = 1)

    geo_key = []
    for i in range(len(geo)):
        geo_key.append(str(geo['route'][i]) + '_' + geo['direct'][i].upper() + '_' + str(geo['mile_min'][i]) + '_' + str(geo['mile_max'][i]))
    geo['key'] = geo_key

    # load segments ids
    conn = getDatabaseConnection()
    SQL_Query = pd.read_sql_query(
    ''' SELECT *
          FROM [RealTimeLoopData].[dbo].[Segments]''', conn)
    segmentIDs = pd.DataFrame(SQL_Query)

    segmentIDs['route'] = segmentIDs['route'].apply(lambda x: x.strip())

    seg_key = []
    for i in range(len(segmentIDs)):
        seg_key.append(str(segmentIDs['route'][i]) + '_' + segmentIDs['mpdirection'][i].upper() + '_' + str(segmentIDs['milepost_small'][i]) + '_' + str(segmentIDs['milepost_large'][i]))
    segmentIDs['key'] = seg_key
    segment = geo.merge(segmentIDs, on = ['key'], how = 'inner')
    
    # create name
    segment['route_name'] = segment['route_x'].apply(route_map_func) 
    segment['direction_name'] = segment['direction'].apply(lambda x: x + 'B')
    segment['name'] = segment.apply(name_map_func, axis = 1)

    return segment



# def GetSegmentGeo():
#     # load geo
#     geo = pd.read_csv('SegmentsGeo.csv')

#     geo_key = []
#     for i in range(len(geo)):
#         geo_key.append(
#             str(geo['route'][i]) + '_' + geo['direct'][i].upper() + '_' + str(geo['mile_min'][i]) + '_' + str(
#                 geo['mile_max'][i]))
#     geo['key'] = geo_key

#     # st.write(geo)

#     # load segments ids
#     conn = getDatabaseConnection()
#     SQL_Query = pd.read_sql_query(
#         '''	SELECT *
#               FROM [RealTimeLoopData].[dbo].[Segments]''', conn)
#     segmentIDs = pd.DataFrame(SQL_Query)

#     segmentIDs['route'] = segmentIDs['route'].apply(lambda x: x.strip())

#     seg_key = []
#     for i in range(len(segmentIDs)):
#         seg_key.append(str(segmentIDs['route'][i]) + '_' + segmentIDs['mpdirection'][i].upper() + '_' + str(
#             segmentIDs['milepost_small'][i]) + '_' + str(segmentIDs['milepost_large'][i]))
#     segmentIDs['key'] = seg_key

#     # st.write(segmentIDs)

#     # merge
#     segment = geo.merge(segmentIDs, on=['key'], how='inner')

#     # st.write(segment)

#     return segment


def style_func_GP(feature):
    colormap = GetColormap()
    value = feature['properties']['TrafficIndex_GP']
    return {
        "color": colormap(value)
        if value is not None
        else "transparent"
    }

def style_func_HOV(feature):
    colormap = GetColormap()
    value = feature['properties']['TrafficIndex_HOV']
    return {
        "color": colormap(value)
        if value is not None
        else "transparent"
    }

def GetColormap():
    colormap = branca.colormap.LinearColormap(vmin = 60, 
                                        vmax= 100, 
                                        colors=['red','orange','yellow','#ccff66','darkgreen'],
                                       caption="Traffic Performance Score")

    return colormap


def GetToolTips():
    tooltip_GP = GeoJsonTooltip(
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
    return tooltip_GP, tooltip_HOV


def GenerateGeo(TPS):
    # st.write(TPS)
    segment = GetSegmentGeo()
    segment.rename(columns={"segmentid": "segmentID"}, inplace=True)

    # merge TPS with segment data
    data = segment.merge(TPS, on=['segmentID'], how='left')
    data.fillna(1, inplace=True)  # fill nan with zero, becuase Out of range float values are not JSON compliant: nan

    scaled_data = data
    scaled_data['TrafficIndex_GP'] = data['TrafficIndex_GP']*100
    scaled_data['TrafficIndex_HOV'] = data['TrafficIndex_HOV']*100

    # transform to geopandas dataframe
    data_gdf = geopandas.GeoDataFrame(scaled_data, crs=fiona.crs.from_epsg(4326))
    data_gdf['time'] = data_gdf['time'].apply(lambda x: pd.to_datetime(x).isoformat())

    m = folium.Map([47.673650, -122.260540], zoom_start=10, tiles="cartodbpositron")

    tooltip_GP, tooltip_HOV = GetToolTips()

    folium.GeoJson(data_gdf, style_function= style_func_GP, tooltip = tooltip_GP, name = 'GP Lane').add_to(m)
    folium.GeoJson(data_gdf, style_function= style_func_HOV, tooltip = tooltip_HOV, name = 'HOV Lane', show = False).add_to(m)

    colormap = GetColormap()
    colormap.add_to(m)
    # full screen plugins
    plugins.Fullscreen(
        position='topright',
        title='Expand me',
        title_cancel='Exit me',
        force_separate_button=True
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # folium.GeoJson('./data.geojson', style_function=style_function).add_to(m)

    # STREAMLIT_STATIC_PATH = "/Users/meixin/anaconda3/lib/python3.7/site-packages/streamlit/static/"

    # STREAMLIT_STATIC_PATH = 'C:\\Users\\Zhiyong\\Anaconda3\\Lib\\site-packages\\streamlit\\static\\'

    STREAMLIT_STATIC_PATH = os.path.dirname(st.__file__) + '\\static\\'

    # st.write(os.path.dirname(st.__file__) + '\\static')

    for filename in glob.glob(STREAMLIT_STATIC_PATH + 'map*'):
        os.remove(filename)

    filename_with_time = f'map_{time.time()}.html'
    map_path = STREAMLIT_STATIC_PATH + filename_with_time
    open(map_path, 'w').write(m._repr_html_())

    # st.markdown('Below is the traffic performance score by segments:' + dt_string)
    st.markdown(f'<iframe src="/{filename_with_time}" ; style="width:100%;height:500px;"> </iframe>',
                unsafe_allow_html=True)
# return m
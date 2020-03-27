#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import numpy as np
import time
import pypyodbc as pyodbc
import datetime
import pydeck as pdk
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image


#####################################################
# SQL query functions
#####################################################
#@st.cache(allow_output_mutation=True)
def getDatabaseConnection():
	return pyodbc.connect('DRIVER={SQL Server};SERVER=128.95.29.74;DATABASE=RealTimeLoopData;UID=starlab;PWD=star*lab1')

@st.cache
def getLoopDetectorLocation():
	conn = getDatabaseConnection()

	SQL_Query = pd.read_sql_query(
	'''	SELECT Distinct [CabName]
		      ,cab.[Lat]
		      ,cab.[Lon]
		  FROM [RealTimeLoopData].[dbo].[cabinets] as cab join [RealTimeLoopData].[dbo].[MinuteDataDefnNW] as def on cab.UnitName = def.id
		  WHERE SUBSTRING(def.id, 12, 2) = '_M' AND (SUBSTRING(def.id, 15, 3) = '___' OR SUBSTRING(def.id, 15, 3) = 'H__')
		  AND def.[covered_dist] > 0 AND def.[covered_dist] <= 2
		  AND [CabName] IS NOT NULL AND cab.[Lat] IS NOT NULL''', conn)

	return pd.DataFrame(SQL_Query)

@st.cache
def getTrafficIndex(date):
	conn = getDatabaseConnection()

	SQL_Query = pd.read_sql_query(
	'''SELECT *
	  FROM [RealTimeLoopData].[dbo].[TrafficIndex]
	  WHERE CAST([time] AS DATE) = ? ''', conn, params = [date])

	return pd.DataFrame(SQL_Query)


def getTrafficIndexMultiDays(sdate, edate):
    conn = getDatabaseConnection()

    SQL_Query = pd.read_sql_query(
    '''SELECT *
      FROM [RealTimeLoopData].[dbo].[TrafficIndex]
      WHERE time between ? and ?''', conn, params = [sdate,edate])

    return pd.DataFrame(SQL_Query)


def getTrafficIndexLoss(sdate, edate):
    conn = getDatabaseConnection()

    SQL_Query = pd.read_sql_query(
    '''	SELECT convert(varchar, CAST([time] AS DATE), 107) as Date, sum(1 - [TrafficIndex_GP]) as GP_loss, sum(1 - [TrafficIndex_HOV]) as HOV_loss
		FROM [RealTimeLoopData].[dbo].[TrafficIndex]
		WHERE CAST([time] AS DATE) between ? and ?
		GROUP BY CAST([time] AS DATE)
		ORDER BY CAST([time] AS DATE)
      	''', conn, params = [sdate,edate])

    return pd.DataFrame(SQL_Query)

def getDailyIndex(sdate, edate):
    conn = getDatabaseConnection()

    SQL_Query = pd.read_sql_query(
    '''	SELECT convert(varchar, CAST([time] AS DATE), 107) as Date, AVG([TrafficIndex_GP]) as daily_index_GP, AVG([TrafficIndex_HOV]) as daily_index_HOV
		FROM [RealTimeLoopData].[dbo].[TrafficIndex]
		WHERE CAST([time] AS DATE) BETWEEN ? AND ?
			AND ( (DATEPART(HOUR, [time]) >= 6 AND DATEPART(HOUR, [time]) <= 9) OR (DATEPART(HOUR, [time]) >= 15 and DATEPART(HOUR, [time]) <= 18) )
		GROUP BY CAST([time] AS DATE)
		ORDER BY CAST([time] AS DATE)
      	''', conn, params = [sdate,edate])

    return pd.DataFrame(SQL_Query)

def getMorningPeakVolume(sdate, edate):
    conn = getDatabaseConnection()

    SQL_Query = pd.read_sql_query(
    '''	SELECT convert(varchar, CAST([time] AS DATE), 107) as Date, AVG(AVG_Vol_GP) as AVG_Vol_GP, AVG(AVG_Vol_HOV) as AVG_Vol_HOV
		FROM [RealTimeLoopData].[dbo].[TrafficIndex]
		WHERE CAST([time] AS DATE) between ? and ?
			AND DATEPART(HOUR, [time]) >= 6 AND DATEPART(HOUR, [time]) <= 9
		GROUP BY CAST([time] AS DATE)
		ORDER BY CAST([time] AS DATE)
      	''', conn, params = [sdate,edate])

    return pd.DataFrame(SQL_Query)


def getEveningPeakVolume(sdate, edate):
    conn = getDatabaseConnection()

    SQL_Query = pd.read_sql_query(
    '''	SELECT convert(varchar, CAST([time] AS DATE), 107) as Date, AVG(AVG_Vol_GP) as AVG_Vol_GP, AVG(AVG_Vol_HOV) as AVG_Vol_HOV
		FROM [RealTimeLoopData].[dbo].[TrafficIndex]
		WHERE CAST([time] AS DATE) between ? and ?
			AND DATEPART(HOUR, [time]) >= 15 and DATEPART(HOUR, [time]) <= 18
		GROUP BY CAST([time] AS DATE)
		ORDER BY CAST([time] AS DATE)
      	''', conn, params = [sdate,edate])

    return pd.DataFrame(SQL_Query)


def getCOVID19Info():
	return pd.read_csv('Washington_COVID_Cases.csv') 

#####################################################
# display functions
#####################################################

def IntroduceTrafficIndex():
	###########
	# Sidebar #
	###########
	# st.sidebar.markdown("## Components")
	# st.sidebar.checkbox("Data Course")
	# st.sidebar.checkbox("Traffic Index Caculation")
	###########
	# Content #
	###########
	st.markdown("## Introduction to Traffic Index")
	st.markdown("## Data Source")
	showLoopDetectorMap()
	st.markdown("## Traffic Index Calculation")
	st.latex(r'''
		\text{Traffic Index} = \frac{\displaystyle\sum_{i=1}^n S_i * V_i * D_i }{ \displaystyle\sum_{i=1}^n V_i * D_i * 65 }
		''')
	st.markdown("where $S_i$, $V_i$, and $D_i$ represent the **S**peed, **V**olume, covered **D**istance "
				"of each road segment $i$, respectively. "
				"The unit of speed is mile per hour (mph) and the unit of covered distance is mile.")

	date = st.date_input('Pick a date', datetime.datetime.now().date())
	df_TI = getTrafficIndex(date)

	# df_TI['trafficindex_gp'] = df_TI['trafficindex_gp'] * 65
	# st.line_chart(df_TI[['trafficindex_gp', 'avg_spd_gp']])

	sampling_interval = 1
	data = df_TI.loc[::sampling_interval, ['time', 'trafficindex_gp', 'trafficindex_hov']]
	lw = 1  # line width
	# Create traces
	fig = go.Figure()
	fig.add_trace(go.Scatter(x=data['time'], y=data['trafficindex_gp'],
							 mode='lines', line=dict(dash='solid', width=lw),
							 name='Main lane'))

	fig.add_trace(go.Scatter(x=data['time'], y=data['trafficindex_hov'],
							 mode='lines', line=dict(dash='solid', width=lw),
							 name='HOV lane'))

	fig.update_layout(xaxis_title='Time', yaxis_title='Traffic Index',
					  legend = dict(x=.01, y=0.05),
					  margin = go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width = 700, height = 450)

	#fig.update_yaxes(range=[0, 1.1])

	st.write('Traffic index of today (', date, '):')

	st.plotly_chart(fig)

	dataFields = st.multiselect('Show Data',  list(df_TI.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
	st.write(df_TI[dataFields])


def showTrafficIndex():
	###########
	# Sidebar #
	###########
	st.sidebar.markdown("## Components")

	# index = st.sidebar.radio( "Display:", ("Daily Index", "Traffic Index per Minute", "Tabular Data"))
	daily_Index = st.sidebar.checkbox("Daily Index", value = True)
	minute_Index = st.sidebar.checkbox("Traffic Index per Minute")
	tablular_Data = st.sidebar.checkbox("Tabular Data")
	########################
	# main content
	########################
	sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
	edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
	st.write('From ',sdate, ' to ', edate,':')
	

	########################
	# Daily Traffic Index #
	########################
	if daily_Index:

		st.markdown("## Daily Traffic Index")

		df_DailyIndex = getDailyIndex(sdate, edate)
		df_DailyIndex['date'] = df_DailyIndex['date'].astype('datetime64[ns]')
		df_DailyIndex['date'] = df_DailyIndex['date'].dt.date

		data = df_DailyIndex[['date', 'daily_index_gp', 'daily_index_hov']]
		lw = 2  # line width
		# Create traces
		fig = go.Figure()
		fig.add_trace(go.Scatter(x=data['date'], y=data['daily_index_gp'],
								 mode='lines', line=dict(dash='solid', width=lw),
								 name='Main lane'))
		fig.add_trace(go.Scatter(x=data['date'], y=data['daily_index_hov'],
								 mode='lines', line=dict(dash='solid', width=lw),
								 name='HOV lane'))
		fig.update_layout(xaxis_title='Date', yaxis_title='Traffic Index',
						  legend=dict(x=.01, y=0.05),
						  margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width = 700, height = 450)
		st.plotly_chart(fig)

	########################
	# Minute Traffic Index 
	########################
	if minute_Index:

		st.markdown("## Traffic Index per Minute")

		df_TI_range = getTrafficIndexMultiDays(sdate, edate)

		sampling_interval = 1
		data = df_TI_range.loc[::sampling_interval, ['time', 'trafficindex_gp', 'trafficindex_hov']]
		lw = 1  # line width
		# Create traces
		fig = go.Figure()
		fig.add_trace(go.Scatter(x=data['time'], y=data['trafficindex_gp'],
								 mode='lines', line=dict(dash='solid', width=lw),
								 name='Main lane'))
		fig.add_trace(go.Scatter(x=data['time'], y=data['trafficindex_hov'],
								 mode='lines', line=dict(dash='solid', width=lw),
								 name='HOV lane'))
		fig.update_layout(xaxis_title='Time', yaxis_title='Traffic Index',
						  legend=dict(x=.01, y=0.05),
						  margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width = 700, height = 450)
		#fig.update_yaxes(range=[0, 1.1])
		st.plotly_chart(fig)

		
	########################
	# Minute Traffic Index 
	########################
	if tablular_Data:

		st.markdown("## Traffic Index Tablular Data")

		df_TI_range = getTrafficIndexMultiDays(sdate, edate)
		dataFields = st.multiselect('Show Data Type',  list(df_TI_range.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
		st.write(df_TI_range[dataFields])


def showDailyIndex():

	sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
	edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
	st.write('From ',sdate, ' to ',edate)

	df_DailyIndex = getDailyIndex(sdate, edate)
	df_DailyIndex['date'] = df_DailyIndex['date'].astype('datetime64[ns]')
	df_DailyIndex['date'] = df_DailyIndex['date'].dt.date

	data = df_DailyIndex[['date', 'daily_index_gp', 'daily_index_hov']]
	lw = 2  # line width
	# Create traces
	fig = go.Figure()
	fig.add_trace(go.Scatter(x=data['date'], y=data['daily_index_gp'],
							 mode='lines', line=dict(dash='solid', width=lw),
							 name='Main lane'))
	fig.add_trace(go.Scatter(x=data['date'], y=data['daily_index_hov'],
							 mode='lines', line=dict(dash='solid', width=lw),
							 name='HOV lane'))
	fig.update_layout(xaxis_title='Date', yaxis_title='Traffic Index',
					  legend=dict(x=.01, y=0.05),
					  margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width = 700, height = 450)
	st.plotly_chart(fig)

	# st.write(df_DailyIndex)

	st.write("<iframe src='https://public.flourish.studio/visualisation/1694092/embed' frameborder='0' scrolling='no' style='width:100%;height:600px;'></iframe><div style='width:100%!;margin-top:4px!important;text-align:right!important;'><a class='flourish-credit' href='https://public.flourish.studio/visualisation/1694092/?utm_source=embed&utm_campaign=visualisation/1694092' target='_top' style='text-decoration:none!important'><img alt='Made with Flourish' src='https://public.flourish.studio/resources/made_with_flourish.svg' style='width:105px!important;height:16px!important;border:none!important;margin:0!important;'> </a></div>", unsafe_allow_html=True)
	
	


def showRushHourVolume():
	###########
	# Sidebar #
	###########
	st.sidebar.markdown("## Components")
	rushHourVolume = st.sidebar.checkbox("Volume at Rush Hours", value = True)

	########################
	# main content
	########################
	if rushHourVolume:
		sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
		edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
		st.write('From ',sdate, ' to ',edate)

		df_mpv = getMorningPeakVolume(sdate, edate)
		df_mpv['date'] = df_mpv['date'].astype('datetime64[ns]')
		df_mpv.rename(columns = {'avg_vol_gp':'Morning_GP', 'avg_vol_hov':'Morning_HOV'}, inplace = True) 

		df_epv = getEveningPeakVolume(sdate, edate)
		df_epv['date'] = df_epv['date'].astype('datetime64[ns]')
		df_epv.rename(columns = {'avg_vol_gp':'Evening_GP', 'avg_vol_hov':'Evening_HOV'}, inplace = True) 

		df_pv = pd.merge(df_mpv, df_epv, on='date')
		df_pv.set_index('date')
		#print(list(df_pv.columns.values))
		dataFields = st.multiselect('Data fields', ['Morning_GP', 'Evening_GP', 'Morning_HOV', 'Evening_HOV'] , default = ['Morning_GP', 'Evening_GP'] )

		data = df_pv[['date'] + dataFields]
		lw = 2  # line width
		# Create traces
		fig = go.Figure()
		for item in dataFields:
			fig.add_trace(go.Scatter(x=data['date'], y=data[item],
								 mode='lines', line=dict(dash='solid', width=lw),
								 name=item))

		fig.update_layout(xaxis_title='Date', yaxis_title='Traffic Volume',
						  legend=dict(x=.01, y=0.05),
						  margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width = 700, height = 450)

		st.plotly_chart(fig)

	#st.line_chart(df_pv[dataFields], use_container_width=True)

def showLoopDetectorMap():	
	df_loop_location = getLoopDetectorLocation()

	st.pydeck_chart(pdk.Deck(
		map_style='mapbox://styles/mapbox/dark-v9',
		# map_style='mapbox://styles/mapbox/light-v9',
			initial_view_state=pdk.ViewState(
			latitude=47.59,
			longitude=-122.24,
			zoom=10,
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

def showCOVID19():
	st.markdown("## Impact of COVID-19")

	sdate = datetime.datetime(2020, 2, 28)
	edate = datetime.datetime(2020, 3, 25)
	df_DailyIndex = getTrafficIndexLoss(sdate, edate)
	df_DailyIndex['date'] = df_DailyIndex['date'].astype('datetime64[ns]')
	

	df_DailyIndex = df_DailyIndex[['date', 'gp_loss', 'hov_loss']]
	
	# get COVID info
	df_COVID19 = getCOVID19Info()
	df_COVID19['date'] = df_DailyIndex['date'].astype('datetime64[ns]')

	data = pd.merge(df_DailyIndex, df_COVID19, on='date')
	# data['date'] = data['date'].dt.date

	# st.write(data)

	lw = 2  # line width




	# Create figure with secondary y-axis
	fig = make_subplots(specs=[[{"secondary_y": True}]])

	# Add traces for axis-2
	fig.add_trace(go.Scatter(x=data['date'], y=data['gp_loss'],
							 mode='lines', line=dict(dash='dot', width=lw, color='#1f77b4'),
							 name='Index - GP',
							 legendgroup='group2'),
					secondary_y=False)
	fig.add_trace(go.Scatter(x=data['date'], y=data['hov_loss'],
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
	fig.add_trace(go.Scatter(x=data['date'], y=data['total death'],
							 mode='lines+markers', line=dict(dash='solid', width=lw, color='black'),
							 name='Total Death',
							 legendgroup='group1'),
					secondary_y=True)
	

	fig.update_traces(textposition='top center')
	# Set x-axis title
	fig.update_xaxes(title_text="Date")
	# Set y-axes titles
	fig.update_yaxes(title_text="Daily Traffic Index", 
						showline=True, 
						linecolor='rgb(204, 204, 204)', 
						linewidth=2, 
						showticklabels=True, 
						ticks='outside', 
						secondary_y=False)
	fig.update_yaxes(title_text="COVID-19 Case Amount", 
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
						legend=dict(x= 0.3, y=1.0, orientation="h"),
					  	margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), 
					  	width = 700, 
					  	height = 450,
					  	plot_bgcolor='white')
	st.plotly_chart(fig)


#####################################################
# Main
#####################################################
def main():
	# hide upper-right menu
	hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
	st.markdown(hide_menu_style, unsafe_allow_html=True)

	st.title("Traffic Index in Seattle Area")

	st.sidebar.title("Traffic Index")
	app_mode = st.sidebar.radio("Navitation",
	        ["Home", "Traffic Index", "Impact of COVID-19", "Other Traffic Metrics"])
	# st.sidebar.markdown("[![this is an image link](./images/STARLab.png)](https://streamlit.io)")
	if  app_mode == "Home":
		IntroduceTrafficIndex()
	elif app_mode == "Traffic Index":
		showTrafficIndex()
	elif app_mode == "Impact of COVID-19":
		showCOVID19()
	# elif app_mode == "Daily Index":
	# 	showDailyIndex()
	elif app_mode == "Other Traffic Metrics":
		showRushHourVolume()


	st.sidebar.title("About")
	st.sidebar.info(
	        "This an open source project developed and maintained by the "
	        "Artificial Intelligence GROUP of [UW STAR Lab](http://www.uwstarlab.org/), University of Washington. "
	        "If you want to contribute to this project, "
	        "please contact the Project Initiator:"
	        " &nbsp;"
	        "[Prof. Yinhai Wang](https://www.ce.washington.edu/facultyfinder/yinhai-wang) ([yinhai@uw.edu](mailto:yinhai@uw.edu))."
	        )

	image_starlab = Image.open('images/STARLab.png')
	st.sidebar.image(image_starlab, width = 240, use_column_width=False)

	# image_uw = Image.open('images/UW2.png')
	# st.sidebar.image(image_uw, width = 300, use_column_width=False)

if __name__ == '__main__':
	main()
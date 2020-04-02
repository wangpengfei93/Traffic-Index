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
from requests_html import HTMLSession
import locale


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
	st.markdown("Traffic index can help us eaisly and intuitively understand the overall performance of urban traffic network. "
				"In this website, we provide a traffic index to quantify the overall traffic condition in Seattle area. "
				"With this website, you can view "
				"\n * Traffic index with different temporal resolutions, ranging from one minute to one day. "
				"\n * Traffic index of general purpose (GP) and HOV lanes. "
				"\n * Impact of COVID-19 on urban traffic reflected by the traffic index. "
				"\n * And other traffic performance metrics. " )
	
	st.markdown( "If you want to check more information, please select on the left navigation panel. Enjoy! :sunglasses:")
	
	#################################################################
	st.markdown("## Today's Traffic Index")
	date = st.date_input('Please pick a date', datetime.datetime.now().date())
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

	# dataFields = st.multiselect('Show Data',  list(df_TI.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
	# st.write(df_TI[dataFields])

	#################################################################
	st.markdown("## Data Source")
	st.markdown("The traffic index is calcualted based on the data collected from more than 44800 inductive loop detector deployed on the freeways in Seattle area, "
				"including I-5, I-90, I-405, SR-520, etc. The raw data comes from Washington State Department of Transportation (WSDOT). "
				"Representative decectors are shown in the following map. ")
	showLoopDetectorMap()

	#################################################################
	st.markdown("## Traffic Index Calculation")
	st.markdown("The raw data contains lane-wise **S**peed, **V**olume, and **O**ccupancy information collected by each loop detector. "
				"Each detector's meta data, including detector category, route, milepost, director, direction, address, etc., are also available. "
				"Based on the consecutive detectors' location information, we seperate the freeways into segments, "
				"each of which only contains one loop detector per lane. We a road segment's length is the corresponding detector's covered length. "
				"The time interval of the data is one-minute. ")
	st.markdown("The **Traffic Index** (**TI**) at time $t$ is calculated using the following equation:")
	st.latex(r'''
		\text{TI}_t = \frac{\displaystyle\sum_{i=1}^n S_t^i * V_t^i * D_t^i }{ \displaystyle\sum_{i=1}^n V_t^i * D_t^i * 65 }
		''')
	st.markdown("where $S_t^i$, $V_t^i$, and $D_t^i$ represent the **S**peed, **V**olume, covered **D**istance "
				"of each road segment $i$ at time $t$, respectively. "
				"The unit of speed is mile per hour (mph), and we set 65 as the upper limit of the speed. "
				"The unit of covered distance is mile.")
	st.markdown("In this way, the **TI** is a value ranges from 0 to 1 ($TI \in [0,1]$). "
				"The closer to one the **TI** is, the better the overall network-wide traffic condition is. ")


	


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

	st.markdown("In this section, we provide the traffic index over a period. Please pick the starting and ending date. "
		"You can check or uncheck the checkbox in the left panel to adjuect the displayed information.")
	# sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
	# edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
	# st.write('From ',sdate, ' to ', edate,':')
	

	########################
	# Daily Traffic Index #
	########################
	if daily_Index:
		st.markdown("## Daily Traffic Index")

		sdate_DI = st.date_input('Pick a start date for Daily Traffic Index', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
		edate_DI = st.date_input('Pick an end date for Daily Traffic Index' , value = datetime.datetime.now().date())
		st.write('From ',sdate_DI, ' to ', edate_DI,':')

		df_DailyIndex = getDailyIndex(sdate_DI, edate_DI)
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

		sdate_MI = st.date_input('Pick a start date:', value = (datetime.datetime.now() - datetime.timedelta(days=7)))
		edate_MI = st.date_input('Pick an end date:', value = datetime.datetime.now().date())
		st.write('From ',sdate_MI, ' to ', edate_MI,':')

		df_TI_range = getTrafficIndexMultiDays(sdate_MI, edate_MI)

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

		sdate_TD = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=1)))
		edate_TD = st.date_input('Pick an end date', value = datetime.datetime.now().date())
		st.write('From ',sdate_TD, ' to ', edate_TD,':')

		df_TI_range = getTrafficIndexMultiDays(sdate_TD, edate_TD)
		dataFields = st.multiselect('Show Data Type',  list(df_TI_range.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
		st.write(df_TI_range[dataFields])

		
		
def get_data_from_sel(sel):
    mylist = []
    try:
        results = r.html.find(sel)
        for result in results:
            mytext = result.text
            mylist.append(mytext)
        return mylist
    except:
        return None



def get_data_from_wikipedia (url):
    session = HTMLSession()
    r = session.get(url)
    sel_date = '#mw-content-text > div > div.barbox.tright > div > table > tbody > tr > td:nth-child(1)'
    sel_cases = '#mw-content-text > div > div.barbox.tright > div > table > tbody > tr > td:nth-child(3) > span > span:nth-child(1)'
    
    date_list = get_data_from_sel(sel_date)
    del date_list[len(date_list)-1]
    del date_list[0]
    cases_list_0 = get_data_from_sel(sel_cases)
    locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )
    cases_list = [];
    for n in cases_list_0:
        cases_list.append(locale.atoi(n))
    
    df = pd.DataFrame(date_list, columns=['date'])
    df['confirmed case'] = cases_list
    df['new case'] = df['new case'] - df['new case'].shift(1)
    df.loc[0,'new case'] = 0
    return df

		
		
def showCOVID19():
	

	st.markdown("## COVID-19 in Washington State")
	st.markdown("Since the early March 2020, the coronavirus start to outbreak in the US. "
				"Besides affecting public health, COVID-19 also has great impact on public transportation, "
				"especially when public business and public agencies shut down. Representative responses are listed as below: [\[source\]](https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Washington_(state))")
	st.markdown("* **March 6**: Major tech companies ask Seattle employees to work from home. Amazon and Facebook have shut down individual offices as well. [\[link\]](https://www.theverge.com/2020/3/5/21166686/coronavirus-amazon-google-facebook-microsoft-twitter-seattle-staff-remote-work)\n"
				"* **March 9**: UW suspends on-site classes and finals. [\[link\]](https://www.washington.edu/coronavirus/2020/03/06/beginning-march-9-classes-and-finals-will-not-be-held-in-person-message-to-students/) \n"
				"* **March 13**: Gov. Inslee announces statewide school closures, expansion of limits on large gatherings. [\[link\]](https://medium.com/wagovernor/inslee-announces-statewide-school-closures-expansion-of-limits-on-large-gatherings-63d442111438) \n"
				"* **March 16**: Gov. Inslee announces statewide shutdown of restaurants, bars and expanded social gathering limits. [\[link\]](https://www.governor.wa.gov/news-media/inslee-statement-statewide-shutdown-restaurants-bars-and-limits-size-gatherings-expanded) \n"
				"* **March 23**: Gov. Inslee announces \"Stay Home, Stay Healthy\" order. [\[link\]](https://www.governor.wa.gov/news-media/inslee-announces-stay-home-stay-healthy%C2%A0order)")
	#################################################################
	st.markdown("## COVID-19 Cases")
	st.markdown("The following dynamic plot displays the process of the coronavirus cases in Washington State.")
	st.write("<iframe src='https://public.flourish.studio/visualisation/1696713/embed' frameborder='0' scrolling='no' style='width:100%;height:600px;'></iframe><div style='width:100%!;margin-top:4px!important;text-align:right!important;'><a class='flourish-credit' href='https://public.flourish.studio/visualisation/1696713/?utm_source=embed&utm_campaign=visualisation/1696713' target='_top' style='text-decoration:none!important'><img alt='Made with Flourish' src='https://public.flourish.studio/resources/made_with_flourish.svg' style='width:105px!important;height:16px!important;border:none!important;margin:0!important;'> </a></div>", unsafe_allow_html=True)
	
	#################################################################
	st.markdown("## Impact of COVID-19 on Urban Traffic")
	st.markdown("This section shows the impact of COVID-19 on urban traffic. "
				"In the following chart, the trends of traffic indices and the coronavirus cases are displayed together.")
	
	# get COVID info
	url = 'https://en.wikipedia.org/wiki/Template:2019%E2%80%9320_coronavirus_pandemic_data/United_States/Washington_State_medical_cases_chart'
	df_COVID19 = get_data_from_wikipedia(url)
	df_COVID19['date'] = df_COVID19['date'].astype('datetime64[ns]')
	
	sdate = datetime.datetime(2020, 2, 28)
	edate = df_COVID19[len(df_COVID19)-1, 'date']
	
	#################################################################
	# daily index
	df_DailyIndex = getDailyIndex(sdate, edate)
	df_DailyIndex['date'] = df_DailyIndex['date'].astype('datetime64[ns]')
	df_DailyIndex = df_DailyIndex[['date', 'daily_index_gp', 'daily_index_hov']]

	# # peak volume
	# df_mpv = getMorningPeakVolume(sdate, edate)
	# df_mpv['date'] = df_mpv['date'].astype('datetime64[ns]')
	# df_mpv.rename(columns = {'avg_vol_gp':'Morning_GP', 'avg_vol_hov':'Morning_HOV'}, inplace = True) 
	# df_epv = getEveningPeakVolume(sdate, edate)
	# df_epv['date'] = df_epv['date'].astype('datetime64[ns]')
	# df_epv.rename(columns = {'avg_vol_gp':'Evening_GP', 'avg_vol_hov':'Evening_HOV'}, inplace = True) 
	# df_pv = pd.merge(df_mpv, df_epv, on='date')
	
	
	data = pd.merge(df_DailyIndex, df_COVID19, on='date')

	lw = 2  # line width

	# Create figure with secondary y-axis
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
	#fig.add_trace(go.Scatter(x=data['date'], y=data['total death'],
	#						 mode='lines+markers', line=dict(dash='solid', width=lw, color='black'),
	#						 name='Total Death',
	#						 legendgroup='group1'),
	#				secondary_y=True)
	

	fig.update_traces(textposition='top center')
	# Set x-axis title
	fig.update_xaxes(title_text="Date")
	# Set y-axes titles
	fig.update_yaxes(title_text="Daily Traffic Index", 
						range=[0.7, 1], 
						showline=True, 
						linecolor='rgb(204, 204, 204)', 
						linewidth=2, 
						showticklabels=True, 
						ticks='outside', 
						secondary_y=False)
	fig.update_yaxes(title_text="COVID-19 Case Amount",
						range=[0, 5000], 
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
	st.plotly_chart(fig)


def showOtherMetrics():
	###########
	# Sidebar #
	###########
	st.sidebar.markdown("## Components")
	rushHourVolume = st.sidebar.checkbox("Volume at Rush Hours", value = True)

	
	########################
	# main content
	########################
	st.markdown("## Other Traffic Performance Metrics")
	sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
	edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
	st.write('From ',sdate, ' to ',edate)
	if rushHourVolume:
		st.markdown("### Volume per Lane at Rush Hours")
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

		fig.update_layout(xaxis_title='Date', yaxis_title='Traffic Volume per Lane',
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
	elif app_mode == "Other Traffic Metrics":
		showOtherMetrics()


	st.sidebar.title("About")
	st.sidebar.info(
        "This an open source project developed and maintained by the "
        "Artificial Intelligence GROUP in the [Smart Transportation Application and Research Lab (STAR Lab)](http://www.uwstarlab.org/) at the University of Washington. "
	        
	)
	st.sidebar.title("Contribute")
	st.sidebar.info(
		"If you want to contribute to this project or collaborate with us, "
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

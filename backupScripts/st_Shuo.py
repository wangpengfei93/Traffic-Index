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

@st.cache
def getCOVID19Info():
	return pd.read_csv('Washington_COVID_Cases.csv')  

#####################################################
# display functions
#####################################################

def IntroduceTrafficIndex():
	st.title("About TRAFFIX")
	st.markdown("Our TRAFFIX shows the real-time and historical traffic condition of partial main lanes in Seattle area. "
				"We provide a traffic index to quantify the traffic condition. "
				"You can view how the traffic varies for any time period you select even to minutes. "
				"We show the index of normal(GP) and HOV lane in each figure separately. "
				"In the home page, you can find out the traffic index for today. "
				"We also provide the daily index, the rush hour volumn analysis and the traffic with COVID19."
				"If you want to check more information, just feel free to select on the left panel!:sunglasses:")
	st.header("Data Source")
	st.markdown("Data is officially provided by **Washington State Department of Transportation**, covering **18** lanes in Washington, "
				"including I5, I90, I99, I405, I520, I522 and so on. ")
	showLoopDetectorMap()
	st.header("Traffic Index Calculation")
	st.markdown("The traffic index is defined by weighted average speed of traffic and road length. The ideal index value is 1."
				"The smaller the index value, the worse the traffic conditions."
				"The formula is as follows:")
	st.latex(r'''
		\text{Traffic Index} = \frac{\displaystyle\sum_{i=1}^n S_i * V_i * D_i }{ \displaystyle\sum_{i=1}^n V_i * D_i * 65 }
		''')
	st.markdown("where $S_i$, $V_i$, and $D_i$ represent the **S**peed, **V**olume, covered **D**istance "
				"of each road segment $i$, respectively. "
				"The unit of speed is mile per hour (mph) and the unit of covered distance is mile. "
				"The average speed is 65 miles/h.")
	st.header("Show index")
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

	dataFields = st.multiselect('Show Data in Data Frame',  list(df_TI.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
	st.write(df_TI[dataFields])


def showTrafficIndexPreriod():
	st.title("TRAFFIX")
	st.markdown("Select the date below. TRAFFIX will show you the index. "
				"You can find more details about our traffic index on the home page. "
				"Try to zoom in or out to check index with variable time scales!")
	sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=7)))
	edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
	st.write('Traffic index from ',sdate, ' to ', edate,':')

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

	dataFields = st.multiselect('Show Data in Data Frame',  list(df_TI_range.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
	st.write(df_TI_range[dataFields])


def showDailyIndex():
	st.title("Daily Index")
	st.markdown("We provide Daily Index for each day. Daily Index is calculated by the sum of daily index loss."
				"A larger daily index value means worse traffic conditions.")
	sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
	edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
	st.write('From ',sdate, ' to ',edate)

	df_TI_loss_range = getTrafficIndexLoss(sdate, edate)
	df_TI_loss_range['date'] = df_TI_loss_range['date'].astype('datetime64[ns]')
	df_TI_loss_range['date'] = df_TI_loss_range['date'].dt.date

	data = df_TI_loss_range[['date', 'gp_loss', 'hov_loss']]
	lw = 2  # line width
	# Create traces
	fig = go.Figure()
	fig.add_trace(go.Scatter(x=data['date'], y=data['gp_loss'],
							 mode='lines', line=dict(dash='solid', width=lw),
							 name='Main lane'))
	fig.add_trace(go.Scatter(x=data['date'], y=data['hov_loss'],
							 mode='lines', line=dict(dash='solid', width=lw),
							 name='HOV lane'))
	fig.update_layout(xaxis_title='Date', yaxis_title='Traffic Index',
					  legend=dict(x=.01, y=0.05),
					  margin=go.layout.Margin(l=50, r=0, b=50, t=10, pad=4), width = 700, height = 450)
	st.plotly_chart(fig)
	st.markdown("Show Data in Data Frame")
	st.write(df_TI_loss_range)

def showRushHourVolume():
	st.title("Rush Hour Volumn")
	st.markdown("Rush Hour is crucial for traffic mobility and traffic analysis. "
				"Here you can get traffic volumns during morning rush hour(6:00 am ~ 9:00 am) and evening rush hours(3:00 pm ~ 6:00 pm)."
				"Pick your date!")
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

	df = getCOVID19Info()
	st.write(df)

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
	image_starlab = Image.open('images/STARLab.png')
	st.sidebar.image(image_starlab, width=240, use_column_width=False)
	st.sidebar.title("Navigation")
	app_mode = st.sidebar.radio("Choose the app mode",
	        ["Home", "Traffic Index", "Impact of COVID-19", "Daily Index", "Rush Hour Volume"])
	# st.sidebar.markdown("[![this is an image link](./images/STARLab.png)](https://streamlit.io)")

	if  app_mode == "Home":
		IntroduceTrafficIndex()
	elif app_mode == "Traffic Index":
		showTrafficIndexPreriod()
	elif app_mode == "Daily Index":
		showDailyIndex()
	elif app_mode == "Rush Hour Volume":
		showRushHourVolume()
	elif app_mode == "Impact of COVID-19":
		showCOVID19()

	st.sidebar.title("About")
	st.sidebar.info(
	        "This an open source project developed and maintained by the "
	        "AI GROUP of [STAR Lab](http://www.uwstarlab.org/), University of Washington. "
	        "If you want to contribute to this project, "
	        "please contact the Project Initiator:"
	        " &nbsp;"
	        "[Prof. Yinhai Wang](https://www.ce.washington.edu/facultyfinder/yinhai-wang) ([yinhai@uw.edu](mailto:yinhai@uw.edu))."
	        )



	# image_uw = Image.open('images/UW2.png')
	# st.sidebar.image(image_uw, width = 300, use_column_width=False)

if __name__ == '__main__':
	main()
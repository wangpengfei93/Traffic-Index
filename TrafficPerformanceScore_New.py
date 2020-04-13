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
import folium

from SQLquery import *
from Figures import *

#####################################################
# SQL query functions
#####################################################
#@st.cache(allow_output_mutation=True)


#@st.cache


#####################################################
# display functions
#####################################################

def IntroduceTrafficIndex():
    ###########
    # Sidebar #
    ###########
    # st.sidebar.markdown("## Components")
    # st.sidebar.checkbox("Data Course")
    # st.sidebar.checkbox("Traffic Performance Score Caculation")
    ###########
    # Content #
    ###########
    st.markdown("# Traffic Performance Score in Seattle Area")
    st.markdown("## Introduction to Traffic Performance Score")
    st.markdown("Traffic Performance Score (TPS) can intuitively indicate the overall performance of urban traffic networks. "
                "In this website, the TPS is calculated and visualized to quantify the overall traffic condition in the Seattle area. "
                "With this website, you can view "
                "\n * The TPS with different temporal resolutions, ranging from one minute to one day. "
                "\n * The TPS of general purpose (GP) and HOV lanes. "
                "\n * Impact of COVID-19 on urban traffic reflected by the TPS. "
                "\n * Other traffic performance metrics. " )

    st.markdown( "To view more information, please select on the left navigation panel. Enjoy! :sunglasses:")

    #################################################################
    st.markdown("## Today's Traffic Performance Score")
    # date = st.date_input('Please select a date', datetime.datetime.now().date())
    date = datetime.datetime.now().date()
    df_TI = getTrafficIndex(datetime.datetime.now().date())

    # remove outliers from HOV traffic index
    df_TI.loc[df_TI['avg_vol_hov'] == 0, 'trafficindex_hov'] = 1.0

    df_TI['trafficindex_gp'] = df_TI['trafficindex_gp'] * 100
    # df_TI['trafficindex_gp'] = df_TI['trafficindex_gp'].astype('int64')
    df_TI['trafficindex_hov'] = df_TI['trafficindex_hov'] * 100
    # df_TI['trafficindex_hov'] = df_TI['trafficindex_hov'].astype('int64')

    # df_TI['trafficindex_gp'] = df_TI['trafficindex_gp'] * 65
    # st.line_chart(df_TI[['trafficindex_gp', 'avg_spd_gp']])
    sampling_interval = 1
    data = df_TI.loc[::sampling_interval, ['time', 'trafficindex_gp', 'trafficindex_hov']]

    fig = plotTPS(data, date_or_time = 'time', lw = 1)
    st.plotly_chart(fig)

    # dataFields = st.multiselect('Show Data',  list(df_TI.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
    # st.write(df_TI[dataFields])

    #################################################################
    st.markdown("## Data Source")
    st.markdown("The TPS is calculated based on data collected from more than 44800 inductive loop detectors deployed on freeways in Seattle, WA area. "
                "Freeways include: I-5, I-90, I-99, I-167, I-405, and SR-520. The raw data comes from Washington State Department of Transportation (WSDOT). "
                "Representative detectors are shown in the following map. ")
    showLoopDetectorMap()

    #################################################################
    st.markdown("## Traffic Performance Score Calculation")
    st.markdown("The raw data contains lane-wise **S**peed, **V**olume, and **O**ccupancy information collected by each loop detector. "
                "Each detector's meta data includes detector category, route, milepost, director, direction, address. "
                "Based on the consecutive detectors' location information, we separate the freeways into segments, "
                "each of which only contains one loop detector per lane. We consider a road segment's length is the corresponding detector's covered length. "
                "The time interval of the data is one-minute. ")
    st.markdown("The **Traffic Performance Score** (**TPS**) at time $t$ is calculated using the following equation:")
    st.latex(r'''
        \text{TPS}_t = \frac{\displaystyle\sum_{i=1}^n S_t^i * V_t^i * D_t^i }{ \displaystyle\sum_{i=1}^n V_t^i * D_t^i * 65 } * 100\%
        ''')
    st.markdown("where $S_t^i$, $V_t^i$, and $D_t^i$ represent the **S**peed, **V**olume, covered **D**istance "
                "of each road segment $i$ at time $t$, respectively. "
                "The unit of speed is mile per hour (mph), and we set 65 as the upper limit of the speed. "
                "The unit of covered distance is mile.")
    st.markdown("In this way, the **TPS** is a value ranges from 0 to 1.0 ($TPS \in [0,1.0]$). "
                "The closer to one the **TPS** is, the better the overall network-wide traffic condition is. ")



def showTrafficIndex():
    ###########
    # Sidebar #
    ###########
    # st.sidebar.markdown("## Components")

    # index = st.sidebar.radio( "Display:", ("Daily Index", "Traffic Performance Score per Minute", "Tabular Data"))
    # daily_Index = st.sidebar.checkbox("Daily Index", value = True)
    # minute_Index = st.sidebar.checkbox("Traffic Performance Score per Minute")
    # tablular_Data = st.sidebar.checkbox("Tabular Data")
    daily_Index, five_minute_Index, tablular_Data = True, True, True
    ########################
    # main content
    ########################
    st.markdown("# Traffic Performance Score")
    st.markdown("In this section, the TPS is provided based on selected start and end dates. ")
        # "You can check or uncheck the checkbox in the left panel to adjuect the displayed information.")
    # sdate = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
    # edate = st.date_input('Pick an end date', value = datetime.datetime.now().date())
    # st.write('From ',sdate, ' to ', edate,':')


    ########################
    # Daily Traffic Performance Score #
    ########################

    if daily_Index:
        st.markdown("## Daily Traffic Performance Score")

        sdate_DI = st.date_input('Select a start date for Daily Traffic Performance Score', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
        edate_DI = st.date_input('Select an end date for Daily Traffic Performance Score' , value = datetime.datetime.now().date())
        st.write('From ',sdate_DI, ' to ', edate_DI,':')

        df_DailyIndex = getDailyIndex(sdate_DI, edate_DI)

        df_DailyIndex['date'] = df_DailyIndex['date'].astype('datetime64[ns]')
        df_DailyIndex['date'] = df_DailyIndex['date'].dt.date

        df_DailyIndex['daily_index_gp'] = df_DailyIndex['daily_index_gp'] * 100
        # df_DailyIndex['daily_index_gp'] = df_DailyIndex['daily_index_gp'].astype('int64')
        df_DailyIndex['daily_index_hov'] = df_DailyIndex['daily_index_hov'] * 100
        # df_DailyIndex['daily_index_hov'] = df_DailyIndex['daily_index_hov'].astype('int64')

        data = df_DailyIndex[['date', 'daily_index_gp', 'daily_index_hov']]
        fig = plotTPS(data, date_or_time = 'date', lw = 2)
        st.plotly_chart(fig)

    ########################
    # Minute Traffic Performance Score
    ########################
    if five_minute_Index:

        st.markdown("## Traffic Performance Score per 5-Minute")

        sdate_MI = st.date_input('Pick a start date:', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
        edate_MI = st.date_input('Pick an end date:', value = datetime.datetime.now().date())
        st.write('From ',sdate_MI, ' to ', edate_MI,':')

        df_TI_range = getTrafficIndexMultiDays(sdate_MI, edate_MI)

        # remove outliers from HOV traffic index
        df_TI_range.loc[df_TI_range['avg_vol_hov'] == 0, 'trafficindex_hov'] = 1.0

        df_TI_range['trafficindex_gp'] = df_TI_range['trafficindex_gp'] * 100
        # df_TI_range['trafficindex_gp'] = df_TI_range['trafficindex_gp'].astype('int64')
        df_TI_range['trafficindex_hov'] = df_TI_range['trafficindex_hov'] * 100
        # df_TI_range['trafficindex_hov'] = df_TI_range['trafficindex_hov'].astype('int64')

        sampling_interval = 1
        data = df_TI_range.loc[::sampling_interval, ['time', 'trafficindex_gp', 'trafficindex_hov']]
        fig = plotTPS(data, date_or_time='time', lw=1)
        st.plotly_chart(fig)


    ########################
    # Minute Traffic Performance Score
    ########################
    if tablular_Data:
        st.markdown("## Traffic Performance Score Tablular Data")

        sdate_TD = st.date_input('Pick a start date', value = (datetime.datetime.now() - datetime.timedelta(days=1)))
        edate_TD = st.date_input('Pick an end date', value = datetime.datetime.now().date())
        st.write('From ',sdate_TD, ' to ', edate_TD,':')

        df_TI_range = getTrafficIndexMultiDays(sdate_TD, edate_TD)

        # remove outliers from HOV traffic index
        df_TI_range.loc[df_TI_range['avg_vol_hov'] == 0, 'trafficindex_hov'] = 1.0
        df_TI_range['trafficindex_gp'] = df_TI_range['trafficindex_gp'] * 100
        df_TI_range['trafficindex_hov'] = df_TI_range['trafficindex_hov'] * 100
        # df_TI_range.columns = ""

        dataFields = st.multiselect('Show Data Type',  list(df_TI_range.columns.values), default = ['time', 'trafficindex_gp', 'trafficindex_hov'] )
        st.write(df_TI_range[dataFields])


def showSegmentTPS():
    st.markdown("# Segment-based Traffic Preformance Score")

    date = st.date_input('Pick an end date', value = datetime.datetime.now().date())


    datatime1 = datetime.datetime.combine(date, datetime.time(00, 00))
    datatime2 = datetime.datetime.combine(date, datetime.time(23, 59))
    # st.write(datatime2)

    df_SegTPS_5Min = getSegmentTPS_5Min(datatime1, datatime2)
    df_SegTPS_5Min.columns = ['time', 'segmentID', 'AVG_Spd_GP', 'AVG_Spd_HOV', 'AVG_Vol_GP', 'AVG_Vol_HOV', 'TrafficIndex_GP', 'TrafficIndex_HOV']
    # time = st.time_input('Pick an end date', value = datetime.datetime.now().time())
    # time = time.replace(second=0, microsecond=0)
    # dt = datetime.datetime.combine(date, time)
    # st.write(dt)
    # st.write(df_SegTPS_5Min)
    # st.write(df_SegTPS_5Min[df_SegTPS_5Min['time'] == dt])

    dt = st.selectbox(
        'Select a time',
        df_SegTPS_5Min['time'].astype(str).unique().tolist()
    )

    data = df_SegTPS_5Min[df_SegTPS_5Min['time'] == dt]
    # st.write(data)
    GenerateGeo(data)
    # map.save('index.html')
    # # st.write(m._repr_html_(), unsafe_allow_html=True)
    # st.write(map._repr_html_(), unsafe_allow_html=True)

    #####
    st.markdown("# Route-based Traffic Preformance Score")

    sdate = st.date_input('Select a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
    edate = st.date_input('Select an end date' , value = datetime.datetime.now().date())

    st.write('From ',sdate, ' to ', edate)

    segments = getSegments()
    segments['label'] = 'Route (' + segments['route'].astype(int).astype(str) + '),\t Direction (' + segments['direction'] + 'B),\t Milepost (' \
                        + segments['milepost_small'].astype(int).astype(str) + ', ' + segments['milepost_large'].astype(int).astype(str) + ')'

    segmentLabel = st.selectbox("", segments['label'].iloc[0:10].values.tolist())
    segmentID = segments[segments['label'] == segmentLabel]['segmentid'].values.tolist()[0]
    # st.write(segmentID.values.tolist()[0])
    df_SegTPS_Day = getSegmentTPS_Day(sdate, edate, segmentID)

    # st.write(segments['label'])

    # remove outliers from HOV traffic index
    df_SegTPS_Day.loc[df_SegTPS_Day['avg_vol_hov'] == 0, 'trafficindex_hov'] = 1.0

    df_SegTPS_Day['trafficindex_gp'] = df_SegTPS_Day['trafficindex_gp'] * 100
    # df_TI_range['trafficindex_gp'] = df_TI_range['trafficindex_gp'].astype('int64')
    df_SegTPS_Day['trafficindex_hov'] = df_SegTPS_Day['trafficindex_hov'] * 100

    fig = plotTPS(df_SegTPS_Day, date_or_time='time', lw=1)

    st.plotly_chart(fig)


def showCOVID19():

    st.markdown("# Impact of COVID-19 on Urban Traffic")
    st.markdown("## COVID-19 in Washington State")
    st.markdown("Since the early March 2020, the coronavirus outbreak has taken hold in the United States. "
                "Besides affecting public health, COVID-19 also has greatly impacted the whole transportation network, "
                "especially when businesses and public agencies shut down. The timeline of responses are listed as below: [\[source\]](https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Washington_(state))")
    st.markdown("* **March 6**: Major tech companies ask Seattle employees to work from home. Amazon and Facebook shut down individual offices as well. [\[link\]](https://www.theverge.com/2020/3/5/21166686/coronavirus-amazon-google-facebook-microsoft-twitter-seattle-staff-remote-work)\n"
                "* **March 9**: UW suspends on-site classes and finals. [\[link\]](https://www.washington.edu/coronavirus/2020/03/06/beginning-march-9-classes-and-finals-will-not-be-held-in-person-message-to-students/) \n"
                "* **March 13**: Gov. Inslee announces statewide school closures, expansion of limits on large gatherings. [\[link\]](https://medium.com/wagovernor/inslee-announces-statewide-school-closures-expansion-of-limits-on-large-gatherings-63d442111438) \n"
                "* **March 16**: Gov. Inslee announces statewide shutdown of restaurants, bars and expanded social gathering limits. [\[link\]](https://www.governor.wa.gov/news-media/inslee-statement-statewide-shutdown-restaurants-bars-and-limits-size-gatherings-expanded) \n"
                "* **March 23**: Gov. Inslee announces \"Stay Home, Stay Healthy\" order. [\[link\]](https://www.governor.wa.gov/news-media/inslee-announces-stay-home-stay-healthy%C2%A0order)")
    #################################################################
    st.markdown("## COVID-19 Cases")
    st.markdown("The following dynamic plot displays the progression of the coronavirus cases in Washington State.")
    st.write("<iframe src='https://public.flourish.studio/visualisation/1696713/embed' frameborder='0' scrolling='no' style='width:100%;height:600px;'></iframe><div style='width:100%!;margin-top:4px!important;text-align:right!important;'><a class='flourish-credit' href='https://public.flourish.studio/visualisation/1696713/?utm_source=embed&utm_campaign=visualisation/1696713' target='_top' style='text-decoration:none!important'><img alt='Made with Flourish' src='https://public.flourish.studio/resources/made_with_flourish.svg' style='width:105px!important;height:16px!important;border:none!important;margin:0!important;'> </a></div>", unsafe_allow_html=True)

    #################################################################
    st.markdown("## Impact of COVID-19 on Urban Traffic")
    st.markdown("This section shows the impact of COVID-19 on urban traffic. "
                "In the following chart, the trends of traffic indices and the coronavirus cases are displayed together.")

    sdate = datetime.datetime(2020, 2, 28)
    edate = datetime.datetime(2020, 3, 25)
    #################################################################
    # get COVID info
    url = 'https://en.wikipedia.org/wiki/Template:2019%E2%80%9320_coronavirus_pandemic_data/United_States/Washington_State_medical_cases_chart'
    df_COVID19 = get_COVID19_from_wikipedia(url)
    df_COVID19['date'] = df_COVID19['date'].astype('datetime64[ns]')
    # st.write(df_COVID19)
    sdate = datetime.datetime(2020, 2, 28)
    edate = df_COVID19.loc[len(df_COVID19)-1, 'date']
    # daily index
    df_DailyIndex = getDailyIndex(sdate, edate)

    # # remove outliers from HOV traffic index
    # df_DailyIndex.loc[df_DailyIndex['avg_vol_hov'] == 0, 'trafficindex_hov'] = 1.0

    df_DailyIndex['date'] = df_DailyIndex['date'].astype('datetime64[ns]')
    df_DailyIndex = df_DailyIndex[['date', 'daily_index_gp', 'daily_index_hov']]

    df_DailyIndex['daily_index_gp'] = df_DailyIndex['daily_index_gp'] * 100
    # df_DailyIndex['daily_index_gp'] = df_DailyIndex['daily_index_gp'].astype('int64')
    df_DailyIndex['daily_index_hov'] = df_DailyIndex['daily_index_hov'] * 100
    # df_DailyIndex['daily_index_hov'] = df_DailyIndex['daily_index_hov'].astype('int64')

    # # peak volume
    # df_mpv = getMorningPeakVolume(sdate, edate)
    # df_mpv['date'] = df_mpv['date'].astype('datetime64[ns]')
    # df_mpv.rename(columns = {'avg_vol_gp':'Morning_GP', 'avg_vol_hov':'Morning_HOV'}, inplace = True)
    # df_epv = getEveningPeakVolume(sdate, edate)
    # df_epv['date'] = df_epv['date'].astype('datetime64[ns]')
    # df_epv.rename(columns = {'avg_vol_gp':'Evening_GP', 'avg_vol_hov':'Evening_HOV'}, inplace = True)
    # df_pv = pd.merge(df_mpv, df_epv, on='date')

    data = pd.merge(df_DailyIndex, df_COVID19, on='date')

    # st.write(data['confirmed case'].max())

    fig = plotCOVID19(data, lw = 2)
    st.plotly_chart(fig)


def showOtherMetrics():
    ###########
    # Sidebar #
    ###########
    # st.sidebar.markdown("## Components")
    # rushHourVolume = st.sidebar.checkbox("Volume at Rush Hours", value = True)
    rushHourVolume = True

    ########################
    # main content
    ########################
    st.markdown("# Other Traffic Performance Metrics")
    sdate = st.date_input('Select a start date', value = (datetime.datetime.now() - datetime.timedelta(days=30)))
    edate = st.date_input('Select an end date', value = datetime.datetime.now().date())
    st.write('From ',sdate, ' to ',edate)
    if rushHourVolume:
        st.markdown("### Volume per Lane at Rush Hour")

        df_mpv = getPeakVolume(sdate, edate, 'Morning')
        df_mpv['date'] = df_mpv['date'].astype('datetime64[ns]')
        df_mpv.rename(columns = {'avg_vol_gp':'Morning_GP', 'avg_vol_hov':'Morning_HOV'}, inplace = True)

        df_epv = getPeakVolume(sdate, edate, 'Evening')
        df_epv['date'] = df_epv['date'].astype('datetime64[ns]')
        df_epv.rename(columns = {'avg_vol_gp':'Evening_GP', 'avg_vol_hov':'Evening_HOV'}, inplace = True)

        df_pv = pd.merge(df_mpv, df_epv, on='date')
        df_pv.set_index('date')
        #print(list(df_pv.columns.values))
        dataFields = st.multiselect('Data fields', ['Morning_GP', 'Evening_GP', 'Morning_HOV', 'Evening_HOV'] , default = ['Morning_GP', 'Evening_GP'] )

        data = df_pv[['date'] + dataFields]

        fig = plotOtherMetrics(data, dataFields, lw=2)
        st.plotly_chart(fig)
        st.markdown("Morning rush hours: 6:00AM-9:00AM; Evening rush hours: 3:00PM-6:00PM")
    #st.line_chart(df_pv[dataFields], use_container_width=True)



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

    # st.title("Traffic Performance Score in Seattle Area")

    st.sidebar.title("Traffic Performance Score")
    app_mode = st.sidebar.radio("Navitation",
            ["Home", "Traffic Performance Score", "Segment-based TPS", "Impact of COVID-19", "Other Traffic Metrics"])
    # st.sidebar.markdown("[![this is an image link](./images/STARLab.png)](https://streamlit.io)")
    if  app_mode == "Home":
        IntroduceTrafficIndex()
    elif app_mode == "Traffic Performance Score":
        showTrafficIndex()
    elif app_mode == "Segment-based TPS":
        showSegmentTPS()
    elif app_mode == "Impact of COVID-19":
        showCOVID19()
    elif app_mode == "Other Traffic Metrics":
        showOtherMetrics()


    st.sidebar.title("About")
    st.sidebar.info(
        "This an open source project developed and maintained by the "
        "*Artificial Intelligence GROUP* in the [Smart Transportation Application and Research Lab (**STAR Lab**)](http://www.uwstarlab.org/) "
        "at the [University of Washington](https://www.washington.edu/). "

    )

    st.sidebar.title("Contribute")
    st.sidebar.info(
        "To inquire about potential collaboration, "
        "please contact the **Principal Investigator**: "
        ""
        "[Prof. Yinhai Wang](https://www.ce.washington.edu/facultyfinder/yinhai-wang) ([yinhai@uw.edu](mailto:yinhai@uw.edu))."
    )

    image_starlab = Image.open('images/STARLab.png')
    st.sidebar.image(image_starlab, width = 240, use_column_width=False)

    image_pactrans = Image.open('images/PacTrans.png')
    st.sidebar.image(image_pactrans, width = 80, use_column_width=False)

    # image_uw = Image.open('images/UW2.png')
    # st.sidebar.image(image_uw, width = 300, use_column_width=False)

if __name__ == '__main__':
    main()

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

#####################################################
# SQLquery
#####################################################

def getDatabaseConnection():
    return pyodbc.connect('DRIVER={SQL Server};SERVER=128.95.29.74;DATABASE=RealTimeLoopData;UID=starlab;PWD=star*lab1')


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
    '''SELECT DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) as [time]
          , AVG([AVG_Spd_GP]) AS [AVG_Spd_GP]
          , AVG([AVG_Vol_GP]) AS [AVG_Vol_GP]
          , AVG([TrafficIndex_GP]) AS [TrafficIndex_GP]
          , AVG([AVG_Spd_HOV]) AS [AVG_Spd_HOV]
          , AVG([AVG_Vol_HOV]) AS [AVG_Vol_HOV]
          , AVG([TrafficIndex_HOV]) AS [TrafficIndex_HOV]
      FROM [RealTimeLoopData].[dbo].[TrafficIndex]
      WHERE CAST([time] AS DATE) = ?
      GROUP BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) 
      ORDER BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) 
      ''', conn, params = [date])

    return pd.DataFrame(SQL_Query)


def getTrafficIndexMultiDays(sdate, edate):
    conn = getDatabaseConnection()

    SQL_Query = pd.read_sql_query(
    '''SELECT DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) as [time]
          , AVG([AVG_Spd_GP]) AS [AVG_Spd_GP]
          , AVG([AVG_Vol_GP]) AS [AVG_Vol_GP]
          , AVG([TrafficIndex_GP]) AS [TrafficIndex_GP]
          , AVG([AVG_Spd_HOV]) AS [AVG_Spd_HOV]
          , AVG([AVG_Vol_HOV]) AS [AVG_Vol_HOV]
          , AVG([TrafficIndex_HOV]) AS [TrafficIndex_HOV]
      FROM [RealTimeLoopData].[dbo].[TrafficIndex]
      WHERE time between ? and ?
      GROUP BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) 
      ORDER BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0)
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


def getSegments():
    conn = getDatabaseConnection()
    SQL_Query = pd.read_sql_query(
    '''	SELECT *
          FROM [RealTimeLoopData].[dbo].[Segments]''', conn)
    return pd.DataFrame(SQL_Query)


def getSegmentTPS_Day(sdate, edate, segmentID):
    conn = getDatabaseConnection()
    SQL_Query = pd.read_sql_query(
    '''	SELECT CONVERT(varchar, CAST([time] AS DATE), 107) as [time]
              ,AVG([AVG_Spd_GP]) AS [AVG_Spd_GP]
              ,AVG([AVG_Spd_HOV]) AS [AVG_Spd_HOV]
              ,AVG([AVG_Vol_GP]) AS [AVG_Vol_GP]
              ,AVG([AVG_Vol_HOV]) AS [AVG_Vol_HOV]
              ,AVG([TrafficIndex_GP]) AS [TrafficIndex_GP]
              ,AVG([TrafficIndex_HOV]) AS [TrafficIndex_HOV]
        FROM [RealTimeLoopData].[dbo].[SegmentTrafficIndex]
        WHERE [time] BETWEEN ? and ?
        AND [segmentID] = ?
        GROUP BY CAST([time] AS DATE)
        ORDER BY CAST([time] AS DATE)
        ''', conn, params = [sdate, edate, segmentID])
    return pd.DataFrame(SQL_Query)


def getSegmentTPS_5Min(sdate, edate, segmentID):
    conn = getDatabaseConnection()
    SQL_Query = pd.read_sql_query(
    '''	SELECT DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) as [time]
              ,AVG([AVG_Spd_GP]) AS [AVG_Spd_GP]
              ,AVG([AVG_Spd_HOV]) AS [AVG_Spd_HOV]
              ,AVG([AVG_Vol_GP]) AS [AVG_Vol_GP]
              ,AVG([AVG_Vol_HOV]) AS [AVG_Vol_HOV]
              ,AVG([TrafficIndex_GP]) AS [TrafficIndex_GP]
              ,AVG([TrafficIndex_HOV]) AS [TrafficIndex_HOV]
        FROM [RealTimeLoopData].[dbo].[SegmentTrafficIndex]
        WHERE [time] BETWEEN ? and ?
        AND [segmentID] = ?
        GROUP BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0)
        ORDER BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0)
        ''', conn, params = [sdate, edate, segmentID])
    return pd.DataFrame(SQL_Query)


def getSegmentTPS_5Min(sdate, edate):
    conn = getDatabaseConnection()
    SQL_Query = pd.read_sql_query(
    '''	SELECT DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0) as [time]
                ,[segmentID]
                ,AVG([AVG_Spd_GP]) AS [AVG_Spd_GP]
                ,AVG([AVG_Spd_HOV]) AS [AVG_Spd_HOV]
                ,AVG([AVG_Vol_GP]) AS [AVG_Vol_GP]
                ,AVG([AVG_Vol_HOV]) AS [AVG_Vol_HOV]
                ,AVG([TrafficIndex_GP]) AS [TrafficIndex_GP]
                ,AVG([TrafficIndex_HOV]) AS [TrafficIndex_HOV]
        FROM [RealTimeLoopData].[dbo].[SegmentTrafficIndex]
        WHERE [time] BETWEEN ? and ?
        GROUP BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0),[segmentID]
        ORDER BY DATEADD(MINUTE, DATEDIFF(MINUTE, 0, [time])/5*5, 0),[segmentID]
        ''', conn, params = [sdate, edate])
    return pd.DataFrame(SQL_Query)


def getPeakVolume(sdate, edate, morn_or_even = 'Morning'):
    conn = getDatabaseConnection()
    if morn_or_even == 'Morning':
        stime, etime = 6, 9
    elif morn_or_even == 'Evening':
        stime, etime = 15, 18
    else:
        stime = etime = 0

    SQL_Query = pd.read_sql_query(
    '''	SELECT convert(varchar, CAST([time] AS DATE), 107) as Date, AVG(AVG_Vol_GP) as AVG_Vol_GP, AVG(AVG_Vol_HOV) as AVG_Vol_HOV
        FROM [RealTimeLoopData].[dbo].[TrafficIndex]
        WHERE CAST([time] AS DATE) between ? and ?
            AND DATEPART(HOUR, [time]) >= ? AND DATEPART(HOUR, [time]) <= ?
        GROUP BY CAST([time] AS DATE)
        ORDER BY CAST([time] AS DATE)
        ''', conn, params = [sdate,edate,stime,etime])

    return pd.DataFrame(SQL_Query)

#####################################################
# get COVID19Info
#####################################################

def getCOVID19Info():
    return pd.read_csv('Washington_COVID_Cases.csv')


def get_data_from_sel(url, sel):
    session = HTMLSession()
    r = session.get(url)
    mylist = []
    try:
        results = r.html.find(sel)
        for result in results:
            mytext = result.text
            mylist.append(mytext)
        return mylist
    except:
        return None


def get_COVID19_from_wikipedia(url):
    sel_date = '#mw-content-text > div > div.barbox.tright > div > table > tbody > tr > td:nth-child(1)'
    sel_cases = '#mw-content-text > div > div.barbox.tright > div > table > tbody > tr > td:nth-child(3) > span > span:nth-child(1)'

    date_list = get_data_from_sel(url, sel_date)
    del date_list[len(date_list) - 1]
    del date_list[0]
    cases_list_0 = get_data_from_sel(url, sel_cases)
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    cases_list = []
    for n in cases_list_0:
        cases_list.append(locale.atoi(n))

    df = pd.DataFrame(date_list, columns=['date'])
    df['confirmed case'] = cases_list
    df['new case'] = df['confirmed case'] - df['confirmed case'].shift(1)
    df.loc[0, 'new case'] = 0
    return df
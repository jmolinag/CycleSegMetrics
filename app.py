import os
import logging
import json
import pandas as pd
import numpy as np
from pandas import json_normalize
import requests
import ast
import flask
import waitress
import code, copy, datetime as dt
from datetime import datetime
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import plotly.io as pio

#pio.renderers.default='notebook'

from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for)





app = Dash(__name__)
baseURL="https://www.aims.structint.com/aimspreprodapi/"

subDomain="ngbu"


AIMS_BaseURL = baseURL

# 1. Get the access token
tokenURL = AIMS_BaseURL + 'token' 
tokenParams = {'grant_type': 'password', 'username':'aims@structint.com', 'password': 'Pass@123', 'subDomain': subDomain}
objToken = requests.post(tokenURL, data = tokenParams)
data = objToken.json()
access_token = data['access_token']


#2. Get TenantID by SubDomain
getTenantIdURL = AIMS_BaseURL + 'api/Report/TenantIdBySubDomain' 
getTenantIdParams = { "SubDomain":subDomain }
header = {'Authorization':'Bearer ' + access_token, 'Content-Type': 'application/json'}
response = requests.request("POST", getTenantIdURL, headers=header, json = getTenantIdParams)
tenantId = response.text.replace('"', '')


# 3. Get the data from AIMS Global Search API
payload = {
"EntityCategoryName":"Asset",
"EntityType":"Cycle Segment",
"UserName":"aims@structint.com",
"SubDomain":"ngbu",
"OrderByField":"Cycle Segment.Name",
"SortOrder":"asc",
"lstAdditionalFields":[
{ "Fields":["Cycle Segment__id" ] },
{ "EntityCategoryName":"Asset", "EntityTypeName":"Pipeline", "Fields":[ "Name"]
},
{ "EntityCategoryName":"Asset", "EntityTypeName":"Cycle Segment", "Fields":[ "Name", "State","Area Type", "Segment Length", "Outside Diameter",
        "Wall Thickness", "Grade", "MAOP", "Test Pressure", "BinLife"]
}


],
"IgnoreDefaultFields":"true",
"PageIndex":"1",
"PageSize":"100000"
}

header = {'Authorization':'Bearer ' + access_token, 'Content-Type': 'application/json'}
globalSearchURL = AIMS_BaseURL + 'api/Filter/GetGlobalSearch' 
response = requests.request("POST", globalSearchURL, headers=header, json = payload)

segments = json.loads(response.text)

listSegment = segments["MainTable"]

df1 =pd.json_normalize(segments,record_path=['MainTable'])
df = df1.replace("", np.nan, inplace = False)
df = df.replace("0", np.nan, inplace = False)
df["Cycle Segment.Has_Outside Diameter"] = np.where(pd.isna(df["Cycle Segment.Outside Diameter"]), 0, 1)
df["Cycle Segment.Has_Wall Thickness"] = np.where(pd.isna(df["Cycle Segment.Wall Thickness"]), 0, 1)
df["Cycle Segment.Has_Grade"] = np.where(pd.isna(df["Cycle Segment.Grade"]), 0, 1)
df["Cycle Segment.Has_MAOP"] = np.where(pd.isna(df["Cycle Segment.MAOP"]), 0, 1)
df["Cycle Segment.Has_Test Pressure"] = np.where(pd.isna(df["Cycle Segment.Test Pressure"]), 0, 1)
df["Length_miles"] =round(df['Cycle Segment.Segment Length'].apply(lambda x: float(x))/5280,1)

app.layout = html.Div([
    html.H4('Analysis of Data'),
    dcc.Graph(id="graph"),
    html.P("Names:"),
    dcc.Dropdown(id='names',
    options=['Cycle Segment.BinLife', 'Cycle Segment.Has_Outside Diameter', 'Cycle Segment.Has_Wall Thickness', 
    'Cycle Segment.Has_Grade', 'Cycle Segment.Has_MAOP', 'Cycle Segment.Has_Test Pressure', 'Pipeline.Name'],
    value='Cycle Segment.BinLife', clearable=False
    ),

    html.P('Select Pipeline:'),
    dcc.Dropdown(id='pipeline_dropdown',
    options=[x for x in sorted(df["Pipeline.Name"].unique())], multi=True,
    value=None, clearable=True
    ),

    html.P('Select State:'),
    dcc.Dropdown(id='state_dropdown',
    options=[x for x in sorted(df["Cycle Segment.State"].unique())], multi=True,
    value=None, clearable=True
    ),

    html.P('Select Consequence Area Type:'),
    dcc.Dropdown(id='area_dropdown',
    options=[x for x in sorted(df["Cycle Segment.Area Type"].unique())], multi =True,
    value=None, clearable=True
    ),
])





@app.callback(
    Output("graph", "figure"), 
    Input("names", "value"), 
    Input("pipeline_dropdown", "value"),
    Input("state_dropdown", "value"),
    Input("area_dropdown", "value"))

def generate_chart(names, pipeline_dropdown, state_dropdown, area_dropdown):
    dff = df.copy()
    if pipeline_dropdown:
        dff = dff[dff['Pipeline.Name'].isin(pipeline_dropdown)]

    if state_dropdown:
        dff = dff[dff['Cycle Segment.State'].isin(state_dropdown)]

    if area_dropdown:
        dff = dff[dff['Cycle Segment.Area Type'].isin(area_dropdown)]    

    fig = px.pie(dff, values=dff['Length_miles'], names=names, hole=.3)
    return fig


if __name__ == '__main__':
    from waitress import serve
    #serve(app, host="0.0.0.0", port=8080)
    app.run_server(debug=True, use_reloader=False)
    





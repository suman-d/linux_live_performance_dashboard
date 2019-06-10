# coding: utf-8
import time
import random
import dash
import yaml
import dash_core_components as dcc
import dash_html_components as html
import dash_daq as daq
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import datetime as dt
import subprocess
import os 
import glob
import json
import random

from dash.dependencies import State, Input, Output
from threading import Thread

import myfio
import monitor_stat 

def print_button():
    printButton = html.A(['Print PDF'],className="button no-print print",style={'position': "absolute", 'top': '-40', 'right': '0'})
    return printButton

def Run2(cmd):
    """Run a cmd[], return the exit code, stdout, and stderr."""
    p = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL)
    return p

def JobWrapper_fio_Local(cmd):
    p = Run2(cmd)

def JobWrapper_fio_all(n_clicks):
    myfio.competitive_tests(n_clicks)

def JobWrapper_statmonitor(iostat_output, final_csv, duration, n_clicks, live_csv):
    monitor_stat.monitor_disk_cpu_mem_lat_util(iostat_output, final_csv, duration, n_clicks, live_csv)

def get_header():
    header = html.Div([

        html.Div([
            html.H1(
                'Linux Performance Demo Dashboard')
        ], className="twelve columns padded",
           style={'text-align': 'center', 'margin-bottom': '15px', 'color': '#DC143C'})
        ], className="row gs-header gs-text-header")
    return header


def get_title(t):
    header = html.Div([

        html.Div([
            html.H2(
                '{}'.format(t))
        ], className="twelve columns padded",
           style={'text-align': 'center', 'margin-bottom': '15px', 'color': '#ffffff', 'backgroundColor': '#DC143C' })
        ], className="row gs-header gs-text-header")
    return header

def get_title2(t):
    header = html.Div([

        html.Div([
            html.H2(
                '{}'.format(t))
        ], className="twelve columns padded",
           style={'text-align': 'center', 'margin-bottom': '15px', 'color': '#ffffff', 'backgroundColor': '#099FFF' })
        ], className="row gs-header gs-text-header")
    return header

def get_last_latency():
    global fio_result
    
    with open(fio_result) as fiofile:
        data = json.load(fiofile)
    read_lat = round(data["jobs"][0]["read"]["clat_ns"]["mean"] * 0.001, 2)
    write_lat = round(data["jobs"][0]["write"]["clat_ns"]["mean"] * 0.001, 2)
    
    return read_lat, write_lat

def define_tests():
    global products, combinations
    cards = [i.lower() for i in products.keys()]
    if "emulex" in cards and "qlogic" in cards:
        combinations = [{"label": "Emulex Only", "value": "Emulex"},
                        {"label": "Qlogic Only", "value": "Qlogic"},
                        {"label": "Emulex and Qlogic", "value": "Emulex And Qlogic"}]
    elif "emulex" in cards:
        combinations = [{"label": "Emulex Only", "value": "Emulex"}]
    elif "qlogic" in cards:
        combinations = [{"label": "Qlogic Only", "value": "Qlogic"}]

    return combinations


def define_tests2():
    global products, combinations
    cards = [i.lower() for i in products.keys()]
    combinations = []
    for p in products:
        label = "{}({})".format(p, products[p][1]["card"])
        value = "{}_{}".format(p, products[p][1]["card"])
        pair = {"label": label, "value": value}
        combinations.append(pair)
    if len(cards) == 2:
        label = combinations[0]['label'] + " And " + combinations[1]['label']
        value = combinations[0]['value'] + " And " + combinations[1]['value']
        pair = {"label": label, "value": value}
        combinations.append(pair)
    return combinations

def cpu_utilization_gauge():
    cpu_gauge = daq.Gauge(
                color={"gradient":True,"ranges":{"green":[0,50],"yellow":[50,80],"red":[80,100]}},
                value=2,
                label='CPU',
                max=100,
                min=0,
                style={"padding": "0px 0px 0px 0px",
                                    "marginLeft": "auto",
                                    "marginRight": "auto",
                                    "align-items": "center",
                                    "textAlign": "center",
                                    "width": "25%",
                                    "display": "inline-block",
                                    "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                }
                )
    return cpu_gauge

# Reading the config file
pwd = os.getcwd()
config = pwd + "/config.yml"
with open(config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

# Checking the products to test

products = cfg["products"]
combinations = define_tests2()
iostat_output = {}
final_csv = {}
fio_result = {}
device = {}
live = pwd + "/" + "live.csv"
for p in products:
    value = "{}_{}".format(p, products[p][1]["card"])
    prefix = p.lower() + "_" + products[p][0]["protocol"] + "_" +  products[p][1]["card"] + "_"
    iostat_file = pwd + "/" + prefix.lower() + "iostat.txt"
    iostat_output[value] = iostat_file
    final_file = pwd + "/" + prefix.lower() + "allstat.csv"
    final_csv[value] = final_file
    fio_file = pwd + "/" + prefix.lower() + "demo.json"
    fio_result[value] = fio_file
    d = products[p][2]["dev_name"].replace(",", ":")
    device[value] = d

# General FIO Configuration 
duration = cfg['test_config']['duration']
write_percentage = cfg['test_config']['write_percentage']
block_size = cfg['test_config']['block_size']
iodepth = cfg['test_config']['iodepth']
numjobs = cfg['test_config']['numjobs']
topology_diagram = cfg['topology']['name']

# Setting the gauge low, medium and max range 
iops_max = cfg['gauge']['iops']['max']
tput_max = cfg['gauge']['throughput']['max']

# Starting the Web Application
app = dash.Dash(__name__)
server = app.server

# Deleting old iostat and allstats file before every new test (test click)
filelist=glob.glob("*iostat.txt")
filelist+=glob.glob("*allstat.csv")
filelist+=glob.glob("*demo.json")
filelist+=glob.glob("live.csv")
for file in filelist:
    os.remove(file)

# Creating the CSV File for allstats 
for f in final_csv:
    monitor_stat.AppendFile("Time,CPU_Utilization,Memory_Utilization,Read_IOPS,Write_IOPS,Read_Throughput(MBps),Write_Throughput(MBps)", final_csv[f])
    monitor_stat.AppendFile("0,0,0,0,0,0,0", final_csv[f])

# Create the live monitor stat file
monitor_stat.AppendFile("CPU_Utilization,Memory_Utilization,Read_IOPS,Write_IOPS,Read_Throughput(MBps),Write_Throughput(MBps)", live)
monitor_stat.AppendFile("0,0,0,0,0,0",live)

# Defining the tests to run for demo based on product select
test_name = combinations[0]['value']

# Making the HTML Layout 
app.layout = html.Div(
    [   get_header(), 
        html.Div([
                get_title2("Test Selection"),                
                html.Div([ 
                        dcc.Dropdown(
                            id='my-dropdown',
                            options=combinations,
                            className=" three columns",                            
                            value=test_name, 
                            style={
                                    "textAlign": "center",
                                    "width": "100%",
                                    "align-items": "flex-start",
                                    'display': 'inline-block'
                                    }
                        ),
                        html.H3(id='output-container', 
                                style={
                                        "textAlign": "center",
                                        "width": "100%",
                                        "align-items": "flex-start",
                                        "display": "inline-block",
                                        "color": "#DC143C"
                                        })
                                                            
                        ]), 
                get_title2("Application Stimulation"),               
                html.H3(
                "Start Application",
                className=" two columns",
                style={
                    "textAlign": "center",
                    "width": "20%",
                    "align-items": "center",
                    'display': 'inline-block'
                      },            
                ),            
                daq.StopButton(
                    id="start-button-fc",
                    buttonText="Start",
                    style={
                        #"display": "flex",
                        "justify-content": "center",
                        "align-items": "center",
                        'display': 'inline-block',
                        "width": "30%",
                    },
                    n_clicks=0,
                    className="three columns",
                    ),
                html.H3(id='start-button-output', 
                        className=" two columns",
                        style={
                                "textAlign": "right",
                                "width": "50%",
                                "align-items": "right",
                                "display": "inline-block",
                                "color": "#DC143C"
                                }),
                daq.Indicator(
                            id="connection-est",
                            value=False,
                            className="three columns",
                            style={'margin': '6px',
                                "width": "1%",
                                "justify-content": "center",
                                "align-items": "center",                                
                                "display": "none",
                                "color": "#DC143C"
                                }
                        ),
                get_title2("Topology Diagram"),
                
                html.Div([html.Img(src=app.get_asset_url(topology_diagram), 
                                    style={ "padding": "0px 0px 0px 0px",
                                    "marginLeft": "auto",
                                    "marginRight": "auto",
                                    "align-items": "center",
                                    "textAlign": "center",
                                    "width": "100%",
                                    "boxShadow": "0px 0px 5px 5px rgba(204,204,204,204)",
                                },), 
                          ]),                
                get_title2("Live Gauges (CPU and Memory)"),
                html.Div([
                        daq.Gauge(
                                    id="live-cpu",
                                    color={"gradient":True,"ranges":{"green":[0,50],"yellow":[50,80],"red":[80,100]}},
                                    value=0,
                                    label={"label":'CPU Utilization', "style": {'fontSize': 20, }},
                                    max=100,
                                    min=0,
                                    labelPosition="top",
                                    units="%",
                                    showCurrentValue=True,                                    
                                    style={"padding": "0px 0px 0px 0px",
                                                        "marginLeft": "auto",
                                                        "marginRight": "auto",
                                                        "align-items": "center",
                                                        "textAlign": "center",
                                                        "width": "50%",
                                                        "display": "inline-block",
                                                        "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                                    }
                                    ), 
                        dcc.Interval(id='live-cpu-update', interval=1000, n_intervals=0),
                        daq.Gauge(
                                    id="live-memory",
                                    color={"color": "#099FFF", "gradient":True,"ranges":{"green":[0,50],"yellow":[50,80],"red":[80,100]}},
                                    value=0,
                                    label={"label":'Memory Utilization', "style": {'fontSize': 20, }},
                                    max=100,
                                    min=0,
                                    labelPosition="top",
                                    units="%",
                                    showCurrentValue=True,                                    
                                    style={"padding": "0px 0px 0px 0px",
                                                        "marginLeft": "auto",
                                                        "marginRight": "auto",
                                                        "align-items": "center",
                                                        "textAlign": "center",
                                                        "width": "50%",
                                                        "display": "inline-block",
                                                        "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                                    }
                                    )                                    
                          , 
                        dcc.Interval(id='live-memory-update', interval=1000, n_intervals=0)]),                        
                get_title2("Live Gagues (Throughput and IOPS)"),
                html.Div([
                        daq.Gauge(
                                    id="live-readiops",
                                    #color={"gradient":True,"ranges":{"red":[0,1000000],"yellow":[1000000,5000000],"green":[5000000,9000000]}},
                                    color="#099FFF",
                                    value=0,
                                    label={"label": "Read IOPS", "style": {'fontSize': 20, }},
                                    max=iops_max,
                                    min=0,
                                    labelPosition="top",
                                    units="IOPS",
                                    showCurrentValue=True,                                    
                                    style={"padding": "0px 0px 0px 0px",
                                                        "marginLeft": "auto",
                                                        "marginRight": "auto",
                                                        "align-items": "center",
                                                        "textAlign": "center",
                                                        "width": "25%",
                                                        "display": "inline-block",
                                                        "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                                    }
                                    ), 
                        dcc.Interval(id='live-readiops-update', interval=1000, n_intervals=0),
                        daq.Gauge(
                                    id="live-writeiops",
                                    #color={"gradient":True,"ranges":{"red":[0,1000000],"yellow":[1000000,5000000],"green":[5000000,9000000]}},
                                    color="#099FFF",
                                    value=0,
                                    label={"label": "Write IOPS", "style": {'fontSize': 20, }},
                                    max=iops_max,
                                    min=0,
                                    labelPosition="top",
                                    units="IOPS",
                                    showCurrentValue=True,                                    
                                    style={"padding": "0px 0px 0px 0px",
                                                        "marginLeft": "auto",
                                                        "marginRight": "auto",
                                                        "align-items": "center",
                                                        "textAlign": "center",
                                                        "width": "25%",
                                                        "display": "inline-block",
                                                        "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                                    }
                                    )                                    
                          , 
                        dcc.Interval(id='live-writeiops-update', interval=1000, n_intervals=0),
                        daq.Gauge(
                                    id="live-readthroughput",
                                    #color={"gradient":True,"ranges":{"red":[0,1600],"yellow":[1600,2400],"green":[2400,3200]}},
                                    color="#099FFF",
                                    value=0,
                                    label={"label": "Read Throughput", "style": {'fontSize': 20, }},
                                    max=tput_max,
                                    min=0,
                                    labelPosition="top",
                                    units="MBps",
                                    showCurrentValue=True,                                    
                                    style={"padding": "0px 0px 0px 0px",
                                                        "marginLeft": "auto",
                                                        "marginRight": "auto",
                                                        "align-items": "center",
                                                        "textAlign": "center",
                                                        "width": "25%",
                                                        "display": "inline-block",
                                                        "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                                    }
                                    ), 
                        dcc.Interval(id='live-readthroughput-update', interval=1000, n_intervals=0),
                        daq.Gauge(
                                    id="live-writethroughput",
                                    #color={"gradient":True,"ranges":{"red":[0,1600],"yellow":[1600,2400],"green":[2400,3200]}},
                                    color="#099FFF",
                                    value=0,
                                    label={"label": "Write Throughput", "style": {'fontSize': 20, }},
                                    max=tput_max,
                                    min=0,
                                    labelPosition="top",
                                    units="MBps",
                                    showCurrentValue=True,                                    
                                    style={"padding": "0px 0px 0px 0px",
                                                        "marginLeft": "auto",
                                                        "marginRight": "auto",
                                                        "align-items": "center",
                                                        "textAlign": "center",
                                                        "width": "25%",
                                                        "display": "inline-block",
                                                        "boxShadow": "0px 5px 5px 0px rgba(204,204,204,204)",
                                                    }
                                    )                                    
                          , 
                        dcc.Interval(id='live-writethroughput-update', interval=1000, n_intervals=0)]), 
                get_title("Throughput Charts"), 
                html.Div([
                        html.Div([dcc.Graph(id='read-throughput'),], 
                                className='twelve columns read-throughput'),
                        dcc.Interval(id='read-throughput-update', interval=2000, n_intervals=0),
                        ], 
                        className='row read-throughput-row'),
                html.Div([
                        html.Div([dcc.Graph(id='write-throughput'),], 
                                className='twelve columns write-throughput'),
                        dcc.Interval(id='write-throughput-update', interval=2000, n_intervals=0),
                        ], 
                        className='row write-throughput-row'),
                get_title("IOPS Charts"), 
                html.Div([
                        html.Div([dcc.Graph(id='read-iops'),], 
                                className='twelve columns read-iops'),
                        dcc.Interval(id='read-iops-update', interval=2000, n_intervals=0),
                        ], 
                        className='row read-iops'),
                html.Div([
                        html.Div([dcc.Graph(id='write-iops'),], 
                                className='twelve columns write-iops'),
                        dcc.Interval(id='write-iops-update', interval=2000, n_intervals=0),
                        ], 
                        className='row write-iops'),
                get_title("CPU Usage"), 
                html.Div([
                        html.Div([dcc.Graph(id='cpu-util'),], 
                                className='twelve columns cpu-util'),
                        dcc.Interval(id='cpu-util-update', interval=2000, n_intervals=0),
                        ], 
                        className='row cpu-util'),
                get_title("Memory Usage"),                         
                html.Div([
                        html.Div([dcc.Graph(id='mem-util'),], 
                                className='twelve columns mem-util'),
                        dcc.Interval(id='mem-util-update', interval=2000, n_intervals=0),
                        ], 
                        className='row mem-util'),
                get_title("Average Latency"),  
                html.Div([
                        html.Div([dcc.Graph(id='latency'),], 
                                className='twelve columns latency'),
                        dcc.Interval(id='latency-update', interval=2000, n_intervals=0),
                        ], 
                        className='row latency'), 
                get_title("Tail Latency"),               
                html.Div([
                        html.Div([dcc.Graph(id='tail-latency-read'),], 
                                className='twelve columns latency'),
                        dcc.Interval(id='tail-latency-read-update', interval=2000, n_intervals=0),
                        ], 
                        className='row latency'), 
            ],
        style={
            "padding": "10px 10px 0px 10px",
            "marginLeft": "auto",
            "marginRight": "auto",
            "width": "1180px",
            "boxShadow": "0px 0px 5px 5px rgba(204,204,204,204)",
        }), 

    ]
)

@app.callback(
    dash.dependencies.Output('output-container', 'children'),
    [dash.dependencies.Input('my-dropdown', 'value')])
def update_output(value):

    global test_name
    test_name = value
    return 'You have selected "{}"'.format(value)

@app.callback(
    Output('start-button-output', 'children'),
    [Input('start-button-fc', 'n_clicks')])
def start_fio(n_clicks):

    global test_name, device, duration, products, live
 
    if "And" not in test_name:      
        _dev = device[test_name]
        _iostat_output = iostat_output[test_name]
        _final_csv = final_csv[test_name]
        _fio_result = fio_result[test_name]
        _fio_dev = _dev.replace("nvme", "/dev/nvme")

        if n_clicks >0:
            if not myfio.fio_running():
                # Start collecting the IOSTAT
                monitor_stat.start_iostat(_dev, duration, _iostat_output)
                time.sleep(2)
                # Start the all stats monitoring 
                monitor_all = Thread(target=JobWrapper_statmonitor, args=(_iostat_output, _final_csv, duration, n_clicks, live))
                monitor_all.start()
                time.sleep(1)
                # Starting the FIO
                cmd = myfio.fio_cmd(_fio_dev, _fio_result)
                fio_test = Thread(target=JobWrapper_fio_Local, args=(cmd,))
                fio_test.start()
                return "Application Started"
            else:
                return "Application Already Running"
    
    else:
        if n_clicks >0:
            if not myfio.fio_running():
                fio_test = Thread(target=JobWrapper_fio_all, args=(n_clicks,))
                fio_test.start()
                time.sleep(1)
                return "Application Started   "
            else:
                return "Application Already Running    "        


# @app.callback(
#     Output('start-button-output', 'children'),
#     [Input('stop-button-fc', 'n_clicks')])
# def stop_application():

#     global final_csv, iostat_output 
#     all_processes = myfio.get_fio_procesids()
#     myfio.kill_all(all_processes)

#     # Deleting old iostat and allstats file before every new test (test click)
#     monitor_stat.run_command("rm -rf {}".format(final_csv))
#     monitor_stat.run_command("rm -rf {}".format(iostat_output))

#     # Creating the CSV File for allstats 
#     monitor_stat.AppendFile("Time,CPU_Utilization,Memory_Utilization,Read_IOPS,Write_IOPS,Read_Throughput(MBps),Write_Throughput(MBps)",
#                 final_csv)
#     monitor_stat.AppendFile("0,0,0,0,0,0,0", final_csv)

#     time.sleep(2)

#     return "Application Stoped"

# @app.callback(
#     Output('start-button-output', 'children'),
#     [Input('start-button-fc', 'n_clicks')])
#     #  Input('stop-button-fc', 'n_clicks')])
# def button_action(start_n_click, stop_n_click):

#     msg = ""
#     if int(start_n_click) > int(stop_n_click):
#         msg = start_fio(start_n_click)
#     elif int(start_n_click) < int(stop_n_click):
#         msg = stop_application()

#     return msg

@app.callback(
    Output('read-throughput', 'figure'), 
    [Input('read-throughput-update', 'n_intervals')])
def throughput_chart_read(interval):

    global final_csv, test_name, products

    workload_type="Read_Throughput(MBps)"

    all_data = [] 

    if "And" not in test_name:      
        _final_csv = final_csv[test_name]
        _name = test_name
        data = _final_csv
        df = pd.read_csv(data) 

        y1_df_BW = df[workload_type]
        x1 = df["Time"]
        
        trace = go.Scatter(
                x = x1,
                y = y1_df_BW,
                name = _name,
                )
        
        layout = go.Layout(title = "Read Throughput",
                        xaxis = dict(title = "Time",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "Throughput (in MBps)",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in final_csv:
            _final_csv = final_csv[p]
            _name = p
            data = _final_csv
            df = pd.read_csv(data) 

            y1_df_BW = df[workload_type]
            x1 = df["Time"]
            
            trace = go.Scatter(
                    x = x1,
                    y = y1_df_BW,
                    name = _name,
                    )
            
            layout = go.Layout(title = "Read Throughput",
                            xaxis = dict(title = "Time",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "Throughput (in MBps)",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   

    
    return go.Figure(data=all_data, layout=layout)


@app.callback(
    Output('write-throughput', 'figure'), 
    [Input('write-throughput-update', 'n_intervals')])
def throughput_chart_write(interval):

    global final_csv, test_name, products

    workload_type="Write_Throughput(MBps)"

    all_data = [] 

    if "And" not in test_name:      
        _final_csv = final_csv[test_name]
        _name = test_name
        data = _final_csv
        df = pd.read_csv(data) 

        y1_df_BW = df[workload_type]
        x1 = df["Time"]
        
        trace = go.Scatter(
                x = x1,
                y = y1_df_BW,
                name = _name,
                )
        
        layout = go.Layout(title = "Write Throughput",
                        xaxis = dict(title = "Time",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "Throughput (in MBps)",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in final_csv:
            _final_csv = final_csv[p]
            _name = p
            data = _final_csv
            df = pd.read_csv(data) 

            y1_df_BW = df[workload_type]
            x1 = df["Time"]
            
            trace = go.Scatter(
                    x = x1,
                    y = y1_df_BW,
                    name = _name,
                    )
            
            layout = go.Layout(title = "Write Throughput",
                            xaxis = dict(title = "Time",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "Throughput (in MBps)",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   

    
    return go.Figure(data=all_data, layout=layout)

@app.callback(
    Output('read-iops', 'figure'), 
    [Input('read-iops-update', 'n_intervals')])
def iops_chart_read(interval):

    global final_csv, test_name, products

    workload_type="Read_IOPS"

    all_data = [] 

    if "And" not in test_name:      
        _final_csv = final_csv[test_name]
        _name = test_name
        data = _final_csv
        df = pd.read_csv(data) 

        y1_df_BW = df[workload_type]
        x1 = df["Time"]
        
        trace = go.Scatter(
                x = x1,
                y = y1_df_BW,
                name = _name,
                )
        
        layout = go.Layout(title = "Read IOPS",
                        xaxis = dict(title = "Time",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "IOPS",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in final_csv:
            _final_csv = final_csv[p]
            _name = p
            data = _final_csv
            df = pd.read_csv(data) 

            y1_df_BW = df[workload_type]
            x1 = df["Time"]
            
            trace = go.Scatter(
                    x = x1,
                    y = y1_df_BW,
                    name = _name,
                    )
            
            layout = go.Layout(title = "Read IOPS",
                            xaxis = dict(title = "Time",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "IOPS",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   

    
    return go.Figure(data=all_data, layout=layout)

@app.callback(
    Output('write-iops', 'figure'), 
    [Input('write-iops-update', 'n_intervals')])
def iops_chart_write(interval):

    global final_csv, test_name, products

    workload_type="Write_IOPS"

    all_data = [] 

    if "And" not in test_name:      
        _final_csv = final_csv[test_name]
        _name = test_name
        data = _final_csv
        df = pd.read_csv(data) 

        y1_df_BW = df[workload_type]
        x1 = df["Time"]
        
        trace = go.Scatter(
                x = x1,
                y = y1_df_BW,
                name = _name,
                )
        
        layout = go.Layout(title = "Write IOPS",
                        xaxis = dict(title = "Time",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "IOPS",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in final_csv:
            _final_csv = final_csv[p]
            _name = p
            data = _final_csv
            df = pd.read_csv(data) 

            y1_df_BW = df[workload_type]
            x1 = df["Time"]
            
            trace = go.Scatter(
                    x = x1,
                    y = y1_df_BW,
                    name = _name,
                    )
            
            layout = go.Layout(title = "Write IOPS",
                            xaxis = dict(title = "Time",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "IOPS",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   

    
    return go.Figure(data=all_data, layout=layout)

@app.callback(
    Output('cpu-util', 'figure'), 
    [Input('cpu-util-update', 'n_intervals')])
def cpu_util(interval):

    global final_csv, test_name, products

    workload_type="CPU_Utilization"

    all_data = [] 

    if "And" not in test_name:      
        _final_csv = final_csv[test_name]
        _name = test_name
        data = _final_csv
        df = pd.read_csv(data) 

        y1_df_BW = df[workload_type]
        x1 = df["Time"]
        
        trace = go.Scatter(
                x = x1,
                y = y1_df_BW,
                name = _name,
                )
        
        layout = go.Layout(title = "CPU Utilization",
                        xaxis = dict(title = "Time",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "CPU Utilization(in %)",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in final_csv:
            _final_csv = final_csv[p]
            _name = p
            data = _final_csv
            df = pd.read_csv(data) 

            y1_df_BW = df[workload_type]
            x1 = df["Time"]
            
            trace = go.Scatter(
                    x = x1,
                    y = y1_df_BW,
                    name = _name,
                    )
            
            layout = go.Layout(title = "CPU Utilization",
                            xaxis = dict(title = "Time",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "CPU Utilization(in %)",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   

    
    return go.Figure(data=all_data, layout=layout)

@app.callback(
    Output('mem-util', 'figure'), 
    [Input('mem-util-update', 'n_intervals')])
def memory_util(interval):

    global final_csv, test_name, products

    workload_type="Memory_Utilization"

    all_data = [] 

    if "And" not in test_name:      
        _final_csv = final_csv[test_name]
        _name = test_name
        data = _final_csv
        df = pd.read_csv(data) 

        y1_df_BW = df[workload_type]
        x1 = df["Time"]
        
        trace = go.Scatter(
                x = x1,
                y = y1_df_BW,
                name = _name,
                )
        
        layout = go.Layout(title = "Memory Utilization",
                        xaxis = dict(title = "Time",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "Memory Utilization(in %)",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in final_csv:
            _final_csv = final_csv[p]
            _name = p
            data = _final_csv
            df = pd.read_csv(data) 

            y1_df_BW = df[workload_type]
            x1 = df["Time"]
            
            trace = go.Scatter(
                    x = x1,
                    y = y1_df_BW,
                    name = _name,
                    )
            
            layout = go.Layout(title = "Memory Utilization",
                            xaxis = dict(title = "Time",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "Memory Utilization(in %)",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   

    
    return go.Figure(data=all_data, layout=layout)

@app.callback(
    Output('latency', 'figure'), 
    [Input('latency-update', 'n_intervals')])
def latency(interval):

    global final_csv, test_name, products, fio_result

    all_data = [] 

    if "And" not in test_name:      
        _fio_result = fio_result[test_name]
        _name = test_name
        try:
            with open(_fio_result, 'r') as f:
                result = json.load(f)
            read_lat =round((result["jobs"][0]["read"]["clat_ns"]["mean"] / 1000), 2)
            write_lat =round((result["jobs"][0]["write"]["clat_ns"]["mean"] / 1000), 2)                
        except (FileNotFoundError, IOError, ValueError):
            read_lat = 0
            write_lat = 0 

        x = ['Read', 'Write']
        y = [read_lat, write_lat]
        
        trace = go.Bar(
                x = x,
                y = y,
                name = _name,
                textposition = 'auto',
                # marker=dict(
                #     color='rgb(158,202,225)',
                #     line=dict(
                #         color='rgb(8,48,107)',
                #         width=1.5),
                #     ),
            )
        
        layout = go.Layout(title = "Latency",
                        xaxis = dict(title = "",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "Latency(in μs)",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in fio_result:
            _fio_result = fio_result[p]
            _name = p
            try:
                with open(_fio_result, 'r') as f:
                    result = json.load(f)
                read_lat =round((result["jobs"][0]["read"]["clat_ns"]["mean"] / 1000), 2)
                write_lat =round((result["jobs"][0]["write"]["clat_ns"]["mean"] / 1000), 2)

            except (FileNotFoundError, IOError, ValueError):
                read_lat = 0
                write_lat = 0 

            x = ['Read', 'Write']
            y = [read_lat, write_lat]
            
            trace = go.Bar(
                    x = x,
                    y = y,
                    name = _name,
                    textposition = 'auto',
                    # marker=dict(
                    #     color='rgb(158,202,225)',
                    #     line=dict(
                    #         color='rgb(8,48,107)',
                    #         width=1.5),
                    #     ),
                )
            
            layout = go.Layout(title = "Latency",
                            xaxis = dict(title = "",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            )
                                            ),
                            yaxis = dict(title = "Latency(in μs)",
                                            titlefont=dict(
                                                color='rgb(153, 0, 0)'
                                            ),
                                            overlaying='y',
                                            side='left'),
                                            legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)  

    return go.Figure(data=all_data, layout=layout)

@app.callback(
    Output('tail-latency-read', 'figure'), 
    [Input('tail-latency-read-update', 'n_intervals')])
def tail_latency_read(interval):

    global final_csv, test_name, products, fio_result

    all_data = [] 

    if "And" not in test_name:      
        _fio_result = fio_result[test_name]
        _name = test_name
        try:
            with open(_fio_result, 'r') as f:
                result = json.load(f)
            read_per =result["jobs"][0]["read"]["clat_ns"]["percentile"]
            read_per = {float(i) :round(read_per[i]/1000, 2) for i in read_per}
            # write_per =result["jobs"][0]["write"]["clat_ns"]["percentile"]   
            # write_per = {float(i) :round(write_per[i]/1000, 2) for i in write_per}

        except (FileNotFoundError, IOError, ValueError):
            read_per = {0: 0}
            # write_per = {0:0} 

        x = list(read_per.values())
        y = list(read_per.keys())
      
        trace = go.Scatter(
                x = x,
                y = y,
                name = _name,
                )
        
        layout = go.Layout(title = "Read Tail Latency",
                        xaxis = dict(title = "Read Latency(in μs)",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        )
                                        ),
                        yaxis = dict(title = "Percentile",
                                        titlefont=dict(
                                            color='rgb(153, 0, 0)'
                                        ),
                                        overlaying='y',
                                        side='left'),
                                        legend=dict(y=1, x=1.05, orientation='v'))
        all_data.append(trace)   
    else:
        for p in fio_result:
            _fio_result = fio_result[p]
            _name = p
            try:
                with open(_fio_result, 'r') as f:
                    result = json.load(f)
                read_per =result["jobs"][0]["read"]["clat_ns"]["percentile"]
                read_per = {float(i) :round(read_per[i]/1000, 2) for i in read_per}
                # write_per =result["jobs"][0]["write"]["clat_ns"]["percentile"]   
                # write_per = {float(i) :round(write_per[i]/1000, 2) for i in write_per}

            except (FileNotFoundError, IOError, ValueError):
                read_per = {0: 0}
                # write_per = {0:0} 

            y = list(read_per.keys())
            x = list(read_per.values())
            
            trace = go.Scatter(
                                    x = x,
                                    y = y,
                                    name = _name,
                                )     
            layout = go.Layout(title = "Read Tail Latency",
                                    xaxis = dict(title = "Read Latency(in μs)",
                                                    titlefont=dict(
                                                        color='rgb(153, 0, 0)'
                                                    )
                                                    ),
                                    yaxis = dict(title = "Percentile",
                                                    titlefont=dict(
                                                        color='rgb(153, 0, 0)'
                                                    ),
                                                    overlaying='y',
                                                    side='left'),
                                                    legend=dict(y=1, x=1.05, orientation='v'))
            all_data.append(trace)   
    return go.Figure(data=all_data, layout=layout)


@app.callback(
    Output('live-cpu', 'value'), 
    [Input('live-cpu-update', 'n_intervals')],
    [State("connection-est", "value")])
def cpu_live(_,interval):
    global live
    df = pd.read_csv(live)
    point = df.tail(1)["CPU_Utilization"]    
    point = int(point)
    return point 

@app.callback(
    Output('live-memory', 'value'), 
    [Input('live-memory-update', 'n_intervals')],
    [State("connection-est", "value")])
def memory_live(_,interval):
    global live
    df = pd.read_csv(live)
    point = df.tail(1)["Memory_Utilization"]    
    point = int(point)
    return point 

@app.callback(
    Output('live-readiops', 'value'), 
    [Input('live-readiops-update', 'n_intervals')],
    [State("connection-est", "value")])
def readiops_live(_,interval):
    global live
    df = pd.read_csv(live)
    point = df.tail(1)["Read_IOPS"]    
    point = int(point)
    return point 

@app.callback(
    Output('live-writeiops', 'value'), 
    [Input('live-writeiops-update', 'n_intervals')],
    [State("connection-est", "value")])
def writeiops_live(_,interval):
    global live
    df = pd.read_csv(live)
    point = df.tail(1)["Write_IOPS"]    
    point = int(point)
    return point 

@app.callback(
    Output('live-readthroughput', 'value'), 
    [Input('live-readthroughput-update', 'n_intervals')],
    [State("connection-est", "value")])
def readthroughput_live(_,interval):
    global live
    df = pd.read_csv(live)
    point = df.tail(1)["Read_Throughput(MBps)"]    
    point = int(point)
    return point 

@app.callback(
    Output('live-writethroughput', 'value'), 
    [Input('live-writethroughput-update', 'n_intervals')],
    [State("connection-est", "value")])
def writethroughput_live(_,interval):
    global live
    df = pd.read_csv(live)
    point = df.tail(1)["Write_Throughput(MBps)"]    
    point = int(point)
    return point 

app.run_server(host="0.0.0.0", debug=True)
#app.run_server(host="0.0.0.0")


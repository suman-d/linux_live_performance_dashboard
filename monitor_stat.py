import psutil
import datetime
import time
import json
import yaml
import os
import subprocess
import csv

from threading import Thread
from collections import OrderedDict
from statistics import mean 


def AppendFile(text, filename):
    """Equivalent to >> in BASH, append a line to a text file."""
    with open(filename, "a") as f:
        f.write(text)
        f.write("\n")

def start_iostat(dev, duration, iostat_output):

    global sleep_time

    pwd = os.getcwd()
    #cmd = "iostat -xdm 1 {} {} > {} &".format(dev, duration+sleep_time, iostat_output)
    cmd = "iostat -xdm 1 -T -g {} {} > {} &".format(dev, duration+sleep_time, iostat_output)
    os.system(cmd)
    
def run_command(command):
    print(command)
    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, err = p.communicate()
    return output.decode("utf-8")

def get_disk_stats(iostat_output):

    with open(iostat_output) as fd:
        data = fd.read().splitlines()
        last_stat = data[-2].split()

    r_iops = int(float(last_stat[3]))
    w_iops = int(float(last_stat[4]))
    r_bw = int(float(last_stat[5]))
    w_bw = int(float(last_stat[6]))

    disk_stat = [r_iops, w_iops, r_bw, w_bw]
    
    return disk_stat

def get_cpu_stat(cpus):
    _stats_per_cpu = psutil.cpu_percent(percpu=True)
    _cpu_data = []
    for c in cpus:
        _cpu_data.append(_stats_per_cpu[int(c)])
    
    return round(mean(_cpu_data), 2)

def monitor_disk_cpu_mem_lat_util(iostat_output, final_csv, duration, n_clicks, live_csv):

    global sleep_time, cpus

    system_stat = OrderedDict()
    # run_command("rm -rf {}".format(final_csv))

    # AppendFile("Time, CPU_Utilization, Memory_Utilization, Read IOPS, Write IOPS, Read Throughput(MBps), Write Throughput(MBps)",
    #            final_csv)

    if n_clicks == 1:
        time_stamp = 1
    else:
        time_stamp = (n_clicks-1) * (duration + sleep_time) + 2*(n_clicks)

    while duration+sleep_time > 0:
        #time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        #time_stamp = datetime.datetime.now().strftime("%M-%S")
        cpu_utilization = get_cpu_stat(cpus)
        mem_utilization = psutil.virtual_memory()[2]
        r_iops, w_iops, r_bw, w_bw = get_disk_stats(iostat_output)

        # Writing the results in CSV 
        with open(final_csv, 'a') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')
            filewriter.writerow([time_stamp, cpu_utilization, mem_utilization, r_iops, w_iops, r_bw, w_bw])

        with open(live_csv, 'a') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',')
            filewriter.writerow([cpu_utilization, mem_utilization, r_iops, w_iops, r_bw, w_bw])

        time_stamp +=1 
        time.sleep(1)
        duration -= 1

    AppendFile("{},0,0,0,0,0,0".format(time_stamp+1), final_csv)

    return system_stat

# Reading the config file
pwd = os.getcwd()
config = pwd + "/config.yml"
with open(config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)


# # Defining the output iostat and final csv file
# iostat_output = pwd + "/iostat.txt"
# final_csv =  pwd + "/allstats.csv"


# # Reading the device name
# dev_name = cfg['storage_config']['dev_name']
# duration = cfg['test_config']['duration']
sleep_time = cfg['test_config']['sleep_time']
cpus = cfg['test_config']['cpus'].split(",")
cpus = [c for c in cpus if c]

# # Starting the monitoring
# start_iostat(dev_name, duration)
# time.sleep(2)

# # Starting all stats monitoring 
# monitor_disk_cpu_mem_lat_util(duration)

if __name__ == "__main__":
    pass
    




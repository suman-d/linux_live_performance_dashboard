import psutil
import datetime
import time
import json
import yaml
import os
import subprocess
import csv
import psutil
from threading import Thread

import monitor_stat 

def Run2(cmd):
    """Run a cmd[], return the exit code, stdout, and stderr."""
    p = subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL)
    return p

def JobWrapper_fio_Local(cmd):
    p = Run2(cmd)

def JobWrapper_statmonitor(iostat_output, final_csv, duration, n_clicks, live_csv):
    monitor_stat.monitor_disk_cpu_mem_lat_util(iostat_output, final_csv, duration, n_clicks, live_csv)

def run_command(command):
    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, err = p.communicate()
    return output.decode("utf-8")

def fio_cmd(device, output_file):

    global write_percentage, block_size, duration, numjobs, iodepth, cpus, rate_iops, rate

    if rate_iops and not rate:
        cmd = "taskset -c {} fio --name=demo --readwrite=randrw --rwmixwrite={} --bs={} \
            --invalidate=1 --end_fsync=0 --group_reporting --direct=1 \
            --filename={} --time_based --runtime={} \
            --ioengine=libaio --numjobs={} --iodepth={} --norandommap --randrepeat=0 \
            --output-format=json+ --exitall --output={} --rate_iops={}".format(cpus, write_percentage, block_size, 
                                                                device, duration, numjobs, iodepth, output_file, rate_iops)
    
    elif rate and not rate_iops:
        cmd = "taskset -c {} fio --name=demo --readwrite=randrw --rwmixwrite={} --bs={} \
            --invalidate=1 --end_fsync=0 --group_reporting --direct=1 \
            --filename={} --time_based --runtime={} \
            --ioengine=libaio --numjobs={} --iodepth={} --norandommap --randrepeat=0 \
            --output-format=json+ --exitall --output={} --rate={}".format(cpus, write_percentage, block_size, 
                                                                device, duration, numjobs, iodepth, output_file, rate)
    
    elif rate and rate_iops:
        cmd = "taskset -c {} fio --name=demo --readwrite=randrw --rwmixwrite={} --bs={} \
            --invalidate=1 --end_fsync=0 --group_reporting --direct=1 \
            --filename={} --time_based --runtime={} \
            --ioengine=libaio --numjobs={} --iodepth={} --norandommap --randrepeat=0 \
            --output-format=json+ --exitall --output={} --rate={} --rate_iops={}".format(cpus, write_percentage, block_size, 
                                                                device, duration, numjobs, iodepth, output_file, rate, rate_iops)
    
    else:
        cmd = "taskset -c {} fio --name=demo --readwrite=randrw --rwmixwrite={} --bs={} \
            --invalidate=1 --end_fsync=0 --group_reporting --direct=1 \
            --filename={} --time_based --runtime={} \
            --ioengine=libaio --numjobs={} --iodepth={} --norandommap --randrepeat=0 \
            --output-format=json+ --exitall --output={}".format(cpus, write_percentage, block_size, 
                                                                device, duration, numjobs, iodepth, output_file)

    return cmd

def get_fio_procesids():
    fio_process = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if 'fio' in p.info['name']]
    return fio_process

def kill_all(proc):
    if proc:
        for i in proc:
            try:
                p = psutil.Process(i)
                p.terminate()
            except (psutil.ZombieProcess, psutil.AccessDenied, psutil.NoSuchProcess):
                pass 
    else:
        pass 

def fio_running2():
    fio_process_check = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if 'fio' in p.info['name']]
    if bool(fio_process_check) == True:
        return True
    else:
        return False

def fio_running():
    fio_process_check = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if 'fio' in p.info['name']]
    if len(fio_process_check) == 0 or len(fio_process_check) == 1:
        return False
    else:
        return True

def competitive_tests(n_clicks):

    global products, sleep_time, device, live

    for p in products.keys():
        value = "{}_{}".format(p, products[p][1]["card"])
        _dev = device[value]
        _iostat_output = iostat_output[value]
        _final_csv = final_csv[value]
        _fio_result = fio_result[value]
        #_fio_dev = _dev.replace("nvme", "/dev/nvme")
        _fio_dev = ":".join([ "/dev/"+i for i in _dev.split(":")]) 

        # Start collecting the IOSTAT
        monitor_stat.start_iostat(_dev, duration, _iostat_output)
        time.sleep(2)
        # Start the all stats monitoring 
        monitor_all = Thread(target=JobWrapper_statmonitor, args=(_iostat_output, _final_csv, duration, n_clicks, live))
        monitor_all.start()
        time.sleep(1)
        # Starting the FIO
        cmd = fio_cmd(_fio_dev, _fio_result)
        fio_test = Thread(target=JobWrapper_fio_Local, args=(cmd,))
        fio_test.start()

        total_time = duration + sleep_time + 5
        time.sleep(total_time)


# Reading the config file
pwd = os.getcwd()
config = pwd + "/config.yml"
with open(config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

products = cfg["products"]
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

duration = cfg['test_config']['duration']
sleep_time = cfg['test_config']['sleep_time']
write_percentage = cfg['test_config']['write_percentage']
block_size = cfg['test_config']['block_size']
iodepth = cfg['test_config']['iodepth']
numjobs = cfg['test_config']['numjobs']
cpus = cfg['test_config']['cpus']
if  cpus.endswith(","):
    cpus = cpus.replace(",", "")
rate_iops = cfg['test_config']['rate_iops']
rate = cfg['test_config']['rate']





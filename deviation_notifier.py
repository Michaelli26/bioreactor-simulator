import pandas as pd
import numpy as np
import datetime



# declare set points of parameters
airflow_sp = 60
pH_sp = 7.2
feed_sp = 40
base_sp = 35
antifoam_sp = 1
rpm_pre_feed_sp = 1000
rpm_post_feed_sp = 1500
feed_triggered = False
headers = ['Timestamp', 'Agitation [rpm]', 'Airflow [mL/s]', 'DO [%]', 'Temp [C]', 'pH',
                       'Feed pump [ml/hr]',
                       'Base Pump [mL/hr]', 'Antifoam Pump [mL/hr]', '_EFT']
def agitation():
    if feed_triggered:
        return 1500
    else:
        return 1000


setpoints = {'Agitation [rpm]': (agitation(), 10), 'Airflow [mL/s]': (60, 5), 'Temp [C]': (32, 2),
             'pH': (7.20, 0.2), 'Feed pump [ml/hr]': (40, 3), 'Base Pump [mL/hr]': (35, 3),
             'Antifoam Pump [mL/hr]': (1, 0.5) }

dtype = {'Timestamp': 'str', 'Agitation [rpm]': 'float', 'Airflow [mL/s]': 'float', 'DO [%]': 'float',
         'Temp [C]': 'float', 'pH': 'float', 'Feed pump [ml/hr]': 'float', 'Base Pump [mL/hr]': 'float',
         'Antifoam Pump [mL/hr]': 'float'}
data = pd.read_csv('dg1.csv', dtype=dtype, parse_dates=['Timestamp'], low_memory=False, na_filter=False)


# only read the entire csv if something in the last row deviates
# TODO check how long pumps have been running for. aka value != 0

for param, value in data.iloc[[-1]].iteritems():
    print(param)
    print(type(value))
    value = value.iat[0]
    if param not in setpoints.keys():
        continue
    setpoint, tolerance = setpoints[param]
    print(f'setpoint {setpoint}    tolerance {tolerance}')
    #print(type(value-setpoint))
    print(value - setpoint)
    if 'pump' in param and value != 0:
        if abs(value - setpoint) > tolerance:
            current_time = data['Timestamp'].iat[-1]
            for idx in reversed(data.index):
                if data.at[idx, param] > tolerance:
                    print('finding running length of deviation')
                    continue
                else:
                    start_time = data['Timestamp'].iat[idx]
                    print(f'start_time {start_time}')
                    running_length = current_time-start_time
                    print(f' Deviation occurring for {running_length}')
                    if running_length > datetime.timedelta(minutes=5):
                        print('deviation over 5 minutes long. should notify operator')

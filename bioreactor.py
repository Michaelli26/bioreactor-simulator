import random, datetime, collections, sys, csv, weakref
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import numpy as np
import pandas as pd
import os
import math


class Reactor:
    __refs__ = collections.defaultdict(list)

    def __init__(self, name, pH=7.20, temp=32, agitation=1000, airflow=60, DO=100,
                 final_eft=datetime.timedelta(hours=68), deviation=False, active=False, start_time=None):
        # def __init__(self, name, params=None, deviation=False, active=False, start_time=None):
        self.name = name
        self.pH = pH
        self.temp = temp
        self.agitation = agitation
        self.airflow = airflow
        self.DO = DO
        self.final_eft = final_eft
        self.deviation = deviation
        self.active = active
        self.start_time = start_time  # might not need and just base start time on first value in csv for timestamp
        self.file = name + '.csv'
        self.params = [self.agitation, self.airflow, self.DO, self.temp, self.pH]
        self.__refs__[self.__class__].append(weakref.ref(self))
        self.feed_triggered = False  # currently unused
        self.feeding = False
        self.spiking = False
        self.last_feed = None
        self.feed_pump = 0
        self.base_pump = 0
        self.antifoam_pump = 0

        # all possible mechnical deviations
        self.antifoam_deviation = None
        self.agitation_deviation = None
        self.feed_deviation = None
        self.base_deviation = None
        self.airflow_deviation = None

    @classmethod
    def get_instances(cls):
        # might be unneeded
        for inst_ref in cls.__refs__[cls]:
            inst = inst_ref()
            if inst is not None:
                yield inst

    def create_deviation(self):
        self.deviation = True
        pass
        # randomly go higher or lower

    def fix_deviation(self):
        pass

    def start_run(self):
        self.active = True
        self.start_time = datetime.datetime.now()

    def end_run(self):
        '''
        once the final_eft time has been reached, the run will not be active
        :return:
        '''
        self.active = False

    def create_csv(self):
        """
        Creates the csv file for the reactor instance with headers and first row of data values. The first timestamp
        is taken to be the start time

        :return: None
        """
        with open(self.file, 'w+', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            headers = ['Timestamp', 'Agitation [rpm]', 'Airflow [mL/s]', 'DO [%]', 'Temp [C]', 'pH',
                       'Feed pump [ml/hr]',
                       'Base Pump [mL/hr]', 'Antifoam Pump [mL/hr]', '_EFT']
            writer.writerow(headers)
            first_values = [self.start_time]
            for parameter in [self.agitation, self.airflow, self.DO, self.temp, self.pH, self.feed_pump, self.base_pump,
                              self.antifoam_pump]:
                if parameter == self.antifoam_pump or parameter == self.base_pump or parameter == self.feed_pump:
                    first_values.append(parameter)
                else:
                    first_values.append(round(random.uniform(0.9995 * parameter, 1.0005 * parameter), 2))

            writer.writerow(first_values)
            csvfile.close()

    def log_data(self):
        """
        logs a single row of data to the reactor's csv file. pH needed to have less noise than the other parameters
        to be more realistic. Checks if the current EFT is less than the final EFT before it logs the data. Calls
        the reactor's end_run() method if it hits the final EFT.
        :return:
        """
        values = []
        lines = open(self.file).readlines()
        last_timestamp_str = lines[-1].split(',')[0]
        last_timestamp = datetime.datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        current_timestamp = last_timestamp + datetime.timedelta(minutes=1)
        current_eft = current_timestamp - self.start_time

        if current_eft < self.final_eft:
            values.append(current_timestamp)
            self.do_trend(current_eft)
            self.first_pulse(current_eft)
            self.feed_spike(current_eft)
            self.feed()
            self.base()
            self.motor_deviation()
            self.antifoam(current_eft)
            self.airflow_adjust()
            # get rest of the row's parameter values
            # self.param does not update with new values
            for parameter in [self.agitation, self.airflow, self.DO, self.temp, self.pH, self.feed_pump, self.base_pump,
                              self.antifoam_pump]:

                if parameter == self.pH:
                    values.append(round(random.uniform(0.9995 * parameter, 1.0005 * parameter), 4))
                # pumps shouldn't have noise
                elif parameter == self.antifoam_pump or parameter == self.base_pump or parameter == self.feed_pump:
                    values.append(parameter)
                else:
                    values.append(round(random.uniform(0.995 * parameter, 1.005 * parameter), 2))
            values.append(current_eft)

            with open(self.file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(values)

        else:
            self.end_run()

    def read_data(self, parameter):
        '''

        :param parameter: must be exactly the same as the header of the parameter you want to analyze
        :return: a pandas dataframe created from the reactor's csv file that only contains the timestamp, EFT, and
        desired parameter
        '''
        dtype = {'Timestamp': 'str', parameter: 'float'}
        data = pd.read_csv(self.file,
                           dtype=dtype,
                           parse_dates=['Timestamp'], usecols=['Timestamp'].append(parameter), low_memory=False,
                           na_filter=False)
        start_time = data['Timestamp'][0]
        # data.insert(loc=2, column='EFT', value=(data['Timestamp'] - start_time) / np.timedelta64(1, 'h'))
        return data


    def antifoam(self, eft):
        """
        turns antifoam pump on at 1 mL/hr for 10 minutes every 3 hours
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return:
        """
        if self.antifoam_deviation == 'on':
            self.antifoam_pump = 1
        elif self.antifoam_deviation == 'off' or self.antifoam_deviation is None:
            self.antifoam_pump = 0
            '''
            if self.DO > 0:
                print(f'beginning {self.DO}')
                csv_data = self.read_data('Antifoam Pump [mL/hr]')
                current_time = csv_data['Timestamp'].iat[-1]
                print(f'current time {current_time}')
                # TODO check how long antifoam pump has been on and decrease DO accordingly
                for idx in reversed(csv_data.index):
                    if csv_data.at[idx, 'Antifoam Pump [mL/hr]'] == 1:
                        print('finding running length')
                        print(f'middle {self.DO}')
                        continue
                    else:
                        start_time = csv_data['Timestamp'].iat[idx]
                        print(f'start_time {start_time}')
                        running_length = current_time-start_time
                        print(f' running length {running_length}')
                        if running_length > datetime.timedelta(minutes=30) and self.DO > 3:
                            self.DO -= 4
                            print('-3')
                        elif running_length > datetime.timedelta(minutes=20) and self.DO > 1:
                            self.DO -= 2
                            print('-1')
                        elif running_length > datetime.timedelta(minutes=10) and self.DO > 0.5:
                            self.DO -= 1
                            print('-0.5')
                        break
                        print(f'end {self.DO}')
                '''
        if not self.antifoam_deviation:
            for hour in range(10, 65, 3):
                # turn pump on every 3 hours
                if eft == datetime.timedelta(hours=hour):
                    self.antifoam_pump = 1
                # turn pump off every 3 hours and 10 minutes
                elif eft == datetime.timedelta(hours=hour, minutes=10):
                    self.antifoam_pump = 0



    def first_pulse(self, eft):
        """
        starts the first pulse of the reactor and simultaneously spikes the pH and DO. Function only used
        from an EFT of 9 to 9:40
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return:
        """
        # start the first feed trigger might not need feed_trigger attribute
        if datetime.timedelta(hours=9) < eft and not self.feeding and not self.feed_triggered:
            if self.pH < 8:
                self.pH += 0.002
            if self.DO < 100:
                self.DO += 0.3
            self.agitation = 1500

    def feed_spike(self, eft):
        '''
        Controls feed spikes indicating cells are starving and need additional glucose
        :param eft:
        :return:
        '''
        if (datetime.timedelta(hours=15) == eft or self.spiking) and self.feed_triggered:
            self.last_feed = eft
            self.spiking = True
            if self.pH < 8:
                self.pH += 0.002
            if self.DO < 100:
                self.DO += 0.3
        elif self.last_feed is not None:
            if datetime.timedelta(hours=15) < eft < datetime.timedelta(hours=30):
                if eft > self.last_feed + datetime.timedelta(hours=1, minutes=30) or self.spiking:
                    self.spiking = True
            elif datetime.timedelta(hours=30) < eft < datetime.timedelta(hours=55):
                if eft > self.last_feed + datetime.timedelta(minutes=30) or self.spiking:
                    self.spiking = True
            elif datetime.timedelta(hours=55) < eft < datetime.timedelta(hours=66):
                if eft > self.last_feed + datetime.timedelta(hours=2) or self.spiking:
                    self.spiking = True

    def do_trend(self, eft):
        """
        adjusts the DO values of the reactor to fit the lag and growth phase trend
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return:
        """
        # initial DO trend during lag phase

        if eft < datetime.timedelta(hours=7, minutes=36):
            int_eft = eft.total_seconds() / 3600
            self.DO = -math.exp(int_eft - 3.5) + 100

    def motor_deviation(self):
        """
        increases the agitation to 1500 rpm once feed has triggered indicating cells are actively consuming glucose and
        need additional oxygen
        :return:
        """
        if self.agitation_deviation is not None:
            if self.agitation_deviation == 'up':
                self.agitation += 5
            elif self.agitation_deviation == 'down':
                self.agitation -= 5
        elif self.agitation_deviation is None:
            if self.feed_triggered:
                self.agitation = 1500
            elif not self.feed_triggered:
                self.agitation = 1000

    def airflow_adjust(self):
        if self.airflow_deviation is None:
            self.airflow = 60
        else:
            if self.airflow_deviation == 'up':
                self.airflow += 0.3
                self.DO += 0.2
            elif self.airflow_deviation == 'down':
                self.airflow -= 0.3
                self.DO -= 0.2

    def feed(self):
        """
        activates the feed pump once the pH has passed 7.27 for the first pulse and 7.22 for all subsequent feed
        spikes. The feed is acidic which decreases the pH and now the cells have a carbon source to consume, the cells
        are metabolically active and the DO value decreases.
        :return:
        """
        # controlling base pump
        if self.feed_deviation is None and self.base_deviation is None:
            if (self.pH > 7.27 or self.feeding) and (not self.feed_triggered or self.pH > 7.20):
                    print('reducing pH >7.27')
                    self.pH -= 0.002
                    if self.DO > 0:
                        self.DO -= 0.4
                    self.feed_pump = 40
                    self.feeding = True
                    self.spiking = False
            elif (self.pH > 7.22 or self.feeding) and self.feed_triggered:
                    print('reducing pH >7.22')
                    self.pH -= 0.002
                    if self.DO > 0:
                        self.DO -= 0.2
                    self.feed_pump = 40
                    self.feeding = True
                    self.spiking = False
            else:
                self.feed_pump = 0
        else:
            if self.feed_deviation == 'on':
                self.feed_pump = 45
                if self.DO > 0:
                    self.DO -= 0.3
                if self.pH > 3:
                    self.pH -= 0.002
            elif self.feed_deviation == 'off':
                self.feed_pump = 0

    def base(self):
        '''
        controls the base pump, if base was ever added to the reactor, that means feed and the first glucose pulse was
        also triggered
        :return:
        '''
        if not self.base_deviation:
            if 0 < self.pH < 7.20:
                self.feeding = False
                self.feed_triggered = True
                self.pH += 0.001
                self.base_pump = 35
            else:
                self.base_pump = 0
        else:

            if self.base_deviation == 'on':
                self.base_pump = 40
                if self.pH < 14:
                    self.pH += 0.05
            elif self.base_deviation == 'off':
                self.base_pump = 0


def create_all(names):
    '''
    Starts the run and creates a csv file for each reactor

    :param names: all the Reactor objects' names to be created
    :type names: list
    :return: all instances of Reactor objects
    :rtype: list
    '''

    reactors = []
    for name in names:
        reactor = Reactor(name=name)
        reactor.start_run()
        reactor.create_csv()
        reactors.append(reactor)
    return reactors


def del_all():
    for reactor in Reactor.get_instances():
        del reactor


def run_all(reactors):
    '''

    :param reactors: every Reactor object that was instantiated
    :type reactors: list
    :return:
    '''

    active_reactors = len(reactors)
    while active_reactors > 0:
        for reactor in reactors:
            if reactor.active:
                reactor.log_data()
            else:
                active_reactors -= 1

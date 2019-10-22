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

    @classmethod
    def get_instances(cls):
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
        self.active = False

    def create_csv(self):
        '''
        Creates the csv file for the reactor instance with headers and first row of data values. The first timestamp
        is taken to be the start time

        :return: None
        '''
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

    def graph(self, parameter):
        '''
        creates graphs of DO, temp, pH, agitation, and airflow vs EFT. Saves each graph as a png to the current folder
        as name+parameter
        :return:
        '''
        headers = ('Agitation [rpm]', 'Airflow [mL/s]', 'DO [%]', 'Temp [C]', 'pH', 'Feed pump [ml/hr]',
                   'Base Pump [mL/hr]', 'Antifoam Pump [mL/hr]')
        for header in headers:
            if parameter in header:
                data = pd.read_csv(self.file,
                                   dtype={'Timestamp': 'str', header: 'float'},
                                   parse_dates=['Timestamp'], usecols=['Timestamp', header], low_memory=False,
                                   na_filter=False)
                start_time = data['Timestamp'][0]
                data.insert(loc=2, column='EFT', value=(data['Timestamp'] - start_time) / np.timedelta64(1, 'h'))
                for label, content in data.iteritems():
                    if label == 'Timestamp' or label == 'EFT':
                        continue
                    else:
                        fig, ax = plt.subplots(figsize=(20, 10))
                        ax.plot(data['EFT'], content)
                        ax.set_xlabel('EFT [hrs]', fontsize=20)
                        ax.set_ylabel(label, fontsize=20)
                        ax.tick_params(labelsize=12)
                        # parameter = label.split()[0]
                        print(self.name + '-' + parameter + '.png')
                        plt.savefig(fname=(self.name + '-' + parameter + '.png'))
                        plt.close()

    def log_data(self):
        '''
        logs a single row of data to the reactor's csv file. pH needed to have less noise than the other parameters
        to be more realistic. Checks if the current EFT is less than the final EFT before it logs the data. Calls
        the reactor's end_run() method if it hits the final EFT.
        :return:
        '''
        values = []

        # with open(self.file, 'r', newline='') as csvfile:
        #   reader = csv.reader(csvfile, delimiter=',')

        # get previous timestamp
        # last_line = subprocess.check_output(["tail", "-1", "imdb-data.csv"])
        lines = open(self.file).readlines()
        last_timestamp_str = lines[-1].split(',')[0]
        last_timestamp = datetime.datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        current_eft = last_timestamp - self.start_time

        if current_eft < self.final_eft:
            values.append(last_timestamp + datetime.timedelta(minutes=1))
            self.do_trend(current_eft)
            self.first_pulse(current_eft)
            self.feed_spike(current_eft)
            self.feed()
            self.base()
            self.antifoam(current_eft)
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

    def antifoam(self, eft):
        '''
        turns antifoam pump on at 1 mL/hr for
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return:
        '''

        for hour in range(10, 65, 5):
            # turn pump on every 5 hours
            if eft == datetime.timedelta(hours=hour):
                self.antifoam_pump = 5
            # turn pump off every 5 hours and 20 minutes
            elif eft == datetime.timedelta(hours=hour, minutes=10):
                self.antifoam_pump = 0

    def first_pulse(self, eft):
        '''
        starts the first pulse of the reactor and simultaneously spikes the pH and DO. Function only used
        from an EFT of 9 to 9:40
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return:
        '''
        # start the first feed trigger might not need feed_trigger attribute
        if datetime.timedelta(hours=9) < eft and not self.feeding and not self.feed_triggered:
            self.pH += 0.002
            self.DO += 0.3

    def feed_spike(self, eft):
        '''
        Controls feed spikes indicating cells are starving and need additional glucose
        :param eft:
        :return:
        '''
        if (datetime.timedelta(hours=15) == eft or self.spiking) and self.feed_triggered:
            self.last_feed = eft
            self.spiking = True
            self.agitation = 1500
            self.pH += 0.002
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
        '''
        adjusts the DO values of the reactor to fit the lag and growth phase trend
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return:
        '''
        # initial DO trend during lag phase
        if eft < datetime.timedelta(hours=7, minutes=15):
            int_eft = eft.total_seconds() / 3600
            self.DO = -math.exp(int_eft - 3) + 100

    def rpm_ramp(self):
        '''
        increases the agitation to 1500 rpm once feed has triggered indicating cells are actively consuming glucose and
        need additional oxygen
        :return:
        '''
        self.agitation = 1500

    def feed(self):
        '''
        activates the feed pump once the pH has passed 7.27 for the first pulse and 7.22 for all subsequent feed
        spikes which decreases the pH and DO values of the reactor.
        :return:
        '''
        # controlling base pump
        if (self.pH > 7.27 or self.feeding) and not self.feed_triggered:
            self.feeding = True
            self.spiking = False
            self.pH -= 0.002
            self.DO -= 0.4
            self.feed_pump = 40
        elif (self.pH > 7.22 or self.feeding) and self.feed_triggered:
            self.pH -= 0.002
            self.DO -= 0.2
            self.feed_pump = 40
            self.feeding = True
            self.spiking = False
        else:
            self.feed_pump = 0

    def base(self):
        '''
        controls the base pump, if base was ever added to the reactor, that means feed and the first glucose pulse was
        also triggered
        :return:
        '''
        if 0 < self.pH < 7.20:
            self.feeding = False
            self.feed_triggered = True
            self.pH += 0.001
            self.base_pump = 35
        else:
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

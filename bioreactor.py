import random
import datetime
import csv
import math


class Reactor:
    """
    The reactor object creates a simulation of a bioreactor and records the data into a csv file similar to how an
    Eppendorf Dasgip would record the data.

    Process Set Points
        Temperature - 32.0 °C
        pH - 7.20
        Airflow - 60 mL/s
        Agitation - 1000 rpm -> 1500 rpm ramp after the first feed is triggered
        DO - Not controlled

    Additions
        Feed - triggered by pH
        Base - triggered by pH
        Antifoam - set time schedule

    Process Description
        This particular fermentation simulates a fed-batch process in which an acidic glucose feed,
    base and antifoam are added to the reactor. The feed is triggered once the microbes show signs of starvation through
    the rise of the pH and DO. During the batch phase the pH is allowed to reach a value of 7.27, indicating all the
    glucose is depleted. At this point, acidic feed will be added until the pH setpoint is dropped to the
    set point (7.20). Since it takes time for the feed to homogenize with the tank broth, the pH will fall below the
    set point which is why the base control is needed. When the feed is first triggered, the motor ramps to 1500 rpm
    as the microbes are more metabolically active and will require more oxygen for the aerobic fermentation process.
    Antifoam is added on a set schedule and turns on for every 3 hours for 10 minutes after an EFT of 10 hours is
    reached.

    Deviations
        The reactor begins with no deviations and deviations are only introduced through the PYQT GUI in the
        simulatorpyqt module. Only mechanical deviations are simulated and include the following: motor, airflow,
        temperature, feed pump, base pump, and antifoam pump errors.

    :param name: name of the reactor
    :type name: str
    :param pH: pH set point
    :type pH: float
    :param temp: temperature set point in °C
    :param agitation: starting agitation set point in rpm
    :type agitation: int
    :param airflow: the airflow set point in mL/s
    :type agitation: int
    :param DO: the starting dissolved oxygen of the reactor in %
    :type DO: int
    """

    def __init__(self, name):
        self.name = name
        self.pH = 7.20
        self.temp = 32.0
        self.agitation = 1000
        self.airflow = 60
        self.DO = 100
        self.final_eft = datetime.timedelta(hours=68)
        self.active = False
        self.start_time = None
        self.file = name + '.csv'
        self.params = [self.agitation, self.airflow, self.DO, self.temp, self.pH]
        self.feed_triggered = False
        self.feeding = False
        self.spiking = False
        self.last_feed = None
        self.feed_pump = 0
        self.base_pump = 0
        self.antifoam_pump = 0

        # all possible mechanical deviations
        self.antifoam_deviation = None
        self.agitation_deviation = None
        self.feed_deviation = None
        self.base_deviation = None
        self.airflow_deviation = None
        self.temp_deviation = None

        # attributes to bring DO back to normal after an agitation or airflow deviation is fixed
        self.fixed_motor = 0
        self.fixed_airflow = 0

    def start_run(self):
        """
        Activates the run and creates the fermentation start time.
        :return: None
        """
        self.active = True
        self.start_time = datetime.datetime.now()

    def end_run(self):
        """
        Once the final_eft time has been reached, the run will not be active.
        :return: None
        """
        self.active = False

    def create_csv(self):
        """
        Creates the csv file for the reactor instance with column headers and the first row of data values.
        :return: None
        """
        with open(self.file, 'w+', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            headers = ['Timestamp', 'Agitation [rpm]', 'Airflow [mL/s]', 'DO [%]', 'Temp [C]', 'pH',
                       'Feed Pump [ml/hr]',
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
        If the run is still active, this calls all the methods that declare the value of each parameter and logs
        a single row of data to the reactor's csv file. Every time a new row of data is logged to the csv, it is counted
        as an EFT of one minute. When the current EFT has reached the final EFT, this will call the end_run method and
        finish the fermentation run.
        :return: None
        """
        values = []
        lines = open(self.file).readlines()
        last_timestamp_str = lines[-1].split(',')[0]
        last_timestamp = datetime.datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        current_timestamp = last_timestamp + datetime.timedelta(minutes=1)
        current_eft = current_timestamp - self.start_time

        if current_eft < self.final_eft:
            values.append(current_timestamp)
            self.initial_DO(current_eft)
            self.first_pulse(current_eft)
            self.feed_spike(current_eft)
            self.feed_controller(current_eft)
            self.base_controller()
            self.motor_controller()
            self.antifoam_controller(current_eft)
            self.airflow_controller()
            self.temp_controller()

            # add all the parameter values to the 'value' list that will be used to append data to the csv file
            for parameter in [self.agitation, self.airflow, self.DO, self.temp, self.pH, self.feed_pump, self.base_pump,
                              self.antifoam_pump]:

                if parameter == self.pH:  # pH needs less noise than other parameters to be more realistic
                    values.append(round(random.uniform(0.9995 * parameter, 1.0005 * parameter), 4))
                # pumps shouldn't have equipment noise i.e. 'off' should hold a steady 0 value
                elif parameter == self.antifoam_pump or parameter == self.base_pump or parameter == self.feed_pump:
                    values.append(parameter)
                else:
                    values.append(round(random.uniform(0.995 * parameter, 1.005 * parameter), 2))
            values.append(current_eft)

            with open(self.file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(values)
                csvfile.close()

        else:
            self.end_run()

    def first_pulse(self, eft):
        """
        Starts the first pulse of the reactor by simultaneously spiking the pH and DO which indicates the cells are
        starving and in need of glucose. This first pulse spikes higher/longer than all subsequent feed spikes to ensure
        the cells are requiring glucose and feed is not prematurely introduced to the reactor. This function is only
        active after an EFT of 9 hours (around the time the actual first feed spike would occur).
        :param eft: current Elapsed Fermentation Time (EFT)
        :type eft: datetime.timedelta object
        :return: None
        """

        if datetime.timedelta(hours=9) < eft and not self.feeding and not self.feed_triggered and \
                not self.feed_deviation == 'on':
            if self.pH < 8:
                self.pH += 0.002
            if self.DO < 100:
                self.DO += 0.3
            self.last_feed = eft

    def feed_spike(self, eft):
        """
        Controls all feed spikes after the first pulse. This function is used to indicate cells are starving and need
        additional feed glucose. These spikes are smaller than the initial feed because an incorrect feed trigger is
        less likely to occur and will have less of a negative impact. Feed triggers occur more during the middle of the
        run when the cells are in the stationary phase of the growth curve. Towards the end of the run the cells begin
        to die (death phrase) and they do not require glucose as frequently.
        :param eft: current Elapsed Fermentation Time (EFT)
        :type eft: datetime.timedelta object
        :return: None
        """

        if self.spiking and self.feed_triggered and \
                not self.feed_deviation == 'on':
            self.last_feed = eft
            self.spiking = True
            if self.pH < 8:
                self.pH += 0.002
            if self.DO < 100:
                self.DO += 0.3

        elif self.last_feed is not None:  # feeding is not a constant intervals throughout the entire run
            if datetime.timedelta(hours=15) < eft < datetime.timedelta(hours=30):
                if eft > self.last_feed + datetime.timedelta(hours=1, minutes=30) or self.spiking:
                    self.spiking = True
                    self.last_feed = eft

            elif datetime.timedelta(hours=30) < eft < datetime.timedelta(hours=55):
                if eft > self.last_feed + datetime.timedelta(minutes=30) or self.spiking:
                    self.spiking = True
                    self.last_feed = eft

            elif datetime.timedelta(hours=55) < eft < datetime.timedelta(hours=66):
                if eft > self.last_feed + datetime.timedelta(hours=2) or self.spiking:
                    self.spiking = True
                    self.last_feed = eft

    def initial_DO(self, eft):
        """
        Adjusts the DO values of the reactor to replicate the trends of the initial lag and growth phases.
        :param eft: current Elapsed Fermentation Time (EFT)
        :type eft: datetime.timedelta object
        :return: None
        """
        if eft < datetime.timedelta(hours=7, minutes=36):
            int_eft = eft.total_seconds() / 3600
            self.DO = -math.exp(int_eft - 3.5) + 100

    def antifoam_controller(self, eft):
        """
        Controls the antifoam pump data including operating under normal conditions or if a deviation causes the pump to
        be on or off.
        :param eft: current EFT
        :type eft: datetime.timedelta object
        :return: None
        """
        if self.antifoam_deviation is None:
            for hour in range(10, 68, 3):
                # turn pump on every 3 hours
                if datetime.timedelta(hours=hour) <= eft <= datetime.timedelta(hours=hour, minutes=10):
                    self.antifoam_pump = 1
                    break
                # turn pump off every 3 hours and 10 minutes
                else:
                    self.antifoam_pump = 0

        elif self.antifoam_deviation == 'on':
            self.antifoam_pump = 1
            if self.DO > 0:
                self.DO -= 0.5

        elif self.antifoam_deviation == 'off':
            self.antifoam_pump = 0

    def motor_controller(self):
        """
        Controls the motor data including operating under normal conditions or if a deviation causes the rpm to be
        higher or lower than the set point. When under normal operating conditions the agitation increases from 1000
        to 1500 rpm once the feed has been triggered indicating cells are actively consuming glucose and need additional
        oxygen.
        :return: None
        """
        change_DO = 0.3
        if self.agitation_deviation is None:  # operate normally
            # after a motor deviation is fixed, appropriately adjust the DO up or down to what it would normally be
            if self.fixed_motor != 0 and self.agitation != 0:
                self.DO -= self.fixed_motor
                self.fixed_motor = 0
            if self.feed_triggered:
                self.agitation = 1500
            elif not self.feed_triggered:
                self.agitation = 1000

        elif self.agitation_deviation == 'up':
            self.agitation += 5
            # complicated to predict DO change due to the motor during the exponential phase so ignore DO effects
            if self.feed_triggered:
                self.DO += change_DO
                self.fixed_motor += change_DO

        elif self.agitation_deviation == 'down' and self.agitation > 0:
            self.agitation -= 5
            # complicated to predict DO change due to the motor during the exponential phase so ignore DO effects
            if self.feed_triggered and self.DO > 0:
                self.DO -= change_DO
                self.fixed_motor -= change_DO

    def temp_controller(self):
        """
        Controls the temperature data including operating under normal conditions or if a deviation causes
        the temperature to drift higher or lower than the set point.
        :return: None
        """
        if self.temp_deviation is None:
            self.temp = 32
        elif self.temp_deviation == 'up':
            self.temp += 0.1
        elif self.temp_deviation == 'down':
            self.temp -= 0.1

    def airflow_controller(self):
        """
        Controls the airflow data including operating under normal conditions or if a deviation causes the airflow to
        drift higher or lower than the set point.
        :return: None
        """
        if self.airflow_deviation is None:
            self.airflow = 60
            if self.fixed_airflow != 0:
                self.DO -= self.fixed_airflow
                self.fixed_airflow = 0

        elif self.airflow_deviation == 'up':
            self.airflow += 0.1
            self.DO += 0.2
            self.fixed_airflow += 0.2

        elif self.airflow_deviation == 'down':
            if self.airflow > 0:
                self.airflow -= 0.1
            if self.DO > 0:
                self.DO -= 0.2
                self.fixed_airflow -= 0.2

    def feed_controller(self, eft):
        """
        Activates the feed pump once the pH has passed 7.27 for the first pulse and 7.22 for all subsequent feed
        spikes. The feed is acidic which decreases the pH and provides the cells a carbon source to consume. This is an
        aerobic fermentation so when the cells are consuming glucose the cells are using oxygen so the DO value
        decreases.
        :return: None
        """
        # disable feeding if a base deviation is causing the pH to rise (which would normally trigger the feed) in order
        # to demonstrated the isolated effects of a base pump
        if self.feed_deviation is None and not self.base_deviation == 'on':
            # in an actual reactor, pH readings lag as the motor is homogenizing tank broth resulting in too much feed
            if self.pH < 7.19:
                self.feeding = False

            if (self.pH > 7.27 or self.feeding) and not self.feed_triggered:
                self.pH -= 0.002
                if self.DO > 0:  # DO will not go lower than the calibrated 0 point
                    self.DO -= 0.4
                self.feed_pump = 40
                self.feeding = True
                self.spiking = False
                if self.pH < 7.20:
                    self.feed_triggered = True
            elif (7.19 < self.pH > 7.22 or self.feeding) and self.feed_triggered:
                self.pH -= 0.002
                if self.DO > 0:
                    if eft > datetime.timedelta(hours=50):
                        self.DO -= 0.1
                    elif eft > datetime.timedelta(hours=45):
                        self.DO -= 0.2
                    elif eft > datetime.timedelta(hours=25):
                        self.DO -= 0.25
                    else:
                        self.DO -= 0.5
                self.feed_pump = 40
                self.feeding = True
                self.spiking = False
            else:
                self.feed_pump = 0

        elif self.feed_deviation == 'on':
            self.feed_pump = 45
            if self.DO > 0:
                self.DO -= 0.3
            if self.pH > 3:
                self.pH -= 0.002

        elif self.feed_deviation == 'off':
            self.feed_pump = 0

    def base_controller(self):
        """
        Controls the base pump including operating under normal conditions or if a deviation causes the base pump to
        turn on or off. I want to display how the acidic feed affects the pH so base is not added during a feed
        deviation. In a real situation if the pH reaches below the set point base would be added to  try and maintain
        the set point.
        :return: None
        """
        # disabled base pump if a feed deviation is causing pH to drop to the base trigger in order to demonstrate
        # the isolated effects of a feed pump
        if self.base_deviation is None and not self.feed_deviation == 'on':
            if 0 < self.pH < 7.20:
                self.feeding = False
                self.pH += 0.001
                self.base_pump = 35
            else:
                self.base_pump = 0

        elif self.base_deviation == 'on':
            self.base_pump = 40
            if self.pH < 14:
                self.pH += 0.005

        elif self.base_deviation == 'off':
            self.base_pump = 0

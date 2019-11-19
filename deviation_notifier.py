import pandas as pd
import datetime
import os
import smtplib
from twilio.rest import Client

notified = {}
rpm = 1000


def read_csv():
    """
    Reads the contents of the reactor's csv file.

    :return: a pandas dataframe of the reactor's csv
    """
    dtype = {'Timestamp': 'str', 'Agitation [rpm]': 'float', 'Airflow [mL/s]': 'float', 'DO [%]': 'float',
             'Temp [C]': 'float', 'pH': 'float', 'Feed Pump [ml/hr]': 'float', 'Base Pump [mL/hr]': 'float',
             'Antifoam Pump [mL/hr]': 'float'}
    data = pd.read_csv('dg1.csv', dtype=dtype, parse_dates=['Timestamp'], low_memory=False, na_filter=False)

    return data


def check_constants(data, setpoint, tolerance):
    """
    Checks if all constant parameters (temp, airflow, and agitation) are within their tolerance range and if not,
    determines where the deviation first occurred.

    :param data: the recorded values of a parameter (temp, airflow, or agitation)
    :type data: a Pandas Series
    :param setpoint: the target value a parameter should be held
    :type setpoint: float
    :param tolerance: a numerical amount the parameter is allowed to deviate from the setpoint before it is accepted to
    be out of the operating range in order to accommodate equipment noise
    :type tolerance: float
    :return: Index where current deviation began occurring, otherwise None
    """
    if abs(setpoint - data.iat[-1]) > tolerance:
        for idx in reversed(data.index):
            if abs(setpoint - data.iat[idx]) > tolerance:
                continue
            else:
                return idx + 1
    else:
        return None


def check_pumps(pump, data, setpoint, tolerance):
    """
    Checks for one out of three different possible pump deviations each time this function is called. These deviations
    include how long a pump has been off, how long a pump has been on, and whether or not the pump flow rate is within
    the tolerance of the setpoint. The last recorded data value will always fall into one of these categories and is
    traced back to the index where sequence first began.

    :param pump: The header of a pump as it is written in the reactor's csv file
    :type pump: str
    :param data: the recorded values of a pump
    :type data: a Pandas Series
    :param setpoint: the target value a parameter should be held
    :type setpoint: float
    :param tolerance: a numerical amount the parameter is allowed to deviate from the setpoint before it is accepted to
    be out of the operating range in order to accommodate equipment noise
    :type tolerance: float
    :return: index of the Pandas Series where the current sequence began and the number of minutes the current sequence
    is allowed to persist
    :rtype: tuple containing two ints
    """
    global rpm
    pump_specs = {'Base Pump [mL/hr]': {'on': 5, 'off': 310}, 'Feed Pump [ml/hr]': {'on': 50, 'off': 310},
                  'Antifoam Pump [mL/hr]': {'on': 20, 'off': 180}}

    if data.iat[-1] == 0:  # checks how long a pump has been inactive
        for idx in reversed(data.index):
            if data.iat[idx] == 0:
                if idx == 0:
                    return idx, 660
                continue
            else:
                if rpm == 1000:
                    return idx + 1, 660
                elif rpm == 1500:
                    return idx + 1, pump_specs[pump]['off']

    else:
        if abs(setpoint - data.iat[-1]) > tolerance:  # checks how long a pump has been out of the tolerance range
            for idx in reversed(data.index):
                if abs(setpoint - data.iat[idx]) > tolerance and data.iat[idx] != 0:
                    if idx == 0:
                        return idx, 5
                    continue
                else:
                    return idx + 1, 5

        else:  # check how long a pump has been running
            for idx in reversed(data.index):
                if data.iat[idx] != 0:
                    if idx == 0:
                        return idx, pump_specs[pump]['on']
                    continue
                else:
                    return idx + 1, pump_specs[pump]['on']


def agitation(data):
    """
    Checks the reactor's csv file to see if the agitation ramped up to 1500. Under normal operating conditions, the rpm
    would jump from 1000 to 1500 when the feed is first triggered. This function cannot mistake any agitation deviations
    for an rpm ramp and should not be called once it has already detected an rpm ramp. Since the setpoint of an
    agitation ramp increases instantly, this function must be called every time a new row of data is logged to the
    reactor's csv file or else this function will miss the agitation jump.

    :param data: the recorded values of the motor
    :type data: a Pandas Series
    :return: True if an agitation jump is detected, False otherwise
    """
    if abs(data.iat[-1] - 1500) < 10:
        if abs(data.iat[-2] - data.iat[-1]) > 50:
            return True
    return False


def check_pH(data, max_ph, min_ph=7.195):
    """
    Checks the pH of the reactor and makes sure its within the allowed range of the pH (pH will rise during a
    starvation).

    :param data: the recorded values of the reactor's pH
    :type data: a Pandas Series
    :param max_ph: the highest pH value allowed in order to accommodate feed spikes
    :type max_ph: float
    :param min_ph: the lowest pH value allowed, which should never fall far from the set point of 7.20
    :type min_ph: float
    :return: Index of the Pandas Series where the deviation first began, otherwise if no deviation is found, None
    """
    if data.iat[-1] < min_ph:
        for idx in reversed(data.index):
            if data.iat[idx] < min_ph:
                continue
            else:
                return idx + 1
    elif data.iat[-1] > max_ph:
        for idx in reversed(data.index):
            if data.iat[idx] > max_ph:
                continue
            else:
                return idx + 1
    else:
        return None


def check_time(timestamps, index, minutes=5):
    """
    This function is used to check the length of time a parameter has been running at its current conditions and whether
    or not it has exceeded the amount of time it is allowed to run at these conditions. In the case of pH, temperature,
    airflow, and agitation, this function is only called when a known deviation from the set point is occurring. In the
    case of pumps, this will check the amount of time a pump has been at it's current operating conditions (on, off, or
    out of tolerance) and determine if it exceeds the amount of time it should be running at this condition. The default
    maximum amount of time to tolerate a deviation is 5 minutes for all parameters other than pumps. Pumps have 
    different runtime tolerances depending on the type of pump and the current operating state it is in so the minutes 
    argument should always be given when used for a pump.

    :param timestamps: The reactor's recorded datetime.datetime objects in the format of '%Y-%m-%d %H:%M:%S.%f'
    :type timestamps:  a Panda Series
    :param index: the index where the deviation was first found
    :type index: int
    :param minutes: number of minutes a parameter is allowed to run in it's current operating state.
    :type minutes: int
    :return: True if the length of a deviation has exceeded the tolerance length, otherwise, False
    """

    tolerance = datetime.timedelta(minutes=minutes)
    length = timestamps.iat[-1] - timestamps.iat[index]
    if length > tolerance:
        return True
    else:
        return False


def email_alert(param, time):
    """
    Alerts the fermentation associate of the deviating parameter along with the start time of the deviation by email.
    :param param: the failing parameter written as it appears in the reactor's csv file
    :type param: str
    :param time: start time of the deviation
    :type time: datetime.datetime object in the format of '%Y-%m-%d %H:%M:%S.%f'
    :return: None
    """
    associate_email = 'biosimulator@gmail.com'
    # login to SMTP server
    smtp_obj = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_obj.ehlo()
    smtp_obj.starttls()
    smtp_obj.login(associate_email, os.environ.get('EMAIL_PASS'))
    msg = f'Deviation with {param} at {time}'
    smtp_obj.sendmail(associate_email, associate_email, 'Subject: Deviation Notifier\n\n' + msg)


def text_alert(param, time):
    """
    Alerts the fermentation associate of the deviating parameter along with the start time of the deviation by text.
    Currently unused because the Twilio account is only on a trial version.
    :param param: the failing parameter
    :type param: str
    :param time: start time of the deviation
    :type time: datetime.datetime object in the format of '%Y-%m-%d %H:%M:%S.%f'
    :return: None
    """
    associate_phone = os.environ.get('PHONE')
    client = Client(os.environ.get('TWILIO_SID'), os.environ.get('TWILIO_TOKEN'))
    message = client.messages.create(
        to=associate_phone,
        from_="+14154814546",  # Twilio phone number is expired
        body=f'Deviation with {param} at {time} ')


def check_deviations():
    """
    This is the main function of this module and it splits the Pandas Dataframe into its individual Series and sends
    each Pandas Series and any necessary arguments to the corresponding helper function. If it is determined necessary
    to notify the fermentation associate, this calls email_alert and text_alert to do so.

    :return: None
    """
    global rpm, notified
    # the setpoints of each parameter at index 0 along with the tolerated amount it is allowed to deviate
    setpoints = {'Agitation [rpm]': (rpm, 10), 'Airflow [mL/s]': (60, 3), 'Temp [C]': (32, 2),
                 'pH': (7.20, 0.2), 'Feed Pump [ml/hr]': (40, 3), 'Base Pump [mL/hr]': (35, 3),
                 'Antifoam Pump [mL/hr]': (1, 0.5)}
    data = read_csv()

    for label, content in data.iteritems():
        notify = None
        if label in setpoints.keys():
            deviation_idx = None
            setpoint, tolerance = setpoints[label]

            if rpm == 1000 and agitation(content):
                rpm = 1500

            # check temp, airflow and agitation
            if 'temp' in label.lower() or 'airflow' in label.lower() or 'agitation' in label.lower():
                deviation_idx = check_constants(content, setpoint, tolerance)

            # check pH
            elif 'ph' in label.lower():
                if rpm == 1500:
                    deviation_idx = check_pH(content, max_ph=7.22)
                else:
                    deviation_idx = check_pH(content, max_ph=7.27)

            if deviation_idx is not None or 'pump' in label.lower():
                # pumps must call check_time function every time new data is logged because there are 3 ways a pump can
                # deviate that have different time dependencies

                if 'pump' in label.lower():
                    # print(f'{label}   {check_pumps(label, content, setpoint, tolerance)}')
                    deviation_idx, time_allowance = check_pumps(label, content, setpoint, tolerance)
                    notify = check_time(data["Timestamp"], deviation_idx, minutes=time_allowance)
                else:
                    notify = check_time(data["Timestamp"], deviation_idx)

                if notify and label not in notified.keys():
                    notified[label] = 0
                    # email_alert(label, data["Timestamp"][deviation_idx])  # uncomment to send email alerts
                    # text_alert(label, data["Timestamp"][deviation_idx])  # uncomment to send text alerts
                    print(f'{label} deviation at {data["Timestamp"][deviation_idx]}')

            if label in notified.keys() and not notify:
                notified[label] += 1
                # if deviation doesn't occur again in the next 120 data logs (120 mins) it is counted as fixed
                # NOTE: does not have to be a consecutive 120 logs
                if notified[label] > 120:
                    del notified[label]


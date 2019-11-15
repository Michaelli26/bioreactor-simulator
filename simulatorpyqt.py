import pyqtgraph as pg
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import pandas as pd
import numpy as np
import sys
from functools import partial
from bioreactor import Reactor
from deviation_notifier import check_deviations


class CustomPlot(pg.PlotWidget):
    """
    A class that extends the PlotWidget to record what reactor trend is being plotted.
    """

    def __init__(self, param, *args, **kwargs):
        super(CustomPlot, self).__init__(*args, **kwargs)
        self.current_param = param


class BioreactorSimulator(QMainWindow):
    """
    Creates the GUI of reactor object and displays two parameters of a reactor in real-time as plots. The plots can be
    switched by clicking buttons of a different trend which will alternate between switching the top and bottom plot
    with the corresponding parameter of the clicked button. This GUI can also introduce mechanical deviations to the
    reactor upon user input via button clicks.
    """
    def __init__(self, *args, **kwargs):
        super(BioreactorSimulator, self).__init__(*args, **kwargs)

        self.change_top_graph = True
        self.setWindowTitle('Bioreactor Simulator')
        layout = QGridLayout()
        self.top_plot = CustomPlot(param='DO', labels={'left': 'DO', 'bottom': 'EFT'})
        self.bottom_plot = CustomPlot(param='pH', labels={'left': 'pH', 'bottom': 'EFT'})

        layout.addWidget(self.top_plot, 1, 0, 5, 12)
        layout.addWidget(self.bottom_plot, 6, 0, 5, 12)

        # add buttons for other graphs
        for col, parameter in enumerate(('Agitation', 'Airflow', 'DO', 'Temp', 'pH', 'Feed', 'Base', 'Antifoam')):
            btn = QPushButton(parameter)
            btn.clicked.connect(partial(self.trend_click, btn))
            layout.addWidget(btn, 12, col + 2)

        # add buttons for deviations
        self.all_deviation_btns = []
        for row, parameter in enumerate(('Feed On', 'Feed Off', 'Base On', 'Base Off', 'Agitation Up',
                                         'Agitation Down', 'Antifoam On', 'Antifoam Off', 'Airflow Up',
                                         'Airflow Down', 'Temp Up', 'Temp Down')):
            deviation_btn = QPushButton(parameter)
            deviation_btn.clicked.connect(partial(self.deviation_click, deviation_btn))
            self.all_deviation_btns.append(deviation_btn)
            layout.addWidget(deviation_btn, 0, row)

        # manage the main widget
        main = QWidget()
        main.setLayout(layout)
        self.setCentralWidget(main)
        self.show()

        # create a reactor object
        self.reactor = Reactor(name='dg1')
        self.reactor.start_run()
        self.reactor.create_csv()
        self.headers = ('Agitation [rpm]', 'Airflow [mL/s]', 'DO [%]', 'Temp [C]', 'pH', 'Feed Pgior.pyump [ml/hr]',
                        'Base Pump [mL/hr]', 'Antifoam Pump [mL/hr]')

        # create reoccurring event to log new data in the csv
        self.timer = QTimer()
        self.timer.timeout.connect(self.reactor.log_data)
        self.timer.timeout.connect(check_deviations)
        self.timer.start(20)  # change int to desired speed

        # create reoccurring event to update graph
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.update_graph)
        self.graph_timer.start(100)  # change int to desired speed

    def trend_click(self, instance):
        """
        On-click event for trend button instances which alternates between switching the top and bottom graph to
        the corresponding trend button that was clicked.
        :param instance: a QPushButton object
        :return: None
        """
        if self.change_top_graph:
            self.top_plot.current_param = instance.text()
            self.change_top_graph = False
            for header in self.headers:
                if self.top_plot.current_param in header:
                    self.top_plot.setLabel(axis='left', text=header)
        else:
            self.bottom_plot.current_param = instance.text()
            self.change_top_graph = True
            for header in self.headers:
                if self.bottom_plot.current_param in header:
                    self.bottom_plot.setLabel(axis='left', text=header)

    def deviation_click(self, instance):
        """
        Sets a reactor's parameter to the corresponding button deviation the first time the button is clicked.
        The second time the button is clicked, the deviation is removed/fixed.
        Only one deviation is allowed to occur within any given time because simulating the effects of many deviations
        occurring simultaneously would be very difficult and unlikely to occur in an actual reactor.
        :param instance: a QPushButton object
        :return: None
        """
        parameter, deviation = instance.text().lower().split()

        for button in self.all_deviation_btns:
            if not button.isEnabled():  # a deviation is already occurring so turn it off

                if parameter == 'antifoam':
                    self.reactor.antifoam_deviation = None
                elif parameter == 'agitation':
                    self.reactor.agitation_deviation = None
                elif parameter == 'feed':
                    self.reactor.feed_deviation = None
                elif parameter == 'base':
                    self.reactor.base_deviation = None
                elif parameter == 'airflow':
                    self.reactor.airflow_deviation = None
                elif parameter == 'temp':
                    self.reactor.temp_deviation = None

                for btn in self.all_deviation_btns:
                    if instance is not button:
                        btn.setEnabled(True)
                break

        else:  # start a new deviation and disable all other deviations so multiple are not occurring at the same time
            for btn in self.all_deviation_btns:
                if instance is not btn:
                    btn.setEnabled(False)

            if parameter == 'antifoam':
                self.reactor.antifoam_deviation = deviation
            elif parameter == 'agitation':
                self.reactor.agitation_deviation = deviation
            elif parameter == 'feed':
                self.reactor.feed_deviation = deviation
            elif parameter == 'base':
                self.reactor.base_deviation = deviation
            elif parameter == 'airflow':
                self.reactor.airflow_deviation = deviation
            elif parameter == 'temp':
                self.reactor.temp_deviation = deviation

    def update_graph(self):
        """
        Uses the Pandas library to read the reactor's CSV file and updates both the top and bottom graph of the main
        widget.
        :return:None
        """
        parameters = []
        dtype = {'Timestamp': 'str'}
        for header in self.headers:
            if self.top_plot.current_param in header or self.bottom_plot.current_param in header:
                parameters.append(header)
                dtype[header] = 'float'
        data = pd.read_csv(self.reactor.file,
                           dtype=dtype,
                           parse_dates=['Timestamp'], usecols=['Timestamp'] + parameters, low_memory=False,
                           na_filter=False)
        start_time = data['Timestamp'][0]
        data.insert(loc=2, column='EFT', value=(data['Timestamp'] - start_time) / np.timedelta64(1, 'h'))

        for label, content in data.iteritems():
            if label == 'Timestamp' or label == 'EFT':
                continue
            elif self.top_plot.current_param in label:
                self.top_plot.clear()
                self.top_plot.plot(data['EFT'], content)
            else:
                self.bottom_plot.clear()
                self.bottom_plot.plot(data['EFT'], content)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BioreactorSimulator()
    sys.exit(app.exec_())

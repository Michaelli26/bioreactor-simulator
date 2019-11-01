import kivy
kivy.require('1.11.1')
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy_garden.graph import Graph, MeshLinePlot
from bioreactor import Reactor
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
#import matplotlib
#matplotlib.use('module://kivy.garden.matplotlib.backend_kivy')
import time





class SimulatorApp(App):
    reactor = Reactor(name='dg1')
    reactor.start_run()
    reactor.create_csv()

    # TODO change hardcoded image source
    '''
    im1 = Image(source='dg1-pH.png', allow_stretch=True, keep_ratio=False)
    im2 = Image(source='dg1-DO.png', allow_stretch=True, keep_ratio=False)
    # Clock.schedule_interval(im1.reload, 1)
    # Clock.schedule_interval(im2.reload, 1)
    '''
    top_image = True

    # fig1, ax1 = reactor.graph('pH')
    # fig2, ax2 = reactor.graph('DO')
    fig1, ax1 = plt.subplots(2)
    ax1[0].set_ylabel('DO')
    ax1[1].set_ylabel('pH')
    ax1[0].set_xlim(left=0, right=70)
    ax1[1].set_xlim(left=0, right=70)
    canvas1 = fig1.canvas
    #canvas2 = fig2.canvas
    # im2 = reactor.graph('DO')

    def build(self):
        main = BoxLayout(orientation='vertical')

        main.add_widget(FigureCanvasKivyAgg(self.fig1))
        # main.add_widget(self.canvas1)
        # main.add_widget(self.canvas2)


        # create graph buttons
        buttons = BoxLayout(size_hint=(1, None))
        for parameter in ('Agitation', 'Airflow', 'DO', 'Temp', 'pH', 'Feed', 'Base', 'Antifoam'):
            btn = Button(text=parameter, font_size=24, size_hint=(1, None), height=70)
            # btn.bind(on_press=self.change_image)
            buttons.add_widget(btn)
        main.add_widget(buttons)

        Clock.schedule_interval(self.update_csv, 1/100)

        Clock.schedule_interval(self.update_png, 2)

        '''
        Clock.schedule_interval(self.update_image, 2)
        '''
        return main

    def update_csv(self, dt):
        self.reactor.log_data()

    def update_png(self, dt):
        t0 = time.time()
        headers = ('Agitation [rpm]', 'Airflow [mL/s]', 'DO [%]', 'Temp [C]', 'pH', 'Feed pump [ml/hr]',
                   'Base Pump [mL/hr]', 'Antifoam Pump [mL/hr]')
        parameters = []
        dtype = {'Timestamp': 'str'}
        for header in headers:
            if self.ax1[0].get_ylabel() in header or self.ax1[1].get_ylabel() in header:
                parameters.append(header)
                dtype['header'] = 'float'

        data = pd.read_csv(self.reactor.file,
                           dtype=dtype,
                           parse_dates=['Timestamp'], usecols=['Timestamp']+parameters, low_memory=False,
                           na_filter=False)
        start_time = data['Timestamp'][0]
        data.insert(loc=2, column='EFT', value=(data['Timestamp'] - start_time) / np.timedelta64(1, 'h'))
        t1 = time.time()
        print(f'read pandas {t1-t0}')
        for label, content in data.iteritems():
            if label == 'Timestamp' or label == 'EFT':
                continue
            else:
                if self.ax1[0].get_ylabel() in label:
                    print('ax 0 in label')
                    i = 0

                else:
                    print('ax 1 in label')
                    i = 1

                background = self.canvas1.copy_from_bbox(self.ax1[i].bbox)
                self.canvas1.restore_region(background)
                line, = self.ax1[i].plot(data['EFT'], content)
                line.set_ydata(content)
                self.ax1[i].draw_artist(line)
                self.fig1.canvas.blit(self.ax1[i].bbox)


                '''
                line, = self.ax1[i].plot(data['EFT'], content)
                line.set_ydata(content)
                self.ax1[i].draw_artist(self.ax1[i].patch)
                self.ax1[i].draw_artist(line)
                # self.canvas1.update()
                self.canvas1.draw_idle()
                self.canvas1.flush_events()
                '''
                '''
                self.ax1[i].clear()
                self.ax1[i].plot(data['EFT'], content)
                #plt.xlabel('EFT')
                #plt.ylabel(label)

                self.ax1[i].set_xlabel('EFT [hrs]', fontsize=20)
                self.ax1[i].set_ylabel(label, fontsize=20)
                self.ax1[i].tick_params(labelsize=12)
                self.ax1[i].set_xlim(left=0, right=70)

                self.canvas1.draw_idle()
                #self.canvas1.blit(self.ax1[i].bbox)
                '''

        t2 = time.time()
        print(f'matplotlib graph {t2-t1}')
        print(f'total time {t2-t0}')

'''
    def update_image(self, dt):
        self.im1.reload()
        self.im2.reload()

    def change_image(self, instance):
            if self.top_image:
            i = 0
            self.top_image = False
            
                                    self.ax1[i].clear()
                        self.ax1[i].set_xlabel('EFT [hrs]', fontsize=20)
                        self.ax1[i].set_ylabel(label, fontsize=20)
                        self.ax1[i].tick_params(labelsize=12)
                        self.ax1[i].set_xlim(left=0, right=70)
        else:
            i = 1
            self.top_image = True
        self.reactor.graph(instance.text)
        if self.top_image:
            self.im1.source = f'{self.reactor.name}-{instance.text}.png'
            self.top_image = False
        else:
            self.im2.source = f'{self.reactor.name}-{instance.text}.png'
            self.top_image = True
'''

if __name__ == '__main__':
    SimulatorApp().run()


# event = Clock.schedule_interval(my_callback, 1 / 30.)

'''
im = Image(source = '1.jpg')
# -- do something --
im.reload()
# image will be re-loaded from disk

im.source

canvas.clear() to remove old images? not be unnecessary if you can just change the source
'''
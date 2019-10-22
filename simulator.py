import kivy
kivy.require('1.11.1')
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.clock import Clock
import re
from bioreactor import Reactor


class Graphs(BoxLayout):

    def __init__(self, **kwargs):
        super(Graphs, self).__init__(**kwargs)
        for parameter in ('Agitation', 'Airflow', 'DO', 'Temp', 'pH', 'Feed', 'Base', 'Antifoam'):
            btn = Button(text=parameter, font_size=24, size_hint=(1, None), height=70)
            btn.bind(on_press=self.change)
            self.add_widget(btn)

    def change(self, instance):
        print('dg1-' + instance.text + '.png')
        # image.source = 'dg1-' + instance.text + '.png'

'''
class ImageWidget(BoxLayout):
    def __init__(self, **kwargs):
        super(ImageWidget, self).__init__(**kwargs)
        im = Image(source='dg1-pH.png')
        im2 = Image(source='dg1-DO.png')
        self.add_widget(im)
        self.add_widget((im2))
        '''



class SimulatorApp(App):
    reactor = Reactor(name='dg1')
    reactor.start_run()
    reactor.create_csv()
    print(reactor.name)



    # TODO change hardcoded image source
    im1 = Image(source='dg1-pH.png', allow_stretch=True, keep_ratio=False)
    im2 = Image(source='dg1-DO.png', allow_stretch=True, keep_ratio=False)
    # Clock.schedule_interval(im1.reload, 1)
    # Clock.schedule_interval(im2.reload, 1)
    top_image = True

    def build(self):
        main = BoxLayout(orientation='vertical')
        # images = ImageWidget(orientation='vertical')
        # main.add_widget(images)
        main.add_widget(self.im1)
        main.add_widget(self.im2)
        # create graph buttons
        buttons = BoxLayout(size_hint=(1, None))
        for parameter in ('Agitation', 'Airflow', 'DO', 'Temp', 'pH', 'Feed', 'Base', 'Antifoam'):
            btn = Button(text=parameter, font_size=24, size_hint=(1, None), height=70)
            btn.bind(on_press=self.change_image)
            buttons.add_widget(btn)
        main.add_widget(buttons)
        # main.add_widget(Graphs(size_hint=(1, None)))

        Clock.schedule_interval(self.update_csv, 1/100)
        Clock.schedule_interval(self.update_png, 2)
        Clock.schedule_interval(self.update_image, 2)
        return main

    def update_csv(self, dt):
        self.reactor.log_data()

    def update_png(self, dt):
        for parameter in ('Agitation', 'Airflow', 'DO', 'Temp', 'pH', 'Feed', 'Base', 'Antifoam'):
            if parameter in self.im1.source or parameter in self.im2.source:
                self.reactor.graph(parameter=parameter)

    def update_image(self, dt):
        self.im1.reload()
        self.im2.reload()

    def change_image(self, instance):
        self.reactor.graph(instance.text)
        if self.top_image:
            self.im1.source = f'{self.reactor.name}-{instance.text}.png'
            self.top_image = False
        else:
            self.im2.source = f'{self.reactor.name}-{instance.text}.png'
            self.top_image = True


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
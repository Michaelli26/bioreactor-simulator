import kivy
import random

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

red = [1,0,0,1]
green = [0,1,0,1]
blue =  [0,0,1,1]
purple = [1,0,1,1]

########################################################################
class NestedLayoutExample(App):
    """
    An example of nesting three horizontally oriented BoxLayouts inside
    of one vertically oriented BoxLayout
    """

    #----------------------------------------------------------------------
    def build(self):
        """
        Horizontal BoxLayout example
        """
        main_layout = BoxLayout(padding=10, orientation="vertical")

        colors = [red, green, blue, purple]

        for i in range(3):
            h_layout = BoxLayout(padding=10)
            for i in range(5):
                btn = Button(text="Button #%s" % (i+1),
                             background_color=random.choice(colors)
                             )

                h_layout.add_widget(btn)
            main_layout.add_widget(h_layout)

        return main_layout

#----------------------------------------------------------------------
if __name__ == "__main__":
    app = NestedLayoutExample()
    app.run()
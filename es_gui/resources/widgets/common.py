import json
import collections
import os
import copy
from functools import partial
from random import choice
import textwrap

import matplotlib as mpl
import matplotlib.pyplot as plt
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
from kivy.app import App
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.modalview import ModalView
from kivy.uix.button import Button
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.popup import Popup
from kivy.uix.spinner import SpinnerOption, Spinner
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.togglebutton import ToggleButton

cwd = os.getcwd()

# Animation durations in seconds #
BASE_TRANSITION_DUR = 0.600
BUTTON_FLASH_DUR = 0.100
ANIM_STAGGER = 0.200
FADEIN_DUR = 1.000
SLIDER_DUR = 1.200
LOADING_DUR = 1.000

# Widget sizes #
TWO_ABC_WIDTH = 800
THREE_ABC_WIDTH = 1200

# Software name and information #
APP_NAME = 'QuESt'
APP_TAGLINE = 'Optimizing Energy Storage'

# Palette #
PALETTE = [(0, 83, 118), (132, 189, 0),
     (0, 173, 208), (255, 163, 0), (255, 88, 93), (174, 37, 115)]

def rgba_to_fraction(rgba):
    """Converts rgb values in int format to fractional values suitable for Kivy."""
    if len(rgba) > 3:
        return float(rgba[0])/255, float(rgba[1])/255, float(rgba[2])/255, rgba[3]
    else:
        return float(rgba[0])/255, float(rgba[1])/255, float(rgba[2])/255, 1

def fade_in_animation(content, *args):
    """Fade in animation (on opacity); to be used with Clock scheduler."""
    anim = Animation(transition='out_expo', duration=FADEIN_DUR, opacity=1)
    anim.start(content)


class LeftAlignedText(Label):
    """Label subclass for left-aligned text labels."""
    pass


class BodyTextBase(LeftAlignedText):
    """Base class for body text labels."""
    pass


class TitleTextBase(LeftAlignedText):
    """Base class for title text labels."""
    pass


class TileButton(Button):
    """Button subclass for the tile buttons used throughout the application."""
    pass


class MenuTileButton(TileButton):
    """Large tile button used for main menus."""
    pass


class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    """The BoxLayout for displaying RecycleView. Adds selection and focus behavior to the RecycleView."""
    pass


class RecycleViewRow(RecycleDataViewBehavior, BoxLayout):
    """The representation for data entries in the RecycleView. A selectable Label with the name of the saved run."""
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    # run_selector = None

    def refresh_view_attrs(self, rv, index, data):
        """
        Catch and handle the view changes.
        """
        self.index = index
        return super(RecycleViewRow, self).refresh_view_attrs(
            rv, index, data)

    def on_enter(self):
        """Update the description boxes when hovered over."""
        pass
        # run_obj = self.run_selector.rv.data[self.index]
        # run_desc_box = self.run_selector.rv_desc
        #
        # # Update the preview text based on the hovered upon object.
        # run_desc_box.text = '\n'.join(
        #     ['[b]{0}[/b]'.format(run_obj['name']),
        #      '[b]Date: [/b] ' + run_obj['time'],
        #      '[b]ISO:[/b] ' + run_obj['iso'],
        #      '[b]Market Type:[/b] ' + run_obj['market type'],
        #      '[b]Year:[/b] ' + run_obj['year'],
        #      '[b]Month:[/b] ' + run_obj['month'],
        #      '[b]Node:[/b] ' + run_obj['node'],
        #      '[b]Parameters set:[/b] ' + repr(run_obj.get('params', 'Used defaults.')),
        #      ]
        # )

    def on_leave(self):
        """
        Update the description boxes when not hovering over an entry.
        """
        pass
        # run_desc_box = self.run_selector.rv_desc
        #
        # # update the text
        # run_desc_box.text = 'Hover over a saved run to view its details.'

    def on_touch_down(self, touch):
        """
        Add selection on touch down.
        """
        if super(RecycleViewRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """
        Respond to the selection of items in the view.
        """
        self.selected = is_selected


class MyRecycleView(RecycleView):
    def __init__(self, **kwargs):
        super(MyRecycleView, self).__init__(**kwargs)

        self.unfiltered_data = self.data

    def filter_rv_data(self, filter_text):
        self.deselect_all_nodes()
                
        if filter_text:
            self.data = [rv_entry for rv_entry in self.unfiltered_data if filter_text.lower() in rv_entry['name'].lower()]
        else:
            self.data = self.unfiltered_data
    
    def deselect_all_nodes(self):
        while len(self.layout_manager.selected_nodes) > 0:
            for selected_node in self.layout_manager.selected_nodes:
                self.layout_manager.deselect_node(selected_node)


class MyPopup(Popup):
    pass


class WarningPopup(MyPopup):
    def __init__(self, **kwargs):
        super(WarningPopup, self).__init__(**kwargs)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self, 'text')

        if self._keyboard.widget:
            pass

        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in ('enter', 'numpadenter'):
            self.dismiss()

        return True


class ValuationRunCompletePopup(MyPopup):
    pass


class PlotSpinner(Spinner, TileButton):
    pass


class PlotSpinnerOptionCls(SpinnerOption):
    pass


class InputError(Exception):
    pass


class LoadingModalView(ModalView):
    pass
    # def on_open(self):
    #     loading_animation = Animation(transition='linear', duration=LOADING_DUR, opacity=0) + Animation(transition='linear', duration=LOADING_DUR, opacity=1)

    #     for x in range(5):
    #         loading_animation += Animation(transition='linear', duration=LOADING_DUR, opacity=0) + Animation(transition='linear', duration=LOADING_DUR, opacity=1)
    #     # loading_animation.repeat = True

    #     Clock.schedule_once(lambda dt: loading_animation.start(self.logo), 0)


class ReportScreen(Screen):
    pass


class WizardCompletePopup(MyPopup):
    pass


class WizardReportInterface(Screen):
    def on_enter(self):
        def _start(*args):
            self.chart_type_toggle.children[-1].state = 'down'

            # random_report = choice(self.chart_type_toggle.children)
            # random_report.state = 'down'

        if not any([button.state == 'down' for button in self.chart_type_toggle.children]):
            Clock.schedule_once(lambda dt: _start(), 0.25)


class ReportChartToggle(ToggleButton, TileButton):
    pass


class ParameterRow(GridLayout):
    """Grid layout containing parameter name, description, text input, and units."""
    def __init__(self, desc, **kwargs):
        super(ParameterRow, self).__init__(**kwargs)

        self._desc = desc

        self.name.text = self.desc.get('name', '')
        self.notes.text = self.desc.get('notes', '')
        self.text_input.hint_text = str(self.desc.get('default', ''))
        self.units.text = self.desc.get('units', '')

    @property
    def desc(self):
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = value


class ParamTextInput(TextInput):
    """A TextInput field for entering parameter values. Limited to float values."""
    def insert_text(self, substring, from_undo=False):
        # limit to 8 chars
        substring = substring[:8 - len(self.text)]
        return super(ParamTextInput, self).insert_text(substring, from_undo=from_undo)


class ParameterGridWidget(GridLayout):
    """Grid layout containing rows of parameter adjustment widgets."""   
    def _validate_inputs(self):
        params = []
        param_set = {}

        for row in self.children:
            attr_name = row.desc['attr name']

            if not row.text_input.text:
                attr_val = row.text_input.hint_text
            else:
                attr_val = row.text_input.text
            
            param_set[attr_name] = float(attr_val)
        
        params.append(param_set)

        return params
    
    def get_inputs(self):
        try:
            params = self._validate_inputs()
        except InputError as e:
            popup = WarningPopup()
            popup.popup_text.text = str(e)
            popup.open()
        else:
            return params
    
    def get_input_strings(self):
        params = []

        for row in self.children:
            param_name = row.desc['name']
            param_units = row.desc['units']
            
            if not row.text_input.text:
                param_val = row.text_input.hint_text
            else:
                param_val = row.text_input.text
            
            param_string = '{name}: {value} {units}'.format(name=param_name, value=param_val, units=param_units)
            params.append(param_string)
        
        return params


class DataGovAPIhelp(ModalView):
    """ModalView to display instructions on how to get a Data.gov (NREL Developer Network) API key."""


class ResultsViewer(Screen):
    """The screen for displaying plots inside the application or exporting results."""
    current_fig = ObjectProperty()
    current_ax = ObjectProperty()

    def __init__(self, **kwargs):
        super(ResultsViewer, self).__init__(**kwargs)

        self.dfs = {}

        self.time_selector.start_time.bind(on_text_validate=self.draw_figure)
        self.time_selector.end_time.bind(on_text_validate=self.draw_figure)

    def on_pre_enter(self):
        pass

    def on_leave(self):
        """Resets all selections and the graph."""
        self._reset_screen()

    # def _on_keyboard_down(self, instance, keyboard, keycode, text, modifiers):
    #     if keycode == 40:  # 40 - Enter key pressed
    #         self.draw_figure()

    def _select_all_runs(self):
        for selectable_node in self.rv.layout_manager.get_selectable_nodes():
            self.rv.layout_manager.select_node(selectable_node)

    def _deselect_all_runs(self):
        while len(self.rv.layout_manager.selected_nodes) > 0:
            for selected_node in self.rv.layout_manager.selected_nodes:
                self.rv.layout_manager.deselect_node(selected_node)

    def _reset_screen(self):
        #rv = self.run_selector.rv
        rv = self.rv

        self._deselect_all_runs()

        # Clears graph.
        while len(self.plotbox.children) > 0:
            for widget in self.plotbox.children:
                if isinstance(widget, FigureCanvasKivyAgg):
                    self.plotbox.remove_widget(widget)

        # Reset spinners.
        self.vars_button.text = 'Select data'

        # Reset text input fields.
        self.time_selector.start_time.text = '0'
        self.time_selector.end_time.text = '744'

    def _reinit_graph(self, has_legend=True):
        # Clears graph.
        while len(self.plotbox.children) > 0:
            for widget in self.plotbox.children:
                if isinstance(widget, FigureCanvasKivyAgg):
                    self.plotbox.remove_widget(widget)
        
        fig, ax = plt.subplots()
        self.current_fig = fig
        self.current_ax = ax

        ax.xaxis.label.set_size(16)
        ax.yaxis.label.set_size(16)
        plt.rcParams.update({'font.size': 18, 'xtick.labelsize': 12, 'ytick.labelsize': 12,
                             'lines.linewidth': 2})
        plt.rc('legend', **{'fontsize': 10})

        if has_legend:
            box = ax.get_position()
            ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])

        plotbox = self.plotbox
        canvas = FigureCanvasKivyAgg(self.current_fig)
        plotbox.add_widget(canvas, index=0)

    def _update_toolbar(self, *args):
        """Updates the data viewing toolbar based on selections."""
        # if not self.dfs:
        #     # if no selections made, disable all toolbar buttons and return
        #     self.vars_button.disabled = True
        #     self.time_button.disabled = True
        #     self.draw_button.disabled = True
        #     self.csv_export_button.disabled = True
        #     self.png_export_button.disabled = True
        #
        #     return

        self.vars_button.disabled = False
        #self.time_button.disabled = False
        self.draw_button.disabled = False
        self.csv_export_button.disabled = False
        self.png_export_button.disabled = False

    def _update_selection(self):
        """Updates the dict. of DataFrames whenever new selections of data are made."""

        # Identify the selected run(s) from RunSelector.
        #rv = self.run_selector.rv
        rv = self.rv
        runs_selected = [rv.data[selected_ix] for selected_ix in rv.layout_manager.selected_nodes]

        results = {}

        for run in runs_selected:
            label = run['name']
            df = run['optimizer'].results

            results[label] = df

        self.dfs = results

    def _validate_inputs(self):
        if not self.dfs:
            # No selections made.
            popup = WarningPopup()
            popup.popup_text.text = "We need data to plot! Let's pick some solved models to view first."
            popup.open()

            return False

        plot_type = self.vars_button.text

        if plot_type == 'Select data':
            # No data to plot has been selected.
            popup = WarningPopup()
            popup.popup_text.text = "We need something to plot! Let's select some data to view first."
            popup.open()

            return False

        if not self.time_selector.validate():
            return False

        return True

    def draw_figure(self, *args):
        pass

    def export_png(self, outdir_root):
        """Exports currently displayed figure to .png file in specified location."""
        os.makedirs(outdir_root, exist_ok=True)

        self._update_selection()

        if self.dfs:
            outname = os.path.join(outdir_root, self.vars_button.text+'.png')
            self.plotbox.children[0].export_to_png(outname)

            popup = WarningPopup(size_hint=(0.4, 0.4))
            popup.title = 'Success!'
            popup.popup_text.text = 'Figure successfully exported to:\n\n' + os.path.abspath(outname)
            popup.open()
        else:
            popup = WarningPopup()
            popup.popup_text.text = "We need a plot to export! Let's pick some solved models to view first."
            popup.open()

    def export_csv(self, outdir_root):
        """Exports selected DataFrames to .csv files in specified location."""
        os.makedirs(outdir_root, exist_ok=True)
        
        self._update_selection()

        if self.dfs:
            for run in self.dfs:
                # Split and regenerate run label to make it filename-friendly.
                run_label_split = run.split(' | ')
                run_name = ' '.join(run_label_split[:4])

                # Strip non-alphanumeric chars.
                delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
                run_name = run_name.translate({ord(i): None for i in delchars})

                outname = os.path.join(outdir_root, run_name + '.csv')
                df = self.dfs[run]
                os.makedirs(outdir_root, exist_ok=True)
                df.to_csv(outname, index=False)

            popup = WarningPopup(size_hint=(0.4, 0.4))
            popup.title = 'Success!'
            popup.popup_text.text = 'File(s) successfully exported to:\n\n' + os.path.abspath(outdir_root)
            popup.open()
        else:
            popup = WarningPopup()
            popup.popup_text.text = "We need some results to export! Let's pick some solved models to view first."
            popup.open()


class TimeSelector(MyPopup):
    """
    A Popup with TextInput fields for determining the range of time to display in the figure.
    """

    def __init__(self, **kwargs):
        super(TimeSelector, self).__init__(**kwargs)

    def _validate(self):
        """
        Validates the field entries before closing the TimeSelector.
        """
        try:
            start_time = int(self.start_time.text)
            end_time = int(self.end_time.text)
            assert(start_time < end_time)
        except ValueError:
            # empty text input
            popup = WarningPopup()
            popup.popup_text.text = 'All input fields must be populated to continue.'
            popup.open()
        except AssertionError:
            # start_time > end_time
            popup = WarningPopup()
            popup.popup_text.text = 'The start time cannot be greater than the end time.'
            popup.open()
        else:
            self.dismiss()

        # Note: We do not necessarily need to check for index errors because Series slicing does not throw exceptions


class TimeSelectorRow(GridLayout):
    def get_inputs(self):
        return int(self.start_time.text), int(self.end_time.text)

    def validate(self):
        """Validates the field entries before closing the TimeSelector."""
        try:
            start_time = int(self.start_time.text)
            end_time = int(self.end_time.text)
            assert(start_time < end_time)
        except ValueError:
            # empty text input
            popup = WarningPopup()
            popup.popup_text.text = 'All input fields must be populated to continue.'
            popup.open()

            return False
        except AssertionError:
            # start_time > end_time
            popup = WarningPopup()
            popup.popup_text.text = 'The start time cannot be greater than the end time.'
            popup.open()

            return False
        else:
            return True


class TimeTextInput(TextInput):
    """
    A TextInput field for entering time indices. Limited to three int characters only.
    """
    def insert_text(self, substring, from_undo=False):
        # limit to 3 chars
        substring = substring[:3 - len(self.text)]
        return super(TimeTextInput, self).insert_text(substring, from_undo=from_undo)
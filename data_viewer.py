from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.io import curdoc
from bokeh.events import Tap
from bokeh.models import HoverTool, TapTool, DatetimeTickFormatter, DateFormatter
from bokeh.tile_providers import get_provider, Vendors
from bokeh.transform import dodge
from scipy.spatial.distance import cdist
from bokeh.models.renderers import GlyphRenderer
from bokeh.models.widgets import DataTable, TableColumn, Slider, Dropdown, Div, Button
from bokeh.layouts import layout, column, row, widgetbox

import os
import pandas as pd
import numpy as np
import xarray as xr
import configparser
import copy



def merc(lat, lon):
    """Convert latitude and longitude into mercator's x and y position

    Parameters
    ----------
    lon : longitude
    lat : latitude

    """
    r_major = 6378137.000
    x = r_major * np.radians(lon)
    scale = x/lon
    y = 180.0/np.pi * np.log(np.tan(np.pi/4.0 +
        lat * (np.pi/180.0)/2.0)) * scale
    return (x, y)


def read_corr_file():
    """
    if corrected file is defined in config, this one is used to color up
    stations in mapplot
    """
    corr_path = config['dir']['corr_path']
    df_corr = pd.read_csv(corr_path, encoding='latin1', delimiter=';')
    # x and y coordinates
    [df_corr['x'], df_corr['y']] = merc(df_corr['Geografische_Länge'], df_corr['Geografische_Breite']) # interchanged because of wrong labeling in wiski
    #  set colors for points
    colors =  {np.nan: "red", 'j': "green"}
    df_corr["color"] = df_corr["corr"].apply(lambda c: colors[c])
    return df_corr


def find_station(df, x, y):
    """
    Find nearest Station for selected coordinates
    """
    coord = np.array([[x,y]])
    coords = np.rot90(np.array([df.x.values, df.y.values]))
    df['dist'] = np.rot90(cdist(coord,coords))
    df_tmp = df.loc[df['dist'].idxmin()]
    df = df.drop(columns='dist')
    df_res = df.loc[df['Stationsnummer']==df_tmp['Stationsnummer']]
    return df_res


def get_data_from_station(data_path, df_res):
    """
    Read data from corresponding netcdf file
    """
    file_path = []
    for filename in df_res['Filename']:
        parent_folder = df_res.loc[df_res['Filename']==filename, ['Parent-Folder']]
        file_path.append(os.path.join(data_path, parent_folder['Parent-Folder'].values[0], filename))
    data = xr.open_mfdataset(file_path, decode_times=True, combine='by_coords').load()
    dfs = data.to_dataframe()
    data.close()
    dfs = dfs.reset_index()
    dfs = dfs.drop(columns=['lat','lon','height'])
    dfs = dfs.set_index('index')
    return dfs

def get_summary(df_res, dfs):
    timespan = "Data from {} to {} ".format(dfs.index[0], dfs.index[-1])
    try:
        params = df_res.drop(columns=['Pegelnullpunkt_[]', 'Messpunkthöhe_[]','Geländeoberkante_[]', 'x', 'y'])
        station_data = params.to_html()
    except:
        station_data = df_res.to_html()
    stats = dfs.describe(include='all').to_html()
    summary = timespan + station_data + stats
    return summary


def get_outfile(df_res, parameter):
    df_out =  df_res.loc[df['Parametername'] == parameter]
    if armed:
        path_out = os.path.join(data_path, df_out['Parent-Folder'].iloc[0], df_out['Filename'].iloc[0])
    else:
        outfile_name = '_new_' + df_out['Filename'].iloc[0] # TODO make "armed" version in config
        path_out = os.path.join(data_path, df_out['Parent-Folder'].iloc[0], outfile_name)
    return path_out


def callback(event):
    """
    Callback function for Mapplot
    """
    global dfs
    global df_res
    Coords=(event.x,event.y)
    df_res = find_station(df, event.x, event.y)
    print(df_res['Stationsmessort'].values[0], ' / ', df_res['Stationsname'].values[0])
    stationsnummer = df_res['Stationsnummer'].iloc[0]
    dfs = get_data_from_station(data_path, df_res)
    summary.text = get_summary(df_res, dfs)
    par_dropdown.menu = list(dfs.columns)
    year_dropdown.menu = np.unique(dfs.index.strftime('%Y')).tolist()
    #dfs.loc[dfs['LT']==999.9] = np.nan # correction of failure values
    # change values in table
    try:
        source = ColumnDataSource.from_df(dfs.loc[str(year_dropdown.value)])
        data_table.source.data = source
    except KeyError:
        print('no data found, select correct year or parameter')


def year_dropdown_change(attr, old, new):
    # set displayed year to dropdown year
    print('Year set to: ', new)
    try:
        source = ColumnDataSource.from_df(dfs.loc[str(new)])
        data_table.source.data = source
        #p2.renderers[0].glyph.y = initial_parameter
        p2.x_range.start = source['index'].min()
        p2.x_range.end = source['index'].max()
        #p2.renderers[0].data_source.data = source
        #print(p2.renderers)

    except:
        print('year without data')


def par_dropdown_change(attr, old, new):
    global parameter
    print('Parameter set to: ', new)
    parameter = new
    # change table
    columns = [
       TableColumn(field="index", title="date", formatter=datefmt),#, editor=DateEditor),
       TableColumn(field=new, title=new),
    ]
    data_table.columns = columns
    source = ColumnDataSource.from_df(dfs.loc[str(year_dropdown.value)])
    data_table.source.data = source
    # change plot
    p2.renderers[0].glyph.y = parameter
    tooltips = [("Date", "@index{%Y-%m-%d %H:%M}"), ("Value", "@{}".format(parameter))]
    p2.tools[5].tooltips = tooltips


def button_click():
    """
    Save changes in DataTable to file
    """
    if parameter != initial_parameter and year_dropdown.value != None and not df_res.empty:
        path_out = get_outfile(df_res, parameter)
        # extracting values from table and setting them to dataframe
        new_vals = pd.Series(data_table.source.data[parameter], index=dfs[year_dropdown.value].index)
        dfs.loc[year_dropdown.value, parameter] = new_vals
        # open outfile
        data_out = xr.open_mfdataset(path_out, decode_times=True, combine='by_coords')
        data_out = data_out.drop(parameter) # drop old data
        data_out = data_out.drop('index') # drop old index
        # assign the new variables
        data_out = data_out.assign_coords({'index': dfs.index.values})
        new = dfs[parameter].values.reshape((1,1,1,dfs[parameter].values.shape[0]))
        dims = ['height', 'lon', 'lat', 'index']
        data_out = data_out.assign({parameter:(dims, new)})
        data_out.to_netcdf(path_out)
        print('Wrote changes to: ', path_out)
    else:
        print('No correct station, year or parameter selected')


### Parsing directories from config file

config = configparser.ConfigParser()
config.read('config.ini')
list_path = config['dir']['list_path']
data_path = config['dir']['data_path']
if config['settings']['armed'] == 'True':
    armed = True
else:
    armed = False

### Read Data

df = pd.read_csv(list_path, encoding='latin1', delimiter=';')
tile_provider = get_provider(Vendors.CARTODBPOSITRON)
[df['x'], df['y']] = merc(df['Geografische_Länge'], df['Geografische_Breite']) # interchanged because of wrong labeling in wiski

#### Some Parameters
edit_table = False # set parameter to false
year = 2012 # startyear for dropdown
initial_parameter = 'XX' # setting initial parameter to dummy
parameter = initial_parameter
df_res = pd.DataFrame() # initialize empty DataFrame

##### Plot

#### Mapplot

tools_to_show_p1 = 'box_zoom,pan,save,hover,reset,tap,wheel_zoom'
p1 = figure(x_range=(1043319, 1471393), y_range=(5684768, 6176606), plot_width=600, plot_height=600,
           x_axis_type="mercator", y_axis_type="mercator", tools=tools_to_show_p1)#, sizing_mode="scale_both")
p1.add_tile(tile_provider)
hover1 = p1.select(dict(type=HoverTool))
hover1.tooltips = [("Stationsname", "@Stationsname"), ("Stationsmessort", "@Stationsmessort"), ("Parametername", "@Parametername")]
hover1.mode = 'mouse'
if config['dir']['corr_path']:
    df_corr = read_corr_file()
    p1.circle(x="x", y="y", size=15, fill_color='color', fill_alpha=0.4, source=df_corr)
else:
    p1.circle(x="x", y="y", size=15, fill_color="blue", fill_alpha=0.4, source=df)

#### Initiate source for plots and table
source = ColumnDataSource(data=dict(index=['1970-01-01 00:00'], XX=['NaN'])) # Initialize empty source for table and plot

#### Datatable
datefmt = DateFormatter(format="%Y-%m-%d %H:%M")
columns = [
       TableColumn(field="index", title="date", formatter=datefmt),#, editor=DateEditor),
       TableColumn(field=parameter, title=parameter),
    ]
old_source = copy.deepcopy(source)
data_table = DataTable(source=source, columns=columns, width=400, height=600, fit_columns=True, editable=True)


#### Valueplot

tools_to_show_p2 = 'box_zoom,pan,save,reset,wheel_zoom'
p2 = figure(tools=tools_to_show_p2, x_axis_type='datetime')
p2.xaxis.formatter=DatetimeTickFormatter(
        hours=["%d %B %Y"],
        days=["%d %B %Y"],
        months=["%d %B %Y"],
        years=["%d %B %Y"])
tooltips = [("Date", "@index{%Y-%m-%d %H:%M}"), ("Value", "@{}".format(parameter))]
hover2 = HoverTool(
    tooltips = tooltips,
    formatters={
        'index': 'datetime',
    })
p2.line(x='index', y=parameter, source=source, name='tmp')
p2.add_tools(hover2)


#### Dropdown for year
year_dropdown = Dropdown(label="Year selection", menu=[])

### Summary
summary = Div(text="")

#### Dropdown for parameterselection
par_dropdown = Dropdown(label="Parameter selection", menu=[])

#### Button for saving CHANGES
button = Button(label="Save edits in table", button_type="warning")

#### Events
taptool = p1.select(type=TapTool)

p1.on_event(Tap, callback)

year_dropdown.on_change("value", year_dropdown_change)
par_dropdown.on_change("value", par_dropdown_change)
button.on_click(button_click)

doc_layout = layout(children=[p1, summary, widgetbox([row(year_dropdown, par_dropdown, button)]), row(p2, data_table)], sizing_mode='fixed')

curdoc().add_root(doc_layout)

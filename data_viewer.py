from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.io import curdoc
from bokeh.events import Tap
from bokeh.models import HoverTool, TapTool, DatetimeTickFormatter, DateFormatter
from bokeh.tile_providers import get_provider, Vendors
from bokeh.transform import dodge
from scipy.spatial.distance import cdist
from bokeh.models.renderers import GlyphRenderer
from bokeh.models.widgets import DataTable, TableColumn, Slider, Dropdown, Div
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
    data = xr.open_mfdataset(file_path,decode_times=True, combine='by_coords')
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

            
def callback(event):
    """
    Callback function
    """
    global dfs
    edit_table = False
    Coords=(event.x,event.y)
    print(Coords)
    df_res = find_station(df, event.x, event.y)
    print(df_res['Stationsmessort'].values[0], ' / ', df_res['Stationsname'].values[0])
    dfs = get_data_from_station(data_path, df_res)
    summary.text = get_summary(df_res, dfs)
    par_dropdown.menu = list(dfs.columns)
    year_dropdown.menu = np.unique(dfs.index.strftime('%Y')).tolist()
    dfs.loc[dfs['LT']==999.9] = np.nan # correction of failure values
    # change values in table
    source = ColumnDataSource.from_df(dfs.loc[str(year_dropdown.value)])
    data_table.source.data = source
    edit_table = True

    
    
def on_change_data_source(attr, old, new):
    # old, new and source.data are the same dictionaries
    #print('-- SOURCE DATA: {}'.format(old))
    #print('>> OLD SOURCE: {}'.format(new))

    # to check changes in the 'y' column:
    #indices = list(range(len(old_source['LT'])))
    #changes = [(i,j,k) for i,j,k in zip(indices, old_source.data['LT'], source.data['LT']) if j != k]
    #print('>> CHANGES: {}'.format(changes))
    #source.data = copy.deepcopy(source.data)
    print('on_change_data_source')

    
def year_dropdown_change(attr, old, new):
    # set displayed year to dropdown year
    print('Year set to: ', new)
    try:
        source = ColumnDataSource.from_df(dfs.loc[str(new)])
        data_table.source.data = source
    except:
        print('year without data')
    
def par_dropdown_change(attr, old, new):
    print('Parameter set to: ', new)
    # change table
    columns = [
       TableColumn(field="index", title="date", formatter=datefmt),#, editor=DateEditor),
       TableColumn(field=new, title=new),
    ]
    data_table.columns = columns
    source = ColumnDataSource.from_df(dfs.loc[str(year_dropdown.value)])
    data_table.source.data = source
    # change plot
    p2.renderers[0].glyph.y = new
    tooltips = [("Date", "@index{%Y-%m-%d %H:%M}"), ("Value", "@{}".format(new))]
    p2.tools[5].tooltips = tooltips
    
### Parsing directories from config file
    
config = configparser.ConfigParser()     
config.read('config.ini')    
list_path = config['dir']['list_path']
data_path = config['dir']['data_path']

### Read Data

df = pd.read_csv(list_path, encoding='latin1', delimiter=';')
tile_provider = get_provider(Vendors.CARTODBPOSITRON)
[df['x'], df['y']] = merc(df['Geografische_Länge'], df['Geografische_Breite']) # interchanged because of wrong labeling in wiski

#### Some Parameters
edit_table = False # set parameter to false
year = 2012 # startyear for dropdown
initial_parameter = 'LT'

##### Plot

#### Mapplot

tools_to_show_p1 = 'box_zoom,pan,save,hover,reset,tap,wheel_zoom'
p1 = figure(x_range=(1043319, 1471393), y_range=(5684768, 6176606), plot_width=600, plot_height=600,
           x_axis_type="mercator", y_axis_type="mercator", tools=tools_to_show_p1)#, sizing_mode="scale_both")
p1.add_tile(tile_provider)
hover1 = p1.select(dict(type=HoverTool))
hover1.tooltips = [("Stationsname", "@Stationsname"), ("Stationsmessort", "@Stationsmessort"), ("Parametername", "@Parametername")]
hover1.mode = 'mouse'
p1.circle(x="x", y="y", size=15, fill_color="blue", fill_alpha=0.4, source=df)

#### Initiate source for plots and table
source = ColumnDataSource(data=dict(index=['1970-01-01 00:00'], LT=['NaN'])) # Initialize empty source for table and plot

#### Datatable
datefmt = DateFormatter(format="%Y-%m-%d %H:%M")
columns = [
       TableColumn(field="index", title="date", formatter=datefmt),#, editor=DateEditor),
       TableColumn(field=initial_parameter, title=initial_parameter),
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
tooltips = [("Date", "@index{%Y-%m-%d %H:%M}"), ("Value", "@{}".format(initial_parameter))]
hover2 = HoverTool(
    tooltips = tooltips,
    formatters={
        'index': 'datetime',
    })
p2.line(x='index', y=initial_parameter, source=source, name='tmp')
p2.add_tools(hover2)



#### Dropdown for year
year_dropdown = Dropdown(label="Year selection", menu=[])

### Summary 
summary = Div(text="")

#### Dropdown for parameterselection
par_dropdown = Dropdown(label="Parameter selection", menu=[])


#### Events
taptool = p1.select(type=TapTool)

p1.on_event(Tap, callback)

year_dropdown.on_change("value", year_dropdown_change)  
par_dropdown.on_change("value", par_dropdown_change)
#if edit_table == True:
#data_table.source.on_change('data', on_change_data_source)

doc_layout = layout(children=[p1, summary, widgetbox([row(year_dropdown, par_dropdown)]), row(p2, data_table)], sizing_mode='fixed')

curdoc().add_root(doc_layout)
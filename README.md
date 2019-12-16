# data_viewer
bokeh tool to view timeseries data from netcdf files and edit single values in a DataTable

## How does it work?
This is a tool to display and edit spatial timeseries, which are stored in netcdf files.


#### generate_overview_csv.py
Reads through all attributes of the netcdf files in subfolders with ending "-nc" (e.g. LT-nc) and stores the attributes in an csv overview file.

#### data_viewer.py
Plots an overview of the stations in a map. The hover tool shows which timeseries parameters are available. At a click on one station, the data of the corresponding station is read at runtime and is showed in the lower plot. There will appear some statistics and metadata of the corresponding station. With dropdown menus year and parameter to display can be selected. The datatable is editable, so it's possible to write out the changes to a netcdf file (armed = True writes it to the same ile, armed = False creates a new file).

called by:
bokeh serve data_viewer.py --show


#### config.ini
must look like:

[dir]

list_path = (path to the overview csv)

data_path = (path to the parent data directory

[settings]

armed = False


## Attention
This is still a draft version, there are some further to-do's:

* fix display in hover in map plot
* visual improvements like station title and correct x-axis name in plot
* map area dynamically (now tyrol, south-tyrol and trentino)
* make it modular (IO-Functions for xarray, csv,...)
* add automated tests
* etc....

Sample Data is just some random data with no corresponding real stations! Just for presentation of the data viewer!

## How does it look like?
An running example can be accessed [here](https://www.exi.rocks/display/EX/Data+Viewer+Application)
![image](https://github.com/Exi666/data_viewer/blob/master/image.png)




### Prequisits
#### Python 3 libraries:
* bokeh
* scipy
* xarray
* netcdf4
* configparser
* numpy
* pandas

## Licensing
![Creative Commons License](https://i.creativecommons.org/l/by-sa/4.0/88x31.png)
This code is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International](http://creativecommons.org/licenses/by-sa/4.0/) License.

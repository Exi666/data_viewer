import xarray as xr
import os
import pandas as pd
import configparser

### read paths from config file

config = configparser.ConfigParser()     
config.read('config.ini')    
csv = config['dir']['list_path']
path = config['dir']['data_path']

### read headers from netcdf files into csv
os.chdir(path)

f = open(csv, 'w')
cnt=0

for item in os.listdir(path):
    if os.path.isdir(item):
        if '-nc' in item: 
            dirpath = os.path.join(path,item)
            #os.chdir(dirpath)
            #print(dirpath)
            for filename in os.listdir(dirpath):
                try:
                    data = xr.open_dataset(os.path.join(dirpath,filename))
                    if cnt == 0:
                        for key, value in data.attrs.items():
                            f.write(key)
                            f.write(';')
                        f.write('Filename')
                        f.write(';')
                        f.write('Parent-Folder')
                        f.write('\n')
                    cnt += 1
                    if cnt > 0:
                        for key, value in data.attrs.items():
                            f.write(str(value))
                            f.write(';')
                        f.write(filename)
                        f.write(';')
                        f.write(item)
                    f.write('\n')
                    data.close()
                except:
                    print('Error in: ', os.path.join(dirpath,filename))
    
                    
f.close()
print('finished parsing')
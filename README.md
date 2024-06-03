# StreamFlow-Forecast

A python project that uses pandas, numpy, matplotlib, and a special module to download live streamflow data from the US Geological Survey (USGS) National Water Information System (NWIS).

## Details
The Hydrofunctions python module allows you to pull live streamflow data from various NWIS sensors around the US. The sensors provide everything from water temperature to river flow levels, updating their data frequently. More about this module and the data it retrieves later.

The program retrieves three weeks worth of data that is anchored on a certain date, as specified by the user. The first two weeks are before the specified date and show historic data from the current year and the previous nine years. The last week is after the specified date and shows historic data from the previous nine years along with a week-long prediction for the current year. The graph is continuous for the full three weeks of data, but there is a vertical line showing where the graph changes from historic data to future predictions (e.g. on the user-specified date).

For the nine years of historic data, I identify which year had the most waterflow and which year had the least waterflow, by total volume, and calculate the "typical" waterflow, which is the average waterflow over the nine years +/- half a standard deviation.

## Plotted
- The year with the most waterflowin a "good" color like green (labeled in the legend)
- The year with the least waterflow in a dull color like blue (labeled in the legend).
- The "typical" waterflow with a light-gray shaded graph (standard deviation).
- For the current year, the two weeks of previous data and one week prediction as a solid black line (labeled in the legend).

See sample graph below:

<img width="628" alt="image" src="https://github.com/TamsynE/StreamFlow-Forecast/assets/93171379/79bbc3e9-b964-49c6-805b-338f8e21f157">


## Hydrofunctions Module
You can install Hydrofunctions with pip install hydrofunctions.

As provided by my professor, we can download historic river flow from the Trinity River Burnt Ranch Gorge sensor like this:

import hydrofunctions as hf
trinity_burnt_ranch_id = '11527000'
nwis_data = hf.NWIS(trinity_burnt_ranch_id, 'iv', start_date='2023-06-01', end_date='2023-06-05')
df = nwis_data.df('discharge')[:]

Once the streamflow data has been obtained, we can perform the necessary calculations and plotting.

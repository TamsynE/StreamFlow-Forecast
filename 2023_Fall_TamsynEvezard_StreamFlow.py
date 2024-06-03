import hydrofunctions as hf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
matplotlib.use('TkAgg')
from datetime import datetime, timedelta

curr_year = str(datetime.now().year)
# PROMPT USER FOR DATE OF CURRENT YEAR
# try:
input_date = input("Please enter the date for Streamflow Forecast (format: MM-DD): ")
# CALCULATE MIDDLE DATE (DATE INPUTTED)
mid_date = input_date
mid_full = datetime.strptime(f"{curr_year}-{input_date}", '%Y-%m-%d')
# CALCULATE TWO WEEKS BEFORE
start = mid_full - timedelta(weeks=2)
start_formatted = start.strftime('%m-%d')
# CALCULATE END DATE
end = mid_full + timedelta(weeks=1)
end_formatted = end.strftime('%m-%d')


sensor_id = '11527000'
# READ LIVE STREAMFLOW DATA FROM THE NWIS DATABASE
nwis_data = hf.NWIS(sensor_id, 'iv', start_date=f"{curr_year}-{start_formatted}", end_date=f"{curr_year}-{mid_date}")
df_curr = nwis_data.df('discharge')[:]

# CURRENT FLOW
old_col_name = 'USGS:' + sensor_id + ":00060:00000"
new_col_name = 'CFS'
df_curr = df_curr.rename(columns={old_col_name:new_col_name})
df_curr_cpy = df_curr.copy() # MAKE COPY FOR LATER USE SO DATETIME INDEX CAN BE DROPPED
df_curr.reset_index(inplace=True)
df_curr.drop(columns=['datetimeUTC'], inplace=True)


# CUMULATIVE WATER VOLUME & CHANGE IN FLOW
first_row = df_curr.index[0]
last_row = df_curr.index[-1]

# Calculate rolling mean for the 'Discharge' column
rolling_mean = (df_curr.loc[first_row:last_row, :]
                .rolling(window=2)
                .mean()
                .fillna(0)
                .round(0)
                .astype(int))

rolling_mean

def calc_total_water_vol(rolling_mean):
    '''Calculates the cumulative water flow of a rolling df'''
    total_water_cf = rolling_mean['CFS'].sum() * 900
    total_water_acre_feet = int(total_water_cf / 43560)
    return total_water_acre_feet

total_water_vol_acre_feet = calc_total_water_vol(rolling_mean)

def get_change_in_flow(df):
    '''Calculates the change in flow between the last two data points of the current flow (previous two weeks)'''
    derivative = df['CFS'].diff().iloc[-1]
    return derivative

flow_change = get_change_in_flow(df_curr)

sign = '' # shows whether water is currently rising, dropping, or staying constant
if flow_change > 0:
    sign = 'rising'
elif flow_change < 0:
    sign = 'dropping'
else:
    sign = '(constant)'

# ADJUST DATA FRAME TO CONTAIN A COLUMN FOR EVERY YEAR (9 YEARS BEFORE TILL CURRENT)
start_year = int(curr_year) - 9

year_list = list(range(start_year, int(curr_year)+1)) # store years in list (inclusive)

# MAKE A NEW LIST FOR EACH DATA FRAME/EACH YEAR TO JOIN TOGETHER
df_list = []
for year in year_list: # use same month-day variables are df_curr
    start_date = f"{year}-{start_formatted}"
    end_date = f"{year}-{end}"

    nwis_col = hf.NWIS(sensor_id, 'iv', start_date=f"{year}-{start_formatted}", end_date=f"{year}-{end_formatted}")
    nwis_col = nwis_col.df('discharge')[:]
    
    old_col_name = 'USGS:' + sensor_id + ":00060:00000"
    new_col_name = f"{year}"
    nwis_col.rename(columns={old_col_name:new_col_name}, inplace=True)
    nwis_col.reset_index(inplace=True)
    dt_df = nwis_col['datetimeUTC']
    nwis_col.drop(columns=['datetimeUTC'], inplace=True)
    df_list.append(nwis_col)

df_all = df_list[0].join(df_list[1:-1]) # join all the 'columns'/years together in one df
df_all.ffill(inplace=True)
dt_df = dt_df.dt.tz_convert('US/Pacific').dt.tz_localize(None) # Change time zone
df = pd.concat([df_all, df_curr['CFS'], dt_df], axis=1)

# convert years to strings to be used for max and min flow year calculations
for i in range(len(year_list)):
    year_list[i] = str(year_list[i])

# CALCULATE THE MAX & MIN FLOW YEARS & ADD TO DF
max_flow_yr = df[year_list[:-1]].sum().idxmax()
min_flow_yr = df[year_list[:-1]].sum().idxmin()

df[f'Max: {max_flow_yr}'] = df[max_flow_yr]
df[f'Min: {min_flow_yr}'] = df[min_flow_yr]

# CALCULATE THE AVERAGE FLOW & ADD TO DF
average = round(df[year_list[:-1]].mean(axis='columns'), 1)
df['Average'] = average

# CALCULATE THE STANDARD DEVIATION & ADD UPPER AND LOWER LIMITS TO DF
stdv = round(df[year_list[:-1]].std(axis='columns'), 1)

df['Standard Dev'] = stdv / 2 # +/- 0.5 stdv for upper and lower (looks neater)

upper = df['Average'] + df['Standard Dev']
lower = df['Average'] - df['Standard Dev']
df['Upper'] = upper
df['Lower'] = lower

# LINEAR REGRESSION: X & Y
two_weeks_ordinals = np.arange(df_curr.index.size) # X
full_timeseries_ordinals = np.arange(df_all.index.size)
y_values = df_curr_cpy['CFS'] # Y
test_values = zip(two_weeks_ordinals, y_values) # combine

# CALCULATE LINEAR REGRESSION
mean_x = two_weeks_ordinals.mean()
mean_y = df_curr['CFS'].mean()
gradient = df_curr_cpy['CFS'].diff() / df_curr_cpy['CFS'].index.to_series().diff().dt.total_seconds()

intercept = mean_y - (gradient * mean_x)
x1 = max(two_weeks_ordinals)
x2 = max(full_timeseries_ordinals)
y1 = gradient * x1 + intercept
y2 = gradient * x2 + intercept

# PLOT IMPORTANT COLUMNS OF DATA FRAME
columns_to_plot = [f'Min: {min_flow_yr}', f'Max: {max_flow_yr}', 'CFS', 'Upper', 'Lower']
df_plot = df[['datetimeUTC'] + columns_to_plot].copy()

# Convert 'datetimeUTC' to datetime format
df_plot['datetimeUTC'] = pd.to_datetime(df_plot['datetimeUTC'])
future_values = np.round(two_weeks_ordinals * (gradient) + intercept, 0)

# Create a new column 'Future' in df_plot
df_plot['Future'] = np.nan
first_nan_index = df['CFS'].isnull().idxmax()

# Set values in 'Future' column starting at first_nan_index
df_plot['Future'].iloc[first_nan_index:] = future_values[0:full_timeseries_ordinals.size - two_weeks_ordinals.size]

# PLOT
plt.figure(figsize=(10, 6))
plt.plot(df_plot['datetimeUTC'], df_plot[f'Min: {min_flow_yr}'], label=f"Lowest ({min_flow_yr})", color='blue')
plt.plot(df_plot['datetimeUTC'], df_plot[f'Max: {max_flow_yr}'], label=f"Highest ({max_flow_yr})", color='green')
plt.plot(df_plot['datetimeUTC'], df['CFS'], label=f"Current ({curr_year})", color='black')
plt.plot(df_plot['datetimeUTC'], df_plot['Upper'], color='grey', alpha=0.5)
plt.plot(df_plot['datetimeUTC'], df_plot['Lower'], color='grey', alpha=0.5)
plt.fill_between(df_plot['datetimeUTC'], df_plot['Upper'], df_plot['Lower'], color="lightgrey")
plt.plot(df_plot['datetimeUTC'], df_plot['Future'], color='black')

# Plot a vertical line at the inputted date
plt.axvline(x=mid_full, color='red', linestyle='dashed', label=f"{mid_full.strftime('%B %d %H:%M')}")

#Format x-axis labels to display only month and day
plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%B %d'))

plt.suptitle("TRINITY RIVER BURNT RANCH (CFS)")
plt.title(f'{total_water_vol_acre_feet} acre-feet: {flow_change} {sign}', fontsize=8, pad = 15)
plt.legend()
plt.show()

# except ValueError:
#     print("Invalid date inputted. Please use MM-DD format.")
#     exit()
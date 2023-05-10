# WLTP time-series data

# Download
WLTP time-series data downloaded from:

    https://unece.org/dhc-12th-session

# Conversion

To use the data for the simulation, the data was taken from the source provided above and written into a .csv-file using
the style:

```
time [s];vehicle_speed [km/h];acceleration [m/s^2];slope [°]
```

The slope is set to zero manually for all time steps.
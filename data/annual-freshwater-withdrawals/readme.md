# Annual freshwater withdrawals - Data package

This data package contains the data that powers the chart ["Annual freshwater withdrawals"](https://ourworldindata.org/grapher/annual-freshwater-withdrawals?v=1&csvType=full&useColumnShortNames=false) on the Our World in Data website. It was downloaded on February 21, 2026.

### Active Filters

A filtered subset of the full data was downloaded. The following filters were applied:

## CSV Structure

The high level structure of the CSV file is that each row is an observation for an entity (usually a country or region) and a timepoint (usually a year).

The first two columns in the CSV file are "Entity" and "Code". "Entity" is the name of the entity (e.g. "United States"). "Code" is the OWID internal entity code that we use if the entity is a country or region. For most countries, this is the same as the [iso alpha-3](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3) code of the entity (e.g. "USA") - for non-standard countries like historical countries these are custom codes.

The third column is either "Year" or "Day". If the data is annual, this is "Year" and contains only the year as an integer. If the column is "Day", the column contains a date string in the form "YYYY-MM-DD".

The final column is the data column, which is the time series that powers the chart. If the CSV data is downloaded using the "full data" option, then the column corresponds to the time series below. If the CSV data is downloaded using the "only selected data visible in the chart" option then the data column is transformed depending on the chart type and thus the association with the time series might not be as straightforward.


## Metadata.json structure

The .metadata.json file contains metadata about the data package. The "charts" key contains information to recreate the chart, like the title, subtitle etc.. The "columns" key contains information about each of the columns in the csv, like the unit, timespan covered, citation for the data etc..

## About the data

Our World in Data is almost never the original producer of the data - almost all of the data we use has been compiled by others. If you want to re-use data, it is your responsibility to ensure that you adhere to the sources' license and to credit them correctly. Please note that a single time series may have more than one source - e.g. when we stich together data from different time periods by different producers or when we calculate per capita metrics using population data from a second source.

## Detailed information about the data


## Annual freshwater withdrawals
Last updated: January 29, 2026  
Next update: January 2027  
Date range: 1962–2022  
Unit: billion cubic meters  
Unit conversion factor: 1000000000  


### How to cite this data

#### In-line citation
If you have limited space (e.g. in data visualizations), you can use this abbreviated in-line citation:  
AQUASTAT - FAO's Global Information System on Water and Agriculture, FAO, via World Bank (2026) – processed by Our World in Data

#### Full citation
AQUASTAT - FAO's Global Information System on Water and Agriculture, FAO, via World Bank (2026) – processed by Our World in Data. “Annual freshwater withdrawals” [dataset]. AQUASTAT - FAO's Global Information System on Water and Agriculture, FAO, via World Bank, “World Development Indicators 125” [original data].
Source: AQUASTAT - FAO's Global Information System on Water and Agriculture, FAO, via World Bank (2026) – processed by Our World In Data

### How is this data described by its producer - AQUASTAT - FAO's Global Information System on Water and Agriculture, FAO, via World Bank (2026)?
Annual freshwater withdrawals refer to total water withdrawals, not counting evaporation losses from storage basins. Withdrawals also include water from desalination plants in countries where they are a significant source. Withdrawals can exceed 100 percent of total renewable resources where extraction from nonrenewable aquifers or desalination plants is considerable or where there is significant water reuse. Withdrawals for agriculture and industry are total withdrawals for irrigation and livestock production and for direct industrial use (including withdrawals for cooling thermoelectric plants). Withdrawals for domestic uses include drinking water, municipal use or supply, and use for public services, commercial establishments, and homes. Data are for the most recent year available for 1987-2002.

### Limitations and exceptions:
A common perception is that most of the available freshwater resources are visible (on the surfaces of lakes, reservoirs and rivers). However, this visible water represents only a tiny fraction of global freshwater resources, as most of it is stored in aquifers, with the largest stocks stored in solid form in the Antarctic and in Greenland's ice cap.

The data on freshwater resources are based on estimates of runoff into rivers and recharge of groundwater. These estimates are based on different sources and refer to different years, so cross-country comparisons should be made with caution. Because the data are collected intermittently, they may hide significant variations in total renewable water resources from year to year. The data also fail to distinguish between seasonal and geographic variations in water availability within countries. Data for small countries and countries in arid and semiarid zones are less reliable than those for larger countries and countries with greater rainfall.

Caution should also be used in comparing data on annual freshwater withdrawals, which are subject to variations in collection and estimation methods. In addition, inflows and outflows are estimated at different times and at different levels of quality and precision, requiring caution in interpreting the data, particularly for water-short countries, notably in the Middle East and North Africa.

The data are based on surveys and estimates provided by governments to the Joint Monitoring Programme of the World Health Organization (WHO) and the United Nations Children's Fund (UNICEF). The coverage rates are based on information from service users on actual household use rather than on information from service providers, which may include nonfunctioning systems.

### Statistical concept and methodology:
Annual freshwater withdrawals are total water withdrawals, not counting evaporation losses from storage basins. Withdrawals also include water from desalination plants in countries where they are a significant source. Water withdrawals can exceed 100 percent of total renewable resources where extraction from nonrenewable aquifers or desalination plants is considerable or where water reuse is significant. Withdrawals for agriculture and industry are total withdrawals for irrigation and livestock production and for direct industrial use (including for cooling thermoelectric plants). Withdrawals for domestic uses include drinking water, municipal use or supply, and use for public services, commercial establishments, and homes.

### Source

#### AQUASTAT - FAO's Global Information System on Water and Agriculture, FAO, via World Bank – World Development Indicators
Retrieved on: 2026-01-30  
Retrieved from: https://data.worldbank.org/indicator/ER.H2O.FWTL.K3  


    
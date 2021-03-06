# Table of Contents

- [Fire Department Simulator](#fire-department-simulator)
  * [Overview](#overview)
- [How To Use](#how-to-use)
- [How it works](#how-it-works)
 
  
# Fire Department Simulator
 
This Python software simulates the operations of a fire department in any city by dispatching fire engines, ambulances, and other apparatus to the scene of incidents. 

Fire departments can use this tool to forecast how any change in the number of fire stations, fire engines, ambulances, etc. would affect their operations. 

## Overview

This software enables the advanced analysis needed to forecast response times performance, the number of units busy responding at the same time at any given hour of the day, and many other metrics. If you choose to display a map, you can follow the simulation while it runs and the simulated incidents while they occur in the city. Here is an example for Washington DC. Each dot is an emergency incident.

![DC_Incidents.gif](https://github.com/fdeberna/FD_simulator/blob/master/img/DC_Incidents.gif)

The output of the software is a table with the list of incidents that occurred in the simulated time period. The structure of this table resembles real [Computer Aided Dispatch data](https://en.wikipedia.org/wiki/Computer-aided_dispatch). This table will contain information including the location of the incidents, the incident type (emergency medical services, fire, etc.), the units (e.g. fire engines and ambulances) which responded to that incidents, the time when they were dispatched, the time when they reached the scene, and more. Here is an example of output from the simulation:

<img src="https://github.com/fdeberna/FD_simulator/blob/master/img/CAD_results.JPG" width="1000">

Units from each station travel towards different parts of the city. Users could examine how opening new stations changes the flux of emergency vehicles. For example, this figure shows that opening a new station allows units from Station 1 and Station 2 to stay more often within their station response areas (FD1 and FD2).

<img src="https://github.com/fdeberna/FD_simulator/blob/master/img/fluxes.JPG" width="750">

Adding or removing stations and units will affect response times. It is easy to observe this effect with the simulated data produced by FD_simulator.

<img src="https://github.com/fdeberna/FD_simulator/blob/master/img/Simulation_TT.png" width="750">

# How To Use

The user provides several data tables that describe the city to model. There are many ways to produce the tables and template tables are provided in the repository to run the code. It does not matter which geographical software is used to produce these tables as long as they follow the template. 

The geographical area of interest is represented by a grid. For example:

![GridDC.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/GridDC.JPG)

The quantities needed to model the city are:

* A **cost matrix**: determines the travel time from one cell of the grid to any other cell. This is as simple as the following table where "start" and "end" are indices of the cells and "cost" is the travel time in seconds.

![cost_matrix.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/cost_matrix.JPG)

* **Frequency of incidents** (this is the file ending in \*location_rates.csv in the repository): a table that specifies, for each cell, the expected number of incidents per second. There is no hard requirement for the type of incidents. Users could report the expected frequency for EMS incidents only, or Fire incidents only. 

![locations_rates.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/locations_rates.JPG)

* **Daily rates**: a table specifying the number of incidents per second expected in each hour of the day and the standard deviation to mean ratio for the number of incidents. This file is used to normalize the number of incidents in each hour, in order to model hour-to-hour variations. 

![daily_rates.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/daily_rates.JPG)

* **Units file**: this table specifies the units available to the department, their type (engines, ladders, transport), their EMS type, for example, Advanced Life Support (ALS) or Basic Life Support (BLS), the initial cell whee the unit is located at the beginning of the simulation, and the average time the unit spend on each type of incidents. This is the table to edit to study the effect of adding or removing units.

![units_file.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/units_file.JPG)

* **Station file**: a simple table, specifying the name of the fire station and the cell where they are located. Modify this table to add or remove stations.

![station_file.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/station_file.JPG)

* **Response model**: a table that describes the way the department responds to each type of incident. How many engines and ladders are dispatched to a fire incident? How many ambulances for a medical emergency?

![resp.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/resp.JPG)

Once the user creates these files, they can be passed to the software simply by editing these lines in the **driver.py**:

![inputs.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/inputs.JPG)

Several settings can be decided by the users. A Graphical User Interface will be provided in a future version. At this stage, the user can modify variables directly in the driver.py file. For example, the start and end date of the simulation, the level of feedback the software provides while running ("verbose level"), deciding if displaying an interactive map while the simulation runs, and many other settings.

![settings.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/settings.JPG)

# How it works

It its essence, the code is a random Poisson generator of fire, EMS, HazMat, or any other type of incident. The location of the incidents is randomized according to the input incidents density. The frequency of the incidents also follows the incident rates that the user provides in the input tables. The frequency of the incidents is typically higher during the daytime and lower at night. The day and night modulation can be modified in the daily rates file described above.

The file that does the work is **driver.py**.  There are functions in the file to find the closest units and assign them to the incident. The code uses Poisson probabilities for the incidents arrival rate and the service rate, that is, the probability of a unit clearing the incident. The Poisson distribution is informed by the input tables. 

The file **c_Apparatus.py** defines various classes with several methods and attributes. Methods and attributes keep track of the status of the units and the incidents occurring in the city.

Apparatus of the department (that is, engines, ladders, ambulances, etc.) belong to the class "Apparatus".  Incidents and fire stations are also a class.

![class_Apparatus.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/class_Apparatus.JPG)

![class_Incidents.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/class_Incidents.JPG)

![class_Station.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/class_Station.JPG )

The class **Apparatus** has several attributes which describe the status of the unit ("available","dispatched", "at the scene", etc.), its type ("engine", "ambulance", etc.), the station it belongs to, and other properties derived from the input tables.

This class has the following methods:

 * **status_update**: update the status of the unit, for example from "available" to "dispatched"
 * **next_update**: sets the time when the next status update is expected to occur.
 * **next_loc**: sets the location of the unit at the next status update. For example a unit dispatched from one cell, will be updated as "on the scene of incident" at a different cell. 
 * **next_inc**: the incident ID number to which the unit is assigned.
 * **track**: appends the history of the unit to a list. Includes the incidents the unit responded to, what time it started to travel towards the scene of the incident, the time when it reached the scene, etc.

The **Incident** class attributes include the unique incident identifier, the type of incident (for example, medical emergency or fire), the type of units required to respond, the number of units required for each type, and the location of the incident.

This class has the following methods:
* **assign_unit**: assigns a unit to the incident. The units assigned to the incident are appended to a list.
* **reduce**: reduces the count of units of a particular type needed to address the incident. This software calls this method after assigning one unit to the incident.
* **increase**: opposite of **reduce**. Increases the number of units needed to address the incident. It might be used to model incidents that escalate to a higher emergency level, or if the unit previously assigned is no longer available for any reason.




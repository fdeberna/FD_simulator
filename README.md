# Fire Department Simulator
 
This Python tool simulates the operations of a fire department in any city, real or not, by dispatching fire engines, ambulances, and other apparatus to the scene of incidents.

The output of the software is a table with the list of incidents that occurred in the simulated time period. The structure of this table resembles real [Computer Aided Dispatch data](https://en.wikipedia.org/wiki/Computer-aided_dispatch). This table will contain information including the location of the incidents, the incident type (emergency medical services, fire, etc.), the units (e.g. fire engines and ambulances) which responded to that incidents, the time when they were dispatched, the time when they reached the scene, and more. Here is an example of output from the simulation:

![CAD_results.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/CAD_results.JPG)

# Goal

Fire departments can use this tool to forecast how any change in the number of fire stations, fire engines, ambulances, etc. would affect their operations. Incidents occurring simultaneously in different parts of the city decrease the efficiency of a fire department and its ability to maintain coverage of the city in ways that are hard to predict. This software enables the advanced analysis needed to forecast response times performance, the number of units busy responding at the same time at any given hour of the day, and many other metrics.

# Quick Preview

Several settings can be decided by the users, including the deploying model, that is, for example, the number of fire engines dispatched to fire incidents. A Graphical User Interface will be provided in a future version. At this stage, the user can modify variables directly in the driver.py file. For example, the start and end date of the simulation, the level of feedback the software provides while running ("verbose level"), deciding if displaying an interactive map while the simulation runs, and many other settings.

![settings.JPG](https://github.com/fdeberna/FD_simulator/blob/master/img/settings.JPG)

If you choose to display a map, you can follow the simulation while it runs and the simulated incidents while they occur in the city. Here is an example for Washington DC. Each dot is an emergency incident.

![DC_Incidents.gif](https://github.com/fdeberna/FD_simulator/blob/master/img/DC_Incidents.gif)


# Technical Details

Coming Soon.

# ha_strava
Custom Component for Home Assistant to integrate your Activity Data from Strava.


## Features
* Gives you access to **up to 10 of your most recent activities** in Strava. 
* Supports both the **metric and the imperial** unit system
* Activity data in Home Assistant **auto-updates** whenever you add, modify, or delete activities on Strava
* Exposes **5 customizeable sensor entities** for each Strava activity
* **Easy set-up**: only enter your Strava Client-ID and -secret and you're ready to go

![](sensor_overview.png)

For every Strava activity, the Strava Home Assistant Integration creates a **device entity** in Home Assistant (max 10 activities). Each of these virtual device entities exposes **five sensor entities** which you can fully customize to display one of the following **activity KPIs**:
* Duration (Minutes),
* Pace (Minutes/Mile ; Minutes/Km)
* Speed (Miles/Hour; Km/Hour)
* Distance (Miles; Km)
* # Kudos
* Kalories (cKal),
* Elevation Gain (Feet, Meter)
* Power (Watts)
* # Trophies

Since every Strava activity gets its own virtual device, you can use the underlying sensor data in your **Dashboards and Automations**, just as you'd use any other sensor data in Home Assistant. 

## Installation
1. Set up remote access to your Home Assistant Installation
2. Obtain your Strava API credentials
3. Add the Strava Home Assistant Integration to your Home Assistant 
4. Make a connection between your Strava account and Home Assistant
Now is the time to fire up the Strava Home Assitant Integration for the first time and make a connection between Strava and your Home Assistant Instance. 

For much more detailed guidelines on how to install Strava Home Assitant, check out the (README)[https://github.com/codingcyclist/ha_strava]

## Configuration/Customization
You have the following options to customize Strava Home Assistant:
- Increase/Decrease the number of Strava activities avaiable in Home
- Customize sensor KPIs for different types of Strava Activities
- Integrate Strava Activities into your Home Assistant UI

For much more detailed guidelines on how to configure Strava Home Assitant, check out the (README)[https://github.com/codingcyclist/ha_strava]
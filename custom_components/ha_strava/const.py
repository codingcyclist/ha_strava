"""Constants for the Strava Home Assistant integration."""

DOMAIN = "ha_strava"

# OAuth Specs
AUTH_CALLBACK_PATH = "/auth/external/callback"
OAUTH2_AUTHORIZE = "https://www.strava.com/oauth/authorize"
OAUTH2_TOKEN = "https://www.strava.com/oauth/token"

# Webhook & API Specs
CONF_WEBHOOK_ID = "webhook_id"
CONF_CALLBACK_URL = "callback_url"
WEBHOOK_SUBSCRIPTION_URL = "https://www.strava.com/api/v3/push_subscriptions"
CONF_NB_ACTIVITIES = "nb_activities"
DEFAULT_NB_ACTIVITIES = 1
MAX_NB_ACTIVITIES = 10

# Event Specs
CONF_STRAVA_UPDATE_EVENT = "strava_data_update"
CONF_STRAVA_RELOAD_EVENT = "ha_strava_reload"

# Sensor Specs
CONF_SENSOR_DATE = "date"
CONF_SENSOR_DURATION = "duration"
CONF_SENSOR_PACE = "pace"
CONF_SENSOR_DISTANCE = "distance"
CONF_SENSOR_KUDOS = "kudos"
CONF_SENSOR_CALORIES = "calories"
CONF_SENSOR_ELEVATION = "elevation_gain"
CONF_SENSOR_POWER = "power"
CONF_SENSOR_TROPHIES = "trophies"
CONF_SENSOR_TITLE = "title"
CONF_SENSOR_CITY = "city"
CONF_SENSOR_MOVING_TIME = "moving_time"
CONF_SENSOR_ACTIVITY_TYPE = "activity_type"
CONF_ACTIVITY_TYPE_RUN = "Run"
CONF_ACTIVITY_TYPE_RIDE = "Ride"
CONF_SENSORS = {
    CONF_SENSOR_DATE: {"icon": "mdi:run"},
    CONF_SENSOR_DURATION: {"icon": "mdi:speedometer"},
    CONF_SENSOR_PACE: {"icon": "mdi:clock-fast"},
    CONF_SENSOR_DISTANCE: {"icon": "mdi:ruler"},
    CONF_SENSOR_KUDOS: {"icon": "mdi:thumb-up-outline"},
    CONF_SENSOR_CALORIES: {"icon": "mdi:fire"},
    CONF_SENSOR_ELEVATION: {"icon": "mdi:elevation-rise"},
    CONF_SENSOR_POWER: {"icon": "mdi:dumbbell"},
    CONF_SENSOR_TROPHIES: {"icon": "mdi:trophy"},
}
FACTOR_METER_TO_MILE = 0.000621371
FACTOR_METER_TO_FEET = 3.28084
FACTOR_KILOJOULES_TO_CALORIES = 0.239006

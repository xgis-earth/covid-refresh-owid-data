# 2019-nCoV Our World in Data Refresh

[![Build Status](https://drone-io.tiepy.dev/api/badges/xgis-earth/covid-refresh-owid-data/status.svg)](https://drone-io.tiepy.dev/xgis-earth/covid-refresh-owid-data)

Hasura event handler for refreshing data from Our World in Data.

## Development Environment

The following environment variables must be defined for the database connection:

* COVID_DB_HOST
* COVID_DB_NAME
* COVID_DB_USER
* COVID_DB_PASS

### Run Example

```bash
uvicorn main:app --reload --no-use-colors
```

## Deployment Configuration

### Cron Trigger Event Definition

#### Name

refresh-owid-data

#### Webhook

http://refresh-owid-data/refresh

#### Cron Schedule

0 * * * *

_(hourly on the hour)_

#### Payload

```json
{
  "action": "refresh"
}
```

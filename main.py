from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from pydantic import BaseModel
from os import environ as env
from io import StringIO
import psycopg2
import traceback
import requests
import csv
import json


# Constants
# ------------------------------------------------------------------------------

url = "https://covid.ourworldindata.org/data/owid-covid-data.csv"


# Classes
# ------------------------------------------------------------------------------

class Payload(BaseModel):
    action: str


class Args(BaseModel):
    payload: Payload


# Functions
# ------------------------------------------------------------------------------

def get_conn():
    host = env.get("COVID_DB_HOST")
    dbname = env.get("COVID_DB_NAME")
    user = env.get("COVID_DB_USER")
    password = env.get("COVID_DB_PASS")
    return psycopg2.connect(host=host, dbname=dbname, user=user, password=password, sslmode="require")


# FastAPI
# ------------------------------------------------------------------------------

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )


@app.post("/refresh", response_model=None)
async def handle_refresh_request(args: Args, response: Response) -> None:
    assert args.payload.action == "refresh"

    r = requests.get(url)
    r.raise_for_status()
    f = StringIO(r.text)

    # iso_code
    # continent
    # location
    # date
    # total_cases
    # new_cases
    # new_cases_smoothed
    # total_deaths
    # new_deaths
    # new_deaths_smoothed
    # total_cases_per_million
    # new_cases_per_million
    # new_cases_smoothed_per_million
    # total_deaths_per_million
    # new_deaths_per_million
    # new_deaths_smoothed_per_million
    # reproduction_rate
    # icu_patients
    # icu_patients_per_million
    # hosp_patients
    # hosp_patients_per_million
    # weekly_icu_admissions
    # weekly_icu_admissions_per_million
    # weekly_hosp_admissions
    # weekly_hosp_admissions_per_million
    # new_tests
    # total_tests
    # total_tests_per_thousand
    # new_tests_per_thousand
    # new_tests_smoothed
    # new_tests_smoothed_per_thousand
    # positive_rate
    # tests_per_case
    # tests_units
    # total_vaccinations
    # new_vaccinations
    # total_vaccinations_per_hundred
    # new_vaccinations_per_million
    # stringency_index
    # population
    # population_density
    # median_age
    # aged_65_older
    # aged_70_older
    # gdp_per_capita
    # extreme_poverty
    # cardiovasc_death_rate
    # diabetes_prevalence
    # female_smokers
    # male_smokers
    # handwashing_facilities
    # hospital_beds_per_thousand
    # life_expectancy
    # human_development_index

    lookup = {}

    csv_reader = csv.DictReader(f)
    for row in csv_reader:

        iso_code = row["iso_code"]
        vaccinations = row["total_vaccinations"]
        hospitalisations = row["hosp_patients"]
        # icu_patients = row["icu_patients"]
        # total_tests = row["total_tests"]
        # positive_rate = row["positive_rate"]

        if not vaccinations and not hospitalisations:
            continue

        if iso_code not in lookup:
            lookup[iso_code] = []

        entry = {
            "date": row["date"]
        }

        if vaccinations:
            entry["vaccinations"] = vaccinations

        if hospitalisations:
            entry["hospitalisations"] = hospitalisations

        # if icu_patients:
        #     entry["icu_patients"] = icu_patients
        #
        # if total_tests:
        #     entry["total_tests"] = total_tests
        #
        # if positive_rate:
        #     entry["positive_rate"] = positive_rate

        lookup[iso_code].append(entry)

    # Connect to database.
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        for iso_code in lookup:
            time_series = lookup[iso_code]

            # Split the time-series for two db fields.
            vaccinations_time_series = []
            hospitalisations_time_series = []
            for item in time_series:
                if "vaccinations" in item:
                    vaccinations_time_series.append({
                        "date": item["date"],
                        "count": int(float(item["vaccinations"]))
                    })
                if "hospitalisations" in item:
                    hospitalisations_time_series.append({
                        "date": item["date"],
                        "count": int(float(item["hospitalisations"]))
                    })

            # Update vaccinations.
            if len(vaccinations_time_series) > 0:
                cur.execute("""
                    UPDATE country SET
                        covid_vaccinations = %s,
                        covid_vaccinations_time_series = %s
                    WHERE iso_alpha3 = %s""", (vaccinations_time_series[-1]["count"],
                                               json.dumps(vaccinations_time_series),
                                               iso_code))

            # Update hospitalisations.
            if len(hospitalisations_time_series) > 0:
                cur.execute("""
                    UPDATE country SET
                        covid_hospitalisations = %s,
                        covid_hospitalisations_time_series = %s
                    WHERE iso_alpha3 = %s""", (int(hospitalisations_time_series[-1]["count"]),
                                               json.dumps(hospitalisations_time_series),
                                               iso_code))

        conn.commit()
        cur.close()
        return None

    except psycopg2.DatabaseError:
        print(f"EXCEPTION\n{traceback.format_exc()}")

    except:
        print(f"EXCEPTION\n{traceback.format_exc()}")

    finally:
        if conn is not None:
            conn.close()

    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return None

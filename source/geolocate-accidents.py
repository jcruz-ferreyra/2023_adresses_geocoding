import logging
import os
import re
import sys
import webbrowser
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import pyinputplus as pyip
from arcgis.geocoding import geocode
from arcgis.gis import GIS
from dotenv import load_dotenv
from opencage.geocoder import OpenCageGeocode


def city_filler(df, city, fill, ids_list):
    """
    This function completes the addresses queries with information about city, prov, country
    of observations with any hint about that (except for observations located in Rosario)

    :df: Original dataframe with an address column.
    :city: Some kind of pattern or string referring to a city of Gran Rosario.
    :fill: Desired name of the corresponding city.

    :return: Dataframe with new information in the address column + IDs of corrected observations.
    """
    mask = df.apply(lambda r: bool(re.search(city, r["direccion_avp"])), axis=1)
    df.loc[mask, "direccion_avp"] = (
        df.loc[mask, "direccion_avp"]
        .str.replace("-", "")
        .str.replace(city, "")
        .str.strip()
    ) + f", {fill}, Santa Fe, Argentina"

    ids_no_rosario = df.loc[mask, "id"].tolist()

    ids_list = ids_list + ids_no_rosario

    return df, ids_list


def map_plotter(df, ids_wrong):
    """
    This function plots every observation in passed dataframe into a Folium Map (interactive).
    It prints in green every observation except for those that the user marks as wrongly geocoded.

    :df: Dataframe with Latitude and Longitude column.
    :ids_wrong: List of IDs of wrongly geocoded addresses.

    :return: Folium Map (interactive).
    """
    rosario_coords = [-32.940506, -60.712480]

    # Create the map
    map_geo = folium.Map(location=rosario_coords, zoom_start=12)

    for index, row in df.iterrows():
        popup = row["id"] + ": " + row["direccion_orig"]

        if not row["id"] in (ids_wrong):
            color = "green"
        elif row["id"] in (ids_wrong):
            color = "red"
        try:
            folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=popup,
                icon=folium.Icon(color=color, icon_color="white"),
            ).add_to(map_geo)
        except Exception as e:
            exception_text = f"Problema encontrado con {row['id']}"
            raise Exception(exception_text)

    return map_geo


def ids_validator(id):
    """
    This function checks format of ID inputted by the user.

    :id: String ID to check.

    :return: Raise Exception or pass.
    """
    if id == "t":
        return
    elif len(id) != len_id:
        raise Exception(f"El id ingresado debe tener {len_id} caracteres numéricos")
    try:
        int(id)
    except Exception as e:
        raise Exception("El id ingresado debe tener solo caracteres numéricos")

    return


def ids_adder(list_ok, list_wrong):
    """
    This function ask the user to enter IDs of wrongly geocoded observations.

    :list_ok: List of IDs present in plotted dataframe.
    :list_wrong: List of wrongly geocoded observation's IDs into which append new ones.

    :return: List of wrongly geocoded observation's Ids with new ones.
    """
    response = ""

    while response != "t":
        print(
            "Ingrese un ID para agregar a las direcciones erroneamente geocodificadas ('t' para terminar): "
        )
        response = pyip.inputCustom(ids_validator)
        if response == "t":
            break
        if response not in list_ok:
            print(
                "ID no presente entre las direcciones geocodificadas. Intente nuevamente. \n"
            )
            continue
        elif response in list_ok:
            if not response in list_wrong:
                list_wrong.append(response)
            print("ID aceptado \n")

    return list_wrong


def ids_remover(list_wrong):
    """
    This function ask the user to enter IDs of rightly geocoded observations present in wrong ones list.

    :list_wrong: List of wrongly geocoded observation's IDs from which remove some.

    :return: List of wrongly geocoded observation's Ids without removed ones.
    """
    response = ""

    while response != "t":
        print(
            "Ingrese un ID a eliminar de las direcciones erroneamente geocodificadas ('t' para terminar): "
        )
        response = pyip.inputCustom(ids_validator)
        if response == "t":
            break
        if response not in list_wrong:
            print(
                "ID no presente entre las direcciones erroneamente geocodificadas. Intente nuevamente.\n"
            )
            continue
        elif response in list_wrong:

            list_wrong.remove(response)
            print("ID aceptado \n")

    return list_wrong


def geo_checker(df, list_right, list_wrong):
    """
    This function provides some options to add or remove IDs to/from
    the list of wrongly geocoded observation's IDs.
    It acts as some kind of organizer of the three main functions to complete the task:
        - map_plotter()
        - ids_adder()
        - ids_remover()
    It displays interactive maps in the browser so that user can check if addresses were
    rightly geocoded.

    :df: Dataframe with geocoded observations with Latitude and Longitude columns.
    :list_right: List of IDs present in the geocoded dataframe.
    :list_wrong: List into which add or remove wrongly geocoded observation's IDs.

    :return: List of wrongly geocoded observations Ids.
    """
    output_file = main_path / "graphs/map_geo.html"

    map_geo = map_plotter(df, list_wrong)
    map_geo.save(output_file)
    webbrowser.open(output_file, new=1)

    list_wrong = ids_adder(list_right, list_wrong)

    while True:
        map_geo = map_plotter(df, list_wrong)
        map_geo.save(output_file)
        webbrowser.open(output_file, new=1)

        response = pyip.inputYesNo(
            prompt="¿Desea confirmar los cambios y continuar? ('si/no') \n",
            yesVal="si",
            noVal="no",
        )

        if response == "si":
            print("Cambios confirmados. \n")
            print()
            break
        elif response == "no":
            response = pyip.inputMenu(
                [
                    "Agregar a las observaciones erroneamente geocodificadas un nuevo ID.",
                    "Eliminar de las observaciones erroneamente geocodificadas un ID.",
                    "Confirmar los cambios y continuar.",
                ],
                prompt="¿Qué modificaciones desea realizar? \n",
                lettered=True,
            )

            print()

            if (
                response
                == "Agregar a las observaciones erroneamente geocodificadas un nuevo ID."
            ):
                list_wrong = ids_adder(list_right, list_wrong)
                continue
            elif (
                response
                == "Eliminar de las observaciones erroneamente geocodificadas un ID."
            ):
                list_wrong = ids_remover(list_wrong)
            elif response == "Confirmar los cambios y continuar.":
                break

    return list_wrong


def oc_geocoder(geocoder, x):
    """
    This function geocodes observations and get Latitude and Longitude information with OpenCage service.
    """
    results = geocoder.geocode(x)
    lat = results[0]["geometry"]["lat"]
    lon = results[0]["geometry"]["lng"]
    return lat, lon


def esri_geocoder(x):
    """
    This function geocodes observations and get Latitude and Longitude information with ESRI service.
    """
    results = geocode(x)
    lat = str(results[0]["location"]["y"])
    lon = str(results[0]["location"]["x"])
    return lat, lon


# --- SET ENVIRONMENT ---
# Get environment variables
load_dotenv()
oc_apikey = os.getenv("OC_APIKEY")
esri_apikey = os.getenv("ESRI_APIKEY")
esri_user = os.getenv("ESRI_USER")
esri_pass = os.getenv("ESRI_PASS")

# Avoid Pandas's warnings
pd.options.mode.chained_assignment = None

# Ask for starting variables
while True:
    anio = input("Ingresa el año de los datos a geocodificar (aaaa):")
    if len(anio) != 4:
        print(f"El año ingresado debe tener 4 caracteres numéricos")
        continue
    try:
        int(anio)
    except Exception as e:
        print("El año ingresado debe tener solo caracteres numéricos")
        continue
    break

while True:
    mes = input("Ingresa el mes de los datos a geocodificar (aa):")
    if len(mes) != 2:
        print(f"El mes ingresado debe tener 2 caracteres numéricos")
        continue
    try:
        int(mes)
    except Exception as e:
        print("El año ingresado debe tener solo caracteres numéricos")
        continue
    break

# Set starting variables
os.chdir(sys.path[0])

main_path = Path.cwd() / "../"
orig_filename = f"Avp {mes} del {anio} con género.xlsx"
dest_filename = f"{anio}-{mes}_AVP-geocoded.xlsx"
log_filename = f"{anio}-{mes}_AVP-geocoded.log"

orig_path = main_path / "data/raw"
dest_path = main_path / f"results/{anio}"
log_path = main_path / f"logs/{anio}"

# Read main dataframe
try:
    df = pd.read_excel(orig_path / orig_filename)
except Exception as e:
    print("Archivo no encontrado.")
    print(f"Búsqueda de: {orig_filename}")
    print(f"Búsqueda en: {orig_path}")
    print()
    sys.exit(1)

# Create destination folders
if not os.path.isdir(dest_path):
    os.makedirs(dest_path)
if not os.path.isdir(log_path):
    os.makedirs(log_path)

# Set up configuration for logging to a file and to the console
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s", "%Y-%m-%d")

file_handler = logging.FileHandler(log_path / log_filename)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)


# --- TRANSFORM DATASET ---
# Format column names
dict_rename = {
    "Fecha de ingreso": "fecha_ingreso",
    "hora de ingreso": "hora_ingreso",
    "fecha del AVP": "fecha_avp",
    "hora del AVP": "hora_avp",
    "categoria horaria": "hora_avp_cat",
    "lugar del AVP": "direccion_avp",
}

df.rename(columns=dict_rename, inplace=True)

# Create unique ID for each row
n_rows = len(df.index)
n_digits = len(str(n_rows))

df["id"] = df["fecha_ingreso"].astype(str).str.replace("-", "") + df["id"].astype(
    str
).str.zfill(n_digits)

len_id = len(df.loc[0, "id"])

# Format addresses columns
df["direccion_avp"] = df["direccion_avp"].str.lower()

df["direccion_orig"] = df["direccion_avp"]

# Create column for Latitude and Longitude
df.insert(len(df.columns), "lat", np.NaN)
df.insert(len(df.columns), "lon", np.NaN)

# Separate null values for adress into a new dataframe
mask = df["direccion_orig"].isnull()
df_geo_na = df.loc[mask, :]
df1 = df.loc[~mask, :]

# Format queries, adding city of location as suffix and changing some streets names
ids_rosario_no = []
dict_cities = {
    "vgg": "Villa Gobernador Galvez",
    "luis palacios": "Luis Palacios",
    "casilda": "Casilda",
    "funes": "Funes",
    "roldan": "Roldan",
    "soldini": "Soldini",
}

for k, v in dict_cities.items():
    df1, ids_rosario_no = city_filler(df1, k, v, ids_rosario_no)

df1["direccion_avp"] = df1["direccion_avp"].str.replace("ref ", "")

df1["direccion_avp"] = df1["direccion_avp"].str.replace("/", " y ")

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"circun\w*\s?", "Avenida de Circunvalación 25 de Mayo ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(av\w*\s)?27 de feb\w*\s?", "Bulevar 27 de Febrero ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(bulevar\w*\s)?(bv)?(av\w*\s)?oroño\s?",
    "Bulevar Nicasio Oroño ",
    regex=True,
    case=False,
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(bulevar\w*\s)?(bv)?(av\w*\s)?rond\w*\s?",
    "Bulevar General José Rondeau ",
    regex=True,
    case=False,
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(av\w*\s)?uriburu\s?", "Avenida José Uriburu ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(av\w*\s)?san mart\w*\s?", "Avenida José de San Martín ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(ovidio\s)?lagos\s?", "Avenida Ovidio Lagos ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(av\w*\s)?pel(l)?egrini\s?", "Avenida Carlos Pellegrini ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(av\w*\s)?francia\s?", "Avenida Francia ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"(av\w*\s)?godoy\s?", "Avenida Presidente Perón ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"colectora\s?", "Colectora Juan Pablo II ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"a(0)?(o)?(\s)?12", "Ruta Nacional A012 ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"b(\w*)?\s*(y)?\s*ordoñez", "Avenida Battle y Ordoñez ", regex=True, case=False
)

df1["direccion_avp"] = df1["direccion_avp"].str.replace(
    r"\s+", " ", regex=True, case=False
)

mask = ~df1["id"].isin(ids_rosario_no)
df1.loc[mask, "direccion_avp"] = (
    df1.loc[mask, "direccion_avp"].str.strip() + ", Rosario, Santa Fe, Argentina"
)


# --- Geocode addresses with OpenCage ---
# Get adresses to geocode as a list (discard intersections for OpenCage)
mask = df1.apply(lambda r: bool(re.search(" y ", r["direccion_avp"])), axis=1)
df_geo_oc = df1.loc[~mask, :]

list_addresses_oc = df_geo_oc["direccion_avp"].tolist()

# Set geocoder object using the corresponding apikey
geocoder = OpenCageGeocode(oc_apikey)

# Geocode list of addresses and add Latitude and Longitude to the dataframe
list_oc = []
list_oc_lat = []
list_oc_lon = []

print("- Comienzo de la geocodificación con el servicio OpenCage -")
for address in list_addresses_oc:
    lat = lon = np.NaN
    try:
        lat, lon = oc_geocoder(geocoder, address)
    except Exception as e:
        print("No se pudo geolocalizar la dirección: " + address)
        print(e)
    list_oc_lat.append(lat)
    list_oc_lon.append(lon)

df_geo_oc["lat"] = list_oc_lat
df_geo_oc["lon"] = list_oc_lon

# Discard observations with generic coords or null coords (worongly geocoded addresses)
mask = (df_geo_oc["lat"] == -32.946820) | (df_geo_oc["lon"] == -60.63932)
df_geo_oc.loc[mask, "lat"] = np.NaN
df_geo_oc.loc[mask, "lon"] = np.NaN

mask = ~((df_geo_oc["lat"].isnull()) | (df_geo_oc["lon"].isnull()))
df_geo_oc = df_geo_oc.loc[mask, :]

# Check interactively for wrongly geocoded adresses
ids_geo_oc = df_geo_oc.loc[:, "id"].tolist()
ids_geo_oc_wrong = []

ids_geo_oc_wrong = geo_checker(
    df=df_geo_oc, list_right=ids_geo_oc, list_wrong=ids_geo_oc_wrong
)

# Keep just correctly geocoded addresses
mask = ~df_geo_oc["id"].isin(ids_geo_oc_wrong)
df_geo_oc = df_geo_oc.loc[mask, :]


# --- Geocode remaining adresses with Esri ---
# Get adresses to geocode as a list
mask = ~df1["id"].isin(ids_geo_oc_wrong)
df_geo_esri = df1.loc[mask, :]

list_addresses_esri = df_geo_esri["direccion_avp"].tolist()

# Set gis object using the corresponding user, password, apikey
gis = GIS(username=esri_user, password=esri_pass, api_key=esri_apikey)

# Geocode list of addresses and add Latitude and Longitude to the dataframe
list_esri = []
list_esri_lat = []
list_esri_lon = []

print("- Comienzo de la geocodificación con el servicio ESRI de ArcGis -")
for address in list_addresses_esri:
    lat = lon = np.NaN
    try:
        lat, lon = esri_geocoder(address)
    except Exception as e:
        print("Can not geocode address: " + address)
        print(e)
    list_esri_lat.append(lat)
    list_esri_lon.append(lon)

df_geo_esri.loc[:, "lat"] = list_esri_lat
df_geo_esri.loc[:, "lon"] = list_esri_lon

# Discard observations with null coords and add them to the original null list
mask = ~((df_geo_esri["lat"].isnull()) | (df_geo_esri["lon"].isnull()))
df_geo_na = pd.concat([df_geo_na, df_geo_esri.loc[~mask, :]], axis=0)
df_geo_esri = df_geo_esri.loc[mask, :]

# Check interactively for wrongly geocoded adresses
ids_geo_esri = df_geo_esri.loc[:, "id"].tolist()
ids_geo_esri_wrong = []

ids_geo_esri_wrong = geo_checker(
    df=df_geo_esri, list_right=ids_geo_esri, list_wrong=ids_geo_esri_wrong
)

# Set Latitude and Longitude to null value for wrongly geocoded observations
mask = df_geo_esri["id"].isin(ids_geo_esri_wrong)
df_geo_esri.loc[mask, "lat"] = np.NaN
df_geo_esri.loc[mask, "lon"] = np.NaN


# --- Save concatenation of the three dataframes: OpenCage, Esri and not geocoded ---
df_list = [df_geo_na, df_geo_oc, df_geo_esri]

df_total = pd.concat(df_list, axis=0)

try:
    assert df.shape[0] == df_total.shape[0]
except:
    pass

while True:
    try:
        df_total.to_excel(dest_path / dest_filename, index=False)
        print("- Archivo guardado correctamente")
        break
    except Exception as e:
        print(e)
    input("Press enter to try again")

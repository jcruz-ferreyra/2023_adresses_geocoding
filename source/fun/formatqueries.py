import pandas as pd
import re

def queries_formatter(df):
    """
    This function completes the addresses queries with information about city, prov, country

    :df: Original dataframe with an address column.

    :return: Dataframe with new information in the address column.
    """
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

    # Format queries, adding city of location as suffix and changing some streets names
    dict_cities = {
        "vgg": "Villa Gobernador Galvez",
        "luis palacios": "Luis Palacios",
        "casilda": "Casilda",
        "funes": "Funes",
        "roldan": "Roldan",
        "soldini": "Soldini",
    }

    # Add city info for adresses not located in Rosario
    ids_rosario_no = []
    for k, v in dict_cities.items():
        df, ids_rosario_no = city_filler(df, k, v, ids_rosario_no)

    df["direccion_avp"] = df["direccion_avp"].str.replace("ref ", "")

    df["direccion_avp"] = df["direccion_avp"].str.replace("/", " y ")

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"circun\w*\s?", "Avenida de Circunvalación 25 de Mayo ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(av\w*\s)?27 de feb\w*\s?", "Bulevar 27 de Febrero ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(bulevar\w*\s)?(bv)?(av\w*\s)?oroño\s?",
        "Bulevar Nicasio Oroño ",
        regex=True,
        case=False,
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(bulevar\w*\s)?(bv)?(av\w*\s)?rond\w*\s?",
        "Bulevar General José Rondeau ",
        regex=True,
        case=False,
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(av\w*\s)?uriburu\s?", "Avenida José Uriburu ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(av\w*\s)?san mart\w*\s?", "Avenida José de San Martín ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(ovidio\s)?lagos\s?", "Avenida Ovidio Lagos ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(av\w*\s)?pel(l)?egrini\s?", "Avenida Carlos Pellegrini ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(av\w*\s)?francia\s?", "Avenida Francia ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"(av\w*\s)?godoy\s?", "Avenida Presidente Perón ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"colectora\s?", "Colectora Juan Pablo II ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"a(0)?(o)?(\s)?12", "Ruta Nacional A012 ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"b(\w*)?\s*(y)?\s*ordoñez", "Avenida Battle y Ordoñez ", regex=True, case=False
    )

    df["direccion_avp"] = df["direccion_avp"].str.replace(
        r"\s+", " ", regex=True, case=False
    )

    # Add city info for adresses located in Rosario
    mask = ~df["id"].isin(ids_rosario_no)
    df.loc[mask, "direccion_avp"] = (
        df.loc[mask, "direccion_avp"].str.strip() + ", Rosario, Santa Fe, Argentina"
    )
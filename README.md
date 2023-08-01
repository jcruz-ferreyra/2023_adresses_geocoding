# 2023_adresses_geocoding

Project created to geocode adresses in the metropolitan area of the city of Rosario. It can be easily adapted for any city.

The project works with a dataframe containing the adresses. Using regex to detect the city it formats the queries,
if no cities other than Rosario are found it completes the query using the information of the main city.

The geocoding process is done using two open services: OpenCage and Esri. Notably, the Opencage service provides better results
when geocoding places (ej 'monumento a la bandera') and Esri performs better for adresses + numbers (ej 'calle moreno 758').

After each of the geocoding processes a leaflet map is opened in the browser to manually check possible mistakes before the next
step. By passing the id of wrongly geocoded adresses, the script tries to geocode it in the next step or leave it blank to be filled
directly in the resulting .xlsx file.

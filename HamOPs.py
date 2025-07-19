#!/home/cem/py/hamRadioDashboard/.venv/bin/python
# -*- coding: utf-8 -*-
import requests
import time
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import skyfield # Obwohl skyfield importiert ist, wird es hier nicht verwendet. Das ist kein Fehler, aber eine Anmerkung.
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk 
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime, timezone
from tkinter import messagebox
import json
import pytz

# GPS kordinanten fallback
my_qth_la = 39.924986 # Breitengrad La
my_qth_lo = 32.836895 # Längengrad Lo
my_qth_el = 907 # höchenangebe 
timeZone = "Europe/Istanbul"

settings ={}
SETTINGS_FILE = "settings.json"

SolarDataURL = "https://www.hamqsl.com/solarxml.php" # für API
SolarPicURL = "https://services.swpc.noaa.gov/images/animations/suvi/primary/195/latest.png"
OpenMeteoURL = "https://api.open-meteo.com/v1/forecast" # für API
LocalWebcamURL = "https://www.fernsehturm-stuttgart.de/webcam/current.jpg" # für API


# APIs
# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)


def get_and_update_data():
    """
    Diese Funktion ruft alle Daten von den APIs ab
    und aktualisiert die globalen Variablen, die dann in den Labels angezeigt werden.
    """
    # Deklariere alle Variablen, die du in dieser Funktion änderst und global nutzen willst
    global current_rain, current_showers, current_snowfall, current_apparent_temperature, \
           current_wind_direction_10m, current_wind_speed_10m, current_relative_humidity_2m, \
           current_temperature_2m, current_precipitation, current_pressure_msl
    
    global updated, solarflux, aindex, kindex, xray, protonflux, electonflux, \
           aurora, sunspots, heliumline, solarwind, magneticfield


    params = { # parameter für OpenMeteo 
	    "latitude": my_qth_la,
	    "longitude": my_qth_lo,
	    "hourly": "temperature_2m",
	    "current": ["rain", "showers", "snowfall", "apparent_temperature", "wind_direction_10m", "wind_speed_10m", "relative_humidity_2m", "temperature_2m", "precipitation", "pressure_msl"],
    	"timezone": "Europe/Berlin",
	    "forecast_days": 1
}

    try:
        responses = openmeteo.weather_api(OpenMeteoURL, params=params) # daten abrufen von OpenMeteo
        response = responses[0]

        # abgerufene daten von OpenMeteo variablen zuweisen 
        current = response.Current()
        current_rain = current.Variables(0).Value()
        current_showers = current.Variables(1).Value()
        current_snowfall = current.Variables(2).Value()
        current_apparent_temperature = current.Variables(3).Value()
        current_wind_direction_10m = current.Variables(4).Value()
        current_wind_speed_10m = current.Variables(5).Value()
        current_relative_humidity_2m = current.Variables(6).Value()
        current_temperature_2m = current.Variables(7).Value()
        current_precipitation = current.Variables(8).Value()
        current_pressure_msl = current.Variables(9).Value()
    except Exception as e:
        print(f"Fehler beim Abrufen der Open-Meteo Daten: {e}")  # Setze Platzhalterwerte, falls ein Fehler auftritt
        current_rain = current_showers = current_snowfall = current_apparent_temperature = \
        current_wind_direction_10m = current_wind_speed_10m = current_relative_humidity_2m = \
        current_temperature_2m = current_precipitation = current_pressure_msl = "N/A"


    try: # greife mit API daten von hamqsl.com ab 
        response = requests.get(SolarDataURL)
        response.raise_for_status() 
        SolarData = ET.fromstring(response.text) # parse die xml

        # abgerufene daten von hamqsl.com variablen zuweisen 
        solardata_inner_element = SolarData.find('solardata') # geht in die solardaten rubrck in der xml (siehe struktur der xml) und extrhiert die gewünschten daten
        updated = solardata_inner_element.find('updated').text.strip() # 
        solarflux = solardata_inner_element.find('solarflux').text.strip()
        aindex = solardata_inner_element.find('aindex').text.strip()
        kindex = solardata_inner_element.find('kindex').text.strip()
        xray = solardata_inner_element.find('xray').text.strip()
        protonflux = solardata_inner_element.find('protonflux').text.strip()
        electonflux = solardata_inner_element.find('electonflux').text.strip()
        aurora = solardata_inner_element.find('aurora').text.strip()
        sunspots = solardata_inner_element.find('sunspots').text.strip()
        heliumline = solardata_inner_element.find('heliumline').text.strip()
        solarwind = solardata_inner_element.find('solarwind').text.strip()
        magneticfield = solardata_inner_element.find('magneticfield').text.strip()

    except requests.exceptions.RequestException as err: 
        print(f"Fehler beim Abrufen der HamQSL Daten: {err}")
        updated = solarflux = aindex = kindex = xray = protonflux = electonflux = \
        aurora = sunspots = heliumline = solarwind = magneticfield = "N/A"
    except ET.ParseError as err:
        print(f"XML-Parsing-Fehler bei HamQSL Daten: {err}")
        updated = solarflux = aindex = kindex = xray = protonflux = electonflux = \
        aurora = sunspots = heliumline = solarwind = magneticfield = "N/A"
    except Exception as err:
        print(f"Ein unerwarteter Fehler bei HamQSL Daten ist aufgetreten: {err}")
        updated = solarflux = aindex = kindex = xray = protonflux = electonflux = \
        aurora = sunspots = heliumline = solarwind = magneticfield = "N/A"

def load_image_from_url(url, width=None, height=None): # Stuttgart Webcam bild
    global tk_webcam_image
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        image_data = BytesIO(response.content)
        pil_image = Image.open(image_data)

    
        if width is None and height is None:
           width = 400  # definiert bildgröße

        if width and height:
            pil_image = pil_image.resize((width, height), Image.LANCZOS)
        elif width:
            aspect_ratio = pil_image.height / pil_image.width
            new_height = int(width * aspect_ratio)
            pil_image = pil_image.resize((width, new_height), Image.LANCZOS)
        elif height:
            aspect_ratio = pil_image.width / pil_image.height
            new_width = int(height * aspect_ratio)
            pil_image = pil_image.resize((new_width, height), Image.LANCZOS)

        tk_webcam_image = ImageTk.PhotoImage(pil_image)
        return tk_webcam_image

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Herunterladen des Bildes von {url}: {e}")
        return None
    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bildes: {e}")
        return None

def update_webcam_image():
    """
    Diese Funktion lädt das Webcam-Bild neu und aktualisiert das Label.
    """
    img = load_image_from_url(LocalWebcamURL) # Lade das Bild
    if img:
        webcam_label.config(image=img) # Weise das Bild dem Label zu
        webcam_label.image = img # Wichtig: Referenz im Label selbst speichern

    root.after(300000, update_webcam_image) # Aktualisiert alle 5 Minuten (300000 ms)


def load_SolarImage_from_url(url, width=None, height=None): # Solar
    global tk_solar_image
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        image_data = BytesIO(response.content)
        pil_image = Image.open(image_data)

    
        if width is None and height is None:
           width = 400  # definiert bildgröße

        if width and height:
            pil_image = pil_image.resize((width, height), Image.LANCZOS)
        elif width:
            aspect_ratio = pil_image.height / pil_image.width
            new_height = int(width * aspect_ratio)
            pil_image = pil_image.resize((width, new_height), Image.LANCZOS)
        elif height:
            aspect_ratio = pil_image.width / pil_image.height
            new_width = int(height * aspect_ratio)
            pil_image = pil_image.resize((new_width, height), Image.LANCZOS)

        tk_solar_image = ImageTk.PhotoImage(pil_image)
        return tk_solar_image

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Herunterladen des Bildes von {url}: {e}")
        return None
    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bildes: {e}")
        return None

def update_solar_image():
    """
    Diese Funktion lädt das Webcam-Bild neu und aktualisiert das Label.
    """
    img = load_SolarImage_from_url(SolarPicURL) # Lade das Bild
    if img:
        solarimage_label.config(image=img) # Weise das Bild dem Label zu
        solarimage_label.image = img # Wichtig: Referenz im Label selbst speichern

    root.after(300000, update_solar_image) # Aktualisiert alle 5 Minuten (300000 ms)
  
def toggle_fullscreen():
    # Prüfen, ob das Fenster aktuell im Vollbildmodus ist
    # root.attributes('-fullscreen') gibt True/False zurück
    is_fullscreen = root.attributes('-fullscreen')
    # Den Vollbildmodus umschalten
    root.attributes('-fullscreen', not is_fullscreen)

def update_utc_time():
    """
    Diese Funktion aktualisiert nur die UTC-Uhrzeit jede Sekunde.
    """
    global utc_time_label # Muss hier global deklariert werden

    current_utc_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    utc_time_label.config(text=f"UTC-Time: {current_utc_time}")
    # Ruft sich selbst nach 1000 ms (1 Sekunde) erneut auf
    root.after(1000, update_utc_time)

def update_dashboard():
    """
    Diese Funktion ruft die neuesten Daten ab und aktualisiert die Labels im Tkinter-Fenster.
    """
    get_and_update_data() # Ruft die Daten ab
    update_webcam_image() # Ladet Webcam bild neu

    # Aktualisiere deine Labels hier
    # Achte darauf, dass 'wetter_label' und 'solar_label' zu diesem Zeitpunkt schon existieren
    wetter_label.config(text=f"Temperature: {round(current_temperature_2m)}°C\n"
                              f"Perceived temperature: {round(current_apparent_temperature)}°C\n"
                              f"Wind: {round(current_wind_speed_10m)} m/s aus {current_wind_direction_10m}°\n"
                              f"Humidity: {current_relative_humidity_2m}%\n"
                              f"Precipitation: {current_precipitation}mm\n"
                              f"Pressure: {current_pressure_msl} hPa\n"
                              f"Rain: {round(current_rain)}mm\n"
                              f"Showers: {current_showers}mm\n"
                              f"Snowfall: {current_snowfall}cm")

    solar_label.config(text=f"Solarflux: {solarflux}\n"
                            f"A-Index: {aindex}, K-Index: {kindex}\n"
                            f"X-Ray: {xray}\n"
                            f"Protonenflux: {protonflux}\n"
                            f"Electronflux: {electonflux}\n"
                            f"Aurora: {aurora}\n"
                            f"Sunspots: {sunspots}\n"
                            f"Heliumline: {heliumline}\n"
                            f"Solarwind: {solarwind}\n"
                            f"Magneticfield: {magneticfield}")

    root.after(300000, update_dashboard) # Aktualisiert alle 5 Minuten (300000 ms)

def save_settings():
    global my_qth_la, my_qth_lo, my_qth_el, LocalWebcamURL, settings
    settings['my_qth_la'] = my_qth_la
    settings['my_qth_lo'] = my_qth_lo
    settings['my_qth_el'] = my_qth_el
    settings['LocalWebcamURL'] = LocalWebcamURL
    settings['timeZone'] = timeZone
    try:
        with open(SETTINGS_FILE, 'w') as f: # offnet die datei im schreibmodus 
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error: {e}")

def load_settings():
    global my_qth_la, my_qth_lo, my_qth_el, settings, LocalWebcamURL
    try:
        with open(SETTINGS_FILE, 'r') as f:
            loaded_settings = json.load(f) # Lese den JSON-Inhalt und konvertiere ihn in ein Python-Dictionary
        if 'my_qth_la' in loaded_settings:
            my_qth_la = loaded_settings['my_qth_la']
        if 'my_qth_lo' in loaded_settings:
            my_qth_lo = loaded_settings['my_qth_lo']
        if 'my_qth_el' in loaded_settings:
            my_qth_el = loaded_settings['my_qth_el']
        if 'LocalWebcamURL' in loaded_settings:
            LocalWebcamURL = loaded_settings['LocalWebcamURL']
        if 'timeZone' in loaded_settings:
            timeZone = load_settings['timeZone']

        settings.update(loaded_settings)
    except FileNotFoundError:
        print("Einstellungsdatei nicht gefunden. Verwende Standardwerte.")
        # Wenn die Datei nicht existiert, setze die aktuellen globalen Werte (deine Standardwerte)
        # in das 'settings'-Dictionary, damit sie beim ersten Speichern geschrieben werden.
        settings['my_qth_la'] = my_qth_la
        settings['my_qth_lo'] = my_qth_lo
        settings['my_qth_el'] = my_qth_el
        settings['LocalWebcamURL'] = LocalWebcamURL
        settings['timeZone'] = timeZone
    except json.JSONDecodeError:
        print("Fehler beim Lesen der Einstellungsdatei. Datei beschädigt?")
        # Fallback zu Standardwerten, wenn JSON fehlerhaft ist
        settings['my_qth_la'] = my_qth_la
        settings['my_qth_lo'] = my_qth_lo
        settings['my_qth_el'] = my_qth_el
        settings['LocalWebcamURL'] = LocalWebcamURL
        settings['timeZone'] = timeZone
    except Exception as e:
        print(f"Unerwarteter Fehler beim Laden der Einstellungen: {e}")
        # Fallback zu Standardwerten bei anderen Fehlern
        settings['my_qth_la'] = my_qth_la
        settings['my_qth_lo'] = my_qth_lo
        settings['my_qth_el'] = my_qth_el
        settings['LocalWebcamURL'] = LocalWebcamURL
        settings['timeZone'] = timeZone

def open_settings_window(): # settings window
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("550x480")
    settings_window.transient(root)
    settings_window.grab_set()
    settings_window.focus_set()

    # Eingabe für die Längengrad
    ttk.Label(settings_window, text="Longitude:").pack(pady=5)
    lo_entry = ttk.Entry(settings_window, width=25)
    lo_entry.insert(0,str(my_qth_lo))
    lo_entry.pack()

    # Eingabe für den Breitengrad
    ttk.Label(settings_window, text="Latitude:").pack(pady=5)
    la_entry = ttk.Entry(settings_window,width=25)
    la_entry.insert(0,str(my_qth_la))
    la_entry.pack()

    # Eingabe für den höche
    ttk.Label(settings_window, text="elevation above sea level in meters :").pack(pady=5)
    el_entry = ttk.Entry(settings_window,width=25)
    el_entry.insert(0,str(my_qth_el))
    el_entry.pack()

    # eingabe von timezone 
    ttk.Label(settings_window, text="Time Zone:").pack(pady=5)
    all_timezones = sorted(pytz.all_timezones)
    timezone_combobox = ttk.Combobox(settings_window, values=all_timezones, width=45)
    if timeZone in all_timezones:
        timezone_combobox.set(timeZone)
    else:
        timezone_combobox.set("Europe/Berlin") # Fallback, falls die geladene Zeitzone nicht in der Liste ist
    timezone_combobox.pack(pady=5)

    ttk.Label(settings_window, text="Link to Local Webcam:").pack(pady=5)
    local_webcam_entry = ttk.Entry(settings_window,width=50)
    local_webcam_entry.insert(0,str(LocalWebcamURL))
    local_webcam_entry.pack()

    def apply_and_close(): # liest die eingegebenen wehrte ein und wendet sie in zahlen (float) um.
        try:
            new_la = float(la_entry.get())
            new_lo = float(lo_entry.get())
            new_el = float(el_entry.get())
            new_webcam_url = local_webcam_entry.get()
            new_timeZone = timezone_combobox.get()

            global my_qth_la, my_qth_lo, my_qth_el, LocalWebcamURL, timeZone
            my_qth_la = new_la
            my_qth_lo = new_lo 
            my_qth_el = new_el
            LocalWebcamURL = new_webcam_url
            timeZone = new_timeZone

            save_settings()
            update_dashboard()
            messagebox.showinfo("Massage", " Saved !" )

        except ValueError:
            # Korrektur der Anführungszeichen im Fehlermeldungstext
            messagebox.showerror("Fehler", "Ungültige Eingabe. Bitte geben Sie gültige Zahlen für die Koordinaten ein.")
        finally:
            settings_window.destroy()

    button_frame = ttk.Frame(settings_window)
    button_frame.pack(pady=15)
    ttk.Button(button_frame, text="Save", command=apply_and_close).pack(side=tk.LEFT, padx=10)
    ttk.Button(button_frame, text="abort", command=settings_window.destroy).pack(side=tk.RIGHT, pady=10)
    root.wait_window(settings_window)

def load_settings():
    """Lädt Einstellungen aus der JSON-Datei."""
    global my_qth_la, my_qth_lo, my_qth_el, settings, LocalWebcamURL, timeZone
    try:
        with open(SETTINGS_FILE, 'r') as f: # Öffne die Datei im Lesemodus ('r')
            loaded_settings = json.load(f) # Lese den JSON-Inhalt und konvertiere ihn in ein Python-Dictionary

        # Aktualisiere die globalen Variablen, falls sie in den geladenen Einstellungen vorhanden sind
        if 'my_qth_la' in loaded_settings:
            my_qth_la = loaded_settings['my_qth_la']
        if 'my_qth_lo' in loaded_settings:
            my_qth_lo = loaded_settings['my_qth_lo']
        if 'my_qth_el' in loaded_settings:
            my_qth_el = loaded_settings['my_qth_el']
        if 'LocalWebcamURL' in loaded_settings:
            LocalWebcamURL = loaded_settings['LocalWebcamURL']
        if 'timeZone' in loaded_settings:
            timeZone = loaded_settings['timeZone']

        # Speichere die geladenen Einstellungen auch im 'settings'-Dictionary
        settings.update(loaded_settings)
    except FileNotFoundError:
        print("Einstellungsdatei nicht gefunden. Verwende Standardwerte.")
        # Wenn die Datei nicht existiert, setze die aktuellen globalen Werte (deine Standardwerte)
        # in das 'settings'-Dictionary, damit sie beim ersten Speichern geschrieben werden.
        settings['my_qth_la'] = my_qth_la
        settings['my_qth_lo'] = my_qth_lo
        settings['my_qth_el'] = my_qth_el
        settings['LocalWebcamURL'] = LocalWebcamURL
        settings['timeZone'] = timeZone
    except json.JSONDecodeError:
        print("Fehler beim Lesen der Einstellungsdatei. Datei beschädigt?")
        # Fallback zu Standardwerten, wenn JSON fehlerhaft ist
        settings['my_qth_la'] = my_qth_la
        settings['my_qth_lo'] = my_qth_lo
        settings['my_qth_el'] = my_qth_el
        settings['LocalWebcamURL'] = LocalWebcamURL
        settings['timeZone'] = timeZone
    except Exception as e:
        print(f"Unerwarteter Fehler beim Laden der Einstellungen: {e}")
        # Fallback zu Standardwerten bei anderen Fehlern
        settings['my_qth_la'] = my_qth_la
        settings['my_qth_lo'] = my_qth_lo
        settings['my_qth_el'] = my_qth_el
        settings['LocalWebcamURL'] = LocalWebcamURL
        settings['timeZone'] = timeZone
     

def open_about_window(): # about window
    about_window = tk.Toplevel(root)
    about_window.title("About")
    about_window.geometry("400x800")

    about_window.transient(root)
    about_window.grab_set()
    about_window.focus_set()

    icon_label = ttk.Label(about_window, image=icon_image)
    icon_label.pack(pady=(50,10))
    

    about_text = """
HamOPs
Version v0.1.0

A dashboard for amateur radio operators displaying
relevant weather and space weather data for radio operations.

Developed by: Cem Dülger

---
Services Used:
- Weather Data: Open-Meteo API
- Solar Data: HamQSL.com

---
Released under the MIT License.
(Icons used from Lucide under ISC License)

Contact: duelger.cem@gmail.com

© 2024 Cem Dülger
"""

    about_label = ttk.Label(about_window, text=about_text, justify="left", wraplength=380)
    about_label.pack(padx=10, pady=10)
    ttk.Button(about_window, text="close", command=about_window.destroy).pack(pady=10)


# Hauptfenster erstellen
root = tk.Tk()

root.title("HamOps")
root.geometry("900x1050") # Startgröße des Fensters
root.minsize(900, 1050)

menubar = tk.Menu(root) # Menü hinzugefügt 
root.config(menu=menubar) # Menü dem root fenster zugewiesen 

# Menue button in der menuebar
settings_menu = tk.Menu(menubar,tearoff=0)
menubar.add_cascade(label="Menue", menu=settings_menu)
settings_menu.add_command(label="Settings", command=open_settings_window) 
settings_menu.add_command(label="about",command=open_about_window)
settings_menu.add_command(label="close",command=root.destroy)

# view button in der menuebar
view_menu = tk.Menu(menubar, tearoff=0) # tearoff=0 verhindert eine gestrichelte Linie oben
menubar.add_cascade(label="view", menu=view_menu) 
view_menu.add_command(label="Fullscreen", command=toggle_fullscreen)

# macht alles dehnbar 
root.grid_columnconfigure(0, weight=1) # Macht Spalte 0 dehnbar
root.grid_columnconfigure(1, weight=1) # Macht Spalte 1 dehnbar
root.grid_columnconfigure(2, weight=1) # Macht Spalte 1 dehnbar
root.grid_columnconfigure(3, weight=1) # Macht Spalte 1 dehnbar
root.grid_columnconfigure(4, weight=1) # Macht Spalte 1 dehnbar


# Ladet icon für programm
icon_image = tk.PhotoImage(file='icon.png')
root.iconphoto(False, icon_image) 



# Stil für modernere Widgets (optional)
style = ttk.Style()
style.theme_use('alt') # oder 'alt', 'default', 'classic'


# Überschrift
title_label = ttk.Label(root, text="HamOPs", font=("Arial", 24, "bold"))
title_label.grid(row=0, column=0, columnspan=2, pady=20, sticky="ew")
title_label.config(anchor="center")

# --- 2 Unterschrift ---
subtitle_label = ttk.Label(root, text="Your Ham Radio Dashboard...", font=("Arial", 12))
subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew") # row=1, da es unter row=0 liegt
subtitle_label.config(anchor="center")

# Füge einen Aktualisierungs-Button hinzu (optional, aber empfohlen für manuelle Updates)
#refresh_button = ttk.Button(root, text="Daten jetzt aktualisieren", command=lambda: [update_dashboard(), update_webcam_image()])
#refresh_button.grid(row=4, column=0, columnspan=2, pady=20) # Platziere den Button in einer neuen Reihe

# --- Bereich für Wetter daten ---
wetter_frame = ttk.LabelFrame(root, text="Local Weather", padding=10)
wetter_frame.grid(row=2, column=0, pady=10, padx=20, sticky="nsew") # sticky für Ausrichtung
wetter_label = ttk.Label(wetter_frame, text="Platzhalter für wetterdaten", font=("Arial", 12), justify="left")
wetter_label.pack(pady=5, fill="x", expand=True)

# --- Bereich für Solar daten ---
solar_frame = ttk.LabelFrame(root, text="SolarData", padding=10)
solar_frame.grid(row=3, column=0, pady=10, padx=20, sticky="nsew") # sticky für Ausrichtung
solar_label = ttk.Label(solar_frame, text="Platzhalter für solar daten", font=("Arial", 12), justify="left")
solar_label.pack(pady=5, fill="x", expand=True)

# --- Bereich für das Webcam-Bild ---
webcam_frame = ttk.LabelFrame(root, text="Local Webcam ", padding=10)
webcam_frame.grid(row=2, column=1, rowspan=1 , pady=10, padx=20, sticky="nsew") # Spannt über 3 Reihen
webcam_label = ttk.Label(webcam_frame) # Das Label, das das Bild halten wird
webcam_label.pack(expand=True, fill="both") # Bild soll den Bereich ausfüllen

# --- Bereich für das Solar-Bild ---
solarimage_frame = ttk.LabelFrame(root, text="Solar ", padding=10)
solarimage_frame.grid(row=3, column=1, rowspan=1 , pady=10, padx=20, sticky="nsew") # Spannt über 3 Reihen
solarimage_label = ttk.Label(solarimage_frame) # Das Label, das das Bild halten wird
solarimage_label.pack(expand=True, fill="both") # Bild soll den Bereich ausfüllen

# ---Bereich für UTC Zeit ---
utc_time_label = ttk.Label(root, text="UTC: Lade...", font=("Arial", 12), anchor="e") # 
utc_time_label.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

# Globale Variable für die Bildreferenz (ganz wichtig!)
tk_webcam_image = None # Initialisiere es, damit es im globalen Scope existiert
tk_solar_image = None

# damit beim start die daten in der gui stehen
load_settings()
load_image_from_url(LocalWebcamURL)
update_dashboard() 
update_webcam_image()
update_solar_image()
update_utc_time()
# Start der Ereignisschleife
root.mainloop()

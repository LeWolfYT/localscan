import datetime as dt
import json
import math
import os
import random as rd
import runpy as rp
import subprocess as sp
import threading as th
import time
import traceback as tra
from io import BytesIO

import cv2
import geocoder as gc
import isodate as it
import map_tile_stitcher as ms
import map_tile_stitcher.util.conversion as msc
import numpy as np
import pygame as pg
import pytz as tz
import requests as r
from pygame._sdl2.mixer import set_post_mix

import vars as varr
#import multiprocessing as mp
#import ffmpeg_streaming as ff

global stinky
stinky = False

global streambg
streambg = getattr(varr, "streambg", False)

global profiling
profiling = {
    "time_ui": 0,
    "time_blits": 0,
    "time_stream": 0,
    "time_math": 0,
}
global framesp
global framect
framect = 0
framesp = 0

def clear_profile():
    global profiling
    profiling = {
        "time_ui": 0,
        "time_blits": 0,
        "time_stream": 0,
        "time_math": 0,
    }

profile = False

def profiling_sect(section):
    def profiling_wrap(func):
        def wrapper(*args, **kwargs):
            if profile:
                start = time.perf_counter()
                val = func(*args, **kwargs)
                end = time.perf_counter()
                diff = end - start
                profiling[section] += diff
                return val
            else:
                return func(*args, **kwargs)
        return wrapper
    return profiling_wrap

def profiling_start():
    return time.perf_counter()

def profiling_end(start, section):
    profiling[section] += (time.perf_counter() - start)

eventt = th.Event()

print("getting variables")
sound = getattr(varr, "sound", True)
manualmusic = getattr(varr, "manualmusic", False)
ads = getattr(varr, "ads", [])
actime = getattr(varr, "adcrawltime", 4)

audiofile = getattr(varr, "audiofile", None)

theme = getattr(varr, "theme", None)

cachedir = os.path.dirname(os.path.abspath(__file__))
themedir = os.path.join(cachedir, "themes")
plugindir = os.path.join(cachedir, "plugins")
icondir = os.path.join(cachedir, "iconpacks")

global stream
stream = getattr(varr, "stream", None)
writer = getattr(varr, "writer", None)

iconpack = getattr(varr, "iconpack", "")

miniplayer = getattr(varr, "miniplayer", False)
miniplayerheight = getattr(varr, "miniplayerheight", 160)

ldltop = getattr(varr, "ldlmode_top", False) #this actually shows the top bar with fixtures
ldlshadow = getattr(varr, "ldlmode_shadow", False)

ldlwatermark = getattr(varr, "ldlmode_watermark", False)
watermark = getattr(varr, "watermark_path", None)

hideleft = getattr(varr, "hide_fixture_left", False)
hideright = getattr(varr, "hide_fixture_right", False)

if ldlwatermark and watermark != None:
    watermark = pg.image.load(watermark)

filters = {
    "title": [],
    "tickerleft": [],
    "tickerright": [],
    "tickerbl": [],
    "tickerbr": [],
    "tickertl": [],
    "tickertr": []
}

actions = {
    "pre": [],
    "post": [],
    "mix": [] #this is for post-mixing
}

travelcities = getattr(varr, "travelcities", ["KATL", "KBOS", "KORD", "KDFW", "KDEN", "KDTW", "KLAX", "KNYC", "KMCO", "KSFO", "KSEA", "KDCA"])

performance = getattr(varr, "performance", False)
usebg = getattr(varr, "background_image_use", False)

compact = getattr(varr, "compact", False)

bgimage = None
bgimager = None
if usebg:
    bgimage = pg.image.load(varr.background)
    bgimager = pg.image.load(getattr(varr, "backgroundred", varr.background))

screenwidth = getattr(varr, "screenwidth", 1366)

tilesneededw = math.ceil(screenwidth / 256) // 2 * 2 + 1
tilesneededh = 3

loadingtasks = []

screendiff = screenwidth - 1024

transitions = True

debug = False
print(f"debug draw mode: {debug}")
def debugsleep():
    if debug:
        time.sleep(0.1)
        pg.display.flip()
        pg.event.pump()

#caches
print("making cache")
global cache
cache = {}
global textcache
textcache = {}
global textcachecol
textcachecol = {}
global tempcache
global tempcachecol
tempcache = {}
tempcachecol = {}
global crunchcache
crunchcache = {}
global crunchcachecol
crunchcachecol = {}
global bigcrunchcache
bigcrunchcache = {}

global rastercache
rastercache = {} #this cache is special because it caches a ton of blits

print("getting more options")
global scaled
scaled = getattr(varr, "scaled", False)
global scale
scale = getattr(varr, "size", (screenwidth, 768))
global smoothsc
smoothsc = getattr(varr, "smoothscale", True)

global partnered
partnered = getattr(varr, "partnered", False)
global partnerlogo
partnerlogo = getattr(varr, "logo", None)

rheaders = {
    "User-Agent": "(lewolfyt.cc, localscope+ciblox3@gmail.com)"
}

rheaders_maps = {
    "User-Agent": "(lewolfyt.cc, localscope+ciblox3@gmail.com)",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

global currentscene
currentscene = 0
#0 = main
#1 = extended travel forecast
#2 = live feed overlay

maskcolor = getattr(varr, "maskcolor", (255, 0, 255))
print("getting directories")
assetdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
iconf = os.path.join(assetdir, "icon.bmp")
mylogof = os.path.join(assetdir, "mylogo.png")

mylogo = pg.image.load(mylogof)

transitionicons = [pg.image.load(os.path.join(assetdir, "weather.png")), pg.Surface((2, 2)), pg.image.load(os.path.join(assetdir, "custom.png"))]


global logo
print("loading logo")
logo = pg.image.load(iconf)
pg.display.set_icon(logo)

graphicloc = getattr(varr, "sector", "CONUS").upper()
wgraphicloc = getattr(varr, "warningsector", "CONUS").upper()
graphicwidth = getattr(varr, "graphicalwidth", 840)

#links, no touching these unless you know what you're doing
gtz = getattr(varr, "timezone", "GMT")

#TODO: figure out if what i figured out n does is correct
print("getting rank")
utn = dt.datetime.now(tz.UTC)
rankid = utn.hour
if rankid < 12:
    if rankid == 0 and utn.minute < 10:
        rank = 0
    elif rankid < 3:
        rank = 1
    elif rankid < 6:
        rank = 2
    elif rankid < 9:
        rank = 3
    else:
        rank = 4
else:
    if rankid < 12:
        rank = 0
    elif rankid < 15:
        rank = 1
    elif rankid < 18:
        rank = 2
    elif rankid < 21:
        rank = 3
    else:
        rank = 4

gtempurl = f"https://graphical.weather.gov/GraphicalNDFD.php?width={graphicwidth}&timezone={gtz}&sector={graphicloc}&element=t&n={rank}"
grainurl = f"https://graphical.weather.gov/GraphicalNDFD.php?width={graphicwidth}&timezone={gtz}&sector={graphicloc}&element=pop12&n={rank}"
warnsurl = f"https://radar.weather.gov/ridge/standard/{wgraphicloc}_0.gif"

#the todo list
#TODO: add a way to organize views
#TODO: add the hourly forecast (graph done)
#TODO: hurricane images
#TODO: make the mouse work better
#TODO: icons to show if the mouse does something

timeformat = "%I:%M %p"
timeformattop = "%I:%M:%S %p"

weatheraddr = getattr(varr, "weatheraddr", "http://wttr.in?format=j2")

musicmode = getattr(varr, "musicmode", "playlist")

playmusic = getattr(varr, "musicdir", False)

@profiling_sect("time_math")
def splubby(time):
    if list(time)[0] == "0":
        return time[1:]
    else:
        return time

@profiling_sect("time_math")
def lltoxy(lat, long, zoom):
    n = 2 ** zoom
    n2 = 2 ** (zoom-1)
    x = math.floor((long + 180)/360 * n)
    y = math.floor((1-(math.log(math.tan(lat * math.pi / 180) +(1/(math.cos(lat * math.pi / 180))))) / math.pi) * n2)
    return (x, y)

@profiling_sect("time_math")
def wraptext(text, rect, font):
    rect = pg.Rect(rect)
    y = rect.top
    lineSpacing = -2

    # get the height of the font
    fontHeight = font.size("Tg")[1]
    lines = []

    while text:
        i = 1
        # determine if the row of text will be outside our area
        if y + fontHeight > rect.bottom:
            break

        # determine maximum width of line
        while font.size(text[:i])[0] < rect.width and i < len(text):
            i += 1

        # if we've wrapped the text, then adjust the wrap to the last word      
        if i < len(text): 
            i = text.rfind(" ", 0, i) + 1

        # render the line and blit it to the surface
        
        lines.append(text[:i])

        y += fontHeight + lineSpacing

        # remove the text we just blitted
        text = text[i:]

    return lines

print("initializing pygame")
if getattr(varr, "audioin", None):
    pg.mixer.pre_init(44100, 32, 2, 512, getattr(varr, "audioin", None))
else:
    pg.mixer.pre_init(44100, 32, 2, 512)
pg.init()
print("done with pygame init")

if not scaled:
    print("making unscaled window")
    realwindow = pg.Window("LocalScope v1.6", (screenwidth, 768))
    realwindow.borderless = True
    window = realwindow.get_surface()
else:
    print("making fake window")
    window = pg.Surface((screenwidth, 768))
    print("making actual window")
    realwindow = pg.Window("LocalScope v1.6", scale)
    final = realwindow.get_surface()

#realops = pg.Window("LocalScope - Admin Panel", (640, 480))

#opswindow = realops.get_surface()

print("screensaver disabled")
pg.display.set_allow_screensaver(False)

print("mouse is invisible")
pg.mouse.set_visible(False)

#print("caption set")
#pg.display.set_caption("LocalScope v1.4")
print("LocalScope v1.6 - The Scheduling Update and also Some Really Smooth Animations")

#get schedule attributes
print("getting schedule")

schedule_active = getattr(varr, "scheduled", False)

schedule_mode = getattr(varr, "schedule_mode", "minutes")

schedule_times = getattr(varr, "schedule_times", [18, 48]) #in minutes mode, this is the minute of the hour that it will fire on
schedule_times = [int(i) for i in schedule_times]

sidebar_times = getattr(varr, "sidebar_times", [8, 28, 38, 58]) #in minutes mode, this is the minute of the hour that it will fire on
sidebar_times = [int(i) for i in sidebar_times]

#here we'll get the presentation mode. "short" is just the normal weather section, "long" includes weather+health and custom slides
presentation = getattr(varr, "presentation", "short")

customtransition = getattr(varr, "customtransition", False)

#note that this only applies when a schedule is active, and a manual override will always show the full presentation on loop

#a bit of documentation here (woah, in this spaghetti? i could never):
#schedulemode defines how the schedule times are set up
#minutes: fires at the specified minute(s) of every hour
#hours: fires at the specified hour(s)
#mixed: fires at the specified minute(s) of the specified hour(s), formatted as [[hour, hour, ...], [minute, minute, ...]]
#custom: fires at the specified time(s) of the day

#right now it's all just minutes, since time constraints

if sound:
    print("loading sound")
    daytheme = pg.mixer.Sound(varr.daytheme)
    nighttheme = pg.mixer.Sound(varr.nighttheme)

@profiling_sect("time_math")
def generateGradient(col1, col2, w=screenwidth, h=768, a1=255, a2=255):
    r1, g1, b1 = col1[0], col1[1], col1[2]
    r2, g2, b2 = col2[0], col2[1], col2[2]
    surface = pg.Surface((w, h)).convert_alpha()
    surface.fill((255, 255, 255, 255))
    for i in range(h):
        tr = i/(h-1)
        transpar = pg.Surface((w, 1)).convert_alpha()
        transpar.fill((255, 255, 255, (a1*(1-tr) + a2*tr)))
        pg.draw.line(transpar, ((r1*(1-tr) + r2*tr), (g1*(1-tr) + g2*tr), (b1*(1-tr) + b2*tr)), (0, 0), (w, 0))
        surface.blit(transpar, (0, i), special_flags=pg.BLEND_RGBA_MULT)
    return surface.convert_alpha()

blurmode = getattr(varr, "blurmode", "gaussian")

cache["blur"] = {}
cache["blur2"] = {}

@profiling_sect("time_math")
def blur(surf: pg.Surface, radius):
    if surf in cache["blur"]:
        return cache["blur"][surf]
    else:
        if blurmode == "box":
            cache["blur"][surf] = pg.transform.box_blur(surf, radius)
            return cache["blur"][surf]
        elif blurmode == "gaussian":
            cache["blur"][surf] = pg.transform.gaussian_blur(surf, radius)
            return cache["blur"][surf]
        elif blurmode == "dropshadow":
            transparent = pg.Surface((surf.get_width()-6, surf.get_height()-6), flags=pg.SRCALPHA)
            transparent.blit(surf, (-3, -3), special_flags=pg.BLEND_RGBA_ADD)
            transparent.fill((32, 32, 32, 255), special_flags=pg.BLEND_RGBA_ADD)
            cache["blur"][surf] = transparent
            return transparent
        else:
            return pg.Surface((1, 1))

@profiling_sect("time_math")
def blur2(surf: pg.Surface, radius):
    if surf in cache["blur2"]:
        return cache["blur2"][surf]
    else:        
        if blurmode == "box":
            cache["blur2"][surf] = pg.transform.box_blur(surf, radius)
            return cache["blur2"][surf]
        elif blurmode == "gaussian":
            cache["blur2"][surf] = pg.transform.gaussian_blur(surf, radius)
            return cache["blur2"][surf]
        elif blurmode == "dropshadow":
            transparent = surf.copy()
            transparent.fill((192, 192, 192, 255), special_flags=pg.BLEND_RGBA_MULT)
            cache["blur2"][surf] = transparent
            return transparent
        else:
            return pg.Surface((1, 1))

@profiling_sect("time_math")
def turnintoashadow(surf: pg.Surface, shadow=127):
    if surf in cache:
        return cache[surf]
    else:
        newsurf = surf.copy().convert_alpha()
        newsurf.fill((0, 0, 0, shadow), special_flags=pg.BLEND_RGBA_MULT)
        #black = pg.Surface((surf.get_width(), surf.get_height()), pg.SRCALPHA)
        #black.fill((0, 0, 0, shadow))
        #newsurf.blit(black, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        newsurf = blur2(expandSurfaceAlpha(newsurf, 6), 4)
        cache[surf] = newsurf
        return newsurf

cache["delicate"] = {}

@profiling_sect("time_math")
def turnintoashadow_delicate(surf: pg.Surface, shadow=127):
    #this uses a slightly different process for some special cases
    if surf in cache["delicate"]:
        return cache["delicate"][surf]
    else:
        newsurf = surf.copy()
        newsurf.fill((0, 0, 0, shadow), None, pg.BLEND_RGBA_MULT)
        #black = pg.Surface((surf.get_width(), surf.get_height()), pg.SRCALPHA)
        #black.fill((0, 0, 0, shadow))
        #newsurf.blit(black, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        newsurf = blur2(expandSurfaceDelicate(newsurf, 6), 4)
        cache[surf] = newsurf
        return newsurf

@profiling_sect("time_math")
def generateGradientHoriz(col1, col2, w=screenwidth, h=768, a1=255, a2=255):
    r1, g1, b1 = col1[0], col1[1], col1[2]
    r2, g2, b2 = col2[0], col2[1], col2[2]
    surface = pg.Surface((w, h), pg.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    for i in range(w):
        tr = i/(w-1)
        pg.draw.line(surface, ((r1*(1-tr) + r2*tr), (g1*(1-tr) + g2*tr), (b1*(1-tr) + b2*tr), (a1*(1-tr) + a2*tr)), (i, 0), (i, h))
    return surface


apikey = varr.apikey
mapkey = varr.mapkey
unites = getattr(varr, "units", "e")

#temp unit
t = "F" if unites == "e" else "C"

#kmph?
kmp = "" if unites == "e" else "k"
kmpb = "" if unites == "e" else "K"

#pressure
pres = "inHg" if unites == "e" else ("mbar" if not compact else "mb")
pres_s = "in." if unites == "e" else ("mbar" if not compact else "mb")

#visibility
visi = ("miles" if not compact else "mi.") if unites == "e" else ("kilometers" if not compact else "km")
visi_c = "mi." if unites == "e" else "km"

#precip
prec = ("inches" if not compact else "in.") if unites == "e" else ("millimeters" if not compact else "mm")
prec_c = "in." if unites == "e" else "mm"

locl = getattr(varr, "locale", "en-US")

lang = {}
langf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang", locl) + ".json"

if not os.path.exists(langf):
    langf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lang", "en-US") + ".json"

with open(langf, "r") as f:
    lang = json.loads(f.read())

tile_amounts = 20
global skipflag
skipflag = False
class TextFilter:
    """
    A filter used on text.
    """
    def __init__(self, main=True, pre=False, post=False, shadow=False):
        """
        Creates a new filter.
        """
        self.main = main
        self.pre = pre
        self.post = post
        self.shadow = shadow
    def filter_pre(self, text: str, font: pg.Font, point: pg.typing.Point, alpha: int):
        """
        Filter code that runs before the text surface is generated. Will only run if "pre" is set to True.
        """
    def filter(self, text: str, font: pg.Font, surf: pg.Surface, point: pg.typing.Point, alpha: int) -> pg.Surface:
        """
        The main filter code. This gets applied to the generated text surface. Will not run if "post" is set to False. Returns the filtered text.
        """
    def filter_post(self, text: str, font: pg.Font, surf: pg.Surface, point: pg.typing.Point, alpha: int) -> pg.Surface:
        """
        Filter code that runs after the text surface is blitted.  Will only run if "post" is set to True.
        """

class GeneralColorFilter(TextFilter):
    def __init__(self, main=True, pre=False, post=False, shadow=False, color=pg.typing.ColorLike):
        self.color = color
        super().__init__(main, pre, post, shadow)
    def filter(self, text, font, surf, point, alpha):
        surf2 = surf.copy()
        surf2.fill(self.color, special_flags=pg.BLEND_RGBA_MULT)
        return surf2

class ShrinkFilter(TextFilter):
    def __init__(self, main=True, pre=False, post=False, shadow=2):
        super().__init__(main, pre, post, shadow)
    def filter(self, text, font, surf, point, alpha):
        scal = 2/len(text)
        return (pg.transform.smoothscale_by(surf, (scal[0], 1))), pg.transform.smoothscale_by(surf[1], (scal, 1))

class CrunchFilter(TextFilter):
    def __init__(self, main=True, pre=False, post=False, shadow=2, target=0):
        self.target = target
        super().__init__(main, pre, post, shadow)
    def filter(self, text, font, surf, point, alpha):
        if surf[0].get_width() > self.target:
            mult = surf[0].get_width() / self.target
            return (pg.transform.smoothscale(surf[0], (self.target, surf[0].get_height())), pg.transform.smoothscale(surf[1], (self.target+12/mult, surf[1].get_height())))
        else:
            return surf

def squish_size_helper(size, amount):
    return (size[0]*(1+amount/2), size[1]*(1-amount/2))
def squish_helper(surf, amount):
    return pg.transform.smoothscale_by(surf, (1+amount/2, 1-amount/2))
class SquishFilter(TextFilter):
    def __init__(self, main=True, pre=False, post=False, shadow=2, amount=0):
        self.amount = amount
        super().__init__(main, pre, post, shadow)
    def filter(self, text, font, surf, point, alpha):
        if self.amount == 0:
            return surf
        else:
            return (squish_helper(surf[0], self.amount), squish_helper(surf[1], self.amount))

def getWeather():
    global loadingstage
    global redmode
    global coords
    redmode = False
    loadingstage=0
    loadingtasks.append("Gathering initial data...")
    if True:
        if getattr(varr, "coords", False):
            coords = getattr(varr, "coords")
        else:
            templl = gc.ip("me")
            gj = templl.geojson
            coords = f'{gj["features"][0]["lat"]},{gj["features"][0]["lng"]}'
    
    st = time.time()
    
    global sunrises
    sunrises = r.get(f"https://api.sunrisesunset.io/json?lat={coords.split(',')[0]}&lng={coords.split(',')[1]}").json()
    
    et = time.time()
    print(et - st)
    
    zoom = 8
    
    basetile = msc.get_index_from_coordinate(ms.Coordinate(float(coords.split(",")[0]), float(coords.split(",")[1])), zoom)
    
    loadingstage=1
    
    global headlines
    weatherendpoint4 = f'https://api.weather.com/v3/wx/forecast/hourly/2day?geocode={coords}&units={unites}&language={locl}&format=json&apiKey={apikey}'
    observationend = f"https://api.weather.com/v3/wx/observations/current?geocode={coords}&units={unites}&language={locl}&format=json&apiKey={apikey}"
    
    global weather2 # current
    loadingstage=2
    loadingtasks.remove("Gathering initial data...")
    
    def getcc():
        global weather2
        loadingtasks.append("Retrieving current conditions...")
        weather2 = r.get(observationend).json()
        loadingtasks.remove("Retrieving current conditions...")
    th.Thread(target=getcc).start()
    
    global stream
    
    global travelweathers
    global travelnames
    travelweathers = []
    travelnames = []
    def gettc():
        loadingtasks.append("Retrieving current travel conditions...")
        global travelweathers
        global travelnames
        for city in range(len(travelcities)):
            citystationinf = r.get(f'https://api.weather.com/v3/location/point?icaoCode={travelcities[city]}&language={locl}&format=json&apiKey={apikey}').json()
            cityw = r.get(f'https://api.weather.com/v3/wx/forecast/hourly/2day?icaoCode={travelcities[city]}&units={unites}&language={locl}&format=json&format=json&apiKey={apikey}').json()
            travelweathers.append(cityw)
            realname = citystationinf["location"]["displayName"]
            travelnames.append(realname)
        travelnames = getattr(vars, "travelnames", ["Atlanta", "Boston", "Chicago", "Dallas/Ft. Worth", "Denver", "Detroit", "Los Angeles", "New York City", "Orlando", "San Francisco", "Seattle", "Washington D.C."])
        loadingtasks.remove("Retrieving current travel conditions...")
    th.Thread(target=gettc).start()
    global realstationname
    def getsi():
        loadingtasks.append("Retrieving station information...")
        global realstationname
        realstationname = r.get(f'https://api.weather.com/v3/location/point?geocode={coords}&language={locl}&format=json&apiKey={apikey}').json()["location"]["city"]
        loadingtasks.remove("Retrieving station information...")
    th.Thread(target=getsi).start()
    
    global weather3 # forecast
    
    global weathericons
    global weathericonbig
    
    def getic():
        global weathericons
        global weathericonbig
        global weathericonshourly
        global weathershadows
        global weathershadowbig
        global weathershadowshourly
        loadingtasks.append("Loading icons...")
        weathericons = [pg.Surface((1, 1)) for _ in range(22)]
        weathershadows = [pg.Surface((1, 1)) for _ in range(22)]
    
        icdir = os.path.join(icondir, iconpack)
        icss = {}
        for image in os.listdir(icdir):
            if image == ".DS_Store":
                continue
            if os.path.isdir(os.path.join(icdir,image)):
                continue
            try:
                icss[image] = pg.image.load(os.path.join(icdir,image))
            except:
                pass
            print(image)
    
        global bottomtomorrowm
        for i in range(22):
            if bottomtomorrowm and i == 0:
                print("icon skipped")
                continue
            if smoothsc:
                try:
                    weathericons[i] = pg.transform.smoothscale(icss[str(weather3["daypart"][0]["iconCode"][i])+str(weather3["daypart"][0]["dayOrNight"][i]).lower()+".png"], (128, 128))
                    if iconpack != "":
                        weathershadows[i] = turnintoashadow_delicate(weathericons[i])
                except:
                    print(f'error on loading icon {weather3["daypart"][0]["iconCode"][i]}{weather3["daypart"][0]["dayOrNight"][0+bottomtomorrowm].lower()}')
            else:
                weathericons[i] = pg.transform.scale(icss[str(weather3["daypart"][0]["iconCode"][i])+str(weather3["daypart"][0]["dayOrNight"][i]).lower()+".png"], (128, 128))
                if iconpack != "":
                    weathershadows[i] = turnintoashadow_delicate(weathericons[i])
            print(f'icon added: {weather3["daypart"][0]["iconCode"][i]}{weather3["daypart"][0]["dayOrNight"][i].lower()}.png')
        
        #load hourly icons
        weathericonshourly = [pg.Surface((1, 1)) for _ in range(24)]
        for i in range(24):
            #note: this uses the 2 day hourly forecast from IBM
            if smoothsc:
                try:
                    weathericonshourly[i] = pg.transform.smoothscale(icss[str(weatherraw["iconCode"][i])+str(weatherraw["dayOrNight"][i]).lower()+".png"], (80, 80))
                except:
                    print(f'error on loading icon {weatherraw["iconCode"][i]}{weatherraw["dayOrNight"][i].lower()}')
            else:
                weathericonshourly[i] = pg.transform.scale(icss[str(weatherraw["iconCode"][i])+str(weatherraw["dayOrNight"][i]).lower()+".png"], (80, 80))
        
        if smoothsc:
            weathericonbig = pg.transform.smoothscale(icss[str(weather3["daypart"][0]["iconCode"][0+bottomtomorrowm])+str(weather3["daypart"][0]["dayOrNight"][0+bottomtomorrowm]).lower()+".png"], (192, 192))
        else:
            weathericonbig = pg.transform.scale(icss[str(weather3["daypart"][0]["iconCode"][0+bottomtomorrowm])+str(weather3["daypart"][0]["dayOrNight"][0+bottomtomorrowm]).lower()+".png"], (192, 192))
        if iconpack != "":
            weathershadowbig = turnintoashadow_delicate(weathericonbig)
        loadingtasks.remove("Loading icons...")
    
    def getef():
        global weather3
        loadingtasks.append("Retrieving extended forecast...")
        weeklyend = f"https://api.weather.com/v3/wx/forecast/daily/10day?geocode={coords}&units={unites}&language={locl}&format=json&apiKey={apikey}"
        weather3 = r.get(weeklyend).json()
        global bottomtomorrowm
        bottomtomorrowm = (weather3["daypart"][0]["daypartName"][0] == None)
        loadingtasks.remove("Retrieving extended forecast...")
        th.Thread(target=getic).start()
    th.Thread(target=getef).start()
    
    def getwh():
        global airq
        global uvi
        global pollen
        loadingtasks.append("Retrieving health information...")
        airend = f"https://api.weather.com/v3/wx/globalAirQuality?geocode={coords}&language={locl}&scale=EPA&format=json&apiKey={apikey}"
        uvend = f"https://api.weather.com/v2/indices/uv/current?geocode={coords}&language={locl}&format=json&apiKey={apikey}"
        pollenend = f"https://api.weather.com/v1/geocode/{coords.split(',')[0]}/{coords.split(',')[1]}/observations/pollen.json?language={locl}&apiKey={apikey}"
        
        airq = r.get(airend).json()
        uvi = r.get(uvend).json()
        pollen = r.get(pollenend).json()
        
        loadingtasks.remove("Retrieving health information...")
    th.Thread(target=getwh).start()
    
    global weatherraw
    def getrw():
        loadingtasks.append("Retrieving hourly forecast...")
        global weatherraw
        weatherraw = r.get(weatherendpoint4).json()
        loadingtasks.remove("Retrieving hourly forecast...")
    th.Thread(target=getrw).start()
    
    global alerts
    def getal():
        global trackhurricanes
        global redmode
        global alerts
        loadingtasks.append("Retrieving alerts...")
        alertyy = r.get(f'https://api.weather.com/v3/alerts/headlines?geocode={coords}&format=json&language={locl}&apiKey={apikey}', headers=rheaders)
        
        if alertyy.status_code not in [404, 204]:
            print("status", alertyy.status_code)
            alertyy = alertyy.json()
        else:
            alertyy = {"alerts": []}
        try:
            alerts = alertyy["alerts"]
        except:
            print(alertyy)
        global alert_details
        alert_details = []
        for alert in alerts:
            print(alert["certainty"])
            print(alert["urgency"])
            alert_details.append(
                r.get(f"https://api.weather.com/v3/alerts/detail?alertId={alert['detailKey']}&format=json&language={locl}&apiKey={apikey}").json()["alertDetail"]["texts"][0]["description"]
            )
            if not alert["certainty"] in ["Observed", "Likely"]:
                continue
            if not alert["urgency"] in ["Immediate", "Expected"]:
                continue
            redmode = True
            if "hurricane" in alert["headlineText"].lower():
                trackhurricanes = True
        loadingtasks.remove("Retrieving alerts...")
    th.Thread(target=getal).start()
    
    def getim():
        loadingtasks.append("Loading images...")
        global mappy
        global trackhurricanes
        trackhurricanes = False
        global radarimage
        radarimage = pg.image.load(BytesIO(r.get(warnsurl, headers=rheaders).content))
        global hurricaneimage
        hurricaneimage = pg.image.load(BytesIO(r.get(f"https://www.nhc.noaa.gov/xgtwo/two_{getattr(varr, 'hurricanesector', 'pac').lower()}_0d0.png", headers=rheaders).content))

        tilestart = ms.GridIndex(basetile.x - math.floor(tilesneededw/2), basetile.y - math.floor(tilesneededh/2), zoom)
        tileend = ms.GridIndex(basetile.x + math.ceil(tilesneededw/2), basetile.y + math.ceil(tilesneededh/2), zoom)

        mappy_temp = [[] for _ in range(abs(tilestart.x - tileend.x))]

        tilesneededx = list(range(tilestart.x, tileend.x+1))
        tilesneededy = list(range(tilestart.y, tileend.y+1))

        global ppa
        ppa = r.get(f"https://api.weather.com/v3/TileServer/series/productSet/PPAcore?apiKey={apikey}").json()

        global mappy_heat
        global mappy_precip
        global timestam

        #osmtiles = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        osmtiles = "https://api.mapbox.com/styles/v1/lewolfyt/cm8m4n5kt01if01s502hmatep/tiles/256/{z}/{x}/{y}?access_token=" + mapkey
        twctiles_heat = "https://api.weather.com/v3/TileServer/tile/twcRadarMosaic?ts={ts}&xyz={x}:{y}:{z}&apiKey=" + apikey
        # twctiles_precip = "https://api.weather.com/v3/TileServer/tile/precip24hrFcst?ts={ts}&fts={fts}&xyz={x}:{y}:{z}&apiKey=" + apikey
        twch_temp = [[[] for _ in range(tile_amounts)] for _ in range(abs(tilestart.x - tileend.x))]
        # twpc_temp = [[[] for _ in range(5)] for _ in range(abs(tilestart.x - tileend.x))]

        try:
            os.mkdir(os.path.join(cachedir, "cache"))
        except:
            pass
        
        realcache = os.path.join(cachedir, "cache")

        timestam = [[], []]
        def premap():
            for i in range(abs(tilestart.x - tileend.x)):
                for j in range(abs(tilestart.y - tileend.y)):
                    url = osmtiles.format(z=zoom, x=tilesneededx[i], y=tilesneededy[j])
                    
                    if not os.path.exists(os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}.png")):
                        ee = r.get(url, headers=rheaders_maps).content
                        mappy_temp[i].append(pg.image.load(BytesIO(ee)))
                        with open(os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}.png"), "wb") as ff:
                            ff.write(ee)
                    else:
                        mappy_temp[i].append(pg.image.load(os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}.png")))
        global maphdone
        maphdone = False
        def getmaph():
            for i in range(abs(tilestart.x - tileend.x)):
                for j in range(abs(tilestart.y - tileend.y)):
                    base1 = ppa["seriesInfo"]["twcRadarMosaic"]["series"]
                    for k in range(tile_amounts):
                        twch_temp[i][k].append(None)
                        timestam[0].append(dt.datetime.fromtimestamp(base1[tile_amounts-1-k]["ts"]))
            def getmaph_sect(k):
                for i in range(abs(tilestart.x - tileend.x)):
                    for j in range(abs(tilestart.y - tileend.y)):
                        base1 = ppa["seriesInfo"]["twcRadarMosaic"]["series"]
                        ht = twctiles_heat.format(ts=base1[tile_amounts-1-k]["ts"], z=zoom, x=tilesneededx[i], y=tilesneededy[j])
                        
                        trying = True
                        while trying:
                            try:
                                eh = r.get(ht, headers=rheaders_maps).content
                                trying = False
                            except:
                                pass
                            if trying == False:
                                break
                        
                        twch_temp[i][k][j] = (pg.image.load(BytesIO(eh)))
                        print("mapsect:", dt.datetime.fromtimestamp(base1[tile_amounts-1-k]["ts"]), "i", i, "j", j, "k", k)
            threads = []
            for k in range(tile_amounts):
                threads.append(th.Thread(target=getmaph_sect, args=[k]))
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            global maphdone
            maphdone = False
        # global mappdone
        # mappdone = False
        # def getmapp():
        #     for i in range(abs(tilestart.x - tileend.x)):
        #         for j in range(abs(tilestart.y - tileend.y)):
        #             base2 = ppa["seriesInfo"]["satradFcst"]["series"][0]
        #             for k in range(5):
        #                 twpc_temp[i][k].append(None)
        #                 timestam[1].append(dt.datetime.fromtimestamp(base2["fts"][-(k+1)]))
        #     def getmapp_sect(k):
        #         for i in range(abs(tilestart.x - tileend.x)):
        #             for j in range(abs(tilestart.y - tileend.y)):
        #                 base2 = ppa["seriesInfo"]["satradFcst"]["series"][0]
        #                 pc = twctiles_precip.format(ts=base2["ts"], fts=base2["fts"][-(k+1)], z=zoom, x=tilesneededx[i], y=tilesneededy[j])
        #                 ep = r.get(pc, headers=rheaders).content
        #                 twpc_temp[i][k][j] = (pg.image.load(BytesIO(ep)))
        #                 print("p ts ", dt.datetime.fromtimestamp(base2["ts"]))
        #                 print("p fts ", dt.datetime.fromtimestamp(base2["fts"][-(k+1)]))
        #                 print("mapsect:", dt.datetime.fromtimestamp(base2["fts"][-(k+1)]), "i", i, "j", j, "k", k)
            
        #     threads = []
        #     for k in range(5):
        #         threads.append(th.Thread(target=getmapp_sect, args=[k]))
        #     for thread in threads:
        #         thread.start()
        #     for thread in threads:
        #         thread.join()
        #     global mappdone
        #     mappdone = False
        
        premapt = th.Thread(target=premap)
        mapht = th.Thread(target=getmaph)
        # mappt = th.Thread(target=getmapp)
        premapt.start()
        mapht.start()
        # mappt.start()
        
        premapt.join()
        mapht.join()
        # mappt.join()
        
        print("maps done")
        mappy = pg.Surface((256 * tilesneededw, 256*tilesneededh))
        mappy_heat = [pg.Surface((256 * tilesneededw, 256*tilesneededh), flags=pg.SRCALPHA) for _ in range(tile_amounts)]
        # mappy_precip = [pg.Surface((256 * tilesneededw, 256*tilesneededh)) for _ in range(tile_amounts)]
        mappy = pg.Surface((256 * tilesneededw, 256*tilesneededh))
        for i in range(len(mappy_temp)):
            for j in range(len(mappy_temp[i])):
                mappy.blit(mappy_temp[i][j], (i*256, j*256))
                for k in range(tile_amounts):
                    while twch_temp[i][k][j] == None:
                        pass
                    mappy_heat[k].blit(twch_temp[i][k][j], (i*256, j*256))
                    # mappy_precip[k].blit(twpc_temp[i][k][j], (i*256, j*256))
        # for k in range(5):
        #     mappy_precip[k].set_alpha(round(255/6*5))
        loadingtasks.remove("Loading images...")
    th.Thread(target=getim).start()
    
    if partnered:
        loadingtasks.append("Loading your logo...")
        global logosurf
        logosurf = pg.image.load(partnerlogo)
        loadingtasks.remove("Loading your logo...")
    global skipflag
    while (len(loadingtasks) > 0) and not skipflag:
        pass
    
    if writer:
        set_post_mix(postmix)

    if stream:
        global realstream
        realstream = cv2.VideoCapture(stream)
        
        vv = th.Thread(target=reader_updater)
        vv.daemon = True
        vv.start()
        
        if miniplayer:
            #get stream dimensions and make a gradient for the miniplayer
            global streamdims
            streamdims = (realstream.get(cv2.CAP_PROP_FRAME_WIDTH), realstream.get(cv2.CAP_PROP_FRAME_HEIGHT))

            global minigradient
            minigradient = generateGradient(*reversed(chartbg_c), w=round(miniplayerheight*streamdims[0]/streamdims[1]), h=miniplayerheight)
        
            global streamdims_scaled
            streamdims_scaled = (round(miniplayerheight*streamdims[0]/streamdims[1])-8, miniplayerheight-8)
        
        if not realstream.isOpened():
            print("Stream not opened! Disabling...")
            stream = None
    
    global loading
    loading = False

def refreshWeather():
    global loadingtext
    global loadingstage
    global redmode
    global coords
    loadingstage=0
    if True:
        if getattr(varr, "coords", False):
            coords = getattr(varr, "coords")
        else:
            templl = gc.ip("me")
            gj = templl.geojson
            coords = f'{gj["features"][0]["lat"]},{gj["features"][0]["lng"]}'
        weatherend = r.get(f'https://api.weather.gov/points/{coords}', headers=rheaders).json()
    global sunrises
    sunrises = r.get(f"https://api.sunrisesunset.io/json?lat={coords.split(',')[0]}&lng={coords.split(',')[1]}").json()
    
    forecastoffice = weatherend["properties"]["forecastOffice"]
    headlineend = forecastoffice + "/headlines"
    global headlines
    weatherendpoint3 = weatherend["properties"]["forecastHourly"]
    weatherendpoint4 = f'https://api.weather.com/v3/wx/forecast/hourly/2day?geocode={coords}&units={unites}&language={locl}&format=json&apiKey={apikey}'
    observationend = f"https://api.weather.com/v3/wx/observations/current?geocode={coords}&units={unites}&language={locl}&format=json&apiKey={apikey}"
    print(observationend)
    stationname = "Temporary"
    print(stationname)
    global weather2 # current
    weather2 = r.get(observationend).json()
    global travelweathers
    global travelnames
    travelweathers = []
    travelnames = []
    for city in range(len(travelcities)):
        citystationinf = r.get(f'https://api.weather.com/v3/location/point?icaoCode={travelcities[city]}&language={locl}&format=json&apiKey={apikey}').json()
        cityw = r.get(f'https://api.weather.com/v3/wx/forecast/hourly/2day?icaoCode={travelcities[city]}&units={unites}&language={locl}&format=json&format=json&apiKey={apikey}').json()
        travelweathers.append(cityw)
        realname = citystationinf["location"]["displayName"]
        travelnames.append(realname)
    travelnames = getattr(vars, "travelnames", ["Atlanta", "Boston", "Chicago", "Dallas/Ft. Worth", "Denver", "Detroit", "Los Angeles", "New York City", "Orlando", "San Francisco", "Seattle", "Washington D.C."])

    global realstationname
    realstationname = r.get(f'https://api.weather.com/v3/location/point?geocode={coords}&language={locl}&format=json&apiKey={apikey}').json()["location"]["city"]
    global weather3 # forecast
    weeklyend = f"https://api.weather.com/v3/wx/forecast/daily/10day?geocode={coords}&units={unites}&language={locl}&format=json&apiKey={apikey}"
    weather3 = r.get(weeklyend).json()
    global airq
    global uvi
    global pollen
    
    airend = f"https://api.weather.com/v3/wx/globalAirQuality?geocode={coords}&language={locl}&scale=EPA&format=json&apiKey={apikey}"
    uvend = f"https://api.weather.com/v2/indices/uv/current?geocode={coords}&language={locl}&format=json&apiKey={apikey}"
    pollenend = f"https://api.weather.com/v1/geocode/{coords.split(',')[0]}/{coords.split(',')[1]}/observations/pollen.json?language={locl}&apiKey={apikey}"
    
    airq = r.get(airend).json()
    uvi = r.get(uvend).json()
    pollen = r.get(pollenend).json()
    
    global weather4
    weather4 = r.get(weatherendpoint3, headers=rheaders).json()
    global weatherraw
    weatherraw = r.get(weatherendpoint4).json()
    global alerts
    global trackhurricanes
    global weathericonshourly
    global weathericons
    global weathericonbig
    headlines = r.get(headlineend, headers=rheaders).json()["@graph"]
    weathericons = [pg.Surface((1, 1)) for _ in range(22)]
    global bottomtomorrowm
    bottomtomorrowm = (weather3["daypart"][0]["daypartName"][0] == None)
    icdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "twc")
    icss = {}
    for image in os.listdir(icdir):
        if image == ".DS_Store":
            continue
        icss[image] = pg.image.load(os.path.join(icdir,image))
    
    if True:
        for i in range(22):
            if bottomtomorrowm and i == 0:
                print("icon skipped")
                continue
            if smoothsc:
                try:
                    weathericons[i] = pg.transform.smoothscale(icss[str(weather3["daypart"][0]["iconCode"][i])+str(weather3["daypart"][0]["dayOrNight"][i]).lower()+".png"], (128, 128))
                    if iconpack != "":
                        weathershadows[i] = turnintoashadow(weathericons[i])
                except:
                    print(f'error on loading icon {weather3["daypart"][0]["iconCode"][i]}{weather3["daypart"][0]["dayOrNight"][0+bottomtomorrowm].lower()}')
            else:
                weathericons[i] = pg.transform.scale(icss[str(weather3["daypart"][0]["iconCode"][i])+str(weather3["daypart"][0]["dayOrNight"][i]).lower()+".png"], (128, 128))
                if iconpack != "":
                    weathershadows[i] = turnintoashadow(weathericons[i])
            print(f'icon added: {weather3["daypart"][0]["iconCode"][i]}{weather3["daypart"][0]["dayOrNight"][i].lower()}.png')
        
        weathericonshourly = [pg.Surface((1, 1)) for _ in range(24)]
        for i in range(24):
            #note: this uses the 2 day hourly forecast from IBM
            if smoothsc:
                try:
                    weathericonshourly[i] = pg.transform.smoothscale(icss[str(weatherraw["iconCode"][i])+str(weatherraw["dayOrNight"][i]).lower()+".png"], (80, 80))
                except:
                    print(f'error on loading icon {weatherraw["iconCode"][i]}{weatherraw["dayOrNight"][i].lower()}')
            else:
                weathericonshourly[i] = pg.transform.scale(icss[str(weatherraw["iconCode"][i])+str(weatherraw["dayOrNight"][i]).lower()+".png"], (80, 80))
    
    if smoothsc:
        weathericonbig = pg.transform.smoothscale(icss[str(weather3["daypart"][0]["iconCode"][0+bottomtomorrowm])+str(weather3["daypart"][0]["dayOrNight"][0+bottomtomorrowm]).lower()+".png"], (192, 192))
    else:
        weathericonbig = pg.transform.scale(icss[str(weather3["daypart"][0]["iconCode"][0+bottomtomorrowm])+str(weather3["daypart"][0]["dayOrNight"][0+bottomtomorrowm]).lower()+".png"], (192, 192))

    #global mappy
    #global radarimage
    #radarimage = pg.image.load(BytesIO(r.get(warnsurl, headers=rheaders).content))
    #global hurricaneimage
    #hurricaneimage = pg.image.load(BytesIO(r.get(f"https://www.nhc.noaa.gov/xgtwo/two_{getattr(varr, 'hurricanesector', 'pac').lower()}_0d0.png", headers=rheaders).content))
    
    
    
    #global ppa
    #ppa = r.get(f"https://api.weather.com/v3/TileServer/series/productSet/PPAcore?apiKey={apikey}").json()
    
    global alert_details
    if True:
        alertyy = r.get(f'https://api.weather.com/v3/alerts/headlines?geocode={coords}&format=json&language={locl}&apiKey={apikey}', headers=rheaders)
        
        if alertyy.status_code not in [404, 204]:
            print("status", alertyy.status_code)
            alertyy = alertyy.json()
        else:
            alertyy = {"alerts": []}
        try:
            alerts = alertyy["alerts"]
        except:
            print(alertyy)
        alert_details = []
        for alert in alerts:
            print(alert["certainty"])
            print(alert["urgency"])
            alert_details.append(
                r.get(f"https://api.weather.com/v3/alerts/detail?alertId={alert['detailKey']}&format=json&language={locl}&apiKey={apikey}").json()["alertDetail"]["texts"][0]["description"]
            )
            if not alert["certainty"] in ["Observed", "Likely"]:
                continue
            if not alert["urgency"] in ["Immediate", "Expected"]:
                continue
            redmode = True
            if "hurricane" in alert["headlineText"].lower():
                trackhurricanes = True
    
def refreshTiles():
    print("refreshing tiles!")
    zoom = 8
    basetile = msc.get_index_from_coordinate(ms.Coordinate(float(coords.split(",")[0]), float(coords.split(",")[1])), zoom)
    
    tilestart = ms.GridIndex(basetile.x - math.floor(tilesneededw/2), basetile.y - math.floor(tilesneededh/2), zoom)
    tileend = ms.GridIndex(basetile.x + math.ceil(tilesneededw/2), basetile.y + math.ceil(tilesneededh/2), zoom)
    
    mappy_temp = [[] for _ in range(abs(tilestart.x - tileend.x))]
    
    tilesneededx = list(range(tilestart.x, tileend.x+1))
    tilesneededy = list(range(tilestart.y, tileend.y+1))
    
    global mappy_heat
    global mappy_precip
    
    #osmtiles = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    osmtiles = "https://api.mapbox.com/styles/v1/goldbblazez/ckgc8lzdz4lzh19qt7q9wbbr9/tiles/256/{z}/{x}/{y}?access_token=" + mapkey
    twctiles_heat = "https://api.weather.com/v3/TileServer/tile/twcRadarMosaic?ts={ts}&xyz={x}:{y}:{z}&apiKey=" + apikey
    # twctiles_precip = "https://api.weather.com/v3/TileServer/tile/precip24hrFcst?ts={ts}&fts={fts}&xyz={x}:{y}:{z}&apiKey=" + apikey
    twch_temp = [[[] for _ in range(tile_amounts)] for _ in range(abs(tilestart.x - tileend.x))]
    # twpc_temp = [[[] for _ in range(5)] for _ in range(abs(tilestart.x - tileend.x))]
    
    try:
        os.mkdir(os.path.join(cachedir, "cache"))
    except:
        pass
    
    realcache = os.path.join(cachedir, "cache")
    
    for i in range(abs(tilestart.x - tileend.x)):
        for j in range(abs(tilestart.y - tileend.y)):
            url = osmtiles.format(z=zoom, x=tilesneededx[i], y=tilesneededy[j])
            
            if not os.path.exists(os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}.png")):
                ee = r.get(url, headers=rheaders).content
                mappy_temp[i].append(pg.image.load(BytesIO(ee)))
                with open(os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}.png"), "wb") as ff:
                    ff.write(ee)
            else:
                mappy_temp[i].append(pg.image.load(os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}.png")))
            #if tilesneededx[i] == basetile.x:
            #        if tilesneededy[j] == basetile.y:
            #            pg.image.save(mappy_temp[i][-1], os.path.join(realcache, f"{zoom}_{tilesneededx[i]}_{tilesneededy[j]}_thisisit.png"))
            base1 = ppa["seriesInfo"]["twcRadarMosaic"]["series"]
            #base2 = ppa["seriesInfo"]["satradFcst"]["series"][0]
            for k in range(tile_amounts):
                ht = twctiles_heat.format(ts=base1[tile_amounts--k]["ts"], z=zoom, x=tilesneededx[i], y=tilesneededy[j])
                # pc = twctiles_precip.format(ts=base2["ts"], fts=base2["fts"][-(k+1)], z=zoom, x=tilesneededx[i], y=tilesneededy[j])
                eh = r.get(ht, headers=rheaders).content
                twch_temp[i][k].append(pg.image.load(BytesIO(eh)))
                # ep = r.get(pc, headers=rheaders).content
                # twpc_temp[i][k].append(pg.image.load(BytesIO(ep)))
                timestam[0][k] = (dt.datetime.fromtimestamp(base1[tile_amounts-k]["ts"]))
                #timestam[1][k] = (dt.datetime.fromtimestamp(base2["fts"][-(k+1)]))
    
    for i in range(len(mappy_temp)):
        for j in range(len(mappy_temp[i])):
            mappy.blit(mappy_temp[i][j], (i*256, j*256))
            for k in range(tile_amounts):
                mappy_heat[k].blit(twch_temp[i][k][j], (i*256, j*256))
                # mappy_precip[k].blit(twpc_temp[i][k][j], (i*256, j*256))
    # for k in range(5):
    #     mappy_precip[k].set_alpha(round(255/6*5))

class RepeatTimer(th.Timer):
    def run(self):  
        while not self.finished.wait(self.interval):  
            self.function(*self.args,**self.kwargs)

print("making timer")
rrt = RepeatTimer(300, refreshWeather)
rrtt = RepeatTimer(300, refreshTiles)
rrt.daemon = True
rrtt.daemon = True

print("generating gradients")

gradient_c = ((0, 80, 255), (0, 180, 255))
gradient_redc = ((255, 0, 0), (255, 90, 0))
sidebar_c = ((0, 80, 255), (0, 180, 255))
sidebar_redc = ((255, 0, 0), (255, 90, 0))
topgradient_c = ((34, 139, 34), (124, 252, 0))
topgradienthealth_c = ((32, 178, 170), (0, 255, 255))
topgradientcustom_c = ((32, 32, 32), (170, 170, 170))
topgradientred_c = ((34, 139, 34), (124, 252, 0))
bottomgradient_c = ((240, 128, 128), (178, 34, 34))
bottomgradient_redc = ((0, 80, 255), (0, 180, 255))
ldlgradient_c = ((240, 128, 128), (178, 34, 34))
chartbg_c = ((0, 140, 255), (0, 40, 255))
hourlybg_c = ((0, 140, 255), (0, 40, 255))
weekbg_c = ((0, 140, 255), (0, 40, 255))
weekbg_darkc = ((140, 140, 140), (40, 40, 40))
weekbg_endc = ((255, 220, 0), (220, 170, 0))
weekbg_dendc = ((215, 105, 0), (215, 85, 0))
nextbg_c = ((0, 80, 255), (0, 180, 255))

# gradient_c = ((136,231,136), (46,111,64))
# gradient_redc = ((255, 0, 0), (255, 90, 0))
# topgradient_c = ((205,28,24), (102,0,51))
# bottomgradient_c = ((99,149,238), (39,39,87))
# bottomgradient_redc = ((136,231,136), (46,111,64))
# chartbg_c = ((136,231,136), (46,111,64))
# chartbg_darkc = ((140, 140, 140), (40, 40, 40))
# nextbg_c = ((0, 80, 255), (0, 180,  255))

themeworks = False

if theme:
    themepath = os.path.join(themedir, theme)
    pypath = os.path.join(themepath, "theme.py")
    if os.path.exists(pypath):
        print(f"loading theme {theme}")
        themedata = rp.run_path(pypath)
        themeworks = True

customfontdict = {}
fontname = getattr(varr, "font", "Arial")
bold = getattr(varr, "bold", True)
sizemult = 1

if themeworks:
    if "color_replace" in themedata:
        replace = themedata["color_replace"]
        for k in list(replace.keys()):
            print(f"replacing {k} from theme")
            vars()[k] = replace[k]
    if "filters" in themedata:
        for filter in themedata["filters"]:
            print("filter found!")
            exec(filter)
    if "actions" in themedata:
        if "pre" in themedata["actions"]:
            for action in themedata["actions"]["pre"]:
                print("pre action found!")
                actions["pre"].append(action)
        if "post" in themedata["actions"]:
            for action in themedata["actions"]["post"]:
                print("post action found!")
                actions["post"].append(action)
    if "customfonts" in themedata:
        for font in themedata["customfonts"]:
            customfontdict[font["type"]] = pg.font.SysFont(font["font"], font["size"]*sizemult, bold=font["bold"])
plugins = getattr(varr, "plugins", [])
pluginswork = [False for _ in range(len(plugins))]

customfixtures = []
customtickers = []
customtickers_m = []
customslides = []

@profiling_sect("time_math")
def get_lang_custom(dat):
    if locl in dat:
        return dat[locl]
    else:
        return dat["en-US"]

for plugin in range(len(plugins)):
    pluginpath = os.path.join(plugindir, plugins[plugin])
    pypath = os.path.join(pluginpath, "plugin.py")
    if os.path.exists(pypath):
        print(f"loading plugin {theme}")
        plugindata = rp.run_path(pypath)
        pluginswork[plugin] = True
        if "init" in plugindata:
            exec(plugindata["init"])
        if "fixtures" in plugindata:
            for x in plugindata["fixtures"]:
                customfixtures.append(x)
        if "tickers" in plugindata:
            for x in plugindata["tickers"]:
                customtickers.append(x)
        if "tickers2" in plugindata:
            for x in plugindata["tickers2"]:
                customtickers_m.append(x)
        if "slides" in plugindata:
            for x in plugindata["slides"]:
                customslides.append(x)
        if "actions" in plugindata:
            if "pre" in plugindata["actions"]:
                for action in plugindata["actions"]["pre"]:
                    print("pre action found! plugin")
                    actions["pre"].append(action)
            if "post" in plugindata["actions"]:
                for action in plugindata["actions"]["post"]:
                    print("post action found! plugin")
                    actions["post"].append(action)

if getattr(varr, "color_replace", None) != None:
    replace = getattr(varr, "color_replace", None)
    for k in list(replace.keys()):
        print(f"replacing {k} from vars")
        vars()[k] = replace[k]

gradient = generateGradient(*gradient_c)
gradientred = generateGradient(*gradient_redc)

sidebar = generateGradient(*sidebar_c, w=350)
sidebarred = generateGradient(*sidebar_redc, w=350)

topgradient = generateGradientHoriz(*topgradient_c, h=64)
topgradienthealth = generateGradientHoriz(*topgradienthealth_c, h=64)
topgradientcustom = generateGradientHoriz(*topgradientcustom_c, h=64)

topgradientred = generateGradientHoriz(*topgradientred_c, h=64)
bottomgradient = generateGradientHoriz(*bottomgradient_c, h=64)
bottomgradientred = generateGradientHoriz(*bottomgradient_redc, h=64)
ldlgradient = generateGradient(*ldlgradient_c, h=128)

topshadow = generateGradient((127, 127, 127), (255, 255, 255), a1=255, a2=255, h=16)
bottomshadow = generateGradient((255, 255, 255), (127, 127, 127), a1=255, a2=255, h=16)
sideshadow = generateGradientHoriz((255, 255, 255), (160, 160, 160), a1=255, a2=255, w=12)

weekbg = generateGradient(*chartbg_c, w=140, h=556)
weekbg.blit(generateGradient(*reversed(chartbg_c), w=130, h=546), (5, 5))

hourlybg = generateGradient(*hourlybg_c, w=(994+screendiff), h=(92))
hourlybg.blit(generateGradient(*reversed(hourlybg_c), w=(994+screendiff-10), h=82), (5, 5))

weekbgn = generateGradient(*weekbg_darkc, w=140, h=556)
weekbgn.blit(generateGradient(*reversed(weekbg_darkc), w=130, h=546), (5, 5))

weekbgc = generateGradient(*weekbg_c, w=140, h=276)
weekbgc.blit(generateGradient(*reversed(weekbg_c), w=130, h=266), (5, 5))

weekbgnc = generateGradient(*weekbg_darkc, w=140, h=276)
weekbgnc.blit(generateGradient(*reversed(weekbg_darkc), w=130, h=266), (5, 5))

weekbgwc = generateGradient(*weekbg_endc, w=140, h=276)
weekbgwc.blit(generateGradient(*reversed(weekbg_endc), w=130, h=266), (5, 5))

weekbgwnc = generateGradient(*weekbg_dendc, w=140, h=276)
weekbgwnc.blit(generateGradient(*reversed(weekbg_dendc), w=130, h=266), (5, 5))

graphbg = generateGradient(*chartbg_c, w=(994+screendiff), h=556)
graphbg.blit(generateGradient(*reversed(chartbg_c), w=(984+screendiff), h=546), (5, 5))

nextbg = pg.Surface((128, 640), pg.SRCALPHA)
pg.draw.ellipse(nextbg, (255, 255, 255, 255), pg.Rect(0, 0, 128, 640))
nextbg.blit(generateGradientHoriz(*reversed(nextbg_c), w=64, h=640), (0, 0), special_flags=pg.BLEND_RGBA_MULT)

nextbg_surf = pg.Surface((120, 632), pg.SRCALPHA)
pg.draw.ellipse(nextbg_surf, (255, 255, 255, 255), pg.Rect(0, 0, 120, 632))
nextbg_surf.blit(generateGradientHoriz(*nextbg_c, w=60, h=632), (0, 0), special_flags=pg.BLEND_RGBA_MULT)

nextbg.blit(nextbg_surf, (4, 4))

if themeworks:
    if "image_replace" in themedata:
        replace = themedata["image_replace"]
        for k in list(replace.keys()):
            print(f"replacing {k} from theme")
            vars()[k] = pg.image.load(replace[k])

if getattr(varr, "image_replace", None) != None:
    replace = getattr(varr, "image_replace", None)
    for k in list(replace.keys()):
        print(f"replacing {k} from vars")
        vars()[k] = pg.image.load(replace[k])

print("done making gradients")

if getattr(varr, "sysfont", True):
    tinyfont = pg.font.SysFont(fontname, round(18 * sizemult), bold=bold)
    smallfont = pg.font.SysFont(fontname, round(24 * sizemult), bold=bold)
    smallishfont = pg.font.SysFont(fontname, round(33 * sizemult), bold=bold)
    smallmedfont = pg.font.SysFont(fontname, round(42 * sizemult), bold=bold)
    medfont = pg.font.SysFont(fontname, round(60 * sizemult), bold=bold)
    bigfont = pg.font.SysFont(fontname, round(96 * sizemult), bold=bold)
    hugefont = pg.font.SysFont(fontname, round(144 * sizemult), bold=bold)
    giganticfont = pg.font.SysFont(fontname, round(320 * sizemult), bold=bold)
else:
    tinyfont = pg.font.Font(fontname, round(18 * sizemult))
    smallfont = pg.font.Font(fontname, round(24 * sizemult))
    smallishfont = pg.font.Font(fontname, round(33 * sizemult))
    smallmedfont = pg.font.Font(fontname, round(42 * sizemult))
    medfont = pg.font.Font(fontname, round(60 * sizemult))
    bigfont = pg.font.Font(fontname, round(96 * sizemult))
    hugefont = pg.font.Font(fontname, round(144 * sizemult))
    giganticfont = pg.font.Font(fontname, round(320 * sizemult))
weatherth = th.Thread(target=getWeather, daemon=True)
weatherth.start()
print("weather thread started")
rrt.start()
rrtt.start()
print("timers started (we changed the order of these functions)")
global rawframe
rawframe = np.zeros((1, 1, 3), np.uint8)
def reader_updater():
    global realstream
    global rawframe
    print(realstream.read())
    print("READ READ READ READ READ READ READ")
    fff = getattr(varr, "forcestreamfps", False)
    frams = realstream.get(cv2.CAP_PROP_FPS)
    while True:
        rt, rawframe = realstream.read()
        if fff:
            time.sleep(1/frams)

@profiling_sect("time_math")
def lerp(a, b, n):
    return a*(1-n) + b*n

@profiling_sect("time_math")
def lerp2(a, b, n):
    t = 1 - (1 - n) * (1 - n)
    return a*(1-t) + b*t

@profiling_sect("time_blits")
def alphablit(surf, alpha, coord):
    transparent = pg.surface.Surface((surf.get_width(), surf.get_height())).convert_alpha()
    transparent.fill((255, 255, 255, alpha))
    transparent.blit(surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
    window.blit(transparent, coord)

@profiling_sect("time_blits")
def alphablit2(surf, alpha, coord, dest):
    transparent = pg.surface.Surface((surf.get_width(), surf.get_height())).convert_alpha()
    transparent.fill((255, 255, 255, alpha))
    transparent.blit(surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
    dest.blit(transparent, coord)
    return transparent

@profiling_sect("time_math")
def expandSurface(surf, expansion):
    newsurf = pg.surface.Surface((surf.get_width() + expansion*2, surf.get_height() + expansion*2))
    newsurf.fill((255, 255, 255, 0))
    newsurf.blit(surf, (expansion, expansion))
    return newsurf

buffer = pg.Surface((140, 276))
pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 140, 276))
buffer = blur(expandSurface(buffer, 6), 4)
cache["7daybuffer"] = buffer

buffer = pg.Surface((994+screendiff, 92))
pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 994+screendiff, 92))
buffer = blur(expandSurface(buffer, 6), 4)
cache["hourlybuffer"] = buffer

buffer = pg.Surface((350-12, 92))
pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 350-12, 92))
buffer = blur(expandSurface(buffer, 6), 4)
cache["hourlysidebar"] = buffer

@profiling_sect("time_math")
def expandSurfaceAlpha(surf, expansion):
    newsurf = pg.surface.Surface((surf.get_width() + expansion*2, surf.get_height() + expansion*2)).convert_alpha()
    newsurf.fill((255, 255, 255, 0))
    newsurf.blit(surf, (expansion, expansion))
    return newsurf

@profiling_sect("time_math")
def expandSurfaceDelicate(surf, expansion):
    newsurf = pg.surface.Surface((surf.get_width() + expansion*2, surf.get_height() + expansion*2), pg.SRCALPHA)
    newsurf.blit(surf, (expansion, expansion))
    return newsurf

@profiling_sect("time_ui")
def drawshadowtext(text, size, x, y, offset, shadow=127, totala=255, wind=window, filters=None):
    text = str(text)
    usecache = True
    if text in textcache:
        if size in textcache[text]:
            textn = textcache[text][size][0]
            textsh = textcache[text][size][1]
            textbland = textcache[text][size][2]
        else:
            usecache = False
    else:
        usecache = False
    debugsleep()
    
    if totala != 255:
        usecache = False
    
    if not usecache:
        textn = size.render(text, 1, (255, 255, 255, 0))
        textsh = size.render(text, 1, (shadow/1.5, shadow/1.5, shadow/1.5, shadow))
        textsh = blur(expandSurface(textsh, 6), 4)
        
        if totala != 255:
            buf = pg.Surface((textsh.get_width(), textsh.get_height()))
            buf.fill((255, 255, 255))
            alphablit2(buf, 255-totala, (0, 0), textsh)
        
        
        textbland = size.render(text, 1, (255, 255, 255, 255))
        if totala == 255:
            if not text in textcache:
                textcache[text] = {}
            textcache[text][size] = []
            textcache[text][size].append(textn)
            textcache[text][size].append(textsh)
            textcache[text][size].append(textbland)
    if filters != None:
        for filter in filters:
            if filter.pre:
                filter.filter_pre(text, size, (x, y), totala)
    if filters != None:
        for filter in filters:
            if filter.main:
                if filter.shadow == 0:
                    textn = filter.filter(text, size, textn, (x, y), totala)
                elif filter.shadow == 1:
                    textsh = filter.filter(text, size, textsh, (x, y), totala)
                elif filter.shadow == 2:
                    textn, textsh = filter.filter(text, size, (textn, textsh), (x, y), totala)
    if totala != 255:
        wind.blit(textsh, (x+offset, y+offset), special_flags=pg.BLEND_RGBA_MULT)
        alphablit2(textn, totala, (x, y), wind)
    else:
        wind.blit(textsh, (x+offset, y+offset), special_flags=pg.BLEND_RGBA_MULT)
        wind.blit(textn, (x, y))
    if filters != None:
        for filter in filters:
            if filter.post:
                filter.filter_post(text, size, (textn, textsh, (textn, textsh))[filter.shadow], (x, y), totala)
    return textbland

@profiling_sect("time_ui")
def drawshadowtextroto(text, size, x, y, angle, offset, shadow=127, totala=255, rx=0, ry=0, wind=window):
    text = str(text)
    usecache = True
    if text in textcache:
        if size in textcache[text]:
            textn = textcache[text][size][0]
            textsh = textcache[text][size][1]
            textbland = textcache[text][size][2]
        else:
            usecache = False
    else:
        usecache = False
    debugsleep()
    
    if totala != 255:
        usecache = False
    
    if not usecache:
        textn = size.render(text, 1, (255, 255, 255, 0))
        textsh = size.render(text, 1, (shadow/1.5, shadow/1.5, shadow/1.5, shadow))
        textsh = blur(expandSurface(textsh, 6), 4)
        
        if totala != 255:
            buf = pg.Surface((textsh.get_width(), textsh.get_height()))
            buf.fill((255, 255, 255))
            alphablit2(buf, 255-totala, (0, 0), textsh)
        
        if totala == 255:
            if not text in textcache:
                textcache[text] = {}
                textcache[text][size] = []
        if totala == 255:
            textcache[text][size].append(textn)
            textcache[text][size].append(textsh)
        textbland = size.render(text, 1, (255, 255, 255, 255))
        if totala == 255:
            textcache[text][size].append(textbland)
    
    rotsh = pg.transform.rotate(textsh, angle)
    rotn = pg.transform.rotate(textn, angle)
    if totala != 255:
        wind.blit(rotsh, (x+offset+rx*rotsh.get_width(), y+offset-ry*rotsh.get_height()), special_flags=pg.BLEND_RGBA_MULT)
        alphablit2(rotn, totala, (x+rx*rotsh.get_width(), y-ry*rotsh.get_height()), wind)
    else:
        wind.blit(rotsh, (x+offset+rx*rotsh.get_width(), y+offset-ry*rotsh.get_height()), special_flags=pg.BLEND_RGBA_MULT)
        wind.blit(rotn, (x+rx*rotsh.get_width(), y-ry*rotsh.get_height()))
    return textbland

@profiling_sect("time_ui")
def drawshadowtemp(temp, size, x, y, offset, shadow=127):
    temp = str(temp)
    usecache = True
    if temp in tempcache:
        if size in tempcache[temp]:
            textn = tempcache[temp][size][0]
            textsh = tempcache[temp][size][1]
        else:
            usecache = False
    else:
        usecache = False
    
    if not usecache:
        textn = size.render(temp, 1, (255, 255, 255, 255))
        textsh = size.render(temp, 1, (shadow/1.5, shadow/1.5, shadow/1.5, shadow))
        if len(temp) == 3:
            textn = pg.transform.smoothscale_by(textn, (2/3, 1))
            textsh = pg.transform.smoothscale_by(textsh, (2/3, 1))
        textsh = blur(expandSurface(textsh, 6), 4)
        if not temp in tempcache:
            tempcache[temp] = {}
        tempcache[temp][size] = []
        tempcache[temp][size].append(textn)
        tempcache[temp][size].append(textsh)
    window.blit(textsh, (x+offset, y+offset), special_flags=pg.BLEND_RGBA_MULT)
    window.blit(textn, (x, y))
    return textn
def drawshadowcrunch(text, size, x, y, offset, targetWidth, shadow=127, totala=255, wind = window, filters=[]):
    return drawshadowtext(text, size, x, y, offset, shadow, totala, wind, [CrunchFilter(target=targetWidth)] + filters)

@profiling_sect("time_math")
def mapnum(minv, maxv, nminv, nmaxv, val):
    firstspan = maxv-minv
    secondspan = nmaxv-nminv
    valsc = val-minv
    return nminv + ((valsc / firstspan) * secondspan)

def drawshadowtextcol(text, col, size, x, y, offset, shadow=127, totala=255, wind = window, filters=[]):
    return drawshadowtext(text, size, x, y, offset, shadow, totala, wind, [GeneralColorFilter(color=col)] + filters)

@profiling_sect("time_ui")
def drawshadowcrunchcol(text, col, size, x, y, offset, targetWidth, shadow=127):
    text = str(text)
    textn = size.render(text, 1, col)
    textsh = size.render(text, 1, (shadow/1.5, shadow/1.5, shadow/1.5, shadow))
    if size.size(text)[0] > targetWidth:
        textn = pg.transform.smoothscale(textn, (targetWidth, size.size(text)[1]))
        textsh = pg.transform.smoothscale(textsh, (targetWidth, size.size(text)[1]))
    textsh = blur(expandSurface(textsh, 6), 4)
    window.blit(textsh, (x+offset, y+offset), special_flags=pg.BLEND_RGBA_MULT)
    window.blit(textn, (x, y))
    return size.render(text, 1, (255, 255, 255, 255))

@profiling_sect("time_math")
def getcrunch(text, size, targetWidth, targetHeight):
    text = str(text)
    textn = size.render(text, 1, (255, 255, 255))
    textsh = size.render(text, 1, (0, 0, 0))
    crunchw = 1
    crunchh = 1
    if textn.get_width() > targetWidth:
        crunchw = targetWidth/textn.get_width()
    if textn.get_height() > targetHeight:
        crunchh = targetHeight/textsh.get_height()
    return crunchw, crunchh, textn.get_width(), textsh.get_height()

def safedivide(x, y):
    if y == 0:
        return 0
    else:
        return x/y

@profiling_sect("time_ui")
def drawshadowbigcrunch(text, col, size, x, y, offset, targetWidth, targetHeight, shadow=127):
    text = str(text)
    usecache = True
    
    if text in bigcrunchcache:
        if size in bigcrunchcache[text]:
            if col in bigcrunchcache[text][size]:
                textn = bigcrunchcache[text][size][col][0]
                textsh = bigcrunchcache[text][size][col][1]
                textbland = bigcrunchcache[text][size][col][2]
            else:
                usecache = False
        else:
            usecache = False
    else:
        usecache = False
    
    if not usecache:
        textn = size.render(text, 1, col)
        textsh = size.render(text, 1, (shadow/1.5, shadow/1.5, shadow/1.5, shadow))
        if textn.get_width() > targetWidth:
            textn = pg.transform.smoothscale_by(textn, (targetWidth/textn.get_width(), 1))
            textsh = pg.transform.smoothscale_by(textsh, (targetWidth/textsh.get_width(), 1))
        if textn.get_height() > targetHeight:
            textn = pg.transform.smoothscale_by(textn, (1, targetHeight/textn.get_height()))
            textsh = pg.transform.smoothscale_by(textsh, (1, targetHeight/textsh.get_height()))
        textsh = blur(expandSurface(textsh, 6), 4)
        if text in bigcrunchcache:
            if size in bigcrunchcache[text]:
                if not col in bigcrunchcache[text][size]:
                    bigcrunchcache[text][size][col] = []
            else:
                bigcrunchcache[text][size] = {}
                bigcrunchcache[text][size][col] = []
        else:
            bigcrunchcache[text] = {}
            bigcrunchcache[text][size] = {}
            bigcrunchcache[text][size][col] = []
        textbland = size.render(text, 1, (255, 255, 255, 255))
        bigcrunchcache[text][size][col].append(textn)
        bigcrunchcache[text][size][col].append(textsh)
        bigcrunchcache[text][size][col].append(textbland)
    window.blit(textsh, (x+offset, y+offset), special_flags=pg.BLEND_RGBA_MULT)
    window.blit(textn, (x, y))
    return textbland

@profiling_sect("time_ui")
def drawshadowtempcol(temp, col, size: pg.font.Font, x, y, offset, shadow=127):
    temp = str(temp)
    usecache = True
    if temp in tempcachecol:
        if size in tempcachecol[temp]:
            if col in tempcachecol[temp][size]:
                textn = tempcachecol[temp][size][col][0]
                textsh = tempcachecol[temp][size][col][1]
            else:
                usecache = False
        else:
            usecache = False
    else:
        usecache = False
    
    if not usecache:
        textn = size.render(temp, 1, col)
        textsh = size.render(temp, 1, (shadow/1.5, shadow/1.5, shadow/1.5, shadow))
        if len(temp) == 3:
            textn = pg.transform.smoothscale_by(textn, (2/3, 1))
            textsh = pg.transform.smoothscale_by(textsh, (2/3, 1))
        textsh = blur(expandSurface(textsh, 6), 4)
        if temp in tempcachecol:
            if size in tempcachecol[temp]:
                if not col in tempcachecol[temp][size]:
                    tempcachecol[temp][size][col] = []
            else:
                tempcachecol[temp][size] = {}
                tempcachecol[temp][size][col] = []
        else:
            tempcachecol[temp] = {}
            tempcachecol[temp][size] = {}
            tempcachecol[temp][size][col] = []
        tempcachecol[temp][size][col].append(textn)
        tempcachecol[temp][size][col].append(textsh)
    window.blit(textsh, (x+offset, y+offset), special_flags=pg.BLEND_RGBA_MULT)
    window.blit(textn, (x, y))
    return textn

@profiling_sect("time_math")
def parsetimelength(timestamp):
    time = timestamp.split("/")[1]
    #2DT6H for example
    finalhours = 0
    delt = it.parse_duration(time)
    days = delt.days
    secs = delt.seconds
    secs /= 3600
    secs = int(secs)
    finalhours += days*24
    finalhours += secs
    return finalhours

@profiling_sect("time_math")
def parseRawTimeStamp(timestamp):
    time = dt.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S+00:00/"+timestamp.split("/")[1])
    time = time - dt.timedelta(hours=4)
    periodtime = parsetimelength(timestamp)
    return (time, time + dt.timedelta(hours=periodtime), periodtime)

@profiling_sect("time_math")
def nonezero(val):
    return 0 if val == None else val

@profiling_sect("time_math")
def getValuesHourly(values):
    #we need to get 24 hours of values
    
    #find offset
    now = dt.datetime.now()
    offset = 0
    alltimes = []
    for value in range(len(values)):
        ti = values[value]["validTime"].split("/")[0]
        length = it.parse_duration(values[value]["validTime"].split("/")[1])
        time = it.parse_datetime(ti).astimezone(tz.timezone(getattr(varr, "timezone", "EST")))
        tim = length.seconds / 3600
        tim += length.days * 24
        for i in range(int(tim)):
            alltimes.append((time + dt.timedelta(hours=i)).astimezone(tz.timezone(getattr(varr, "timezone", "EST"))))
    now.replace(tzinfo=tz.timezone(getattr(varr, "timezone", "EST")))
    for time in range(len(alltimes)):
        if now.astimezone(tz.timezone(getattr(varr, "timezone", "EST"))) > alltimes[time].astimezone(tz.timezone(getattr(varr, "timezone", "EST"))):
            offset = time
    vals = []
    for value in values:
        val = value["value"]
        tstart, tend, t = parseRawTimeStamp(value["validTime"])
        for i in range(t):
            vals.append(int(val))
        if len(vals) >= 25+offset:
            break
    if len(vals) < 25+offset:
        while len(vals) < 25+offset:
            vals.append(vals[-1])
    return vals[offset:]

@profiling_sect("time_ui")
def makehourlygraph():
    w = 984+screendiff
    h = 546
    surf = pg.Surface((w, h)).convert_alpha()
    surf2 = pg.Surface((w, h)).convert_alpha()
    
    temps = weatherraw["temperature"][0:25]
    cloud = weatherraw["cloudCover"][0:25]
    precip = weatherraw["precipChance"][0:25]
    #for val in getValuesHourly(weatherraw["properties"]["temperature"]["values"]):
    #    temps.append(round(float(val)*1.8+32))
    offset = 0
    mintemp = min(temps)
    maxtemp = max(temps)
    medtemp = round((mintemp+maxtemp)/2)
    #time = dt.now(tz.utc)
    #order: cloud, precip, temp
    surf.fill((255, 255, 255, 0))
    surf2.fill((255, 255, 255))
    
    for i in range(24):
        pg.draw.line(surf2, (0, 0, 0), (mapnum(0, 24, 0, w, i), mapnum(100, 0, 0, h-6, cloud[i])+2), (mapnum(0, 24, 0, w, i+1), mapnum(100, 0, 0, h-6, cloud[i+1])+2), 6)
    for i in range(24):
        pg.draw.line(surf, (255, 127, 0), (mapnum(0, 24, 0, w, i), mapnum(100, 0, 0, h-6, cloud[i])), (mapnum(0, 24, 0, w, i+1), mapnum(100, 0, 0, h-6, cloud[i+1])), 3)
    for i in range(24):
        pg.draw.line(surf2, (0, 0, 0), (mapnum(0, 24, 0, w, i), mapnum(100, 0, 0, h-6, precip[i])+2), (mapnum(0, 24, 0, w, i+1), mapnum(100, 0, 0, h-6, precip[i+1])+2), 6)
    for i in range(24):
        pg.draw.line(surf, (0, 255, 255), (mapnum(0, 24, 0, w, i), mapnum(100, 0, 0, h-6, precip[i])), (mapnum(0, 24, 0, w, i+1), mapnum(100, 0, 0, h-6, precip[i+1])), 3)
    for i in range(24):
        pg.draw.line(surf2, (0, 0, 0), (mapnum(0, 24, 0, w, i), mapnum(maxtemp, mintemp, 0, h-6, temps[i])+2), (mapnum(0, 24, 0, w, i+1), mapnum(maxtemp, mintemp, 0, h-6, temps[i+1])+2), 6)
    for i in range(24):
        pg.draw.line(surf, (255, 0, 0), (mapnum(0, 24, 0, w, i), mapnum(maxtemp, mintemp, 0, h-6, temps[i])), (mapnum(0, 24, 0, w, i+1), mapnum(maxtemp, mintemp, 0, h-6, temps[i+1])), 3)
    
    surf2 = blur(expandSurface(surf2, 6), 4)
    
    return surf, surf2, {"mintemp": mintemp, "maxtemp": maxtemp, "medtemp": medtemp}

@profiling_sect("time_math")
def trail(num):
    ln = str(num)
    if len(ln) < 2:
        return "0" + ln
    return ln

eighteen_coconutties = pg.Surface((screenwidth, 768), pg.SRCALPHA)

def domusic(warn=False):
    if not sound:
        return
    global music
    global shuffle
    now = dt.datetime.now()
    if not warn:
        if True:
            if True:
                if sound:
                    def egr(st):
                        if len(st) < 11:
                            return "0" + st
                    sunset = dt.datetime.strptime(egr(sunrises["results"]["sunset"]), "%I:%M:%S %p")
                    sunrise = dt.datetime.strptime(egr(sunrises["results"]["sunrise"]), "%I:%M:%S %p")
                    night = False
                    if musicmode == "playlist":
                        if not manualmusic:
                            if music == None:
                                musicc = pg.mixer.Sound(os.path.join(playmusic, rd.choice(stripdss(os.listdir(playmusic)))))
                                music = musicc.play(fade_ms=1000)
                            elif not music.get_busy():
                                musicc = pg.mixer.Sound(os.path.join(playmusic, rd.choice(stripdss(os.listdir(playmusic)))))
                                music = musicc.play(fade_ms=1000)
                            if shuffle:
                                shuffle = 0
                                music.fadeout(1000)
                                musicc = pg.mixer.Sound(os.path.join(playmusic, rd.choice(stripdss(os.listdir(playmusic)))))
                                music = musicc.play(fade_ms=1000)

                        else:
                            if music == None:
                                musicc = pg.mixer.Sound(os.path.join(playmusic, rd.choice(stripdss(os.listdir(playmusic)))))
                                music = musicc.play(-1, fade_ms=1000)
                            if shuffle:
                                shuffle = 0
                                music.fadeout(1000)
                                musicc = pg.mixer.Sound(os.path.join(playmusic, rd.choice(stripdss(os.listdir(playmusic)))))
                                music = musicc.play(-1, fade_ms=1000)
                    else:
                        global playingmusic
                        if True:
                            if now.hour > sunset.hour:
                                night = True
                            if now.hour < sunrise.hour:
                                night = True
                            if now.hour == sunrise.hour:
                                if now.minute < sunrise.minute:
                                    night = True
                            if now.hour == sunset.hour:
                                if now.minute > sunset.minute:
                                    night = True
                            if (1 + night) != playingmusic:
                                playingmusic = 1 + night
                                if playingmusic == 1:
                                    nighttheme.fadeout(1000)
                                    daytheme.play(-1, fade_ms=1000)
                                elif playingmusic == 2:
                                    daytheme.fadeout(1000)
                                    nighttheme.play(-1, fade_ms=1000)
    else:
        if musicmode == "playlist":
            music.fadeout(1000)
        else:
            daytheme.fadeout(1000)
            nighttheme.fadeout(1000)

@profiling_sect("time_math")
def roundd(val, precision=0):
    if val in [None, "Error"]:
        return "Error"
    else:
        return round(val, precision)

@profiling_sect("time_math")
def stripdss(array: list):
    newar = array
    if ".DS_Store" in newar:
        newar.remove(".DS_Store")
    return newar

def imagethread():
    if writer:
        while True:
            eventt.wait()
            if not stinky:
                #winarray = pg.surfarray.array3d(window)
                #winarray = cv2.cvtColor(winarray, cv2.COLOR_RGB2BGR)
                #winarray = cv2.transpose(winarray)
                
                winarray = pg.image.tobytes(window, "RGB")
            #global realwriter
            #realwriter.stdin.write(winarray.tobytes())
            
                #pipe = os.open("lsvid", os.O_WRONLY)
                #chsize = 16384
                #dat = bytes(winarray)
                #for i in range(0, len(dat), chsize):
                #    # Write to named pipe as writing to a file (but write the data in small chunks).
                #    os.write(pipe, dat[i:chsize+i])
                #os.close(pipe)
                
                global realwriter
                #realwriter.stdin.write(bytes(winarray))
                realwriter.stdin.write(winarray)
            eventt.clear()

print("pumping events")
pg.event.pump()
def main():
    realdebug = False
    loadingd = 0
    bottomtomorrow = 0
    working = True
    global playingmusic
    playingmusic = 0
    view = 0
    alertscroll = 0
    alertscrollbig = 0
    alertshow = 0
    showingalert = 0
    alertdir = 1
    alerttimer = 300
    clock = pg.time.Clock()
    angl = 0
    night = False
    nightv= False
    global music
    music = None
    global shuffle
    shuffle = 0
    redded = False
    changetime = 60 * 15
    baselinetime = 60 * 4
    justswitched = True
    transitiontime = 0
    ticker = 0
    tickertimer = 60 * 4
    tickerbase = 60 * 4
    overdrawtime = 0
    
    global eighteen_coconutties
    
    alerttimeout = 60 * 10
    adindex = -1
    scrollalert = False
    alerttarget = 0
    lastname = ""
    name = ""
    overridetime = 0
    
    showfps = False
    
    sidebarscroll = 0
    sidebarnamescroll = 0
    sidebartimer = 0
    sidebarsection = 0
    sidebarstart = 0
    sidebaractive = False
    
    justticked = False
    
    def fader():
        nonlocal baselinetime
        if justswitched:
            baselinetime = changetime*1
            return 1
        if changetime < 15:
            return ((15-changetime)/15)**2
        if changetime > (baselinetime-15):
            return ((changetime - (baselinetime-15))/15)**2
        return 0
    def tickerfader():
        nonlocal tickerbase
        if justticked:
            tickerbase = tickertimer*1
        if tickertimer > (tickerbase-15):
            return ((tickertimer - (tickerbase-15))/15)**2
        if tickertimer < 15:
            return ((15-tickertimer)/15)**2
        return 0
    def overdraw():
        if overdrawtime == 0:
            return
        fade = 1-(overdrawtime/15)**2
        if not usebg:
            window.blit(gradient if not redmode else gradientred, (-fade*screenwidth, 0))
        else:
            if smoothsc:
                window.blit(pg.transform.smoothscale(bgimage if not redmode else bgimager, (screenwidth, 768)), (-fade*screenwidth, 0))
            else:
                window.blit(pg.transform.scale(bgimage if not redmode else bgimager, (screenwidth, 768)), (-fade*screenwidth, 0))
        window.blit(topgradient if not redmode else topgradientred, (0, -fade*64))
        window.blit(topshadow, (0, 64-fade*64), special_flags=pg.BLEND_RGBA_MULT)
        
        realbotg = (bottomgradient if not redmode else bottomgradientred)
        window.blit(realbotg, (0, 768-realbotg.get_height()+fade*64))
        window.blit(bottomshadow, (0, 768-realbotg.get_height()-bottomshadow.get_height()+64*fade), special_flags=pg.BLEND_RGBA_MULT)
    
    totalseg = 1#2 + (len(customslides) > 0)
    
    currentscene = 0
    currentsection = 0
    
    rotatee = 0
    
    cflag = False
    lsd = 0
    
    schedule_fired = False #this variable exists so that we don't accidentally start the presentation twice in a minute, though that would only be possible if the slide time was really short
    
    sectionscroll = 0
    
    #logotex = sdl.Texture.from_surface()
    #cache
    
    #currently:
    #hourlygraph
    @profiling_sect("time_math")
    def namer(name, preview=False):
        if preview:
            if "$2" in name or "$3" in name:
                return ""
            if compact:
                return name.replace("$1", "36h")
            else:
                return name.replace("$1", "36-Hour")
        if compact:
            return name.replace("$", "")
        else:
            return name.replace("$1", periods['daypartName'][0+bottomtomorrowm]).replace("$2", periods['daypartName'][1+bottomtomorrowm]).replace("$3", periods['daypartName'][2+bottomtomorrowm])
    sections = [11, 3]
    print("main loop started")
    
    def dointro():
        if justswitched:
            changetime = 5 * 60
        nam = lang["sectionnames"][currentsection]
        nextup = lang["nextup"]
        
        animtime = (5 * 60 - changetime) / (5 * 60)
        
        textorigin = -bigfont.size(nextup)[0]
        textorigin2 = -bigfont.size(nam)[0]
        
        drawshadowtext(nextup, bigfont, lerp(textorigin, screenwidth, animtime), 256, 5)
        
        drawshadowtext(nam, bigfont, lerp(screenwidth, textorigin2, animtime), 404, 5)
    
    try:
        global loading
        loading = True
    except:
        pass
    while working:
        justticked = False
        global stream
        global rawframe
        delta = clock.tick(60) / 1000
        profst = time.perf_counter()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                working = False
            if not loading:
                global bottomtomorrowm
                if bottomtomorrowm:
                    if bottomtomorrow == 0:
                        bottomtomorrow = 1
                if event.type == pg.MOUSEBUTTONDOWN:
                    if event.button == pg.BUTTON_LEFT:
                        bottomtomorrow += 1
                        if bottomtomorrow > 19:
                            bottomtomorrow = 0
                        nightv += 1
                        if nightv > 4:
                            nightv = 0
                        
                        ticker += 1
                    elif event.button == pg.BUTTON_RIGHT:
                        bottomtomorrow = 0
                        alertshow = 0
                        nightv = False
                        view += 1
                        if currentsection != 2:
                            if view > sections[currentsection]:
                                view = 0
                        else:
                            if view > len(customslides):
                                view = 0
                        justswitched = True
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_EQUALS:
                    realwindow.set_fullscreen(True)
                elif event.key == pg.K_BACKSLASH:
                    realwindow.set_fullscreen(False)
                elif event.key == pg.K_MINUS:
                    shuffle = 1
                elif event.key == pg.K_9:
                    pg.display.iconify()
                elif event.key == pg.K_1:
                    currentscene = 0
                elif event.key == pg.K_2:
                    currentscene = -1
                elif event.key == pg.K_3:
                    currentscene = 1
                elif event.key == pg.key.key_code("c"):
                    cflag = True
                elif event.key == pg.key.key_code("f"):
                    showfps = not showfps
                    overridetime = 5 * 60
                    name = "Toggled FPS View!"
                elif event.key == pg.key.key_code("d"):
                    realdebug = not realdebug
                    overridetime = 5 * 60
                    name = "Toggled debug mode!"
                elif event.key == pg.key.key_code("r"):
                    redded = not redded
                    overridetime = 5 * 60
                    name = "Toggled red mode test!"
                elif event.key == pg.key.key_code("s"):
                    global skipflag
                    skipflag = True
                elif event.key == pg.key.key_code("x"):
                    raise InterruptedError("This is a test exception!")
                elif event.key == pg.key.key_code("e"):
                    try:
                        os.mkdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "export"))
                    except:
                        pass
                    pg.image.save(gradient, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "gradient.png"))
                    pg.image.save(gradientred, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "gradientred.png"))
                    pg.image.save(topgradient, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "topgradient.png"))
                    pg.image.save(topgradienthealth, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "topgradienthealth.png"))
                    pg.image.save(topgradientcustom, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "topgradientcustom.png"))
                    pg.image.save(topgradientred, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "topgradientred.png"))
                    pg.image.save(bottomgradient, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "bottomgradient.png"))
                    pg.image.save(ldlgradient, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "ldlgradient.png"))
                    pg.image.save(weekbgc, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "weekbgc.png"))
                    pg.image.save(weekbgnc, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "weekbgnc.png"))
                    pg.image.save(weekbgwc, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "weekbgwc.png"))
                    pg.image.save(weekbgwnc, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "weekbgwnc.png"))
                    pg.image.save(graphbg, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "graphbg.png"))
                    pg.image.save(hourlybg, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "hourlybg.png"))
                    pg.image.save(nextbg, os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "nextbg.png"))
                    #pg.image.save(turnintoashadow(weathericons[bottomtomorrow]).convert_alpha(), os.path.join(os.path.dirname(os.path.abspath(__file__)), "export", "corrupt.png"))
                    
                    overridetime = 5 * 60
                    name = "Exported gradients successfully!"
                elif event.key == pg.key.key_code("b"):
                    sidebaractive = True
                    sidebartimer = 0
                    sidebarsection = 0
                    sidebarstart = 0
                elif event.key == pg.key.key_code("u"):
                    currentscene = 0
                    currentsection = 0
                    view = 0
                    changetime = 60*4
                    eighteen_coconutties = window.copy()
        if not working:
            break
        perfit = (True if not performance else justswitched)
        fading = fader()
        cuefade = 0
        if currentsection == 0 and view == 0 and schedule_active and changetime >= 60*3+45 and not loading:
            cuefade = ((changetime-60*3-45)/15)**2
        if perfit and not streambg:
            if view == 0 and schedule_active:
                window.blit(eighteen_coconutties, (0, 0))
            if not usebg:
                window.blit(gradient if not redmode else gradientred, (-cuefade*screenwidth, 0))
            else:
                if smoothsc:
                    window.blit(pg.transform.smoothscale(bgimage if not redmode else bgimager, (screenwidth, 768)), (-cuefade*screenwidth, 0))
                else:
                    window.blit(pg.transform.scale(bgimage if not redmode else bgimager, (screenwidth, 768)), (-cuefade*screenwidth, 0))
        if streambg:
            if stream:
                st = profiling_start()
                global rawframe
                frame = cv2.cvtColor(rawframe, cv2.COLOR_BGR2RGB)
                #frame = cv2.flip(frame, 1)
                frame = cv2.transpose(frame)
                frame = cv2.resize(frame, (768, screenwidth))
                framesurf = pg.surfarray.make_surface(frame)
                window.blit(framesurf, (0, 0))
                profiling_end(st, "time_stream")
            else:
                window.fill(maskcolor)
        
        for action in actions["pre"]:
            exec(action)
        
        if loading:
            loadingd += 0.1
            angl += 5 * math.sin(math.pi * math.sin(loadingd/10))
            lgs = pg.transform.rotozoom(logo, angl - 45, math.log(loadingd/100+0.1))
            window.blit(lgs, (screenwidth/2-lgs.get_width()/2, (768/2)-lgs.get_height()/2))
            
            loadtext = smallmedfont.render("Current tasks:\n" + "\n".join(loadingtasks), 1, (255, 255, 255, 255))
            loadshadow = smallmedfont.render("Current tasks:\n" + "\n".join(loadingtasks), 1, (0, 0, 0, 100))
            alphablit(loadshadow, 127, (5+7, 5+7))
            window.blit(loadtext, (5, 5))
        elif currentscene == -1:
            now = dt.datetime.now()
            domusic()
            obstime = dt.datetime.strptime("-".join(weather2["validTimeLocal"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S")
            #obstimetemp = obstime.replace(tzinfo=tz.utc)
            #obstimetemp = obstimetemp.astimezone(tz.timezone(getattr(varr, "timezone", "UTC")))
            #obstimeshort = splubby(obstimetemp.strftime("%I:%M %p"))
            obstimeshort = splubby(obstime.strftime("%I:%M %p"))
            currenttime = splubby(now.strftime("%I:%M:%S %p"))
            currentdate = now.strftime("%a %b ") + splubby(now.strftime("%d"))
            
            if stream:
                st = profiling_start()
                window.blit(gradient, (0, 0))
                global realstream
                
                
                stretchmode = getattr(varr, "stretchmode", "stretch")
                height = getattr(varr, "streamheight", 0)
                streamy = getattr(varr, "streamy", 0)
                
                frame = cv2.cvtColor(rawframe, cv2.COLOR_BGR2RGB)
                #frame = cv2.flip(frame, 1)
                frame = cv2.transpose(frame)
                
                if stretchmode == "stretch":
                    if height == 0:
                        frame = cv2.resize(frame, (768, screenwidth))
                    else:
                        frame = cv2.resize(frame, (height, screenwidth))
                elif stretchmode == "fit":
                    if height == 0:
                        #fullscreen, but keep aspect ratio
                        aspect = frame.shape[0] / frame.shape[1]
                        frame = cv2.resize(frame, (768, int(aspect*768)))
                    else:
                        #fit to height, but keep aspect ratio
                        aspect = frame.shape[0] / frame.shape[1]
                        frame = cv2.resize(frame, (height, int(aspect*height)))
                elif stretchmode == "fill":
                    aspect = frame.shape[1] / frame.shape[0] #inverted
                    frame = cv2.resize(frame, (int(aspect*screenwidth), screenwidth))
                
                framesurf = pg.surfarray.make_surface(frame)
                #framesurf = pg.transform.rotate(framesurf, -90)
                #framesurf = pg.transform.flip(framesurf, True, False)
                #if smoothsc:
                #    framesurf = pg.transform.smoothscale(framesurf, (screenwidth, 768))
                #else:
                #    framesurf = pg.transform.scale(framesurf, (screenwidth, 768))
                xx = screenwidth/2 - framesurf.get_width()/2
                offset = sidebarscroll/2
                if (screenwidth/2 - framesurf.get_width()/2 + offset) < 0:
                    xx = 0
                else:
                    xx = screenwidth/2 - framesurf.get_width()/2 + offset
                window.blit(framesurf, (xx, streamy))
                profiling_end(st, "time_stream")
            else:
                window.fill(maskcolor)
            
            overdrawtime -= delta * 60
            overdrawtime = max(overdrawtime, 0)
            
            if sidebarscroll != 0:
                st = profiling_start()
                window.blit(sidebarred if redmode else sidebar, (screenwidth+sidebarscroll, 0))
                window.blit(sideshadow, (screenwidth+sidebarscroll-12, 0), special_flags=pg.BLEND_RGB_MULT)
                drawshadowtext(lang["yourweather"], smallmedfont, screenwidth+sidebarscroll+5, 5, 5)
                if sidebarsection == 0:
                    chosenfont = medfont
                    wrap = False
                    if chosenfont.size(realstationname)[0] > 340:
                        chosenfont = smallmedfont
                        if chosenfont.size(realstationname)[0] > 340:
                            chosenfont = smallishfont
                        else:
                            wrap = True
                    
                    if wrap:
                        drawshadowtext("\n".join(wraptext(realstationname, pg.Rect(0, 0, 350, 768), chosenfont)), chosenfont, screenwidth + sidebarnamescroll + 5, 40, 5)
                    else:
                        drawshadowtext(realstationname, chosenfont, screenwidth + sidebarnamescroll + 5, 40, 5)
                elif sidebarsection == 1:
                    vv = drawshadowtemp(f"{round(weather2['temperature'])}", hugefont, screenwidth + sidebarnamescroll + 5, 40, 5, 196)
                    drawshadowtext(f"°{t}", bigfont, screenwidth + sidebarnamescroll + vv.get_width() + 5, 50, 4, 196)
                    drawshadowtext(weather2["wxPhraseLong"], smallishfont, screenwidth + sidebarnamescroll + 5, 190, 5)
                    drawshadowtext(f"{lang['wind']}: {lang['calm'] if weather2['windDirectionCardinal'] != 'CALM' else '{} @ {} {}MPH'.format(lang['windDirectionCardinal'], weather2['windSpeed'], kmpb)}\n{lang['humid']}: {weather2['relativeHumidity']}%\n{lang['precipshort']}: {weather2['precip24Hour']}{prec_c}\n{lang['visib']}: {weather2['visibility']}{visi_c}\n{lang['feels']}: {round(weather2['temperatureFeelsLike'])}°{t}\n{lang['pressure']}: {weather2['pressureAltimeter']}{pres_s}", smallishfont, screenwidth + sidebarnamescroll + 5, 225, 5)
                elif sidebarsection == 2:
                    drawshadowtext(lang['viewnames'][4], smallmedfont, screenwidth + sidebarnamescroll + 5, 60, 5)
                    for i in range(10):
                        now = dt.datetime.now() + dt.timedelta(hours=i)
                        drawshadowtext(splubby(now.strftime("%I%p")), smallfont, screenwidth + sidebarnamescroll + 5, 132+50*i, 5)
                        
                        drawshadowtemp(weatherraw["temperature"][i], smallmedfont, screenwidth + sidebarnamescroll + 70, 120+50*i, 5)
                        drawshadowtext(weatherraw["wxPhraseShort"][i], smallfont, screenwidth + sidebarnamescroll + 140, 122+50*i, 5)
                        #drawshadowtempcol(weatherraw["temperatureFeelsLike"][i], (255, 0, 0) if weatherraw["temperatureFeelsLike"][i]>weatherraw["temperature"][i] else ((255, 255, 255) if weatherraw["temperatureFeelsLike"][i]==weatherraw["temperature"][i] else (0, 255, 255)), smallishfont, screenwidth + sidebarnamescroll + 140, 140+50*i, 5)
                        drawshadowtext((str(weatherraw["windSpeed"][i]) + kmp + "mph ") + weatherraw["windDirectionCardinal"][i], smallfont, screenwidth + sidebarnamescroll + 140, 143+50*i, 5)
                        # drawshadowtext(lang["wind"] + ":", smallmedfont, 300+15+92+5, 90+96*i+40 + scr, 5)
                        # drawshadowtext((str(weatherraw["windSpeed"][i]) + kmp + "mph ") + weatherraw["windDirectionCardinal"][i], smallmedfont, 300+15+92+5, 90+92/2+96*i+40 + scr, 5)
                        # drawshadowtextcol(str(weatherraw["precipChance"][i]) + "%", (0, 255, 255), smallmedfont, 600+15+92+5, 90+96*i+40 + scr, 5)
                        # drawshadowtextcol(str(weatherraw["relativeHumidity"][i]) + "%", (255, 127, 0), smallmedfont, 600+15+92+5, 90+92/2+96*i+40 + scr, 5)
                        # drawshadowtextcol(lang["feels"] + ":", (255, 0, 0), smallmedfont, 750+15+92+5, 90+96*i+40 + scr, 5)
                        # drawshadowtextcol(str(weatherraw["temperatureFeelsLike"][i]) + "°" + t, (255, 0, 0), smallmedfont, 750+15+92+5, 90+92/2+96*i+40 + scr, 5)
                        
                elif sidebarsection == 3:
                    drawshadowtext(lang['viewnames'][10], smallmedfont, screenwidth + sidebarnamescroll + 5, 60, 5)
                    map_left = round(mappy.get_width()/2-175)
                    map_top = round(mappy.get_height()/2-250)
                    map_area = pg.Rect(map_left, map_top, 350, 500)
                    window.blit(mappy, (screenwidth + sidebarnamescroll, 768-628), map_area)
                    if sidebartimer < 2:
                        mappyind = round(sidebartimer*10)
                    elif sidebartimer < 3:
                        mappyind = 19
                    elif sidebartimer < 5:
                        mappyind = round((sidebartimer-3)*10)
                    else:
                        mappyind = 19
                    if mappyind > 19:
                        mappyind = 19
                    window.blit(mappy_heat[mappyind], (screenwidth + sidebarnamescroll, 768-628), map_area)
                    drawshadowtext(timestam[0][mappyind], smallishfont, screenwidth + sidebarnamescroll + 5, 768-628, 5)

                profiling_end(st, "time_ui")

            if sidebaractive:
                sidebarscroll = lerp(sidebarscroll, -350, 0.1)
                if sidebarsection != 0:
                    sidebarstart = lerp(sidebarstart, 1, 0.1)
                sidebartimer += delta
                if sidebartimer < 1:
                    sidebarnamescroll = lerp(sidebarnamescroll, 0, 0.2)
                elif sidebartimer < 6:
                    sidebarnamescroll = lerp(sidebarnamescroll, -350, 0.075)
                elif sidebartimer > 7:
                    sidebartimer = 0
                    sidebarsection += 1
                    if sidebarsection > 3:
                        sidebaractive = False
                else:
                    sidebarnamescroll = lerp(sidebarnamescroll, 0, 0.2)
            else:
                sidebarscroll = lerp(sidebarscroll, 0, 0.1)
                sidebarnamescroll = lerp(sidebarnamescroll, 0, 0.2)
                
            window.blit(ldlgradient, (0, 768-ldlgradient.get_height()))
            def four(fourcc):
                return "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            if realdebug:
                drawshadowtext(f"Stream FPS: {round(realstream.get(cv2.CAP_PROP_FPS))}", smallmedfont, 5, 40, 5, 127)
                drawshadowtext(f"Stream Resolution: {realstream.get(cv2.CAP_PROP_FRAME_WIDTH)}x{realstream.get(cv2.CAP_PROP_FRAME_HEIGHT)}", smallmedfont, 5, 80, 5, 127)
                drawshadowtext(f"FourCC: {four(int(realstream.get(cv2.CAP_PROP_FOURCC)))}", smallmedfont, 5, 120, 5, 127)
                drawshadowtext(f"FPS: {round(clock.get_fps())}", smallmedfont, 5, 160, 5, 127)
                drawshadowtext(f"Pixel Format: {four(int(realstream.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)))}", smallmedfont, 5, 200, 5, 127)


            if len(alerts) > 0:
                if len(alerts) > 1:
                    if alerttimer > 0:
                        alerttimer -= delta * 60
                    else:
                        if performance:
                            alertscroll = screenwidth
                        else:
                            alertscroll += 5 * delta * 60
                if alertscroll > screenwidth:
                    showingalert += 1
                    alertscroll = 0
                    alerttimer = 300
                    if showingalert > len(alerts)-1:
                        showingalert = 0
                drawshadowcrunch(alerts[showingalert]["headlineText"], smallmedfont, 5 + alertscroll, 704-64+5, 5, screenwidth-10, 127)
                if len(alerts) > 1:
                    drawshadowcrunch(alerts[(showingalert+1) if showingalert != len(alerts)-1 else 0]["headlineText"], smallmedfont, -screenwidth + 5 + alertscroll, 704-64+5, 5, screenwidth-10, 127)
            else:
                drawshadowtext(currentdate, smallmedfont, 5, 704-64+5, 5, 127, filters=filters["tickertl"])
                drawshadowtext(currenttime, smallmedfont, screenwidth - 5 - smallmedfont.size(currenttime)[0], 704-64+5, 5, 127, filters=filters["tickertr"])
            
            if tickertimer <= 0:
                ticker += 1
                if ticker > (6 + len(customtickers_m)):
                    ticker = 0
                if ticker == (6 + len(customtickers_m)):
                    adindex += 1
                    if adindex > len(ads)-1:
                        adindex = 0
                    tickertimer = 60 * actime
                else:
                    tickertimer = 60 * 4
                justticked = True
            else:
                tickertimer -= 60 * delta
            
            tickerf = tickerfader()
            
            tickerright = ""
            if ticker == 0:
                tickername = f'Last updated at {obstimeshort}'
                tickername = f'Current conditions for {realstationname}'
            elif ticker == 1:
                tickername = f'{lang["temp"]}: {round(weather2["temperature"])}°{t}'
                tickerright = f'{lang["feels"]}: {round(weather2["temperatureFeelsLike"])}°{t}'
            elif ticker == 2:
                tickername = f'{lang["humid"]}: {roundd(weather2["relativeHumidity"])}%'
                tickerright = f'{lang["uv"]}: {round(weather2["uvIndex"])}'
            elif ticker == 3:
                pressa = ["(-)", "(+)", "(-)", "(++)", "(--)"]
                tickername = f'{lang["pressure"]}: {round(weather2["pressureAltimeter"], 2)} {pres_s} {pressa[weather2["pressureTendencyCode"]]}'
            elif ticker == 4:
                if weather2["windDirectionCardinal"] != "CALM":
                    tickername = f'{lang["wind"]}: {weather2["windDirectionCardinal"]} @ {round(weather2["windSpeed"])} {kmp}mph'
                else:
                    tickername = f"{lang['wind']}: {lang['calm']}"
                if weather2["windGust"]:
                    tickerright = f"{lang['gusts']}: {weather2['windGust']} {kmp}mph"
            elif ticker == 5:
                try:
                    ceiling = nonezero(weather2["cloudCeiling"])
                except IndexError:
                    ceiling = 0
                tickername = f'{lang["visib"]}: {round(weather2["visibility"])} {visi}'
                tickerright = f'{lang["ceil"]}: {"Unlimited" if ceiling == 0 else f"{ceiling} feet"}'
            elif (len(customtickers_m) > 0 and ticker < (6 + len(customtickers_m))):
                exec(customtickers_m[ticker - 6])
            elif ticker == (6 + len(customtickers_m)):
                tickername = ads[adindex]
            overdraw()
            if not ((len(customtickers_m) > 0) and (ticker > 5) and (ticker <  (6 + len(customtickers_m)))):
                drawshadowtext(tickername, smallmedfont, 5, 768-64+5+64*tickerf, 5, 127, filters=filters["tickerbl"])
                drawshadowtext(tickerright, smallmedfont, screenwidth-5-smallmedfont.size(tickerright)[0], 768-64+5+64*tickerf, 5, 127, filters=filters["tickerbr"])
            if ldltop:
                window.blit(topgradient, (0, 0))
                if not hideleft:
                    drawshadowtext("Live Feed", smallmedfont, 5, 5, 5, 127)
                if not hideright:
                    drawshadowtext(realstationname, smallmedfont, screenwidth-10-smallmedfont.size(realstationname)[0], 5, 5, 127)
                for fixture in customfixtures:
                    exec(fixture)
            if ldlshadow:
                window.blit(bottomshadow, (0, 768-128-16), special_flags=pg.BLEND_RGBA_MULT)
                if ldltop:
                    window.blit(topshadow, (0, 64), special_flags=pg.BLEND_RGBA_MULT)
            
            if ldlwatermark:
                window.blit(watermark, (screenwidth-watermark.get_width()-5, 768-128-watermark.get_height()-5))
            
            if transitiontime > 0 and not performance:
                transitiontime -= 1
            
            #schedule time!
            if schedule_active:
                if schedule_mode == "minutes":
                    now = dt.datetime.now()
                    if (now.minute in schedule_times) and not schedule_fired:
                        #change to normal scene
                        currentscene = 0
                        justswitched = True
                        
                        if not customtransition:
                            transitiontime = 60
                        
                        schedule_fired = True
                        eighteen_coconutties = window.copy()
                    else:
                        schedule_fired = False
                elif schedule_mode == "hours":
                    now = dt.datetime.now()
                    if (now.hour in schedule_times) and (now.minute == 0) and not schedule_fired:
                        #change to normal scene
                        currentscene = 0
                        justswitched = True
                        if not customtransition:
                            transitiontime = 60
                        schedule_fired = True
                        eighteen_coconutties = window.copy()
                    else:
                        schedule_fired = False
                elif schedule_mode == "mix":
                    valid_hours = schedule_times[0]
                    valid_minutes = schedule_times[1]
                    now = dt.datetime.now()
                    if (now.hour in valid_hours) and (now.minute in valid_minutes) and not schedule_fired:
                        #change to normal scene
                        currentscene = 0
                        justswitched = True
                        if not customtransition:
                            transitiontime = 60
                        schedule_fired = True
                        eighteen_coconutties = window.copy()
                    else:
                        schedule_fired = False
            now = dt.datetime.now()
            if now.minute in sidebar_times and now.second < 20 and not sidebaractive:
                sidebaractive = True
                sidebartimer = 0
                sidebarsection = 0
                sidebarstart = 0
        else:
            if not redded:
                if redmode:
                    view = 0
                    changetime = 60 * 30
                redded = True
            domusic()
            periods = weather3["daypart"][0]
            currenttemp = giganticfont.render(f'{trail(round(weather2["temperature"]))}', 1, (255, 255, 255, 255))
            currentcondition = smallmedfont.render(weather2["wxPhraseLong"], 1, (255, 255, 255, 255))
            #top bar
            
            # window.blit(topshadow, (0, 64), special_flags=pg.BLEND_RGBA_MULT)
            # window.blit(topgradient, (0, 0))
            
            # if view == 0:
            #     window.blit(topshadow, (0, 524), special_flags=pg.BLEND_RGBA_MULT)
            #     window.blit(topgradient, (0, 460))
            #     drawshadowtext(periods[bottomtomorrow]["name"].upper(), smallmedfont, 5, 465, 5, 127)
            
            # viewnames = ["Split View", "Overview", "7-Day Forecast", "Hourly Graph", f"Weather Report ({periods[0]['name']})", f"Weather Report ({periods[1]['name']})", f"Weather Report ({periods[2]['name']})", "Alerts"]
            # viewName = viewnames[view]
            # if view == 2:
            #     nightv = 4
            #     #force view 2
            #     viewName = ["7-Day Forecast (Day)", "7-Day Forecast (Night)", "7-Day Forecast (Page 1)", "7-Day Forecast (Page 2)", "7-Day Forecast"][nightv]
            # if wttr:
            #     location = smallmedfont.render(weather["nearest_area"][0]["areaName"][0]["value"], 1, (255, 255, 255, 255))
            # drawshadowtext(viewName, smallmedfont, 824-screendiff/2-smallmedfont.size(viewName)[0]/2, 5, 5, 127)
            # drawshadowtext(dt.datetime.now().strftime(timeformattop), smallmedfont, 5, 5, 5, 127)
            # #drawshadowtext(clock.get_fps(), smallmedfont, 5, 5, 5, 127)
            # if wttr:
            #     drawshadowtext(weather["nearest_area"][0]["areaName"][0]["value"], smallmedfont, screenwidth-10-location.get_width(), 5, 5, 127)
            
            #today
            # today's forecast (min, axg, max) (deprecated)
            #drawshadowtemp("Previous 24h extremes:", smallmedfont, 5, 80, 5, 127)
            #drawshadowtempcol(round(formatMetric(weather2["features"][0]["properties"]["minTemperatureLast24Hours"])), (135, 206, 250, 255), smallmedfont,405, 80, 5, 127)
            #drawshadowtempcol(round(formatMetric(weather2["features"][0]["properties"]["maxTemperatureLast24Hours"])), (255, 140, 0, 255), smallmedfont, 480, 80, 5, 127)
            
            # current
            
            perfit = (True if not performance else justswitched)
            if view == 0:
                if justswitched:
                    alertscrollbig = 0
                    alerttimeout = 60 * 10
                scrollalert = False
                if len(alerts) > 0:
                    fnt = smallmedfont
                    if getcrunch(alert_details[alertshow], smallmedfont, 994+screendiff, 588)[0] < 1:
                        fnt = smallishfont
                        if getcrunch(alert_details[alertshow], smallishfont, 994+screendiff, 588)[1] < 0.75:
                            scrollalert = True
                            alerttarget = getcrunch(alert_details[alertshow], smallishfont, 994+screendiff, 588)[3] + 5 - 588
                    elif getcrunch(alert_details[alertshow], smallmedfont, 994+screendiff, 588)[1] < 0.75:
                        fnt = smallishfont
                        if getcrunch(alert_details[alertshow], smallishfont, 994+screendiff, 588)[1] < 0.75:
                            scrollalert = True
                            alerttarget = getcrunch(alert_details[alertshow], smallfont, 994+screendiff, 588)[3] + 5 - 588

                    if alerttimeout <= 0:
                        if scrollalert:
                            if performance:
                                if alertdir == 1:
                                    if alertscrollbig < alerttarget:
                                        alertscrollbig += 300
                                        alerttimeout = 60 * 5
                                    elif alertscrollbig >= alerttarget:
                                        alertscrollbig = 0
                                        alertdir = -1
                                        alerttimeout = 60 * 10
                                else:
                                    if alertscrollbig > 0:
                                        alertscrollbig -= 300
                                        alerttimeout = 60 * 5
                                        if alertscrollbig <= 0:
                                            alertscrollbig = 0
                                            alerttimeout = 60 * 10
                                            alertdir = 1
                                    else:
                                        alertscrollbig = 0
                                        alerttimeout = 60 * 10
                                        alertdir = 1
                            else:
                                if alertdir == 1:
                                    if alertscrollbig < alerttarget:
                                        alertscrollbig += 60 * delta
                                    else:
                                        alertscrollbig = alerttarget
                                        alertdir = -1
                                        alerttimeout = 60 * 10
                                else:
                                    if alertscrollbig > 0:
                                        alertscrollbig -= 60 * delta
                                    else:
                                        alertscrollbig = 0
                                        alertdir = 1
                                        alerttimeout = 60 * 10
                    else:
                        alerttimeout -= 60 * delta

                    if scrollalert:
                        drawshadowbigcrunch(alert_details[alertshow], (255, 224, 224), fnt, 15, 96-alertscrollbig, 5, screenwidth-10, 9999, 127)
                    else:
                        alertscroll = 0
                        drawshadowbigcrunch(alert_details[alertshow], (255, 224, 224), fnt, 15, 96, 5, screenwidth-10, 588, 127)
                else:
                    if justswitched:
                        changetime = 4 * 60
                    nam = lang["sectionnames"][currentsection]
                    namss = []
                    
                    if currentsection != 2:
                        advisory = (len(alerts)>0)
                        
                        nvn = ("viewnames" if not redmode else "viewnamesred")
                        for k, naym in enumerate(lang[[nvn, "viewnameshealth"][currentsection]][1:]):
                            if k == 0 and advisory:
                                namss.append(lang["alerts"])
                                continue
                            nm = namer(naym, True)
                            if nm != "":
                                namss.append(nm)
                    else:
                        for naym in customslides:
                            namss.append(get_lang_custom(naym[0]))
                    
                    nextup = "\n".join(namss)
                    
                    fant = bigfont# if not compact else medfont
                    fint = smallmedfont# if not compact else smallishfont
                    
                    longest = 0
                    for nameee in namss:
                        sz = fint.size(nameee)[0]
                        if sz > longest:
                            longest = sz
                    
                    animtime = (2 * 60 - changetime + 2 * 60) / (2 * 60)
                    
                    if animtime < 0:
                        animtime = 0
                    
                    if animtime > 1:
                        animtime = 1
                    
                    animtime2 = (-changetime + 60) / 60
                    
                    if animtime2 < 0:
                        animtime2 = 0
                    
                    textorigin = -fant.size(nextup)[0]
                    textorigin0 = -fant.size(nextup)[1] * 5
                    textorigin2 = -longest

                    rotatee += 1
                    
                    rotatay = pg.transform.rotate(transitionicons[currentsection], rotatee % 360)

                    window.blit(rotatay, (screenwidth-rotatay.get_width()/2, -rotatay.get_height()/2-fading*512))
                    
                    offs = fant.size(nam)
                    
                    off = squish_size_helper(offs, 1-animtime**1.4)
                    
                    drawshadowtext(nam, fant, lerp2(textorigin, 5, animtime**1.4)+offs[0]/2-off[0]/2, lerp2(64, textorigin0, animtime2)+offs[1]/2-off[1]/2, 5, filters=[SquishFilter(amount=(1-animtime**1.4))])#, screenwidth-longest-10)

                    drawshadowtext(nextup, fint, lerp2(screenwidth, screenwidth + textorigin2 - 5, animtime), lerp2(90-32+fant.size(nam)[1], 768, animtime2), 5)
            
            if currentsection == 0:
                if view == -1:
                    pass
                elif view in [1, 2] and perfit:
                    offy = (fading if (view == 1 and changetime > 15) or (view == 2 and changetime <= 15) else 0)*screenwidth
                    precip = weather2["precip1Hour"]
                    if precip == None:
                        precip = "0"
                    else:
                        precip = str(round(precip/25.4, 1))
                    currenttemp = drawshadowtemp(trail(round(weather2["temperature"])), giganticfont, 60-offy, 80, 20, 180)
                    drawshadowtext(f"°{t}", bigfont, currenttemp.get_width()+60+getattr(varr, "foffset", 0)-offy, 125, 10, 160)
                    moffset = getattr(varr, "moffset", 0)
                    if weather2["windDirectionCardinal"] != "CALM":
                        #print(weather2["features"][0]["properties"]["windSpeed"])
                        drawshadowtext(f'{lang["wind"]}: {weather2["windDirectionCardinal"]} @ {round((weather2["windSpeed"]))} {kmpb}MPH', smallmedfont, 540-offy+moffset, 125, 5, 127)
                    else:
                        drawshadowtext(f'{lang["wind"]}: {lang["calm"]}', smallmedfont, 540-offy+moffset, 125, 5, 127)
                    drawshadowtext(f'{lang["relhumid"]}: {roundd(weather2["relativeHumidity"], 1)}%', smallmedfont, 540-offy+moffset, 175, 5, 127)
                    drawshadowtext(f'{lang["precip"]}: {precip} {prec}', smallmedfont, 540-offy+moffset, 225, 5, 127)
                    drawshadowtext(f'{lang["visib"]}: {round(weather2["visibility"], 1)} {visi}', smallmedfont, 540-offy+moffset, 275, 5, 127)
                    drawshadowtext(f'{lang["feels"]}: {round(weather2["temperatureFeelsLike"])}°{t}', smallmedfont, 540-offy+moffset, 325, 5, 127)

                    pressa = ["", "(+)", "(-)", "(/)", "(\\)"]

                    drawshadowtext(f'{lang["pressure"]}: {roundd(weather2["pressureAltimeter"], 2)} {pres} {pressa[weather2["pressureTendencyCode"]]}', smallmedfont, 540-offy+moffset, 375, 5, 127)
                    #window.blit(currenttemp, (60, 80))
                    offsetw = -currentcondition.get_width()/2
                    if offsetw < -220:
                        offsetw = -220

                    drawshadowcrunch(weather2["wxPhraseLong"], smallmedfont, 60+currenttemp.get_width()/2+offsetw-offy, 400, 5, 440, 127)

                    periods = weather3["daypart"][0]
                    if bottomtomorrow == 0 and bottomtomorrowm:
                        bottomtomorrow = 1
                    offz = fading * screenwidth
                    if view == 1:
                        #tomorrow
                        # forecasted temps
                        tm1 = drawshadowtemp(trail(periods["temperature"][bottomtomorrow]), bigfont, 60-offz, 560, 10, 140)
                        #tm2 = drawshadowtempcol(periods["temperatureMin"][bottomtomorrow], (135, 206, 250), medfont, 280, 540, 7, 127)
                        #tm3 = drawshadowtempcol(periods["temperatureMax"][bottomtomorrow], (255, 140, 0), medfont, 280, 610, 7, 127)
                        drawshadowtext(f"°{t}", bigfont, tm1.get_width()+60-offz, 560, 10, 140)
                        #drawshadowtextcol(f"°{t}", (135, 206, 250, 255), medfont, tm2.get_width()+280, 540, 10, 140)
                        #drawshadowtextcol(f"°{t}", (255, 140, 0, 255), medfont, tm3.get_width()+280, 610, 10, 140)
                        if iconpack == "":
                            buffer = pg.Surface((128, 128))
                            pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 128, 128))
                            buffer = blur(expandSurface(buffer, 6), 4)
                            window.blit(buffer, (tm1.get_width() + 190-offz, 560), special_flags=pg.BLEND_RGBA_MULT)
                        else:
                            global weathershadows
                            buffer = weathershadows[bottomtomorrow]
                            window.blit(buffer, (tm1.get_width() + 190-offz, 560))
                        
                        window.blit(weathericons[bottomtomorrow], (tm1.get_width() + 180-offz, 550))
                        # other metrics
                        prval = periods["precipChance"][bottomtomorrow]
                        if prval == None:
                            prval = "0"
                        drawshadowtext(f'{lang["precipchance"]}: {prval}%', smallmedfont, 440-offz, 540, 5, 127)
                        drawshadowtext(f'{lang["wind"]}: {periods["windDirectionCardinal"][bottomtomorrow]} @ {periods["windSpeed"][bottomtomorrow]}', smallmedfont, 440-offz, 590, 5, 127)
                        drawshadowcrunch(periods["wxPhraseLong"][bottomtomorrow], smallmedfont, 440-offz, 640, 5, screenwidth-440-10, 127)
                    else:
                        drawshadowtext("\n".join(wraptext(periods["narrative"][bottomtomorrow], pg.Rect(350, 480, screenwidth-350-15, 768-64-15), smallishfont)), smallishfont, 350-offz, 480, 5, 127)
                        
                        if iconpack == "":
                            buffer = pg.Surface((192, 192))
                            pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 192, 192))
                            buffer = blur(expandSurface(buffer, 6), 4)
                            window.blit(buffer, (110-offz, 490), special_flags=pg.BLEND_RGBA_MULT)
                        else:
                            global weathershadowbig
                            buffer = weathershadowbig
                            window.blit(buffer, (110-offz, 490))
                        
                        if weathericonbig != None:
                            window.blit(weathericonbig, (100-offz, 480))
                elif view == 3 and perfit:
                    nightv = 4
                    nowisday = (periods["dayOrNight"][0] == "D")
                    # if nightv <= 1:
                    #     for i in range(7):
                    #         buffer = pg.Surface((140, 556))
                    #         pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 140, 556))
                    #         buffer = blur(expandSurface(buffer, 6), 4)
                    #         window.blit(buffer, (20 + i*142, 133), special_flags=pg.BLEND_RGBA_MULT)
                    #         window.blit(weekbg if not nightv else weekbgn, (15 + i*142, 128))
                    #         if nowisday and i == 0:
                    #             continue
                    #         if not nowisday and i == 6 and nightv:
                    #             continue
                    #         drawshadowtext(periods[i*2+(not nowisday)+nightv]["name"][0:3].upper(), smallmedfont, 15+i*142+70-smallmedfont.size(periods[i*2+(not nowisday)+nightv]["name"][0:3].upper())[0]/2, 138, 5, 127)
                    #         drawshadowtemp(periods[i*2+(not nowisday)+nightv]["temperature"], bigfont, 30 + i*142, 168, 5, 127)
                    #         drawshadowtext(f"{lang['wind']}:", smallishfont, 40 + i*142, 300, 5, 127)
                    #         drawshadowtext(periods[i*2+(not nowisday)+nightv]["windDirection"], medfont, 85+i*142-medfont.size(periods[i*2+(not nowisday)+nightv]["windDirection"])[0]/2, 330, 5, 127)
                    #         window.blit(weathericons[i*2+(not nowisday)+nightv], (21+142*i, 417+128+5))
                    # elif nightv <= 3:
                    #     for i in range(7):
                    #         buffer = pg.Surface((140, 556))
                    #         pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 140, 556))
                    #         buffer = blur(expandSurface(buffer, 6), 4)
                    #         window.blit(buffer, (20 + i*142, 133), special_flags=pg.BLEND_RGBA_MULT)
                    #         drawnight = (i % 2 == 0)
                    #         offset = not nowisday
                    #         if not nowisday:
                    #             drawnight = not drawnight
                    #         if nightv in [2, 3]:
                    #             drawnight = not drawnight
                    #         if nightv == 3:
                    #             drawnight = not drawnight
                    #         window.blit(weekbg if not drawnight else weekbgn, (15 + i*142, 128))
                    #         if nowisday and i in [0, 1] and nightv == 2:
                    #             continue
                    #         if not nowisday and i >= 5 and nightv == 3:
                    #             continue
                    #         drawshadowtext(periods[i+offset+(nightv-2)*7]["name"][0:3].upper(), smallmedfont, 15+i*142+70-smallmedfont.size(periods[i+offset+(nightv-2)*7]["name"][0:3].upper())[0]/2, 138, 5, 127)
                    #         drawshadowtemp(periods[i+offset+(nightv-2)*7]["temperature"], bigfont, 30 + i*142, 168, 5, 127)
                    #         drawshadowtext(f"{lang['wind']}:", smallishfont, 40 + i*142, 300, 5, 127)
                    #         drawshadowtext(periods[i+offset+(nightv-2)*7]["windDirection"], medfont, 85+i*142-medfont.size(periods[i+offset+(nightv-2)*7]["windDirection"])[0]/2, 330, 5, 127)
                    #         window.blit(weathericons[i+offset+(nightv-2)*7], (21+142*i, 417+128+5))
                    # else:
                    buffer = cache["7daybuffer"]
                    exfm = getattr(varr, "extendedfamount", 18)
                    for j in range(exfm):
                        i = j/2
                        drawingn = (periods["dayOrNight"][j] == "N")
                        #if nowisday and i == 0:
                        #    continue
                        #if not nowisday and i == 6 and drawingn:
                        #    continue
                        sind = 0
                        if periods["daypartName"] == None:
                            sind += 1
                        else:
                            sind += 2
                        ind = (j + sind)
                        
                        offy = fading * screenwidth * (1 if drawingn else -1)

                        off = -142+71*(20-exfm+1)/2 + 78 * nowisday + offy

                        if not drawingn:
                            off += 71

                        scrh = off

                        window.blit(buffer, (20 + scrh + i*142 - 78 * nowisday, 133+280*drawingn), special_flags=pg.BLEND_RGBA_MULT)
                        
                        now = dt.date.today()
                        plus = now + dt.timedelta(days=(j/2+sind/2))
                        
                        bgg = weekbgc if not drawingn else weekbgnc
                        if plus.weekday() >= 5:
                            bgg = weekbgwc if not drawingn else weekbgwnc
                        
                        window.blit(bgg, (15 + scrh + i*142 - 78 * nowisday, 128+280*drawingn))
                        
                        drawshadowtext(weather3["dayOfWeek"][math.floor(j/2+sind/2)][0:(3 if locl != "de-DE" else 2)].upper(), smallmedfont, 15+ scrh +i*142 - 78 * nowisday+70-smallmedfont.size(weather3["dayOfWeek"][math.floor(j/2+sind/2)][0:(3 if locl != "de-DE" else 2)].upper())[0]/2, 138+280*drawingn, 5, 127)
                        drawshadowtemp(trail(periods["temperature"][ind]), medfont, 85 - 78 * nowisday - medfont.size(trail(str(periods["temperature"][ind])))[0]/2 + scrh + i*142, 172+280*drawingn, 5, 127)
                        if weathericons[ind] != None:
                            window.blit(weathericons[ind], (21+ scrh +142*i - 78 * nowisday, 417+128+5-280*(not drawingn)))
                        drawshadowtext(f'{lang["wind"]}: {periods["windDirectionCardinal"][ind]}', smallfont, 84+ scrh - 78 * nowisday +i*142-smallfont.size(f'{lang["wind"]}: {periods["windDirectionCardinal"][ind]}')[0]/2, 234+280*drawingn, 5, 127)
                        #if partnered:
                        #    window.blit(turnintoashadow(logosurf), (20 - 39 * nowisday + 142 * 7, 138))
                        #    window.blit(logosurf, (15 - 39 * nowisday + 142 * 7, 133))
                elif view == 4 and perfit:
                    #drawshadowtext("\n".join(wraptext("Unimplemented! If you want to see this, wait for the official update!", pg.Rect(5, 5, 1356, 768-128-64), medfont)), medfont, 5, 133, 5)
                    scr = 0
                    ct = 15*60 - changetime
                    if ct > 2*60:
                        scr = -1728 * (ct - 2*60) / (11*60)
                    if ct > 13*60:
                        scr = -1728
                    for i in range(24):
                        offy = fading * screenwidth * (1 if (i%2) else -1)
                        #skip if not visible
                        if (128+96*i + scr) > 768:
                            continue
                        
                        if (128+96*i + scr) < -101:
                            continue
                        
                        window.blit(cache["hourlybuffer"], (20+offy, 133 + 96*i + scr), special_flags=pg.BLEND_RGBA_MULT)
                        window.blit(hourlybg, (15+offy, 128+96*i + scr))
                        global weathericonshourly
                        window.blit(weathericonshourly[i], (21+offy, 128+96*i+6 + scr))
                        #draw metrics
                        tx = f'{splubby(dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][i]).strftime("%I"))} {("AM" if (dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][i]).strftime("%p") == "AM") else "PM")}'
                        drawshadowtext(tx, smallmedfont, screenwidth - smallmedfont.size(tx)[0]-20+offy, 128+20+96*i + scr, 5)
                        drawshadowtext(str(weatherraw["temperature"][i]) + "°" + t, bigfont, 15+92+5+offy, 100+18+96*i + scr, 5)
                        drawshadowtext(lang["wind"] + ":", smallmedfont, 300+15+92+5+offy, 90+96*i+40 + scr, 5)
                        drawshadowtext((str(weatherraw["windSpeed"][i]) + kmp + "mph ") + weatherraw["windDirectionCardinal"][i], smallmedfont, 300+15+92+5+offy, 90+92/2+96*i+40 + scr, 5)
                        drawshadowtextcol(str(weatherraw["precipChance"][i]) + "%", (0, 255, 255), smallmedfont, 600+15+92+5+offy, 90+96*i+40 + scr, 5)
                        drawshadowtextcol(str(weatherraw["relativeHumidity"][i]) + "%", (255, 127, 0), smallmedfont, 600+15+92+5+offy, 90+92/2+96*i+40 + scr, 5)
                        drawshadowtextcol(lang["feels"] + ":", (255, 0, 0), smallmedfont, 750+15+92+5+offy, 90+96*i+40 + scr, 5)
                        drawshadowtextcol(str(weatherraw["temperatureFeelsLike"][i]) + "°" + t, (255, 0, 0), smallmedfont, 750+15+92+5+offy, 90+92/2+96*i+40 + scr, 5)
                
                elif view == 5 and perfit:
                    offy = fading * 768
                    if justswitched:
                        g, gs, vs = makehourlygraph()

                        buffer = pg.Surface((994+screendiff, 556))
                        pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, 994+screendiff, 556))
                        buffer = blur(expandSurface(buffer, 6), 4)

                        cache["hourlybuffer"] = buffer
                        cache["hourlygraph"] = [g, gs, vs]
                        justswitched = False
                    else:
                        g, gs, vs = cache["hourlygraph"]
                        buffer = cache["hourlybuffer"]

                    window.blit(buffer, (20, 133-offy), special_flags=pg.BLEND_RGBA_MULT)
                    window.blit(graphbg, (15, 128-offy))
                    window.blit(gs, (20, 133-offy), special_flags=pg.BLEND_RGBA_MULT)
                    window.blit(g, (20, 133-offy))
                    now = dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][0])
                    now6 = dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][0]) + dt.timedelta(hours=6)
                    now12 = dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][0]) + dt.timedelta(hours=12)
                    now18= dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][0]) + dt.timedelta(hours=18)
                    now24 = dt.datetime.fromtimestamp(weatherraw["validTimeUtc"][0]) + dt.timedelta(hours=24)
                    time1 = splubby(now.strftime("%I")) + ("AM" if (now.strftime("%p") == "AM") else "PM")
                    time2 = splubby(now6.strftime("%I")) + ("AM" if (now6.strftime("%p") == "AM") else "PM")
                    time3 = splubby(now12.strftime("%I")) + ("AM" if (now12.strftime("%p") == "AM") else "PM")
                    time4 = splubby(now18.strftime("%I")) + ("AM" if (now18.strftime("%p") == "AM") else "PM")
                    time5 = splubby(now24.strftime("%I")) + ("AM" if (now24.strftime("%p") == "AM") else "PM")
                    drawshadowtext(f'{round(vs["maxtemp"])}°', smallmedfont, 20, 128-offy, 5)
                    drawshadowtext(f'{round(vs["medtemp"])}°', smallmedfont, 20, 128+440/2-offy, 5)
                    drawshadowtext(f'{round(vs["mintemp"])}°', smallmedfont, 20, 128+440-offy, 5)
                    drawshadowtext(time1, smallmedfont, 20, 128+500-offy, 5)
                    drawshadowtext(time2, smallmedfont, (screenwidth-640+530)/4 + 15, 128+500-offy, 5)
                    drawshadowtext(time3, smallmedfont, (screenwidth-640+530)/2 + 10, 128+500-offy, 5)
                    drawshadowtext(time4, smallmedfont, (screenwidth-640+530)*3/4 + 5, 128+500-offy, 5)
                    drawshadowtext(time5, smallmedfont, screenwidth-640+530, 128+500-offy, 5)
                    drawshadowtextcol(f"{lang['temp']}", (255, 0, 0), smallmedfont, screenwidth-16-smallmedfont.size(f"{lang['temp']}")[0], 128, 5-offy, 127)
                    drawshadowtextcol(f"{lang['precip']} %", (0, 255, 255), smallmedfont, screenwidth-16-smallmedfont.size(f"{lang['precip']} %")[0], 168, 5-offy, 127)
                    drawshadowtextcol(f"{lang['relhumidshort']} %", (255, 127, 0), smallmedfont, screenwidth-16-smallmedfont.size(f"{lang['relhumidshort']} %")[0], 208, 5-offy, 127)
                elif view == 6 and perfit:
                    if justswitched:
                        cache["tempscache"] = {}
                    for city in range(len(travelcities)):
                        offy = fading * screenwidth * (1 if (city%2) else -1)
                        if city >= len(travelnames):
                            drawshadowtext(lang["loading"], smallmedfont, 5+offy, 130 + city*45, 5)
                            continue
                        if city >= len(travelweathers):
                            drawshadowtext(lang["loading"], smallmedfont, 5+offy, 130 + city*45, 5)
                            continue
                        
                        drawshadowtext(travelnames[city], smallmedfont, 5+offy, 130 + city*45, 5)
                        if justswitched:
                            temps = []
                            err = False 
                            try:
                                for temp in travelweathers[city]["temperature"]:
                                    temps.append(temp)
                            except:
                                err = True
                                temps = [0, 1000000]
                            lowt = min(temps)
                            hight = max(temps)
                            cache["tempscache"][city] = [lowt, hight, err]
                        else:
                            lowt, hight, err = cache["tempscache"][city]
                        if not compact:
                            if not err:
                                drawshadowtempcol(f'{lang["low"]}: {lowt}°{t}', (135, 206, 235), smallmedfont, screenwidth - 550+offy, 130 + city*45, 5)
                                drawshadowtextcol(f'{lang["high"]}: {hight}°{t}', (255, 140, 0), smallmedfont, screenwidth - 250+offy, 130 + city*45, 5)
                            else:
                                drawshadowtempcol(lang["dataerror"], (255, 0, 0), smallmedfont, screenwidth - 550+offy, 130 + city*45, 5)
                        else:
                            if not err:
                                drawshadowtemp(f'{lowt}°{t}/{hight}°{t}', smallmedfont, screenwidth - 250+offy, 130 + city*45, 5)
                            else:
                                drawshadowtempcol(f'Error', (255, 0, 0), smallmedfont, screenwidth - 550+offy, 130 + city*45, 5)
                elif view == 7 and perfit:
                    drawshadowbigcrunch("\n".join(wraptext(f'{periods["daypartName"][0+bottomtomorrowm]}...{periods["narrative"][0+bottomtomorrowm]}', pg.Rect(15, 128, 994+screendiff, 588+32), smallmedfont)), (255, 255, 255), smallmedfont, 15-fading*screenwidth, 128, 5, 994+screendiff, 588+32, 127)
                elif view == 8 and perfit:
                    drawshadowbigcrunch("\n".join(wraptext(f'{periods["daypartName"][1+bottomtomorrowm]}...{periods["narrative"][1+bottomtomorrowm]}', pg.Rect(15, 128, 994+screendiff, 588+32), smallmedfont)), (255, 255, 255), smallmedfont, 15-fading*screenwidth, 128, 5, 994+screendiff, 588+32, 127)
                elif view == 9 and perfit:
                    drawshadowbigcrunch("\n".join(wraptext(f'{periods["daypartName"][2+bottomtomorrowm]}...{periods["narrative"][2+bottomtomorrowm]}', pg.Rect(15, 128, 994+screendiff, 588+32), smallmedfont)), (255, 255, 255), smallmedfont, 15-fading*screenwidth, 128, 5, 994+screendiff, 588+32, 127)
                elif view == 10 and perfit:
                    offy = fading * 768
                    if justswitched and not (schedule_active and presentation == "short"):
                        changetime = 30 * 60
                    mappyind = -(math.floor(changetime / 30) % 20 + 1)
                    if True: #temp
                        window.blit(mappy, (screenwidth/2-mappy.get_width()/2, 768/2-mappy.get_height()/2+offy))
                        window.blit(mappy_heat[mappyind], (screenwidth/2-mappy_heat[mappyind].get_width()/2, 768/2-mappy_heat[mappyind].get_height()/2+offy))
                        drawshadowtext(str(timestam[0][mappyind]), smallishfont, 5, 70+offy, 5)
                        if debug:
                            #draw a red square around the base tile
                            global basetilee
                            
                    else:
                        buffer = pg.Surface((radarimage.get_width(), radarimage.get_height()))
                        pg.draw.rect(buffer, (127, 127, 127, 127), pg.rect.Rect(0, 0, radarimage.get_width(), radarimage.get_height()))
                        buffer = blur(expandSurface(buffer, 6), 4)
                        window.blit(buffer, (screenwidth/2-radarimage.get_width()/2+5, 800/2-radarimage.get_height()/2+5), special_flags=pg.BLEND_RGBA_MULT)
                        window.blit(radarimage, (screenwidth/2-radarimage.get_width()/2, 800/2-radarimage.get_height()/2))
                elif view == 11 and perfit:
                    offy = fading * 768
                    if "credits" not in rastercache:
                        rastercache["credits"] = pg.Surface(window.size, pg.SRCALPHA)
                        #rastercache["credits"].blit(logo, (5, 128))
                        #rastercache["credits"].blit(mylogo, (screenwidth-mylogo.get_width()-100, 188))
                        #if partnered:
                            #rastercache["credits"].
                    #window.blit(turnintoashadow(logo), (10, 133))
                    #drawshadowtextroto(lang["localscopeby"], medfont, screenwidth-5, 128, 0, 5, rx=-1)
                    #window.blit(turnintoashadow(mylogo), (screenwidth-mylogo.get_width()-95, 188+5))
                    #drawshadowtextcol(lang["alsotry"], (255, 255, 0), medfont, 5, 768-64-80, 5)
                    if partnered:
                        window.blit(turnintoashadow(logosurf), (screenwidth/2-logosurf.get_width()/2+5, 768/2-logosurf.get_height()/2+5-offy))
                        window.blit(logosurf, (screenwidth/2-logosurf.get_width()/2, 768/2-logosurf.get_height()/2-offy))
                    #window.blit(rastercache["credits"], (0, 0))
                    
            elif currentsection == 1:
                # HEALTHSECT (here for search purposes)
                if view == 1 and perfit:
                    offy = fading * screenwidth
                    drawshadowtext(f'Air Quality Index: {airq["globalairquality"]["airQualityIndex"]} ({airq["globalairquality"]["airQualityCategory"]})', medfont, 5-offy, 128, 5)
                    drawshadowtext(f'Primary Pollutant: {airq["globalairquality"]["primaryPollutant"]}', smallmedfont, 5-offy, 200, 5)
                    drawshadowtext(airq["globalairquality"]["messages"]["General"]["title"], smallmedfont, 5-offy, 260, 5)
                    drawshadowcrunch(airq["globalairquality"]["messages"]["General"]["text"], smallishfont, 5-offy, 305, 5, screenwidth-10)
                    drawshadowtext(airq["globalairquality"]["messages"]["Sensitive Group"]["title"], smallmedfont, 5-offy, 340, 5)
                    drawshadowcrunch(airq["globalairquality"]["messages"]["Sensitive Group"]["text"], smallishfont, 5-offy, 385, 5, screenwidth-10)
                    drawshadowcrunch(airq["globalairquality"]["source"], tinyfont, 5-offy, 668, 5, screenwidth-10)
                elif view == 2 and perfit:
                    offy = fading * screenwidth
                    drawshadowtext(f'UV Index: {uvi["uvIndexCurrent"]["uvIndex"]} ({uvi["uvIndexCurrent"]["uvDesc"]})', medfont, 5-offy, 128, 5)
                    drawshadowtext(uvi["uvIndexCurrent"]["uvWarning"] if uvi["uvIndexCurrent"]["uvWarning"] else lang["noalertshort"], smallmedfont, 5-offy, 200, 5)
                elif view == 3 and perfit:
                    offy = fading * screenwidth
                    global pollen
                    drawshadowtext(pollen["pollenobservations"][0]["stn_cmnt"], smallmedfont, 5-offy, 128, 5)
                    obser = pollen["pollenobservations"][0]["pollenobservation"]
                    for i in range(len(obser)):
                        drawshadowtext(f'{obser[i]["pollen_type"]}: {obser[i]["pollen_desc"]}', smallmedfont, 5-offy, 168+i*40, 5)
                    
            if perfit and (currentsection == 0):
                if view == 1:
                    window.blit(topshadow, (0-offz, 524), special_flags=pg.BLEND_RGBA_MULT)
                    window.blit(topgradient if not redmode else topgradientred, (-offz, 460))
                    if bottomtomorrowm:
                        if bottomtomorrow == 0:
                            bottomtomorrow = 1
                    drawshadowtext(periods["daypartName"][bottomtomorrow], smallmedfont, 5-offz, 465, 5, 127, filters=filters["title"])
                    
            elif (currentsection == 2) and (len(customslides) > 0):
                # CUSTOMSECT
                if view != 0:
                    exec(customslides[view - 1][1])
            
            if justswitched:
                justswitched = False
            if changetime <= 0:
                lastname = viewName[::][::]
                view += 1
                
                def get_bigger():
                    if currentsection == 2:
                        if (view) > len(customslides):
                            return True
                    else:
                        if view > sections[currentsection]:
                            return True
                    return False
                
                if get_bigger():
                    #check if we're on short presentation
                    if presentation == "short" and schedule_active:
                        currentscene = -1
                        view = 0
                        transitiontime = 60
                        overdrawtime = 15
                    else:
                        view = 0
                        currentsection += 1
                        if currentsection > (totalseg + (len(customslides) > 0)):
                            currentsection = 0
                
                if view == 6 and redmode:
                    view = 8
                if view == 0 and len(alerts) > 0:
                    changetime = 60 * 45
                    alertshow += 1
                    alertshow = alertshow % len(alerts)
                else:
                    changetime = 60 * 15
                    if schedule_active:
                        changetime = 60*10
                        if view == 4:
                            changetime = 60*15
                justswitched = True
                transitiontime = 60
            else:
                changetime -= 60 * delta
            
            #housekeeping
            realbotg = (bottomgradient if not redmode else bottomgradientred)
            window.blit(realbotg, (0, 768-realbotg.get_height()+cuefade*64))
            
            if tickertimer <= 0:
                ticker += 1
                if ticker > (6 + len(customtickers)):
                    ticker = 0
                if ticker == (6 + len(customtickers)):
                    adindex += 1
                    if adindex > len(ads)-1:
                        adindex = 0
                    tickertimer = 60 * actime
                else:
                    tickertimer = 60 * 4
                justticked = True
            else:
                tickertimer -= 60 * delta
            
            tickerf = tickerfader()
            tickerright = ""
            obstime = dt.datetime.strptime("-".join(weather2["validTimeLocal"].split("-")[:-1]), "%Y-%m-%dT%H:%M:%S")
            obstimeshort = splubby(obstime.strftime("%I:%M %p"))
            if ticker == 0:
                tickername = f'Last updated at {obstimeshort}'
            elif ticker == 1:
                tickername = f'{lang["temp"]}: {round(weather2["temperature"])}°{t}'
                tickerright = f'{lang["feels"]}: {round(weather2["temperatureFeelsLike"])}°{t}'
            elif ticker == 2:
                tickername = f'{lang["humid"]}: {roundd(weather2["relativeHumidity"])}%'
                tickerright = f'{lang["uv"]}: {round(weather2["uvIndex"])}'
            elif ticker == 3:
                pressa = ["(-)", "(+)", "(-)", "(++)", "(--)"]
                tickername = f'{lang["pressure"]}: {round(weather2["pressureAltimeter"], 2)} {pres_s} {pressa[weather2["pressureTendencyCode"]]}'
            elif ticker == 4:
                if weather2["windDirectionCardinal"] != "CALM":
                    tickername = f'{lang["wind"]}: {weather2["windDirectionCardinal"]} @ {round(weather2["windSpeed"])} {kmp}mph'
                else:
                    tickername = f"{lang['wind']}: {lang['calm']}"
                if weather2["windGust"]:
                    tickerright = f"{lang['gusts']}: {weather2['windGust']} {kmp}mph"
            elif ticker == 5:
                try:
                    ceiling = nonezero(weather2["cloudCeiling"])
                except IndexError:
                    ceiling = 0
                tickername = f'{lang["visib"]}: {round(weather2["visibility"])} {visi}'
                tickerright = f'{lang["ceil"]}: {"Unlimited" if ceiling == 0 else f"{ceiling} feet"}'
            elif (len(customtickers) > 0 and ticker < (6 + len(customtickers))):
                exec(customtickers[ticker - 6])
            elif ticker == (6 + len(customtickers)):
                tickername = ads[adindex]
            if not ((len(customtickers) > 0) and (ticker > 5) and (ticker <  (6 + len(customtickers)))):
                tickerzz = (64*tickerf)
                drawshadowtext(tickername, smallmedfont, 5, 768-64+5+tickerzz, 5, 127, filters=filters["tickerleft"])
                drawshadowtext(tickerright, smallmedfont, screenwidth-5-smallmedfont.size(tickerright)[0], 768-64+5+tickerzz, 5, 127, filters=filters["tickerright"])
            if perfit:
                window.blit(bottomshadow, (0, 768-realbotg.get_height()-bottomshadow.get_height()+64*cuefade), special_flags=pg.BLEND_RGBA_MULT)
            
            #top bar (moved from top)
            if perfit:
                window.blit(topshadow, (0, 64-cuefade*64), special_flags=pg.BLEND_RGBA_MULT)
            window.blit([topgradient, topgradienthealth, topgradientcustom][currentsection] if not redmode else topgradientred, (0, -cuefade*64))
            
            #viewnames = ["Split View", "Overview", "Extended Forecast", "Hourly Graph", "Travel Cities", f"Weather Report ({periods['daypartName'][0+bottomtomorrowm]})", f"Weather Report ({periods['daypartName'][1+bottomtomorrowm]})", f"Weather Report ({periods['daypartName'][2+bottomtomorrowm]})", "Satellite/Radar Forecast" if not redmode else "Severe Weather Rader", "Probability of Precipitation" if not trackhurricanes else "Hurricane Tracker", "Forecast Office Headlines", "Alerts"]
            viewnames = lang["viewnames"] if not redmode else lang["viewnamesred"]
            if currentsection == 1:
                viewnames = lang["viewnameshealth"]
            if currentsection == 2:
                if view == 0:
                    viewName = lang["nextup"]
                else:
                    viewName = get_lang_custom(customslides[view - 1][0])
            else:
                advisory = (len(alerts)>0)
                if view == 0 and advisory:
                    viewName = lang["alerts"]
                else:
                    viewName = namer(viewnames[view])
                #viewName = "error"
            
            #if view == 2:
            #    #force view 2
            #    viewName = ["7-Day Forecast (Day)", "7-Day Forecast (Night)", "7-Day Forecast (Page 1)", "7-Day Forecast (Page 2)", "Extended Forecast"][nightv]
            
            
            if overridetime > 0:
                overridetime -= 60 * delta
                viewName = name
            
            drawshadowtext(viewName, smallmedfont, screenwidth/2-smallmedfont.size(viewName)[0]/2, 5-fading*64, 5, 127, filters=filters["title"])
            
            if not hideleft:
                if showfps:
                    drawshadowtext(round(clock.get_fps()), smallmedfont, 5, 5, 5-cuefade*64, 127)
                else:
                    drawshadowtext(splubby(dt.datetime.now().strftime(timeformattop)), smallmedfont, 5, 5-cuefade*64, 5, 127)
            
            if not hideright:
                drawshadowtext(realstationname, smallmedfont, screenwidth-10-smallmedfont.size(realstationname)[0], 5, 5-cuefade*64, 127)
            
            for fixture in customfixtures:
                exec(fixture)
            
            # if justswitched:
            #     justswitched = False
            # if changetime <= 0:
            #     lastname = viewName[::][::]
            #     view += 1
                
            #     def get_bigger():
            #         if currentsection == 2:
            #             if (view) > len(customslides):
            #                 return True
            #         else:
            #             if view > sections[currentsection]:
            #                 return True
            #         return False
                
            #     if get_bigger():
                
            #         view = 0
            #         currentsection += 1
            #         if currentsection > (totalseg + (len(customslides) > 0)):
            #             currentsection = 0
            #     if view == 6 and redmode:
            #         view = 8
            #     if view == 0 and len(alerts) > 0:
            #         changetime = 60 * 45
            #     else:
            #         changetime = 60 * 15
            #     justswitched = True
            #     transitiontime = 60
            #     transition_s = window.copy()
            # else:
            #     changetime -= 60 * delta
            def get_bigger():
                if currentsection == 2:
                    if (view) > len(customslides):
                        return True
                else:
                    if view > sections[currentsection]:
                        return True
                return False
            #moved alerts here to avoid them getting screen captured by the transition
            alerth = 0 #offset
            if currentsection == 0 and view == 10:
                alerth = 768-64-60-80
            if view != 0 and (True if not performance else justswitched):
                if len(alerts) > 0:
                    if len(alerts) > 1:
                        if alerttimer > 0:
                            alerttimer -= 1 * delta * 60
                        else:
                            if performance:
                                alertscroll = screenwidth
                            else:
                                alertscroll += 5 * delta * 60
                    if alertscroll > screenwidth:
                        showingalert += 1
                        alertscroll = 0
                        alerttimer = 300
                        if showingalert > len(alerts)-1:
                            showingalert = 0
                    if not redmode:
                        drawshadowcrunchcol(alerts[showingalert]["headlineText"], (255, 0, 0), smallmedfont, 5 + alertscroll, 80+alerth, 5, screenwidth-10, 127)
                    else:
                        drawshadowcrunchcol(alerts[showingalert]["headlineText"], (0, 127, 255), smallmedfont, 5 + alertscroll, 80+alerth, 5, screenwidth-10, 127)
                    if len(alerts) > 1:
                        drawshadowcrunchcol(alerts[(showingalert+1) if showingalert != len(alerts)-1 else 0]["headlineText"], (255, 0, 0) if not redmode else (0, 127, 255), smallmedfont, -screenwidth + 5 + alertscroll, 80+alerth, 5, screenwidth-15, 127)
                else:
                    drawshadowtext(lang["noalert"], smallmedfont, 5, 80+alerth, 5, 127)
            
            if (get_bigger() and changetime <= 60*5 and not (schedule_active and presentation == "short") and not (currentsection == (2 if len(customslides) > 1 else 1))):
                nextsect = currentsection + 1
                if currentsection > (totalseg + (len(customslides) > 1)):
                    nextsect = 0
                sectionscroll = lerp(sectionscroll, -64, 0.04)
                if round(sectionscroll) == -64:
                    sectionscroll = -64
                window.blit(nextbg, (screenwidth + sectionscroll, 64), pg.Rect(0, 0, 64, 640))
                drawshadowtextroto(f"{lang['nextup']} {lang['sectionnames'][nextsect]}", smallishfont, screenwidth+sectionscroll+20, 768/2, 90, 5, ry=0.5)
            if ((view == 0) and changetime >= 60*10 and not (schedule_active and presentation == "short")):
                sectionscroll = lerp(sectionscroll, 0, 0.04)
                if round(sectionscroll) == 0:
                    sectionscroll = 0
                window.blit(nextbg, (screenwidth + sectionscroll, 64), pg.Rect(0, 0, 64, 640))
                drawshadowtextroto(f"{lang['nextup']} {lang['sectionnames'][currentsection]}", smallishfont, screenwidth+sectionscroll+20, 768/2, 90, 5, ry=0.5)
            if not loading and "stream" in globals() and miniplayer:
                if stream:
                    st = profiling_start()
                    global streamdims_scaled
                    frame = cv2.resize(rawframe, streamdims_scaled)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    #frame = cv2.flip(frame, 1)
                    frame = cv2.transpose(frame)
                    framesurf = pg.surfarray.make_surface(frame)
                    #framesurf = pg.transform.rotate(framesurf, -90)
                    #framesurf = pg.transform.flip(framesurf, True, False)
                    #if smoothsc:
                    #    framesurf = pg.transform.smoothscale(framesurf, (screenwidth, 768))
                    #else:
                    #    framesurf = pg.transform.scale(framesurf, (screenwidth, 768))

                    global minigradient
                    window.blit(minigradient, (screenwidth - minigradient.get_width() - 5, 768-64-miniplayerheight-5))
                    window.blit(framesurf, (screenwidth - minigradient.get_width() - 5 + 4, 768-64-miniplayerheight-5 + 4))
                    profiling_end(st, "time_stream")
        #lsd += 1
        #lsd = lsd % 360
        #lsdd = pg.Color(0, 0, 0, 127)
        #lsdd.hsva = (lsd, 100, 50, 50)
        #lsdd.a = 127
        #window.fill(lsdd, special_flags=pg.BLEND_RGBA_ADD)
        for action in actions["post"]:
            exec(action)
        
        if profile:
            pr = time.perf_counter() - profst
            global framect
            global framesp
            if cflag:
                cflag = False
                framect = 0
                framesp = 0
            framect += 1
            framesp += pr
            
            sinfo = ""
            if stream:
                if "realstream" in globals():
                    sinfo = f"\nstream reported fps: {realstream.get(cv2.CAP_PROP_FPS)}"
            fn = smallmedfont.render(f"stream: {safedivide(1, profiling['time_stream'])}\nmath: {safedivide(1, profiling['time_math'])}\nui: {safedivide(1, profiling['time_ui'])}\nother blits: {safedivide(1, profiling['time_blits'])}\nframe total: {pr}\nfps avg: {framect/framesp}{sinfo}", False, (255, 255, 255), (0, 0, 0))
            window.blit(fn, (0, 0))
        
        eventt.set()
        
        if scaled:
            if smoothsc:
                final.blit(pg.transform.smoothscale(window, scale), (0, 0))
            else:
                final.blit(pg.transform.scale(window, scale), (0, 0))
        #opswindow.fill((0, 130, 255))
        #drawshadowtext("Admin Panel", smallmedfont, 5, 5, 5, wind=opswindow)
        realwindow.flip()
        clear_profile()
        #realops.flip()

if not getattr(pg, "IS_CE", False):
    print("Pygame CE is no longer required for this application. At least, I think so. You're limited to drop shadows though.")


def postmix(dev, mem):
    #if not stinky:
    #    pipe = os.open("lsaud", os.O_WRONLY)
    #    os.write(pipe, bytes(mem))
    #    os.close(pipe)
    for action in actions["mix"]:
        exec(action)

def makefifo():
    os.mkfifo("lsaud")
    os.mkfifo("lsvid")

def breakfifo():
    os.unlink("lsaud")
    os.unlink("lsvid")

if writer:
    global realwriter
    cmd = ['ffmpeg',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', '{}x{}'.format(screenwidth, 768),
        '-re',
        '-i', '-',
        #'-re',
        #'-f', 'f32le',
        #'-ar', '44100',
        #'-ac', '2',
        #'-i', 'lsaud',
        '-c:v', 'libx264',
        #'-c:a', 'aac',
        '-preset', 'veryfast',
        '-r', '60',
        '-f', 'flv',
        writer
    ]
    
    if type(writer) == list:
        writerstring = "[f=flv]" + "|[f=flv]".join(writer)
        cmd = ['ffmpeg',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', '{}x{}'.format(screenwidth, 768),
            '-re',
            '-i', '-',
            #'-f', 'f32le',
            #'-i', '/tmp/lsaud',
            '-c:v', 'libx264',
            #'-c:a', 'aac',
            '-preset', 'veryfast',
            '-r', '60',
            '-f', 'tee',
            '-use_fifo', 'true',
            '-map', '0:v',
            #'-map', '1:a',
            writerstring
        ]
        
    #makefifo()
    realwriter = sp.Popen(cmd, stdin=sp.PIPE)
    imageth = th.Thread(target=imagethread)
    imageth.daemon = True
    imageth.start()

try:
    main()
except Exception as err:
    print(tra.format_exc())
    work = True
    while work:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                work = False
        window.blit(gradientred, (0, 0))
        drawshadowtext(tra.format_exc(), smallfont, 15, 15, 5)
        
        realwindow.flip()
finally:
    if writer:
        stinky = True
        realwriter.kill()
        #if writer:
        #    breakfifo()

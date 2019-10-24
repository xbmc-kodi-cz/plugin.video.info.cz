# -*- coding: utf-8 -*-
# Module: default
# Author: Petr Čermák
# Created on: 8.4.2019
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys, os
from collections import OrderedDict
from urllib import urlencode
import urllib2
from urlparse import parse_qsl
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import feedparser
import re
from bs4 import BeautifulSoup

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
_addon_ = xbmcaddon.Addon('plugin.video.info.cz')
_scriptname_ = _addon_.getAddonInfo('name')
home = _addon_.getAddonInfo('path')

FEEDS = OrderedDict([

        ('Nejnovější', ['https://video.info.cz/rss/5623', None, None]),
        ('Štrunc!',     ['https://video.info.cz/rss/6635', None, None]),
        ('Topol Show', ['https://video.info.cz/rss/7456', None, None]),

        ])

def log(msg, level=xbmc.LOGDEBUG):
    if type(msg).__name__=='unicode':
        msg = msg.encode('utf-8')
    xbmc.log("[%s] %s"%(_scriptname_,msg.__str__()), level)

def logDbg(msg):
    log(msg,level=xbmc.LOGDEBUG)

def logErr(msg):
    log(msg,level=xbmc.LOGERROR)

def fetchUrl(url, label):
    logErr("fetchUrl " + url + ", label:" + label)
    httpdata = ''	
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0')
        resp = urllib2.urlopen(req)
        size = resp.info().getheader('Content-Length', 9000)
        for line in resp:
            httpdata += line
    except:
        httpdata = None
        showErrorNotification("Error loading video")
    finally:
        resp.close()
    return httpdata

def showNotification(message, icon):
    xbmcgui.Dialog().notification(_dialogTitle_, message, icon)

def showErrorNotification(message):
    showNotification(message, 'error')

def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def get_videos(category):
    """
    Get the list of videofiles/streams.

    Here you can insert some parsing code that retrieves
    the list of video streams in the given category from some site or server.

    .. note:: Consider using `generators functions <https://wiki.python.org/moin/Generators>`_
        instead of returning lists.

    :param category: Category name
    :type category: str
    :return: the list of videos in the category
    :rtype: list
    """
    VideoFeed = feedparser.parse(FEEDS[category][0])
    for entry in VideoFeed.entries:
        yield entry


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    """
    #xbmcplugin.setPluginCategory(_handle, 'Info.cz videos')
    xbmcplugin.setContent(_handle, 'videos')

    for category in FEEDS.iterkeys():
        list_item = xbmcgui.ListItem(label=category)
      
        url = get_url(action='listing', category=category)
        is_folder = True
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)
        logErr("category " + category + " added")
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED)
    
    xbmcplugin.endOfDirectory(_handle)

def list_videos(category):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, category)
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get the list of videos in the category.
    videos = get_videos(category)
    # Iterate through videos.
    for video in videos:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=video.title)
        
        bs = BeautifulSoup(video.summary, "html.parser")
    
        # Set additional info for the list item.
        # 'mediatype' is needed for skin to display info for this ListItem correctly.
        list_item.setInfo('video', {'title': video.title,
                                    'plot': bs.get_text().strip(),
                                    'mediatype': 'video'})
                                    
        if bs.img:
            th = re.search("\/(\d+)-img", bs.img['src'])
            thumb="https://img.cncenter.cz/img/12-full-"+th.group(1)+".jpg"
            list_item.setArt({'thumb': thumb, 'icon': thumb, 'fanart': thumb})

        list_item.setProperty('IsPlayable', 'true')
        
        url = get_url(action='play', video=video.links[0].href)    
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False

        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(_handle)


def play_video(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # get video link
    html = fetchUrl(path, "Loading video...")
    if html:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.findAll("div", {"class": "cnc-video-container"}):
            stag = tag.findNext('script').text
            m = re.search("hlsUrl(.*?)'(.*?)'", stag)
            videolink = m.group(2)
            break
        
        play_item = xbmcgui.ListItem(path=videolink)
        # Pass the item to the Kodi player.
        play_item.setProperty('inputstreamaddon','inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type','hls')
        xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            list_videos(params['category'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])

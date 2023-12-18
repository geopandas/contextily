"""
Downloading and Plotting Maps
-----------------------------

Plotting maps with Contextily.

Contextily is designed to pull map tile information from the web. In many
cases we want to go from a location to a map of that location as quickly
as possible. There are two main ways to do this with Contextily.

Searching for places with text
==============================

The simplest approach is to search for a location with text. You can do
this with the ``Place`` class. This will return an object that contains
metadata about the place, such as its bounding box. It will also contain an
image of the place.
"""
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx

loc = cx.Place("boulder", zoom_adjust=0)  # zoom_adjust modifies the auto-zoom

# Print some metadata
for attr in ["w", "s", "e", "n", "place", "zoom", "n_tiles"]:
    print("{}: {}".format(attr, getattr(loc, attr)))

# Show the map
im1 = loc.im

fig, axs = plt.subplots(1, 3, figsize=(15, 5))
cx.plot_map(loc, ax=axs[0])

###############################################################################
# The zoom level will be chosen for you by default, though you can specify
# this manually as well:

loc2 = cx.Place("boulder", zoom=11)
cx.plot_map(loc2, ax=axs[1])

###############################################################################
# Downloading tiles from bounds
# =============================
#
# You can also grab tile information directly from a bounding box + zoom level.
# This is demoed below:

im2, bbox = cx.bounds2img(loc.w, loc.s, loc.e, loc.n, zoom=loc.zoom, ll=True)
cx.plot_map(im2, bbox, ax=axs[2], title="Boulder, CO")

plt.show()

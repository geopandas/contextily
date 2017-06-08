import numpy as np
import matplotlib.pyplot as plt
import contextily as cx

loc = cx.Place('boulder', zoom_adjust=0)
cx.plot_map(loc)
plt.show()

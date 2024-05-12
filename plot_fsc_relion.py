# -*- coding: utf-8 -*-
"""
Created on Sun May 12 18:40:07 2024

@author: baymo
"""

#!/usr/bin/python


import numpy as np
import matplotlib.pyplot as plt

###########################################################

fsc_file="postprocess_fsc.dat"    #file name of fsc data from Relion
resolution=2.65                    #reported resolution
output_fsc_figure="fsc.pdf"       #file name of output fsc figure

###########################################################

frequency=[]
fsc=[]
with open(fsc_file,'r') as file:
    for each in file.readlines():
        line=each.strip().split()
        frequency.append(float(line[0]))
        fsc.append(float(line[1]))
frequency=np.array(frequency)
fsc=np.array(fsc)
max_frequency=max(frequency)
plt.xlabel('Resolution ('+r'1/$\AA$'+')')
plt.ylabel('Fourier Shell Correlation')
plt.xlim(0,max_frequency)
plt.ylim(0,1.0)
plt.plot(frequency,fsc,'r-')
plt.legend(["halfmap_fsc"],loc=1)
plt.axhline(y=0.143,xmin=0,xmax=1.0,color='k',linestyle="--",label="FSC of 0.143")
plt.text(0.1,0.17,"fsc=0.143",fontsize=12)
plt.axhline(y=0.5,xmin=0,xmax=1.0,color='k',linestyle="--",label="FSC of 0.5")
plt.text(0.1,0.527,"fsc=0.5",fontsize=12)
plt.axvline(x=1/resolution,ymin=0,ymax=0.143,color='k',linestyle="--")
plt.savefig(output_fsc_figure,dpi=300,transparent=True)


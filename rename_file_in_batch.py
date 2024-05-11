# -*- coding: utf-8 -*-
"""
Created on Thu Apr 25 16:11:57 2024

@author: baymo
"""

#!/usr/bin/python

import os
import argparse

def parse_command_line():
     description="strip uid from cryosparc data and rename mrc to mrcs for Relion processing"
     epilog="Author: Morgan from USTC\n"
     parser=argparse.ArgumentParser(description=description,epilog=epilog)
     parser.add_argument("--i",help="input folder name")
     parser.add_argument("--strip_uid",type=int,help="strip uid for each file, yes(1) or no(0), default=0",default=0)
     parser.add_argument("--mrc2mrcs",type=int,help="rename mrc to mrcs for each file, yes(1) or no(0), default=0",default=0)
     
     args=parser.parse_args()
     return args

args=parse_command_line()
folder=args.i
working_dir=os.getcwd()

#file_path=os.path.join(working_dir,folder)
#for filename in os.listdir(file_path):
#    file=os.path.join(file_path,filename)
#    if os.path.isfile(file):
#        new_name=filename.split('_')
#        new_filename='_'.join(new_name[1:])
#        new_path=os.path.join(file_path,new_filename)
#        old_path=os.path.join(file_path,filename)
#        os.rename(old_path,new_path)
        
def strip_uid(working_dir,folder):
    file_path=os.path.join(working_dir,folder)
    for filename in os.listdir(file_path):
        file=os.path.join(file_path,filename)
        if os.path.isfile(file):
            new_name=filename.split('_')
            new_filename='_'.join(new_name[1:])
            new_path=os.path.join(file_path,new_filename)
            old_path=os.path.join(file_path,filename)
            os.rename(old_path,new_path)
            
def mrc2mrcs(working_dir,folder):
    file_path=os.path.join(working_dir,folder)
    for filename in os.listdir(file_path):
        file=os.path.join(file_path,filename)
        if os.path.isfile(file):
            old_path=os.path.join(file_path,filename)
            new_filename=list(os.path.splitext(filename))
            new_filename[-1]='.mrcs'
            new_filename=new_filename[0]+new_filename[-1]
            new_path=os.path.join(file_path,new_filename)
            os.renames(old_path,new_path)

if args.strip_uid==1:
    strip_uid(working_dir,folder)
    print("strip-uid excuted successfully!")
else:
    print("no strip-uid excuted")

if args.mrc2mrcs==1:
    mrc2mrcs(working_dir, folder)
    print("mrc2mrcs rename excuted successfully!")
else:
    print("no mrc2mrcs rename excuted")
            
            
    
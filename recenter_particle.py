# -*- coding: utf-8 -*-
"""
Created on Sat Apr 20 16:59:25 2024

Purpose: recenter particles on focused domain for 3D refinement and classification

Usage help: python recenter_particle -h

@author: Aimin Cheng at Peking University
"""
#!/usr/bin/python


import numpy as np
import os
import argparse


def parse_command_line():
    description="Recenter particles on focused domain for refinement and classification.\n \
        The input (cor_x,cor_y,cor_z)=box_center_coordinate-mass_center_coordinate_of_focused_domain, similar to relion_image_handler."
    epilog="Author: Morgan from USTC\n"
    parser=argparse.ArgumentParser(description=description,epilog=epilog)
    parser.add_argument("--i",help="input refined star file",default="run_data.star")
    parser.add_argument("--cor_x",type=float,help="coordinate X to center particles on (in pix)")
    parser.add_argument("--cor_y",type=float,help="coordinate Y to center particles on (in pix)")
    parser.add_argument("--cor_z",type=float,help="coordinate Z to center particles on (in pix)")
    parser.add_argument("--binning_factor",type=float,help="binning factor for particles in refinement")
    parser.add_argument("--pixel_size",type=float,help="pixel size [A/pix] of the original images used in the Extracted job")
    parser.add_argument("--job",help="AutoPick job name, e.g.: job012")

    args=parser.parse_args()
    return args

args=parse_command_line()
cor_x=args.cor_x
cor_y=args.cor_y
cor_z=args.cor_z
binning_factor=args.binning_factor
pixel_size=args.pixel_size
particle_star=args.i
autopick_job=args.job

class Particle:
    def __init__(self,rlnCoordinateX,rlnCoordinateY,rlnAngleRot,rlnAngleTilt,rlnAnglePsi,rlnOriginXAngst,rlnOriginYAngst,\
                 rlnImageName,rlnMicrographName):
        self.coordinateX=rlnCoordinateX
        self.coordinateY=rlnCoordinateY
        self.AngleRot=rlnAngleRot
        self.AngleTilt=rlnAngleTilt
        self.AnglePsi=rlnAnglePsi
        self.offsetX=rlnOriginXAngst
        self.offsetY=rlnOriginYAngst
        self.imagename=rlnImageName
        self.micrographname=rlnMicrographName

def extract_meta_label(starfile,meta_label):
    with open(starfile,'r') as fi:
        for each in fi.readlines():
            if  each.strip().startswith("_rln"):
                key,value=each.strip().split()[0],each.strip().split()[1]
                meta_label[key]=value.lstrip('#')
    return meta_label

def euler_matrix(psi,theta,phi):
    psi=psi/180.0*np.pi
    theta=theta/180.0*np.pi
    phi=phi/180.0*np.pi
    r11=np.cos(psi)*np.cos(theta)*np.cos(phi)-np.sin(psi)*np.sin(phi)
    r12=np.cos(psi)*np.cos(theta)*np.sin(phi)+np.sin(psi)*np.cos(phi)
    r13=-np.cos(psi)*np.sin(theta)
    r21=-np.sin(psi)*np.cos(theta)*np.cos(phi)-np.cos(psi)*np.sin(phi)
    r22=-np.sin(psi)*np.cos(theta)*np.sin(phi)+np.cos(psi)*np.cos(phi)
    r23=np.sin(psi)*np.sin(theta)
    r31=np.sin(theta)*np.cos(phi)
    r32=np.sin(theta)*np.sin(phi)
    r33=np.cos(theta)
    
    R=np.array([[r11,r12,r13],[r21,r22,r23],[r31,r32,r33]])
    
    return R

def projection2D(R,cor_x,cor_y,cor_z):
    x_2d,y_2d,z_2d=R@np.array([cor_x,cor_y,cor_z])
    return x_2d,y_2d

def recenter(rlnCoordinateX,rlnCoordinateY,x_2d,y_2d,rlnOriginXAngst,rlnOriginYAngst,pixel_size,binning_factor):
    new_rlnCoordinateX,new_rlnCoordinateY=np.array([rlnCoordinateX,rlnCoordinateY])-np.array([x_2d,y_2d])*binning_factor- \
    np.array([rlnOriginXAngst,rlnOriginYAngst])/pixel_size
    new_rlnCoordinateX_round,new_rlnCoordinateY_round=round(new_rlnCoordinateX,6),round(new_rlnCoordinateY,6)
    new_rlnOriginXAngst,new_rlnOriginYAngst=(np.array([new_rlnCoordinateX,new_rlnCoordinateY])-np.array([new_rlnCoordinateX_round,new_rlnCoordinateY_round]))*pixel_size
    return new_rlnCoordinateX_round,new_rlnCoordinateY_round,new_rlnOriginXAngst,new_rlnOriginYAngst

def write_header(star):
    meta_data = ["data_", "loop_", "_rlnCoordinateX #1", "_rlnCoordinateY #2", "_rlnAngleRot #3", "_rlnAngleTilt #4", "_rlnAnglePsi #5", \
                 "_rlnOriginXAngst #6", "_rlnOriginYAngst #7",""]
    with open(star, 'a+') as starfile:
        lines = starfile.readlines()
        for meta in meta_data:
            if not any(line.strip().startswith(meta) for line in lines):
                starfile.write(meta + '\n')

def write_autopick_star(star):
    meta_data = ["# version 30001","","data_coordinate_files","","loop_","_rlnMicrographName #1","_rlnMicrographCoordinates #2"]
    with open(star, 'a+') as starfile:
        lines = starfile.readlines()
        for meta in meta_data:
            if not any(line.strip().startswith(meta) for line in lines):
                starfile.write(meta + '\n')
                
                
meta_flag=['#','data_optics','data_particles','loop_','opticsGroup','_rln']
meta_label={}
meta_label=extract_meta_label(particle_star,meta_label)
with open(particle_star,'r') as star:
    for line in star.readlines():
        if line.strip().startswith(tuple(meta_flag)):
            continue
        elif bool(line.strip()):
            particle_data=line.strip().split()
            corX_col=int(meta_label["_rlnCoordinateX"])-1
            corY_col=int(meta_label["_rlnCoordinateY"])-1
            AngleRot_col=int(meta_label["_rlnAngleRot"])-1
            AngleTilt_col=int(meta_label["_rlnAngleTilt"])-1
            AnglePsi_col=int(meta_label["_rlnAnglePsi"])-1
            OriginXAngst_col=int(meta_label["_rlnOriginXAngst"])-1
            OriginYAngst_col=int(meta_label["_rlnOriginYAngst"])-1
            ImageName_col=int(meta_label["_rlnImageName"])-1
            MicrographName_col=int(meta_label["_rlnMicrographName"])-1
            particle=Particle(float(particle_data[corX_col]),float(particle_data[corY_col]),float(particle_data[AngleRot_col]),float(particle_data[AngleTilt_col]), \
                              float(particle_data[AnglePsi_col]),float(particle_data[OriginXAngst_col]),float(particle_data[OriginYAngst_col]), \
                              particle_data[ImageName_col],particle_data[MicrographName_col])
            transform_matrix=euler_matrix(particle.AnglePsi,particle.AngleTilt,particle.AngleRot)
            x_2d,y_2d=projection2D(transform_matrix, cor_x, cor_y, cor_z)
            particle.coordinateX,particle.coordinateY,particle.offsetX,particle.offsetY=recenter(particle.coordinateX,particle.coordinateY, x_2d,y_2d,particle.offsetX,particle.offsetY,pixel_size,binning_factor)
            micrographstar=particle.micrographname.strip().split('/')[-1].rstrip('.mrc')+'_autopick.star'
            folder="rawdata"
            work_dir=os.getcwd()
            path_folder=os.path.join(work_dir,folder)
            if not os.path.exists(path_folder):
                os.makedirs(path_folder)
            path=os.path.join(folder,micrographstar)
            if not os.path.isfile(path):
                write_header(path)
            with open(path,'a') as file:
                particle_info="{0:<25}".format(particle.coordinateX)+"{0:<25}".format(particle.coordinateY)+"{0:<25}".format(particle.AngleRot) \
                    +"{0:<25}".format(particle.AngleTilt)+"{0:<25}".format(particle.AnglePsi)+"{0:<25}".format(particle.offsetX) \
                        +"{0:<25}".format(particle.offsetY)
                file.write(particle_info+'\n')
            autopick_star="autopick.star"
            autopick_star=os.path.join(work_dir,autopick_star)
            if not os.path.isfile(autopick_star):
                write_autopick_star(autopick_star)
            particle_flag=particle.imagename.strip().split('@')
            if int(particle_flag[0])==1:
                with open(autopick_star,'a') as autopick:
                    autopick_micrographname=particle.micrographname
                    autopick_starname="AutoPick/"+autopick_job+"/rawdata/"+micrographstar
                    autopick_info="{0:60}".format(autopick_micrographname)+"{0:<60}".format(autopick_starname)
                    autopick.write(autopick_info+'\n')


            


# -*- coding: utf-8 -*-
"""
Created on Mon Apr 22 20:09:39 2024

Purpose: convert cryosparc cs format into relion star format

Usage help: python csparc2relionstar_parser.py

@author: Aimin Cheng at Peking University

"""
#!/usr/bin/python

import numpy as np
import os
import argparse
from scipy.spatial.transform import Rotation as R

def parse_command_line():
    description="convert particles from cryosparc cs format into relion star format"
    epilog="Author: Morgan from USTC\n"
    parser=argparse.ArgumentParser(description=description,epilog=epilog)
    parser.add_argument("--cs",help="input cs file")
    parser.add_argument("--passthrough",help="input passthrough file")
    parser.add_argument("--o",help="output star file, default=particles.star",default="particles.star")
    parser.add_argument("--OriginalPixelSize",type=float,help="original pixel size of micrograph, not super-resolution pixel size")
    parser.add_argument("--OpticsGroup",type=int,help="OpticsGroup Number, default=1",default=1)
    parser.add_argument("--OpticsGroupName",help="OpticsGroup Name, default=opticsGroup1",default="opticsGroup1")
    parser.add_argument("--flip_Y",type=bool,help="wether to flip along Y axis or not, True(1) for tif, False(0) for MRC and eer. Default=1",default=1)
    parser.add_argument("--MtfFile",help="relative path for MTF file, default=../../data_mtf_k3_std_300kv.star",default="../../data_mtf_k3_std_300kv.star")
    args=parser.parse_args()
    return args

args=parse_command_line()
cs_particle_file=args.cs
cs_passthrough_file=args.passthrough
star=args.o
rlnMicrographOriginalPixelSize=args.OriginalPixelSize
OpticsGroup=args.OpticsGroup
OpticsGroupName=args.OpticsGroupName
flipY=args.flip_Y
MtfFileName=args.MtfFile



class Particle:
    def __init__(self,rlnCoordinateX,rlnCoordinateY,rlnAngleRot,rlnAngleTilt,rlnAnglePsi,rlnOriginXAngst,rlnOriginYAngst,\
                 rlnImageName,rlnMicrographName,rlnDefocusU,rlnDefocusV,rlnDefocusAngle,rlnOpticsGroup,rlnCtfBfactor,\
                     rlnPhaseShift):
        self.coordinateX=rlnCoordinateX
        self.coordinateY=rlnCoordinateY
        self.AngleRot=rlnAngleRot
        self.AngleTilt=rlnAngleTilt
        self.AnglePsi=rlnAnglePsi
        self.offsetX=rlnOriginXAngst
        self.offsetY=rlnOriginYAngst
        self.imagename=rlnImageName
        self.micrographname=rlnMicrographName
        self.defocusU=rlnDefocusU
        self.defocusV=rlnDefocusV
        self.defocusAngle=rlnDefocusAngle
        self.opticsgroup=rlnOpticsGroup
        self.ctfbfactor=rlnCtfBfactor
        self.phaseshift=rlnPhaseShift
        

def ViewVector2EulerAngle(alignments3D_pose):
    viewvector=alignments3D_pose
    r=R.from_rotvec(viewvector)
    e=r.as_euler('zyz',degrees=True)
    rlnAnglePsi=e[0]
    rlnAngleTilt=e[1]
    rlnAngleRot=e[2]
    return rlnAngleRot,rlnAngleTilt,rlnAnglePsi


def write_header(star):
    meta_data = ["","","","data_particles","", "loop_", "_rlnCoordinateX #1", "_rlnCoordinateY #2", "_rlnAnglePsi #3",\
                 "_rlnImageName #4","_rlnMicrographName #5","_rlnOpticsGroup #6","_rlnDefocusU #7","_rlnDefocusV #8","_rlnDefocusAngle #9",\
                 "_rlnCtfBfactor #10","_rlnAngleRot #11","_rlnAngleTilt #12","_rlnOriginXAngst #13", "_rlnOriginYAngst #14"]
    with open(star, 'a+') as starfile:
        lines = starfile.readlines()
        for meta in meta_data:
            if not any(line.strip().startswith(meta) for line in lines):
                starfile.write(meta + '\n')

def write_data_optics(star):
    meta_data = ["# version 30001","","data_optics","","loop_","_rlnOpticsGroupName #1","_rlnOpticsGroup #2","_rlnMtfFileName #3",\
                 "_rlnMicrographOriginalPixelSize #4","_rlnVoltage #5","_rlnSphericalAberration #6","_rlnAmplitudeContrast #7",\
                 "_rlnImagePixelSize #8","_rlnImageSize #9","_rlnImageDimensionality #10"]
    with open(star, 'a+') as starfile:
        lines = starfile.readlines()
        for meta in meta_data:
            if not any(line.strip().startswith(meta) for line in lines):
                starfile.write(meta + '\n')

path=os.getcwd()
cs_file=os.path.join(path,cs_particle_file)
cs_passthrough=os.path.join(path,cs_passthrough_file)
cs=np.load(cs_file)
cs_passthrough=np.load(cs_passthrough)
#rlnMicrographOriginalPixelSize=cs_passthrough['blob/psize_A'][0]
rlnVoltage=cs['ctf/accel_kv'][0] if 'ctf/accel_kv' in cs.dtype.names else cs_passthrough['ctf/accel_kv'][0]
rlnSphericalAberration=cs['ctf/cs_mm'][0] if 'ctf/cs_mm' in cs.dtype.names else cs_passthrough['ctf/cs_mm'][0]
rlnAmplitudeContrast=cs['ctf/amp_contrast'][0] if 'ctf/amp_contrast' in cs.dtype.names else cs_passthrough['ctf/amp_contrast'][0]
rlnImagePixelSize=cs['blob/psize_A'][0]
rlnImageSize=cs['blob/shape'][0][0]
rlnImageDimensionality=2
    
        
data_optics="{0:<20}".format(OpticsGroupName)+"{0:<20}".format(str(OpticsGroup))+"{0:<40}".format(MtfFileName)+"{0:<25}".format(rlnMicrographOriginalPixelSize)+\
    "{0:<25}".format(rlnVoltage)+"{0:<25.2f}".format(rlnSphericalAberration)+"{0:<25.2f}".format(rlnAmplitudeContrast)+"{0:<25.4f}".format(rlnImagePixelSize)+\
        "{0:<20}".format(str(rlnImageSize))+"{0:<20}".format(rlnImageDimensionality)

        
def extract_particle_info(cs,cs_passthrough,count,rlnMicrographOriginalPixelSize,OpticsGroup=1):
    loc_x=cs_passthrough['location/center_x_frac'][count] if 'location/center_x_frac' in cs_passthrough.dtype.names else cs['location/center_x_frac'][count]
    loc_y=cs_passthrough['location/center_y_frac'][count] if 'location/center_y_frac' in cs_passthrough.dtype.names else cs['location/center_y_frac'][count]
    alignments3D_shift=cs['alignments3D/shift'][count] if 'alignments3D/shift' in cs.dtype.names else np.array([0.0,0.0])
    micrograph_shape=cs_passthrough['location/micrograph_shape'][count] if 'location/micrograph_shape' in cs_passthrough.dtype.names else cs['location/micrograph_shape'][count]
    
#    blob_psize=cs['blob/psize_A'][count]
    alignments3D_pix=cs['alignments3D/psize_A'][count] if 'alignments3D/psize_A' in cs.dtype.names else 0.0
    mic_shape_x=micrograph_shape[1]
    mic_shape_y=micrograph_shape[0]
    corX=loc_x*mic_shape_x
    corY=mic_shape_y-loc_y*mic_shape_y if flipY else loc_y*mic_shape_y
    #new_corX,new_corY=np.array(loc_x,loc_y)*micrograph_shape-alignments3D_shift*alignments3D_pix/rlnMicrographOriginalPixelSize
    new_corX,new_corY=np.array([corX,corY])-alignments3D_shift*alignments3D_pix/rlnMicrographOriginalPixelSize
    new_corX_round=round(new_corX,6)
    new_corY_round=round(new_corY,6)
    offsetX,offsetY=(np.array([new_corX,new_corY])-np.array([new_corX_round,new_corY_round]))*rlnMicrographOriginalPixelSize
    alignments3D_pose=cs['alignments3D/pose'][count] if 'alignments3D/pose' in cs.dtype.names else None
    rlnAngleRot,rlnAngleTilt,rlnAnglePsi=ViewVector2EulerAngle(alignments3D_pose) if alignments3D_pose is not None else np.array([0.0,0.0,0.0])
    ctf_df1=cs['ctf/df1_A'][count] 
    ctf_df2=cs['ctf/df2_A'][count]
    ctf_angle_rad=cs['ctf/df_angle_rad'][count]
    ctf_angle=ctf_angle_rad*180.0/np.pi
    phaseshift=cs['ctf/phase_shift_rad'][count]
    ctf_bfactor=cs['ctf/bfactor'][count]
    particleID_per_micrograph=cs['blob/idx'][count]
    particle_name=str(cs['blob/path'][count]).strip().split('_')
#    particle_path=str(cs['blob/path'][count]).strip().split('_')[0]
    particle_path=particle_name[0]
    particle_path=particle_path.strip().split('/')[0:-1]
    particle_path[0]=particle_path[0].strip("b'")
    particle_name='_'.join(particle_name[1:]).strip("'")
    particle_path.append(particle_name)
    particle_name='{0:>06}'.format(particleID_per_micrograph)+'@'+'/'.join(particle_path)
    location_micrograph_path=cs_passthrough['location/micrograph_path'][count] if 'location/micrograph_path' in cs_passthrough.dtype.names else cs['location/micrograph_path'][count]
    micrograph_name=str(location_micrograph_path).strip().split('_')
#    micrograph_name=str(cs_passthrough['location/micrograph_path'][count]).strip().split('_')
    micrograph_path=micrograph_name[0]
    micrograph_path=micrograph_path.strip().split('/')[0:-1]
    micrograph_path[0]=micrograph_path[0].strip("b'")
    micrograph_name='_'.join(micrograph_name[1:]).strip("'")
    micrograph_path.append(micrograph_name)
    micrograph_name='/'.join(micrograph_path)
    rlnOpticsGroup=OpticsGroup
    return new_corX_round,new_corY_round,offsetX,offsetY,rlnAngleRot,rlnAngleTilt,rlnAnglePsi,ctf_df1,ctf_df2,ctf_angle,phaseshift,ctf_bfactor,\
        particle_name,micrograph_name,rlnOpticsGroup


star_path=os.path.join(path,star)
if not os.path.isfile(star_path):
    write_data_optics(star_path)

with open(star_path,'a+') as starfile:
    starfile.write(data_optics+'\n')
    
write_header(star_path)


with open(star_path,'a+') as starfile:
    for i in range(0,len(cs)):
        new_corX_round,new_corY_round,offsetX,offsetY,rlnAngleRot,rlnAngleTilt,rlnAnglePsi,ctf_df1,ctf_df2,ctf_angle,phaseshift,ctf_bfactor,\
            particle_name,micrograph_name,rlnOpticsGroup=extract_particle_info(cs,cs_passthrough,i,rlnMicrographOriginalPixelSize,OpticsGroup)
        particle=Particle(new_corX_round, new_corY_round, rlnAngleRot, rlnAngleTilt, rlnAnglePsi, offsetX, offsetY, particle_name, micrograph_name, \
                          ctf_df1, ctf_df2, ctf_angle, rlnOpticsGroup, ctf_bfactor, phaseshift)
        particle_info="{0:<25}".format(particle.coordinateX)+"{0:<25}".format(particle.coordinateY)+"{0:<25}".format(particle.AnglePsi)+"{0:<120}".format(particle.imagename)+\
            "{0:<120}".format(particle.micrographname)+"{0:<10}".format(particle.opticsgroup)+"{0:<25}".format(particle.defocusU)+"{0:<25}".format(particle.defocusV)+\
                "{0:<25}".format(particle.defocusAngle)+"{0:<10}".format(particle.ctfbfactor)+"{0:<25}".format(particle.AngleRot)+"{0:<25}".format(particle.AngleTilt)+\
                "{0:<25}".format(particle.offsetX)+"{0:<25}".format(particle.offsetY)
        starfile.write(particle_info+'\n')
        
        
        

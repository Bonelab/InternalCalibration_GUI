#
# This script performs internal calibration from an input image and tissue reference mask.
# This method has been published as Michalski et al. (2020) "CT-based internal density calibration for opportunistic skeletal assessment using abdominal CT scans" Med Eng Phys
# DOI: https://doi.org/10.1016/j.medengphy.2020.01.009
#####
#
# Andrew Michalski
# University of Calgary
# Biomedical Engineering Graduate Program
# April 25, 2019
# Modified to Py3: March 25, 2020

# Updates by Chantal de Bakker - Feb-May, 2021:
# - Modified to use 3 reference tissues (bone, muscle, air) instead of the original 5 (bone, muscle, air, adipose, blood)
# - Modified to incorporate ITK-SNAP for all-in-one selection of tissues & running of internal calibration
# - Add dialog box to select file
# - Add DICOM to NIFTI converter
#####

script_version = 1.1

import ogo_helper_3Materials_BoneMuscleAir as ogo
import MassAttenuationTables as mat
import os
import sys
import argparse
import time
from datetime import date
from collections import OrderedDict
import subprocess
from PyQt5.QtWidgets import QApplication
from PyQt5 import Qt
import vtk

import gui

orientation_mat = vtk.vtkMatrix4x4()
orientation_mat.SetElement(0,0,1)
orientation_mat.SetElement(0,1,0)
orientation_mat.SetElement(0,2,0)
orientation_mat.SetElement(0,3,0)
orientation_mat.SetElement(1,0,0)
orientation_mat.SetElement(1,1,0)
orientation_mat.SetElement(1,2,1)
orientation_mat.SetElement(1,3,0)
orientation_mat.SetElement(2,0,0)
orientation_mat.SetElement(2,1,1)
orientation_mat.SetElement(2,2,0)
orientation_mat.SetElement(2,3,0)
orientation_mat.SetElement(3,0,0)
orientation_mat.SetElement(3,1,0)
orientation_mat.SetElement(3,2,0)
orientation_mat.SetElement(3,3,0)

####
# Start Script

# Ask user to select the file for the first, uncalibrated dicom image:
# (dicoms must be in uncompressed format)
app = QApplication(sys.argv)
ex = ogo.FileDlg()
image = ex.openFileNameDialog()
# print(image)

#Convert DICOM to NIFTI:
image_pathname = os.path.dirname(image)
print(image_pathname)
nii_fnm = os.path.split(image_pathname)[1]
ogo.dicom2nifti(image_pathname, nii_fnm, orientation_mat)
image = image_pathname+'/'+nii_fnm+'.nii'


# Call ITK-SNAP and load in the correct nifti image
# image = '/Volumes/Work/MetastaticBoneDisease/InternalCalibration/QCT_CAL/IncorporateITKSNAP/QCTCAL_0002.nii'
os.system('open -a ITK-SNAP '+image)
tt = os.popen('ps ax | grep ITK-SNAP').read()
# print(tt)

pid = tt.split()[0]
new_pid = tt.split()[0]
# print(pid)

mask_stats = Qt.QApplication(sys.argv)
window = gui.MainWindow()
mask_stats.exec_()


# Wait until user closes ITK-SNAP, then continue running
while pid==new_pid:
    tt = os.popen('ps ax | grep ITK-SNAP').read()
    new_pid = tt.split()[0]
    status = os.system('sleep 1')


# Find the newly created labels file = most recent file in directory
os.chdir(image_pathname)
ttt = os.popen('ls -lt *.nii').read()
mask_fnm = ttt.split()[8]
# print(ttt.split()[8])

# subprocess.run(['open', '-a', 'ITK-SNAP'])


####
# Start Internal Calibration
ogo.message("Start of Internal Calibration...")


#Determine image locations and names of files
image_pathname = os.path.dirname(image)
image_basename = os.path.basename(image)
mask_pathname = image_pathname #mask and image file must be saved in same directory
mask_basename = mask_fnm
mask = mask_pathname + '/' + mask_basename
org_fileName = image_basename.replace(".nii","")
fileName = image_basename.replace(".nii","_IC_K2HPO4.nii")
fileName2 = image_basename.replace(".nii","_IC_ARCH.nii")

##
# Read input image with correct reader
ogo.message("Reading input image...")
if (os.path.isdir(image)):
    ogo.message("Input image is DICOM")
    imageData = ogo.readDCM(image)
    imageType = 1

else:
    ext = os.path.splitext(image)[1]
    if (ext == ".nii" or ext == ".nifti"):
        ogo.message("Input image is NIFTI")
        imageData = ogo.readNii(image)
        imageType = 2
    else:
        print(("ERROR: image format not recognized for " + image))
        sys.exit()

##
# Read mask image with correct reader
ogo.message("Reading input mask image...")
if (os.path.isdir(mask)):
    ogo.message("Input mask is DICOM")
    maskData = ogo.readDCM(mask)

else:
    ext = os.path.splitext(mask)[1]
    if (ext == ".nii" or ext == ".nifti"):
        ogo.message("Input mask is NIFTI")
        maskData = ogo.readNii(mask)
    else:
        print(("ERROR: image format not recognized for " + mask))
        sys.exit()

##
# Extract reference tissues from the mask
# Using only 3 reference tissues (air, bone, and muscle)

ogo.message("Extracting reference tissue: Air...")
air_roi = ogo.maskThreshold(maskData, 2)
air_mask = ogo.applyMask(imageData, air_roi)
air_HU = ogo.imageHistogramMean(air_mask)
# ogo.message("Air ROI Mean HU: %8.4f " % air_HU[0])


ogo.message("Extracting reference tissue: Cortical Bone...")
bone_roi = ogo.maskThreshold(maskData, 4)
bone_mask = ogo.applyMask(imageData, bone_roi)
bone_HU = ogo.imageHistogramMean(bone_mask)
# ogo.message("Cortical Bone ROI Mean HU: %8.4f " % bone_HU[0])

ogo.message("Extracting reference tissue: Skeletal Muscle...")
muscle_roi = ogo.maskThreshold(maskData, 5)
muscle_mask = ogo.applyMask(imageData, muscle_roi)
muscle_HU = ogo.imageHistogramMean(muscle_mask)
# ogo.message("Skeletal Muscle ROI Mean HU: %8.4f " % muscle_HU[0])

mean_hu = [air_HU[0], bone_HU[0], muscle_HU[0]]

##
# Prep Reference Material Tables with interpolation over energy levels 1-200 keV
ogo.message("Deriving material tables...")
air_interp = ogo.icInterpolation(mat.air_table)
bone_interp = ogo.icInterpolation(mat.bone_table)
muscle_interp = ogo.icInterpolation(mat.muscle_table)
k2hpo4_interp = ogo.icInterpolation(mat.k2hpo4_table)
cha_interp = ogo.icInterpolation(mat.cha_table)
triglyceride_interp = ogo.icInterpolation(mat.triglyceride_table)
water_interp = ogo.icInterpolation(mat.water_table)

##
# Determine scan effective energy
ogo.message("Determining the scan effective energy...")
ic_parameters = ogo.icEffectiveEnergy(mean_hu, air_interp, bone_interp, muscle_interp, k2hpo4_interp, cha_interp, triglyceride_interp, water_interp)
attenuation_values = [ic_parameters['Air u/p'], ic_parameters['Cortical Bone u/p'], ic_parameters['Skeletal Muscle u/p']]


##
# Determine the HU-Mass Attenuation Relationship
ogo.message("Determining the HU-Mass Attenuation Relationship...")
hu_MUrho = ogo.icLinearRegression(mean_hu, attenuation_values, 'HU-u/p Slope', 'HU-u/p Y-Intercept')

##
# Determine the material densities
ogo.message("Determining the Material Densities...")
air_den = ogo.icMaterialDensity(air_HU[0], ic_parameters['Air u/p'], ic_parameters['Water u/p'], 1.0)
bone_den = ogo.icMaterialDensity(bone_HU[0], ic_parameters['Cortical Bone u/p'], ic_parameters['Water u/p'], 1.0)
muscle_den = ogo.icMaterialDensity(muscle_HU[0], ic_parameters['Skeletal Muscle u/p'], ic_parameters['Water u/p'], 1.0)

material_densities = [air_den, bone_den, muscle_den]

##
# Determine the HU-density relationship
ogo.message("Determining the HU-Material Density Relationship...")
hu_rho = ogo.icLinearRegression(mean_hu, material_densities, 'HU-Material Density Slope', 'HU-Material Density Y-Intercept')

##
# Compile the calibration parameters
ogo.message("Compiling the internal calibration parameters...")
cali_parameters = OrderedDict()
cali_parameters['ID'] = org_fileName
cali_parameters['Output File'] = fileName
cali_parameters['Python Script'] = sys.argv[0]
cali_parameters['Version'] = script_version
cali_parameters['Date Created'] = str(date.today())
cali_parameters['Image Directory'] = image_pathname
cali_parameters['Image'] = image_basename
cali_parameters['Mask Directory'] = mask_pathname
cali_parameters['Mask'] = mask_basename
cali_parameters['+++++'] = '+++++'
cali_parameters['Effective Energy [keV]'] = ic_parameters['Effective Energy [keV]']
cali_parameters['Max R^2'] = ic_parameters['Max R^2']
cali_parameters['HU-u/p Slope'] = hu_MUrho['HU-u/p Slope']
cali_parameters['HU-u/p Y-Intercept'] = hu_MUrho['HU-u/p Y-Intercept']
cali_parameters['HU-Material Density Slope'] = hu_rho['HU-Material Density Slope']
cali_parameters['HU-Material Density Y-Intercept'] = hu_rho['HU-Material Density Y-Intercept']
cali_parameters['Air u/p'] = ic_parameters['Air u/p']
cali_parameters['Cortical Bone u/p'] = ic_parameters['Cortical Bone u/p']
cali_parameters['Skeletal Muscle u/p'] = ic_parameters['Skeletal Muscle u/p']
cali_parameters['K2HPO4 u/p'] = ic_parameters['K2HPO4 u/p']
cali_parameters['CHA u/p'] = ic_parameters['CHA u/p']
cali_parameters['Triglyceride u/p'] = ic_parameters['Triglyceride u/p']
cali_parameters['Water u/p'] = ic_parameters['Water u/p']

# Write the output text file
txt_fileName = org_fileName + "_IntCalibParameters.txt"
ogo.message("Writing parameters to output text file: %s" % txt_fileName)
ogo.writeTXTfile(cali_parameters, txt_fileName, image_pathname)

##
# Apply the internal density calibration to the image
ogo.message("Applying the calibration to the image...")
calibrated_image, ARCH_image = ogo.applyInternalCalibration(imageData, cali_parameters)

##
# Write out calibrated image
ogo.message("Writing out the K2HPO4 calibrated image: %s" % fileName)
ogo.writeNii(calibrated_image, fileName, image_pathname, orientation_mat)
ogo.message("Writing out the Archimedean calibrated image: %s" % fileName2)
ogo.writeNii(ARCH_image, fileName2, image_pathname, orientation_mat)



##
# End of script
ogo.message("End of Script.")
ogo.message("Please cite 'Michalski et al. 2020 Med Eng Phys' when using this analysis.")
ogo.message("https://doi.org/10.1016/j.medengphy.2020.01.009")
sys.exit()

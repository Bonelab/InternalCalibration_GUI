import sys

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui
from PyQt5 import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QMenuBar, QMenu, QAction, QFileDialog, QErrorMessage,
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QTableWidget,
    QGroupBox, QWidget, QPushButton, QTableWidgetItem
)

import ogo_helper_3Materials_BoneMuscleAir as ogo

class MainWindow(QMainWindow):

    def __init__(self, parent=None, image=None):

        super().__init__(parent)

        self.image = image

        self._create_actions()
        self._create_menu_bar()

        self._create_materials_dict()

        self._create_layout()

        self._start()

    def _create_actions(self):
        pass

    def _create_menu_bar(self):
        pass

    def _create_materials_dict(self):

        #df = pd.read_fwf("Internal-Calibration_ITKSNAP_Labels.txt",skiprows=14,colspecs='infer')

        # one day this function will do something fancy where it reads an ITKSNAP
        # segmentation description file and automatically generates the material
        # dictionary, for now it is hardcoded since the accompanying script is

        self.materials_dict = {
            'Air': {
                'ID': 2,
                'color': 'green',
                'stats': {
                    'mean': {
                        'function': np.mean,
                        'value': 0
                    },
                    'variance': {
                        'function': np.var,
                        'value': 0
                    },
                    'min': {
                        'function': np.min,
                        'value': 0
                    },
                    'max': {
                        'function': np.max,
                        'value': 0
                    },
                }

            },
            'Cortical Bone': {
                'ID': 4,
                'color': 'purple',
                'stats': {
                    'mean': {
                        'function': np.mean,
                        'value': 0
                    },
                    'variance': {
                        'function': np.var,
                        'value': 0
                    },
                    'min': {
                        'function': np.min,
                        'value': 0
                    },
                    'max': {
                        'function': np.max,
                        'value': 0
                    },
                }
            },
            'Skeletal Muscle': {
                'ID': 5,
                'color': 'teal',
                'stats': {
                    'mean': {
                        'function': np.mean,
                        'value': 0
                    },
                    'variance': {
                        'function': np.var,
                        'value': 0
                    },
                    'min': {
                        'function': np.min,
                        'value': 0
                    },
                    'max': {
                        'function': np.max,
                        'value': 0
                    },
                }
            }
        }


    def _create_layout(self):

        self.frame = QFrame()
        self.layout = QVBoxLayout()

        self.layout.addWidget(self._create_buttons_group_box())
        self.layout.addWidget(self._create_scroll_area())

        self.frame.setLayout(self.layout)
        self.setCentralWidget(self.frame)

        self.update_material_tables()

    def _create_buttons_group_box(self):

        self.buttons_group_box = QGroupBox('Image and Mask')

        self.buttons_group_box_layout = QHBoxLayout()

        self.get_image_button = QPushButton('Get image \nfrom file...')
        self.get_image_button.clicked.connect(self.get_image)
        self.buttons_group_box_layout.addWidget(self.get_image_button)

        self.get_mask_button = QPushButton('Get mask \nfrom file...')
        self.get_mask_button.clicked.connect(self.get_mask)
        self.buttons_group_box_layout.addWidget(self.get_mask_button)

        self.update_mask_button = QPushButton('Reload mask,\nupdate parameters.')
        self.update_mask_button.clicked.connect(self.update_mask)
        self.buttons_group_box_layout.addWidget(self.update_mask_button)

        self.buttons_group_box.setLayout(self.buttons_group_box_layout)

        return self.buttons_group_box

    def _create_scroll_area(self):

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_area_widget = QWidget()
        self.scroll_area_layout = QVBoxLayout(self.scroll_area_widget)
        self.scroll_area.setWidget(self.scroll_area_widget)

        for m in self.materials_dict.keys():

            group_box = QGroupBox(m)
            layout = QHBoxLayout()
            group_box.setLayout(layout)

            group_box.setStyleSheet(
                f" QGroupBox {{ color: {self.materials_dict[m]['color']}; font-size: 15px }} "
            )

            self.materials_dict[m]['table'] = QTableWidget()
            self.materials_dict[m]['table'].setMinimumHeight(100)
            layout.addWidget(self.materials_dict[m]['table'])

            self.scroll_area_layout.addWidget(group_box)



        return self.scroll_area

    def get_data_from_file(self,title):
        # have the user select a dicom or nifti with a file dialog
        filepath, _ = QFileDialog.getOpenFileName(self,
            title,
            '.',
            'DICOM or NIFTI Files (*.dcm *.nii);; Nifti Files (*.nii) ;;DICOM Files (*.dcm)',
            'DICOM or NIFTI (*.dcm *.nii)',
            QFileDialog.DontUseNativeDialog
        )

        # if the user closed the dialog without choosing a file then we are done here
        if len(filepath)==0:
            return None

        # check the file extension and create an appropriate reader object
        if filepath.endswith('.nii'):
            data = ogo.readNii(filepath)

        elif filepath.endswith('.dcm'):
            data = ogo.readDCM(filepath)

        else:
            # because of the filter on the file dialog we should never end up
            # here, but if we do then trigger a warning
            msg = QErrorMessage()
            msg.showMessage("You selected a file other than *.nii or *.dcm, which shouldn't even be possible.")
            msg.exec_()
            data = None

        return data

    def get_image(self):

        image = self.get_data_from_file('Select image file')
        self.image = image if image else self.image

    def get_mask(self):

        mask = self.get_data_from_file('Select mask file')
        self.mask = mask if mask else self.mask

        self.update_mask()

    def update_mask(self):

        if not(self.image):
            print('No image loaded, cannot update')
            return

        if not(self.mask):
            print('No mask loaded, cannot update')
            return

        for m in self.materials_dict.keys():

            roi = ogo.maskThreshold(self.mask, self.materials_dict[m]['ID'])
            data = ogo.applyMask(self.image, roi)

            for s in self.materials_dict[m]['stats']:

                self.materials_dict[m]['stats'][s]['value'] = \
                    self.materials_dict[m]['stats'][s]['function'](ogo.vtk2numpy(data).flatten())

        self.update_material_tables()

    def update_material_tables(self):

        for m in self.materials_dict.keys():
            i = 0
            self.materials_dict[m]['table'].setColumnCount(2)
            self.materials_dict[m]['table'].setRowCount(len(self.materials_dict[m]['stats'].keys()))
            for s in self.materials_dict[m]['stats'].keys():
                self.materials_dict[m]['table'].setItem(i,0,QTableWidgetItem(s))
                self.materials_dict[m]['table'].setItem(i,1,QTableWidgetItem(f"{self.materials_dict[m]['stats'][s]['value']:0.2f}"))
                i += 1


    def _start(self):

        self.show()

def main():
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

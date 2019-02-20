# -*- coding: utf-8 -*-
import os
import pymol
import re
import ntpath
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox
import shutil



def __init_plugin__(app=None):
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('Enlighten', run_plugin_gui)


def run_plugin_gui():
    dialog = pymol.Qt.QtWidgets.QDialog()
    ui_file = os.path.join(os.path.dirname(__file__), 'ui_form2.ui')
    form = pymol.Qt.utils.loadUi(ui_file, dialog)

    form.pymolObjectRadio.toggled.connect(lambda: update_view(form))
    bind_file_dialog(form.pdbFileEdit, form.pdbFileBrowseButton)
    bind_directory_dialog(form.enlightenEdit, form.enlightenBrowseButton)
    bind_directory_dialog(form.amberEdit, form.amberBrowseButton)
    bind_directory_dialog(form.outputEdit, form.outputBrowseButton)

    form.runPrepButton.clicked.connect(lambda: run_prep(form))
    form.websiteButton.clicked.connect(open_enlighten_website)

    form.AdvancedOptionsButton.clicked.connect(lambda: advanced_options(form))

    form.SphereSizeSlider.sliderReleased.connect(lambda: change_slider_value(
        form, form.SphereSizeSlider.value()))
    form.SphereSizeValue.textChanged.connect(lambda: change_slider_position(form))

    form.phValue.textChanged.connect(lambda: change_pHvariable(form, form.phValue.text))


    adv_op_settings(form)
    initialize_view(form)


    dialog.show()


def initialize_view(form):
    form.pymolObjectRadio.setChecked(True)
    objects = pymol.cmd.get_names('objects')
    form.pymolObjectCombo.addItems(objects)
    form.pymolObjectCombo.setCurrentIndex(len(objects) - 1)

    enlighten_dir = os.getenv('ENLIGHTEN',
                              "Please specify ENLIGHTEN home directory")
    form.enlightenEdit.setText(enlighten_dir)

    amber_dir = os.getenv('AMBERHOME', "Please specify AMBER home directory")
    form.amberEdit.setText(amber_dir)

    form.outputEdit.setText(os.getcwd())
    form.ligandChargeEdit.setValidator(pymol.Qt.QtGui.QIntValidator())
    form.ligandChargeEdit.setText("0")

    ADVANCED_OPTIONS_WIDGETS = ('phLabel', 'SphereSizeLabel', 'phValue',
                                'SphereSizeSlider', 'SphereSizeValue')
    hide_widgets(form, ADVANCED_OPTIONS_WIDGETS)
    form.resize(400, 295)

    form.runStructButton.setEnabled(False)
    form.runDynamButton.setEnabled(False)
    form.advOpFrame.hide()


def advanced_options(form):

    ADVANCED_OPTIONS_WIDGETS = ('phLabel', 'SphereSizeLabel', 'phValue',
                                'SphereSizeSlider', 'SphereSizeValue')
    if form.AdvancedOptionsButton.text() == 'Show Advanced Options':
        form.advOpFrame.show()
        show_widgets(form, ADVANCED_OPTIONS_WIDGETS)
        form.AdvancedOptionsButton.setText('Hide Advanced Options')
        form.resize(405, 360)

    else:
        form.advOpFrame.hide()
        hide_widgets(form, ADVANCED_OPTIONS_WIDGETS)
        form.AdvancedOptionsButton.setText('Show Advanced Options')
        form.resize(405, 295)


def adv_op_settings(form):
    form.SphereSizeSlider.setMinimum(10)
    form.SphereSizeSlider.setMaximum(60)
    form.SphereSizeSlider.setValue(20)
    form.SphereSizeValue.setText(str(20) + "Å")

    form.phValue.setText('7.0')


def change_slider_value(form, sphereValue):
    sphere_size = int(sphereValue)
    form.SphereSizeValue.setText(str(sphereValue) + ' Å')


def change_slider_position(form):
    sphereValue = int(''.join(x for x in form.SphereSizeValue.text() if x.isdigit()))
    form.SphereSizeSlider.setValue(int(sphereValue))
    print("Set Sphere Size: " + str(sphereValue) + ' Å')


def change_ph_variable(form, pH):
    print('pH set to: ' + str(pH))


def update_view(form):
    PDB_FILE_WIDGETS = ('pdbFileLabel', 'pdbFileEdit', 'pdbFileBrowseButton')
    PYMOL_OBJECT_WIDGETS = ('pymolObjectLabel', 'pymolObjectCombo')

    if form.pdbFileRadio.isChecked():
        show_widgets(form, PDB_FILE_WIDGETS)
        hide_widgets(form, PYMOL_OBJECT_WIDGETS)
    else:
        show_widgets(form, PYMOL_OBJECT_WIDGETS)
        hide_widgets(form, PDB_FILE_WIDGETS)


def run_prep(form):
    import subprocess
    import sys
    import threads

    if validate_fields(form):
        return

    if form.pdbFileRadio.isChecked():
        pdb_file = form.pdbFileEdit.text()
        set_pdb_folder_location(form, form.pdbFileEdit.text())
    else:
        pdb_file = write_object_to_pdb(form.pymolObjectCombo.currentText())
        set_pdb_folder_location(form, form.pymolObjectCombo.currentText())

    if delete_pdb_verification is True:
        delete_pdb_folder(output_path)
    else:
        print("exiting prep")
        return

    ligand_name = form.ligandNameEdit.text()
    ligand_charge = form.ligandChargeEdit.text()
    enlighten = form.enlightenEdit.text()
    amberhome = form.amberEdit.text()
    os.chdir(form.outputEdit.text())
    os.environ.update({'AMBERHOME': amberhome})
    prepThread = threads.SubprocessThread("{}/prep.py {} {} {}"
                                          .format(enlighten, pdb_file,
                                                  ligand_name, ligand_charge))

    def prep_done():
        form.runPrepButton.setText("Run PREP")
        form.runPrepButton.setEnabled(True)
        form.runStructButton.setEnabled(True)
        if prepThread.error:
            error_message(form,
                          "The following errors were encountered:\n" +
                          prepThread.error)
        else:
            info_message(form, prepThread.output)
            form.runPrepButton.setEnabled(False)

    prepThread.finished.connect(prep_done)

    form.runPrepButton.setText("Running...")

    prepThread.start()


def set_pdb_folder_location(form, pdb_selected):
    if pdb_selected == form.pdbFileEdit.text():
        pdb_folder = os.path.splitext(os.path.basename(str(pdb_selected)))[0]
    else:
        pdb_folder = pdb_selected

    output_path = os.path.join(form.outputEdit.text(), pdb_folder)
    check_pdb_folder_existence(form, output_path)


def check_pdb_folder_existence(form, output_path):
    if os.path.isdir(output_path):
        pop_up_window(form, pdb_folder)


def pop_up_window(form, pdb_folder):
    delete_pdb_verification = QMessageBox.question(form, 'Warning',
                                        "A folder named {0} already exists. "
                                "Continuing will the delete folder, are you "
                        "sure you want to continue?".format(pdb_folder),
                                        QMessageBox.Yes | QMessageBox.No,
                                        QMessageBox.No)
    return delete_pdb_verification == QMessageBox.Yes


def delete_pdb_folder(output_path):
    if os.path.isdir(output_path):
        shutil.rmtree(output_path)
        print('Deleting folder at: ' + output_path)
    else:
        print("Folder no longer exists")


def run_struct():
    print("running STRUCT")
    form.runStructButton.setEnabled(False)

    def struct_done():
        print("STRUCT done")
        form.runStructButton.setEnabled(True)
        form.runDynamButton.setEnabled(True)


def run_dynam():
    print("running DYNAM")
    form.runDynamButton.setEnabled(False)

    def dynam_done():
        print("DYNAM is done")
        form.runDynamButton.setEnabled(True)


def write_object_to_pdb(object_name):
    filename = os.path.join(os.getcwd(), object_name + '.pdb')
    pymol.cmd.save(filename, '({})'.format(object_name))
    return filename


def open_enlighten_website():
    import webbrowser
    webbrowser.open_new("https://github.com/vanderkamp/enlighten2/")


def validate_fields(form):
    VALIDATORS = [pdb_validator, enlighten_validator,
                  amber_validator, output_validator, ligand_validator]
    results = [validator(form) for validator in VALIDATORS]
    errors = [result for result in results if result is not None]
    if errors:
        error_message(form,
                      "The following errors were encountered:\n"
                      "{}".format("\n".join(errors)))
    return errors


def pdb_validator(form):
    if not form.pdbFileRadio.isChecked():
        return None
    if not os.path.isfile(form.pdbFileEdit.text()):
        return "PDB file not found"
    return None


def enlighten_validator(form):
    enlighten_path = form.enlightenEdit.text()
    if not os.path.isdir(enlighten_path):
        return "Wrong Enlighten path"
    if not os.path.isfile(os.path.join(enlighten_path, 'prep.py')):
        return "prep.py not found in {}".format(enlighten_path)
    return None


def amber_validator(form):
    amber_bin_path = os.path.join(form.amberEdit.text(), 'bin')
    if not os.path.isdir(amber_bin_path):
        return "Wrong AMBER path"
    for filename in ('antechamber', 'pdb4amber', 'reduce'):
        if not os.path.isfile(os.path.join(amber_bin_path, filename)):
            return "{} not found in {}".format(filename, amber_bin_path)
    return None


def output_validator(form):
    output_path = form.outputEdit.text()
    if not os.path.isdir(output_path):
        return "directory {} does not exist".format(output_path)
    return None


def ligand_validator(form):
    if not form.ligandNameEdit.text():
        return "Ligand name not provided"
    return None


def info_message(form, text):
    pymol.Qt.QtWidgets.QMessageBox.information(form, "Enlighten", text)


def error_message(form, text):
    pymol.Qt.QtWidgets.QMessageBox.critical(form, "Enlighten", text)


def show_widgets(form, widgets):
    for widget in widgets:
        getattr(form, widget).show()


def hide_widgets(form, widgets):
    for widget in widgets:
        getattr(form, widget).hide()


def bind_file_dialog(lineEdit, browseButton):
    browseButton.clicked.connect(lambda: assign_filename(lineEdit))


def bind_directory_dialog(lineEdit, browseButton):
    browseButton.clicked.connect(lambda: assign_directory(lineEdit))


def assign_filename(lineEdit):
    lineEdit.setText(pymol.Qt.QtWidgets.QFileDialog.getOpenFileName()[0])


def assign_directory(lineEdit):
    lineEdit.setText(pymol.Qt.QtWidgets.QFileDialog.getExistingDirectory())

'''
def external_advanced_options():
    popUpDialog = pymol.Qt.QtWidgets.QDialog()
    pop_up_ui_file = os.path.join(os.path.dirname(__file__), 'ui_pop_up.ui')
    popup = pymol.Qt.utils.loadUi(pop_up_ui_file, popUpDialog)

    global object_file_name

    popup.popUpText.setText("A folder named {0} already exists. Continuing will"
                            " the delete folder, are you sure you want to "
                            "continue?"
                            .format(object_file_name))

    popup.cancelButton.clicked.connect(lambda: popUpDialog.close())
    popup.continueButton.clicked.connect(lambda: delete_pdb_folder(popup))

    popUpDialog.exec_()
'''

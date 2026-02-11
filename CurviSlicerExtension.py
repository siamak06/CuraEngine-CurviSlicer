# CurviSlicerExtension.py
# Cura Extension Plugin for CurviSlicer Integration
# Place in: %APPDATA%/cura/[VERSION]/plugins/CurviSlicerPlugin/

from UM.Extension import Extension
from UM.Application import Application
from UM.Message import Message
from UM.Logger import Logger
from UM.i18n import i18nCatalog
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator

from cura.CuraApplication import CuraApplication

from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, pyqtProperty
from PyQt6.QtWidgets import QFileDialog

import os
import subprocess
import tempfile
import shutil
import platform

catalog = i18nCatalog("cura")


class CurviSlicerExtension(Extension, QObject):
    """
    Cura Extension for CurviSlicer non-planar slicing integration
    """
    
    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Extension.__init__(self)
        
        self._application = CuraApplication.getInstance()
        
        # Plugin settings
        self._curvislicer_path = self._get_plugin_path()
        self._temp_dir = tempfile.gettempdir()
        
        # Add menu item
        self.setMenuName(catalog.i18nc("@item:inmenu", "CurviSlicer"))
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Process with CurviSlicer"), self.processCurviSlicer)
        self.addMenuItem(catalog.i18nc("@item:inmenu", "Settings"), self.showSettings)
        
        Logger.log("i", "CurviSlicer Extension loaded")
    
    def _get_plugin_path(self):
        """Get the path to the CurviSlicer binaries"""
        # Try to find CurviSlicer in plugin directory
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(plugin_dir, "bin")
        
        # Check platform
        system = platform.system()
        if system == "Windows":
            bin_dir = os.path.join(bin_dir, "windows")
        elif system == "Linux":
            bin_dir = os.path.join(bin_dir, "linux")
        else:
            Logger.log("w", f"Unsupported platform: {system}")
            return None
        
        if os.path.exists(bin_dir):
            return bin_dir
        
        Logger.log("w", "CurviSlicer binaries not found in plugin directory")
        return None
    
    def processCurviSlicer(self):
        """Main function: Process selected model with CurviSlicer"""
        
        # Check if binaries are available
        if not self._curvislicer_path:
            self._show_error("CurviSlicer binaries not found. Please check installation.")
            return
        
        # Get selected objects
        selected_objects = self._get_selected_objects()
        if not selected_objects:
            self._show_error("Please select a model to process")
            return
        
        if len(selected_objects) > 1:
            self._show_error("Please select only one model at a time")
            return
        
        selected_node = selected_objects[0]
        
        # Show processing message
        message = Message(
            catalog.i18nc("@info:status", "Processing with CurviSlicer..."),
            lifetime=0,
            dismissable=False,
            progress=-1
        )
        message.show()
        
        try:
            # Step 1: Export current model to STL
            stl_path = self._export_model_to_stl(selected_node)
            
            # Step 2: Run CurviSlicer optimizer
            optimized_stl = self._run_curvislicer(stl_path)
            
            # Step 3: Load optimized model back
            self._load_optimized_model(optimized_stl, selected_node)
            
            message.hide()
            self._show_success("Model processed successfully with CurviSlicer!")
            
        except Exception as e:
            message.hide()
            self._show_error(f"CurviSlicer processing failed: {str(e)}")
            Logger.log("e", f"CurviSlicer error: {str(e)}")
    
    def _get_selected_objects(self):
        """Get currently selected objects in the scene"""
        selected_objects = []
        for node in DepthFirstIterator(self._application.getController().getScene().getRoot()):
            if node.callDecoration("isSliceable") and node.isSelected():
                selected_objects.append(node)
        return selected_objects
    
    def _export_model_to_stl(self, node):
        """Export a scene node to STL file"""
        # Get mesh data
        mesh_data = node.getMeshData()
        if not mesh_data:
            raise Exception("No mesh data found")
        
        # Create temporary STL file
        stl_path = os.path.join(self._temp_dir, "curvi_input.stl")
        
        # Use Cura's STL writer
        from cura.Snapshot import Snapshot
        from UM.Mesh.MeshWriter import MeshWriter
        from UM.PluginRegistry import PluginRegistry
        
        writer = PluginRegistry.getInstance().getPluginObject("STLWriter")
        if not writer:
            raise Exception("STL Writer not found")
        
        # Write STL
        if not writer.write(stl_path, [node], MeshWriter.OutputMode.BinaryMode):
            raise Exception("Failed to export STL")
        
        Logger.log("i", f"Exported model to: {stl_path}")
        return stl_path
    
    def _run_curvislicer(self, stl_path, layer_height=0.3, nozzle_size=0.4):
        """Run CurviSlicer optimizer on the STL file"""
        
        # Determine executable name
        if platform.system() == "Windows":
            exe_name = "curvislice.bat"
        else:
            exe_name = "curvislice.sh"
        
        exe_path = os.path.join(self._curvislicer_path, exe_name)
        
        if not os.path.exists(exe_path):
            raise Exception(f"CurviSlicer executable not found: {exe_path}")
        
        # Get global stack for settings
        global_stack = self._application.getGlobalContainerStack()
        if global_stack:
            layer_height = global_stack.getProperty("layer_height", "value")
            nozzle_size = global_stack.getProperty("machine_nozzle_size", "value")
        
        # Build command
        cmd = [
            exe_path,
            "0",  # volumic
            str(nozzle_size),
            str(layer_height),
            "1.75",  # filament diameter
            "0",  # ironing
            stl_path
        ]
        
        Logger.log("i", f"Running CurviSlicer: {' '.join(cmd)}")
        
        # Run CurviSlicer
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self._curvislicer_path
            )
            
            if result.returncode != 0:
                Logger.log("e", f"CurviSlicer stderr: {result.stderr}")
                raise Exception(f"CurviSlicer failed with code {result.returncode}")
            
            Logger.log("i", "CurviSlicer optimization complete")
            
        except subprocess.TimeoutExpired:
            raise Exception("CurviSlicer timed out after 5 minutes")
        
        # Find the output file (after.stl)
        base_name = os.path.splitext(os.path.basename(stl_path))[0]
        output_dir = os.path.join(os.path.dirname(stl_path), base_name)
        optimized_stl = os.path.join(output_dir, "after.stl")
        
        if not os.path.exists(optimized_stl):
            raise Exception(f"Optimized STL not found: {optimized_stl}")
        
        return optimized_stl
    
    def _load_optimized_model(self, stl_path, original_node):
        """Load the optimized STL back into Cura, replacing original"""
        from UM.Scene.SceneNode import SceneNode
        from UM.Math.Vector import Vector
        from UM.Mesh.MeshReader import MeshReader
        from UM.PluginRegistry import PluginRegistry
        
        # Read the optimized STL
        reader = PluginRegistry.getInstance().getPluginObject("STLReader")
        if not reader:
            raise Exception("STL Reader not found")
        
        # Load mesh
        mesh_data = reader.read(stl_path)
        if not mesh_data:
            raise Exception("Failed to read optimized STL")
        
        # Get original position and transformations
        original_position = original_node.getPosition()
        original_scale = original_node.getScale()
        original_rotation = original_node.getOrientation()
        
        # Remove original node
        op = self._application.getController().getScene().getRoot().removeChild(original_node)
        if op:
            op.push()
        
        # Create new node with optimized mesh
        new_node = SceneNode()
        new_node.setMeshData(mesh_data)
        new_node.setSelectable(True)
        new_node.setName("CurviSliced_" + original_node.getName())
        
        # Apply original transformations
        new_node.setPosition(original_position)
        new_node.setScale(original_scale)
        new_node.setOrientation(original_rotation)
        
        # Add to scene
        op = self._application.getController().getScene().getRoot().addChild(new_node)
        if op:
            op.push()
        
        Logger.log("i", "Loaded optimized model into scene")
    
    def showSettings(self):
        """Show settings dialog"""
        self._show_info("CurviSlicer Settings\n\nBinaries path: " + str(self._curvislicer_path))
    
    def _show_error(self, text):
        """Display error message"""
        Message(
            text,
            title=catalog.i18nc("@info:title", "CurviSlicer Error"),
            lifetime=10
        ).show()
    
    def _show_success(self, text):
        """Display success message"""
        Message(
            text,
            title=catalog.i18nc("@info:title", "CurviSlicer"),
            lifetime=5
        ).show()
    
    def _show_info(self, text):
        """Display info message"""
        Message(
            text,
            title=catalog.i18nc("@info:title", "CurviSlicer Info"),
            lifetime=10
        ).show()


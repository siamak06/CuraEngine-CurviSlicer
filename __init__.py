from . import CurviSlicerExtension

def getMetaData():
    return {
        "mesh_writer": {},
        "extension": {
            "name": "CurviSlicer Integration",
            "description": "Non-planar curved layer slicing"
        }
    }

def register(app):
    return {
        "extension": CurviSlicerExtension.CurviSlicerExtension(app)
    }

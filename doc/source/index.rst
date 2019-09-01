.. PyWunderCam documentation master file, created by
   sphinx-quickstart on Sun Sep  1 21:08:18 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyWunderCam's documentation!
=======================================

Draft design doc

* Connection
    * Handles just the connectivity of the camera
    * Initialise with Camera-IP
    * If camera found, it returns success and a handle to the camera
    * For the camera to be "found" it has to answer to a basic parameter sweep message
    
* CameraConfiguration
    * Tells the camera what to do

* Camera
    * Is a composition of the above
    * Synchronise state between camera and app (two modes, sync and force.)
    * Take a shot, return the image(s) of the shot
    * Take a video, return the video.
    * Get handle to an AssetSequence in camera.
    
* AssetSequence
    * Get a named regexp for the format of the filename
    * scan a specific directory for contents
    

.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

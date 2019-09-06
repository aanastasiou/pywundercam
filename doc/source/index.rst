.. PyWunderCam documentation master file, created by
   sphinx-quickstart on Sun Sep  1 21:08:18 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyWunderCam's documentation!
=======================================

PyWunderCam is a Python module that enables control of the Wunder 360 S1 panoramic camera from a Python program.

The camera is based on a `Rockchip 1108 System on Chip (SoC) <http://rockchip.wikidot.com/rk1108>`_ running Linux. 
Within its operating system, it raises three services to serve images and video, control the camera and stream video 
over the WiFi interface. In addition to these services, the camera presents itself as a standard webcam if connected 
via USB but with minimal control over its parameters. 

At the time of writing, PyWunderCam interfaces with the first two services and enables functionality that is not 
possible via the provided mobile phone application. 

Streaming video and extended functionality are scheduled for upcoming releases.


Quickstart
----------

Directing the camera to take pictures and video
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most usual cycle of interaction with the hardware is as follows:

0. Ensure that the computer has joined the network advertised by the camera.
1. Connect to the camera via the PyWunderCam client.
2. Get the camera state.
3. Ensure that it is in the desired...state.
4. Trigger the action (e.g. take a snapshot, burst, video, etc)

So, to take a 360 picture:
::

    from pywundercam import PyWunderCam
    
    camera_client = PyWunderCam("192.168.100.1")
    camera_state = camera_client.state
    # Ensure that the camera is in single picture mode
    camera_state.shoot_mode = 0
    # Set the camera to the desired state
    camera_client.state = camera_state
    # Trigger the camera
    camera_client.trigger()

Once ``trigger()`` is called, the camera will sound a beep and it will have taken a picture and stored it in its 
internal SD card. 

To take a set of pictures in burst mode, change the ``shoot_mode`` to ``3`` and to start (and stop) taking a 
video, set the ``shoot_mode`` to ``1``.


Retrieving the captured images / videos
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is achieved with a number of steps that are very similar to directing the camera to take pictures:

0. Ensure that the computer has joined the network advertised by the camera.
1. Connect to the camera via the PyWunderCam client.
2. Get the camera state.
3. *Get the file system state* (**BEFORE** the action) 
4. Ensure that camera state is in the desired...state.
5. Trigger the action (e.g. take a snapshot, burst, video, etc)
6. *Get the file system state* (**AFTER** the action)
7. *Retrieve the difference AFTER - BEFORE, to determine which files were generated and download them*.

So, to take a 360 picture and retrieve the image data:
::

    from pywundercam import PyWunderCam
    
    camera_client = PyWunderCam("192.168.100.1")
    camera_state = camera_client.state
    # Ensure that the camera is in single picture mode
    camera_state.shoot_mode = 0
    # Set the camera to the desired state
    camera_client.state = camera_state
    # Get a "snapshot" of its file contents BEFORE the shot
    contents_before = camera_client.get_resources()
    # Trigger the camera
    camera_client.trigger()
    # Get a "snapshot" of the file contents AFTER the shot
    contents_after = camera_client.get_resources()
    # Create a new snapshot that only contains the image that was acquired by this action
    latest_image = contents_after["images"] - contents_before["images"]
    
Without getting into a lot of detais at this point, ``latest_image`` will contain only one image. To retrieve it:
::

    shot_image = latest_image[0].get()
    
The ``get()`` function will trigger a file transfer from the camera to the computer over WiFi and depending on the size
of the file, it will introduce a small pause.

At the time of writing, PyWunderCam serves images as ``PIL.Image`` objects. Therefore, after ``get()``, the image is 
already in a form that can be passed to other algorithms (e.g. machine vision) for further processing. 

Trying to retrieve a video in the same way will **raise an exception**. 


Videos can still be transferred over WiFi and stored to the local computer for further processing.

To do this:

::

    from pywundercam import PyWunderCam
    
    camera_client = PyWunderCam("192.168.100.1")
    camera_state = camera_client.state
    # Ensure that the camera is in video mode
    camera_state.shoot_mode = 1
    # Set the camera to the desired state
    camera_client.state = camera_state
    # Get a "snapshot" of its file contents BEFORE the shot
    contents_before = camera_client.get_resources()
    # Trigger the camera
    camera_client.trigger()
    # Get a "snapshot" of the file contents AFTER the shot
    contents_after = camera_client.get_resources()
    # Create a new snapshot that only contains the video that was acquired by this action
    latest_video = contents_after["videos"] - contents_before["videos"]
    latest_video[0].save_to("myvideo.mp4")
    

This concludes the quickstart. 

You could now browse over to the rest of the documentation sections to learn more about exceptions, hardware, and 
software design around PyWunderCam.


.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   concepts
   details
   code_doc



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

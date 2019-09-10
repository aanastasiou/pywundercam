Advanced Use
============

The Quickstart guide made use of a special class called ``PyWunderCamAuto``. That class provides two functions
(``.single_shot()``, ``.continuous_shot()``) that hide the details of communicating with the camera.

``PyWunderCamAuto`` is based on the ``PyWunderCam`` class and that class is allowing much finer control over 
the functionality of the camera.

The objective of this section is to outline the use of ``PyWunderCam`` and the way communication is carried out between 
a client and the camera.

Directing the camera to take pictures / video
---------------------------------------------
The most usual cycle of interaction with the hardware is as follows:

0. Ensure that the computer has joined the network advertised by the camera.
1. Connect to the camera via the ``PyWunderCam`` client.
2. Get the current camera state.
3. Ensure that it is in the desired...state, depending on what is to be carried out.
4. Trigger the action (e.g. take a snapshot, burst, video, etc)

So, to take a single 360 picture:
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
---------------------------------------

This is achieved with a few additional steps that are conceptually very similar to directing the camera 
to take pictures:

0. Ensure that the computer has joined the network advertised by the camera.
1. Connect to the camera via the ``PyWunderCam`` client.
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

At the time of writing, ``PyWunderCam`` serves images as ``PIL.Image`` objects. Therefore, after ``get()``, the image is 
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
    

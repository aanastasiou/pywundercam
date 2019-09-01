.. PyWunderCam documentation master file, created by
   sphinx-quickstart on Sun Sep  1 21:08:18 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyWunderCam's documentation!
=======================================

PyWunderCam is a Python module to take control of the Wunder 360 S1 panoramic camera.

The camera is based on a Rockchip 8211 SoC that presents itself as a complete system running a version of linux. Within 
its operating system, it raises three services to serve images and video, control the camera and stream video over the
WiFi interface. In addition to these services, the camera presents itself as a standard webcam if connected via USB but
with minimal control over its resolution. 

At the time of writing, PyWunderCam interfaces with the first two services while an upcoming release will offer 
streaming video preview either via WiFi or Video4Linux.

Quickstart
----------

A key concept when working with PyWunderCam is that of **state**. The camera is in a particular *state* and when
*triggered* in that *state* it will carry out an *action* that will likely modify its **state**.

For example: The camera powers up in *single photo* mode with a fresh SD card and indicates that it has capacity for 
approximately 2000 pictures. In this simple example, **mode** and **capacity** determine the state of the camera.
After triggering the camera to take a snapshot, it will have remained in the same mode but its capacity will now have 
been reduced by 1 frame.

Triggering actions based on the current state
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Therefore, the most usual cycle of interaction with the hardware is as follows:

1. Connect to the camera
2. Get its current state
3. Ensure that it is in the desired state
4. Trigger an action

And in code:
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

Once ``trigger()`` is called, the camera will sound a beep and it will have taken a picture. Repeatedly calling 
``trigger()`` will be repeating the same *action* provided that the *state* of the camera has not changed since the 
last time it was reset.

To take a set of pictures in quick succession, change the ``shoot_mode`` to ``3`` and to start (and stop) taking a 
video, set the ``shoot_mode`` to ``1``.

Retrieving the shot material
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that we know how to trigger the camera to carry out an action, let's see how to retrieve the images / videos it 
has shot.

Again, the concept of **state** is very important here. Remember our last example, we put the camera in a particular 
state, triggered an action and the action brought the camera to a new state.

This is exactly what happens with its file space too. **BEFORE** we take a single 360 shot with the camera, there were 
(for instance) 5 pictures on its SD card. **AFTER** we took a single shot, there are now 6 pictures on its SD card and
therefore, we can pinpoint which image was the result of our last action.

In code:
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
already in a form that can be passed to other algorithms (e.g. machine vision) for further processing. Trying to 
retrieve a video in the same way will raise an exception. Videos can still be transferred over WiFi and stored to the 
local computer for further processing.

To do this:

::

    from pywundercam import PyWunderCam
    
    camera_client = PyWunderCam("192.168.100.1")
    camera_state = camera_client.state
    # Ensure that the camera is in single picture mode
    camera_state.shoot_mode = 1
    # Set the camera to the desired state
    camera_client.state = camera_state
    # Get a "snapshot" of its file contents BEFORE the shot
    contents_before = camera_client.get_resources()
    # Trigger the camera
    camera_client.trigger()
    # Get a "snapshot" of the file contents AFTER the shot
    contents_after = camera_client.get_resources()
    # Create a new snapshot that only contains the image that was acquired by this action
    latest_video = contents_after["videos"] - contents_before["videos"]
    latest_video[0].save_to("myvideo.mp4")
    
This concludes the quickstart. Head over to the rest of the documentation sections to know more about PyWunderCam.


.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   code_doc



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

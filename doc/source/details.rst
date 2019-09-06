Details
=======

Camera Control
--------------

There are two classes that facilitate camera control:

* :class:`pywundercam.PyWunderCam`
* :class:`pywundercam.CamState`

All interaction with the camera (connecting to different services, exchanging data, etc) is handled by ``PyWunderCam``,
while state tracking and validation is handled by ``CamState``.

``CamState`` exposes all camera parameters as class properties and the getters and setters of those properties are 
doing the marshalling from and to the camera parameter names. To reduce the amount of communications with the camera, 
all the changes of individual parameters are scheduled in one batch rather than changed immediately.

When the state is obtained with something like:
::

    wc = PyWunderCam()
    camera_state = wc.camera_state

The camera state object is entering *edit mode*. In that mode, any changes to its attributes are simply recorded and 
put in a queue. If multiple changes are applied to an attribute, only the last change is preserved.

When the state is assigned back to the camera with:
::

    wc.camera_state = camera_state
    
All queued camera state changes are applied to the camera and the responses collated to reflect the latest camera state.

Resource I/O
------------

All interaction with the camera's file system occurs over a typical HTTP interface. The onboard camera control service 
does contain file system functionality (e.g. calls to list, retrieve, delete files) but since an HTTP interface is 
provided, all file related requests are handled via HTTP "verbs" such as ``GET, POST, PUT, DELETE, HEAD``.

There are three classes that facilitate file I/O:

* :class:`pywundercam.ResourceContainer`
* :class:`pywundercam.SingleResource`
* :class:`pywundercam.SequenceResource`

The design here is straightforward, a ``ResourceContainer`` contains zero or more ``SingleResource`` or 
``SequenceResource``. ``SingleResource`` represents a single file, ``SequenceResource`` represents mutliple (grouped)
files, such as those that result from taking pictures in "Burst" mode. ``SequenceResource`` is in fact a list of 
``SingleResource`` with a set of convenience functions.


When the file system state is captured with something like:
::

    fs_state = wc.get_resources()
    
PyWunderCam returns a dictionary with two top level ``ResourceContainer`` s. One for images and one for videos.

A ``ResourceContainer`` is a representation of the camera's file **state** at the moment it was obtained. To discover 
new files that were created as the result of an action (e.g. taking one or more pictures or videos), simply subtract 
two ``ResourceContainer`` objects. Usually these are the **AFTER** the action and **BEFORE** the action was taken
objects. This *temporal order* (*AFTER-BEFORE*) needs to be preserved, otherwise the difference is obtained but results
to an empty set.

This means that a camera's actions can be scripted and a collection of the files that were generated be returned to the 
user in one block. For example, the user could obtain a baseline ``ResourceContainer``, program the camera to obtain 
two single shot images and 2 bursts at different rates and finally get a ``ResourceContainer`` with all the files 
that where created by this "programmable" type of action.

Resource Metadata
^^^^^^^^^^^^^^^^^

``ResourceContainer`` s are relying on 
`regular expressions with named groups <https://docs.python.org/3/howto/regex.html#non-capturing-and-named-groups>`_  
to extract metadata from the filename of a resource.

In the case of the Wunder360 S1, image and video filenames follow a simple naming pattern that encodes the type of 
file resource, the date and time of acquisition, the frame (if acquired in "Burst" mode) and the format of the resource
in the extension.

The named regular expression rules used by the Wunder 360 S1 are already encoded in constants 
``pywundercam.IMG_FILE_RE`` and ``pywundercam.VID_FILE_RE``.

Metadata for a ``SingleResource`` are accessed via the ``.metadata`` read-only attribute.

Resource Transfers
^^^^^^^^^^^^^^^^^^

File transfers are handled by ``pywundercam.SingleResource.get()`` and ``pywundercam.SingleResrouce.save_to()``. 
Specifically, if an image is retrieved, it is served back as a ``PIL.Image`` object and can be readily used by a wide 
array of other Python packages. ``save_to()`` will simply transfer the file and save it locally. 

The ``SequenceResource`` equivalent ``save_to()`` and ``get()`` functions have similar side-effects but automatically 
applied over image sequences.

Advanced Use
============

Basic Concepts
--------------

Wunder 360 S1 - Hardware
^^^^^^^^^^^^^^^^^^^^^^^^
This is a very brief section on the camera's hardware and will be expanded with more details in upcoming versions.

The camera is based on a `Rockchip 1108 SoC <http://rockchip.wikidot.com/rk1108>`_ and boots into Linux. Once the 
system is up and running, it starts at least 3 processes:

1. A secure shell (SSH) server.
2. A web server (NGINX).
3. A `Real Time Streaming Protocol / Real Data Transfer (RTSP / RDT) <https://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol>`_ 
   server.
4. A common "USB camera" service that provides streaming preview.
   
On the default image that the product was shipped with, the credentials to login to the SSH server are:
::

    Username: root
    Password: root

NGINX starts typically on port 80 and serves part of the camera's filespace as:
::

    /
        DCIM/
            Images/
            Videos/
            
.. note::
    PyWunderCam's File I/O is coordinated entirely over this interface.
    
NGINX also hosts a small `Common Gateway Interface <https://en.wikipedia.org/wiki/Common_Gateway_Interface>`_ (CGI) 
binary that enables control of the camera over HTTP. The script is called ``fcgi_client.cgi`` and accepts control 
commands and returns responses from the camera hardware. It is interesting to note here the bizarre choice of having 
HTTP GET verbs used for *setting state* for **some** variables but using HTTP POST for others.

The RTSP / RDT server interface would imply that the camera could be used as an 
`IP Camera <https://en.wikipedia.org/wiki/IP_camera>`_. However, it is not entirely clear if this service is active 
throughout the time the camera is on, or it is started as a response to a command.



State
^^^^^

PyWunderCam's design is based around the concept of managing **state**. The camera is set to a particular *state* and 
when *triggered* in that *state* it will carry out an **action** that will likely modify its **state**.

For example: Suppose that the camera powers up in *single photo mode* with a fresh SD card and indicates that it has 
*capacity* for approximately 2000 pictures. In this simple example, **mode** and **capacity** determine the **state** 
of the camera. After triggering the camera to take a snapshot, it will have remained in the same mode but its capacity 
will now have been reduced by 1 frame.

This concept of **state* is extended to the camera's file system too. Continuing with the above example, when the camera
powers up, it contains a set of file resources such as images and videos. After taking a snapshot (triggering an action)
more images and videos will be added to its set of files. Here, the state of the file system is directly equivalent to 
the files it holds. In general, the structure of the file system would have to be taken into account as well, but the 
file organisation on cameras is very simple and usually static. On the Wunder S1 for example, there is a top level 
directory ``DCIM/`` that is further split into ``Images/`` and ``Videos/`` and this file organisation doesn't change.

The rest of this document contains detailed notes for each of PyWunderCam's components along with advanced usage.

Camera Control
--------------

There are two classes that facilitate camera control:

* :class:`wundercam.wundercam.PyWunderCam`
* :class:`wundercam.wundercam.CamState`

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

File I/O
--------

All interaction with the camera's file system occurs over a typical HTTP interface. The onboard camera control service 
does contain file system functionality (e.g. calls to list, retrieve, delete files) but since an HTTP interface is 
provided, all file related requests are handled via HTTP "verbs" such as ``GET, POST, PUT, DELETE, HEAD``.

There are three classes that facilitate file I/O:

* :class:`wundercam.wundercam.ResourceContainer`
* :class:`wundercam.wundercam.SingleResource`
* :class:`wundercam.wundercam.SequenceResource`

The design here is straightforward, a ``ResourceContainer`` contains zero or more ``SingleResource`` or 
``SequenceResource``. ``SingleResource`` represents a single file, ``SequenceResource`` represents mutliple (grouped)
files, such as those that result from taking pictures in "Burst" mode.


When the file system state is captured with something like:
::

    fs_state = wc.get_resources()
    
PyWunderCam returns a dictionary with two top level ``ResourceContainer``s. One for images and one for videos.

A ``ResourceContainer`` is a representation of the camera's file **state** at the moment it was obtained. To discover 
new files that were created as the result of an action (e.g. taking one or more pictures or videos), simply subtract 
two ``ResourceContainer`` objects. Usually these are the **BEFORE** the action and **AFTER** the action was taken.

This means that a camera's actions can be scripted and a collection of the files that were generated be returned to the 
user in one block. For example, the user could obtain a baseline ``ResourceContainer``, program the camera to obtain 
two single shot images and 2 bursts at different rates and finally get a ``ResourceContainer`` with all the files 
that where created by this "programmable" type of action.

Metadata
^^^^^^^^

``ResourceContainer``s are relying on 
`regular expressions with named groups <https://docs.python.org/3/howto/regex.html#non-capturing-and-named-groups>`_  
to extract metadata from the filename of a resource.

In the case of the Wunder360 S1, image and video filenames follow a simple naming pattern that encodes the type of 
file resource, the date and time of acquisition, the frame (if acquired in "Burst" mode) and the format of the resource
in the extension.

The named regular expression rules used by the Wunder 360 S1 are already encoded in constants 
``pywundercam.IMG_FILE_RE`` and ``pywundercam.VID_FILE_RE``.

File transfers
^^^^^^^^^^^^^^

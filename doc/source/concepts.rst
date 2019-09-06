Basic Concepts
==============

State
-----

PyWunderCam's design is based around the concept of managing **state**. The camera is set to a particular *state* and 
when *triggered* in that *state* it will carry out an **action** that will likely modify its **state**.


Camera State
^^^^^^^^^^^^

Suppose that the camera powers up in *single photo mode* with a fresh SD card and indicates that it has 
*capacity* for approximately 2000 pictures. In this simple example, **single photo mode** and **capacity** determine 
the **camera state**. After triggering the camera to take a snapshot, it will have remained in the same mode but its 
capacity will now have been decreased by 1 frame.

On the Wunder 360 S1, the camera state is defined by 31 parameters such as battery condition, ISO, White Balance and 
others.


Resource State
^^^^^^^^^^^^^^

This concept of **state** is extended to the camera's file system too. 

Continuing with the above example, when the camera powers up, it contains a set of **file resources** such as images 
and videos. After taking a snapshot (*triggering an action*), more images and videos will be added to its set of files. 

Here, the state of the file system is directly equivalent to the files it holds. In general, the structure of the file 
system would have to be taken into account as well, but the file organisation on cameras is very simple and usually 
static. On the Wunder 360 S1 for example, there is a top level directory ``DCIM/`` that is further split into 
``Images/`` and ``Videos/`` and this file organisation doesn't change (at least by the camera's onboard logic).


Wunder 360 S1 - Hardware
------------------------

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

The common USB webcam interface does enable the Wunder 360 S1 to be connected to a PC (or other device) but it does not 
"advertise" any parameters other than "brightness". The preview received over USB however **is** responsive to any 
state changes that might be applied over the WiFi control connection.

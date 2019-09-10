""" 
This module implements an interface to a Wunder 360 S1 through Python.

:authors: Athanasios Anastasiou
:date: August 2019


"""

import re                           # Regular expressions to decode the metadata in image and video filenames
import requests                     # Handles all file I/O activity with the camera over an HTTP interface

from .exceptions import (PyWunderCamTimeOutError, PyWunderCamConnectionError, PyWunderCamDataTransferError, 
                        PyWunderCamContentTypeError, PyWunderCamValueError, PyWunderCamCameraNotFoundError,
                        PyWunderCamSDCardUnusable)
from .resourceio import SingleResource, SequenceResource, ResourceContainer
from .state import CamState
import time


# Convenience presets for the naming rules used by the S1 hardware to name Image and Video files.

#: Named regular expression for decoding metadata from the name of an image file.
#: The named attributes of this regular expression are preserved along with a 
#: file resource as metadata.
IMG_FILE_RE = re.compile("Img_(?P<year>[0-9][0-9][0-9][0-9])(?P<month>[0-9][0-9])(?P<day>[0-9][0-9])_(?P<hour>[0-9][0-9])(?P<minute>[0-9][0-9])(?P<second>[0-9][0-9])_(?P<frame>[0-9][0-9][0-9])\.jpg")

#: Named regular expression for decoding metadata from the name of a video file.
#: The named attributes of this regular expression are preserved along with a 
#: file resource as metadata.
VID_FILE_RE = re.compile("Vid_(?P<year>[0-9][0-9][0-9][0-9])(?P<month>[0-9][0-9])(?P<day>[0-9][0-9])_(?P<hour>[0-9][0-9])(?P<minute>[0-9][0-9])(?P<second>[0-9][0-9])_(?P<frame>[0-9][0-9][0-9])\.mp4")

# Named attributes (from the above sequences) to distinguish between single snapshots 
# and "Continuous" snapshots. 
# In the case of "Continuous" takes, PyWunderCam can pack them together in a sequence automatically.

#: Attributes to group sets of images by. Images that are shot in quick succession (for example, 
#: in "Continuous" (or "Burst") mode). In that case, the images can be grouped by same values in
#: these attributes.
IMG_GROUP_BY = ["year", "month", "day", "hour", "minute", "second"]

#: Similar to ``IMG_GROUP_BY`` but for videos.
VID_GROUP_BY = IMG_GROUP_BY

#: Attribute to order image sequences by. This refers to a field of the metadata regular expressions.
IMG_ORDER_BY = "frame"

#: Similar to ``IMG_ORDER_BY`` but for videos.
VID_ORDER_BY = IMG_ORDER_BY
                
                
class PyWunderCam:
    """The main client object that communicates with the various services exposed by the camera.
    
    WunderCam handles all hardware requests and data transfers. At the very least, the camera exposes the following
    services:
    
    1. An NGINX web server on ``camera_ip:80``. (Known here as the "File I/O service")
    2. A ``fcgi_client.cgi`` script that handles specific commands towards the hardware. (Known here as the "Control
       Service")
    3. A Real Time Streaming Protocol (RTSP)/Real Data Transport (RDT) service to handle preview video streaming.
    
    Currently, the WunderCam interfaces to the first two services and there are plans to be able to decode individual
    frames from a stream, at will, in the future.
    """
        
    def __req_data(self, command, params = None):
        """Makes a request to the camera taking care of timeouts, status codes and return result data type.
        
        :param command: A numeric command, corresponds to the parameter ``cmd`` of the ``fcgi_client.cgi`` script.
        :type command: int (positive)
        :params: Parameters associated with ``command``. Usually, it is the ``WRITE`` commands that require parameters.
        """        
        try:
            req_params = {"cmd":command}
            if params:
                req_params.update(params)
            camera_data = requests.get(self.control_uri, req_params, timeout=5)
        except requests.exceptions.ConnectionError:
            raise PyWunderCamConnectionError("Failed to connect to %s." % self.control_uri)
        except requests.exceptions.Timeout:
            raise PyWunderCamTimeOutError("Request timed out.")
        except:
            raise
            
        if camera_data.status_code!=200:
            raise PyWunderCamDataTransferError(message="Response status code:%s. %s." % (camera_data.status_code, camera_data.message))
        
        return camera_data.json()

    def __init__(self, camera_ip="192.168.100.1"):
        """Initialises the main WunderCam client through the camera's Internet Protocol (IP) address.
        
        :param camera_ip: The IP that the camera is on. For WunderCam this is ``192.168.100.1`` by default.
        :type camera_ip: str (IP)
        """
         
        self._camera_ip = None
        self._control_uri = None
        self._file_io_uri = None
        self._current_camera_state = None

        self.control_uri = "http://%s/fcgi_client.cgi" % camera_ip
        try:
            # Check if the service endpoints have come online on the camera.
            # If the control service is online it will return the current time.
            sd_card_flag = self.__req_data(3)
            is_camera_control_service_live = len(sd_card_flag)>0
            # If the file control is online, this deliberate mistake should fail.
            is_camera_web_server_live = requests.get("http://%s/DCIM/img/" % camera_ip, timeout=5).status_code == 404
        except requests.exceptions.ConnectionError:
            raise PyWunderCamConnectionError("Could not connect to %s" % camera_ip)
        except:
            raise
        # If either of the services are not in place, the camera is considered inactive.    
        if not (is_camera_control_service_live and is_camera_web_server_live):
            raise PyWunderCamCameraNotFoundError("Camera Not Found at %s" % camera_ip)

        # If the SD Card is not plugged in AND formatted, the camera itself will raise an alarm.
        if sd_card_flag["SdcardplugFlag"]!=2:
            raise PyWunderCamSDCardUnusable("The SD card is not in a usable state (%s)." % sd_card_flag["SdcardplugFlag"])
        # At this point everything has gone well, so make the final assignements and perform a full read of the camera's
        # state.    
        self._camera_ip = camera_ip
        self._control_uri = "http://%s/fcgi_client.cgi" % self.camera_ip
        self._file_io_uri = "http://%s/DCIM/" % self.camera_ip
        self._current_camera_state = self._full_read()

            
    @property
    def camera_ip(self):
        """Returns the IP that the camera was initialised with."""
        return self._camera_ip
        
    @property
    def camera_state(self):
        """Prepares and returns the camera state object to the user.
        
        When the object enters the "prepare" state, any variable state changes are logged but **NOT** applied, until 
        the user resets the state back to the camera. At that point, any changes to the state are unrolled, applied 
        and their effect on the camera logged.
        """
        self._current_camera_state._prepare()
        return self._current_camera_state
        
    @camera_state.setter
    def camera_state(self, new_camera_state):
        """Applies a prepared state object to the camera.
        
        The object must have been obtained by the ``.camera_state`` property."""
        
        if len(new_camera_state.operations)>0:
            returned_state_data = {}
            for an_operation in new_camera_state.operations.items():
                returned_state_data.update(self.__req_data(an_operation[0], params=an_operation[1]))
            self._current_camera_state._camera_data_structure.update(returned_state_data)
        return self
        
    def _full_read(self):
        """Performs a full read of all known camera parameters.
        
        Note: 
        
        * This function performs more than one requests to the camera's hardware and is generally slow.
        """
        try:
            full_scan_3 = self.__req_data(3)
            full_scan_3.update(self.__req_data(37))
            full_scan_3.update(self.__req_data(4))
            full_scan_3.update(self.__req_data(5))
            full_scan_3.update(self.__req_data(6))
            full_scan_3.update(self.__req_data(7))
            full_scan_3.update(self.__req_data(8))
            full_scan_3.update(self.__req_data(9))
            full_scan_3.update(self.__req_data(10))
            full_scan_3.update(self.__req_data(11))
            full_scan_3.update(self.__req_data(12))
            full_scan_3.update(self.__req_data(13))
            full_scan_3.update(self.__req_data(14))
            full_scan_3.update(self.__req_data(15))
            full_scan_3.update(self.__req_data(16))
            full_scan_3.update(self.__req_data(17))
            cc = CamState(full_scan_3)
            return cc
        except Exception:
            raise Exception("Something Went wrong")

    def trigger(self):
        """
        Triggers the camera to take an action given its current configuration.
        """
        self.__req_data(24)
        # TODO: Update frames and video time
        
    def get_resources(self, img_file_re = IMG_FILE_RE, vid_file_re = VID_FILE_RE, img_group_by = IMG_GROUP_BY, vid_group_by = VID_GROUP_BY, img_order_by = IMG_ORDER_BY):
        """Returns the two resource sets that reside on the camera's file space. One for images and one for videos.
        
        :param img_file_re: Regular expression to unpack image filename metadata. By default set to the one the 
                            Wunder 360 S1 is using.
        :type img_file_re: compiled regexp
        :param vid_file_re: Similarly to ``img_file_re`` but for the video resource.
        :type vid_file_re: compiled regexp
        :param img_group_by: List of named attributes from ``img_file_re`` to use in distinguishing sequences from singles.
        :type img_group_by: list of str
        :param vid_group_by: Similarly to ``img_group_by`` but for video resources
        :type vid_group_by: list of str
        :param img_order_by: Named attribute from the image filename regular expression to be used for ordering sequences.
        :type img_order_by: str
        """
        
        return {"images":ResourceContainer("%sImage/" % self._file_io_uri, file_re = IMG_FILE_RE, group_by = IMG_GROUP_BY, order_by = IMG_ORDER_BY), 
                "videos":ResourceContainer("%sVideo/" % self._file_io_uri, file_re = VID_FILE_RE, group_by = VID_GROUP_BY)}


class PyWunderCamAuto(PyWunderCam):
    """
    Represents an "automatic" camera with a set of quick and easy defaults for quick shots.
    """        
    def _trigger_shot(self, single_or_continuous = 0, iso = None, white_balance_mode = None, exposure_compensation = None):
        # Take a snapshot of the camera's resources before the shot
        before_shot = self.get_resources()
        # Get the camera's state
        current_state = self.camera_state
        
        # Set it to the right shoot mode
        if single_or_continuous == 0:
            current_state.shoot_mode = 0
        else:
            current_state.shoot_mode = 3
        
        # Check if the camera needs to go manual
        if iso or white_balance_mode or exposure_compensation:
            current_state.setting_mode = 1
            if iso:
                current_state.iso = iso
            
            if exposure_compensation:
                current_state.exposure_compensation = exposure_compensation
                
            if white_balance_mode:
                current_state.white_balance_mode = white_balance_mode
        else:
            current_state.setting_mode = 0
            
        # Reset the state to the camera
        self.camera_state = current_state
        # Take the shot
        self.trigger()
        # Very brief pause to give time to the camera to write the file to the SD card
        time.sleep(10)
        # Take a snapshot of the camera's resources after the shot
        after_shot = self.get_resources()
        return after_shot["images"]-before_shot["images"]

    def single_shot(self, iso = None, white_balance_mode = None, exposure_compensation = None):
        """Triggers a single snapshot.
        
        If none of the image parameters are set, the camera enters automatic mode, otherwise, it enters manual mode, 
        sets up the shot and executes it.
        
        :param iso:
        :type iso:
        :param white_balance_mode:
        :type white_balance_mode:
        :param exposure_compensation:
        :type exposure_compensation:
        
        :returns: ResourceContainer with the resources that were created from this shot
        """
        return self._trigger_shot(0, iso, white_balance_mode, exposure_compensation)
        
        
    def continuous_shot(self, iso=None, white_balance_mode=None, exposure_compensation=None):
        """Triggers a burst mode shot."""
        return self._trigger_shot(1, iso, white_balance_mode, exposure_compensation)

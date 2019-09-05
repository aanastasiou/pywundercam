""" 
:authors: Athanasios Anastasiou
:date: August 2019

The main file that interfaces with a Wunder Cam S1 through Python.
"""

import os                           # Handles paths and filenames
import re                           # Regular expressions to decode the metadata in image and video filenames
import io                           # File handlers for streams in saving SingleStorage
import copy                         # Handles copying of the ResourceContainer data structure
import requests                     # Handles all file I/O activity with the camera over an HTTP interface
import PIL.Image                    # Serves images, directly capable to be modified by python code.
from collections import OrderedDict

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

class AbstractResource:
    def __init__(self):
        self._hash_value = None
        
    def __hash__(self):
        return self._hash_value
        
    def get(self):
        raise NotImplementedError("AbstractResource is not to be instantiated directly")
        
    def save_to(self):
        raise NotImplementedError("AbstractResource is not to be instantiated directly")
        
        
class SingleResource(AbstractResource):    
    """A single file resource held in the camera's disk space.
    
    This can be a single image or video stored on the camera's SD card.
    
    .. note::
        If you are simply using this package to interface with the camera you do not usually need to 
        instantiate this class directly.
    """
    
    def __init__(self, full_remote_filename, metadata = None):
        """Instantiates the SingleResource by its filename and optional metadata.
        
        :param full_remote_filename: Usually something of the form http://camera_ip/DCIM/Image/somethingsomething.jpg
        :type full_remote_filename: str(path)
        :param metadata: Metadata recovered from applying a filename regular expression.
        :type metadata: dict:"""
        super().__init__()
        self.full_remote_filename = full_remote_filename
        if metadata is not None:
            self.metadata = metadata
        # Hash values are used for fast difference operations, when it comes to filtering out which resources where 
        # created by a particular action. See function ResourceList.__sub__() for more details.
        self._hash_value = hash(self.full_remote_filename)
                    
    def get(self):
        """Retrieves a resource from the camera and serves it to the application in the right format.
        
        .. warning :: 
            As of writing this line, anything other than image/jpeg will raise an exception. To save the 
            resource locally, please see SingleResource.save_to()."""
        
        try:
            image_data = requests.get(self.full_remote_filename, timeout=5)
        except requests.exceptions.Timeout:
            raise Exception("Request Timedout")
            
        if not image_data.status_code==200:
            raise Exception("Transfer went wrong")
            
        if image_data.headers["content-type"] == "image/jpeg":    
            return PIL.Image.open(io.BytesIO(image_data.content))
        else:
            raise Exception("Cannot handle content type %s" % image_data.headers["content-type"])
            
    def save_to(self, filename=None):
        """Saves a resource to a local path as a binary file.
        
        :param filename: The local filename to save this file to.
        :type filename: str(path)"""
        
        local_filename = filename or os.path.split(self.full_remote_filename)[1]
        
        try:
            data = requests.get(self.full_remote_filename, timeout=5)
        except requests.exceptions.Timeout:
            raise Exception("Request Timedout")
        
        if not data.status_code == 200:
            raise Exception("Transfer went wrong")
            
        with open(local_filename, "wb") as fd:
            fd.write(data.content)


class SequenceResource(AbstractResource):
    """A sequence resource at the camera's memory space.
    
    Sequence resources are produced by the "Continuous" (or "Burst") mode and are basically a set of images that were
    collected after a single "trigger" action. PyWunderCam will serve these as one resource if a filename regular
    expression and list of group-by attributes are provided.
    
    .. note::        
        This is basically a tuple of SingleResource with a convenience get() to retrieve all resources of the sequence.    
    """
    
    def __init__(self, file_io_uri, file_list):
        """Initialises the SequenceResource.
        
        .. note ::
        
            If you are simply using this package to interface with the camera you do not usually need to 
            instantiate this class directly.
        
            SequenceReousrce is instantiated via a list of resources that describe multiple files.
            For the specifics of the format of file_list, please see the documentation of ResourceContainer.
            
        :param file_io_uri: The top level URI that the resource resides in at the camera's memory space.
        :type file_io_uri: str(URI)
        :param file_list: A list of (filename, metadata, index string) for each of the resources. Please see 
                          ResourceContainer for more.
        :type file_list: list
        """        
        super().__init__()
        self._seq = []
        # The hash value of a sequence is the hash value of its concatenated filenames.
        self._hash_value = hash("".join(map(lambda x:x[0], file_list)))
        for a_file in file_list:
            self._seq.append(SingleResource("%s%s" % (file_io_uri,a_file[0]), metadata = a_file[1]))
        # Notice here, resources are essentially immutable.
        self._seq = tuple(self._seq)
                
    def __getitem__(self, item):
        """ **Zero based** simple accessor for the individual SingleResource that make up a sequence.
        
        If an attribute to sort resources by was provided when ResourceContainer was instantiated, SingleResources
        will appear sorted. However, the camera uses **one based indexing** but thie accessor here is using plain 
        simple **zero based** indexing. 
        
        :param item: The index within the sequence to retrieve.
        :type item: int (0 < item < len(self._seq))
        """
        
        return self._seq[item]
        
    def __len__(self):
        return len(self._seq)
        
    def get(self):
        result = []
        for an_item in self._seq:
            result.append(an_item.get())
        return result
        
    def save_to(self, directory):
        for an_item in self._seq:
            an_item.save_to()
        
    
        
class ResourceContainer:
    """A ResourceContainer represents a list of files that are accessed via an HTTP interface.
    
    Usually, in devices like cameras, scanners, etc, the file name of an image, encodes a number of metadata, such 
    as time, date, sequence number and others. A file_rule is used to parse these metadata. Based on the 
    assumption that sequences of resources would share part of their filename characteristics, it is possible to group 
    resources that are created as a result of a **single action**. If a "frame" attribute is provided as well, it is 
    also possible to order these resources in the order they were taken.
    """    
    def __init__(self, file_io_uri, file_re = None, group_by = None, order_by = None):
        """Initialises ResourceContainer and performs an initial scan of the remote file space.
        
        :param file_io_uri: The top level remote URI to scan. Most of the times this is a directory, so **its trailing
                            slash must be retained**.
        :type file_io_uri: str(path)
        :param file_re: A regular expression with named groups to extract metadata from a resource's filename. If not
                        provided
        :type file_re: str(compiled regexp)
        :param group_by: list of attributes (from the named groups) to identify sequences of resources by.
        :type group_by: list of str
        :param order_by: A single attribute to order sequence elements by. e.g. Frame Number. 
        :type order_by: str
        """
        # A very simple rule to read individual anchor elements that denote individual file resources.
        self.anchor_re = re.compile("\<a href=\"(?P<href>.+?)\"\>.+?\</a\>")
        self.file_re = None
        self.group_by = None
        self.order_by = None
        self._resources = []
        
        self.file_re = file_re
        self.group_by = group_by
        self.order_by = order_by
        
        try:
            file_data_response = requests.get(file_io_uri, timeout=5)
        except requests.excepetions.Timeout:
            raise Exception("Something went wrong")

        # Remove the ../ entry in any case
        all_files = list(map(lambda x:[x,None, None],self.anchor_re.findall(file_data_response.text)))[1:]
        if file_re is not None:
            for a_file in enumerate(all_files):
                file_metadata = self.file_re.match(a_file[1][0])
                if file_metadata is not None:
                    all_files[a_file[0]][1] = file_metadata.groupdict()
                    if group_by is not None:
                        concatenated_attrs = ""
                        for an_item in group_by:
                            concatenated_attrs+=str(file_metadata.groupdict()[an_item])
                        all_files[a_file[0]][2] = concatenated_attrs
                        
        grouped_files = {}
        if group_by is not None:
            for a_file in all_files:
                try:
                    grouped_files[a_file[2]].append(a_file)
                except KeyError:
                    grouped_files[a_file[2]] = [a_file]
        else:
            for a_file in enumerate(all_files):
                grouped_files[a_file[0]] = [a_file[1]]
                
        for a_file in grouped_files.values():
            if len(a_file)>1:
                if order_by is not None:
                    self._resources.append(SequenceResource(file_io_uri,sorted(a_file, key=lambda x:int(x[1][order_by]))))
                else:
                    self._resources.append(SequenceResource(file_io_uri,a_file))
            else:
                self._resources.append(SingleResource("%s%s" % (file_io_uri,a_file[0][0]),metadata=a_file[0][1]))
        self._resources = tuple(self._resources)
                
    def __getitem__(self,item):
        return self._resources[item]
        
    def __len__(self):
        return len(self._resources)
        
    def __sub__(self, other):
        """Performs a quick subtraction between two ResourceContainer to discover which files have changed.
        
        The subtraction has to respect the "order" of operands. The usual sequence of actions is:
        
        1. Setup camera's state (C)
        2. Get a ResourceContainer (U)
        3. Trigger camera (updates state)
        4. Get a ResourceContainer (V)
        
        To discover which resources were created as a result of the trigger, you can simply do:
        >> changed_resources = V-U
        Doing the opposite would indicate no change.
        
        :param other: Another ResourceContainer to evaluate the difference on
        :type other: ResourceContainer
        """
        
        # TODO: HIGH, Raise exception when the result is null
        
        asset_idx = {}
        diff_resources = []
        for another_resource in other._resources:
            asset_idx[hash(another_resource)] = another_resource
                
        for a_resource in self._resources:
            try:
                asset_idx[hash(a_resource)]
            except KeyError:
                diff_resources.append(a_resource)
        new_resource_container = copy.copy(self)
        new_resource_container._resources = tuple(diff_resources)
        return new_resource_container
                
                

class CamState:
    """Represents all data that capture the camera's state.
    
    The class exposes properties with Pythonic names that are fully documented and ensures that the values 
    that represent the camera's state are valid throughout their round trip to the hardware and back. This class
    also handles marshalling between the variable names used by the hardware and their Python counterparts.
    """
    
    # These are all the camera attributes that this package can interpret. These are the actual keys in various JSON
    # data structures that are exchanged between the client and the server.
    _camera_data_attributes = ["CurPvSMStatus", "CurHpSMStatus", "CurWpSMStatus", "BatteryGird", "ShootMode", 
        "SettingMode", "ChargeFlag", "HDMIonnectFlag", "SdcardplugFlag", "ErrorCode", "bSupport30p", "PhotoDelay",
        "PhotoNumber", "PhotoTime", "VideoFrameRate", "VideoFrameInterval", "LoopVideoTime", "SerialNumber", 
        "ProductModel", "FirmwareSoftwareVersion", "ISO", "WhiteBalanceMode", "ExposureCompensation", "SceneMode",
        "capacity", "remainTime", "remainNum", "Mute", "AutoShutDown", "WifiPass", "WifiSSID"]
            
    def __init__(self, camera_data = None):
        """Initialise a state object, optionally with default values.
        
        :param camera_data: A dictionary of default values to set various fields at.
        :type camera_data: dict
        """
        self._camera_data_structure={}
        self._ops_to_apply = OrderedDict()

        self._camera_data_structure = dict(zip([key for key in self._camera_data_attributes], 
                                                [None]*len(self._camera_data_attributes)))

        if camera_data is not None:
            self._camera_data_structure.update(camera_data)
    
    def _prepare(self):
        """Prepares the state data structure to start queing state request changes."""
        self._ops_to_apply = OrderedDict()
        
    @property
    def operations(self):
        """Returns a list of operations to be sent to the camera hardware so that its state reflects the requested state.
        
            The list is of the format ``(command, params)``, where ``command`` is usually an integer and `params` a 
            dictionary of command specific parameters. ``command`` and ``params`` are hardware specific.
        """
        return self._ops_to_apply
        
    @property
    def cur_pv_sm_status(self):
        return self._camera_data_structure["CurPvSMStatus"]
        
    @property
    def cur_hp_sm_status(self):
        return self._camera_data_structure["CurHpSMStatus"]
        
    @property
    def cur_wp_sm_status(self):
        return self._camera_data_structure["CurWpSMStatus"]
        
    @property
    def battery_grid(self):
        """Battery charge indicator in an arbitrary scale. Integer [0..6]. (Read only).
        
        Note:
        
        * The battery charge indicator on the camera is a 3 bar icon. This indicator goes all the way up to 6.
        * The property name on the camera has been mispolled (BatterGird).
        """
        return self._camera_data_structure["BatteryGird"]
        
    @property
    def shoot_mode(self):
        """Determines which shoot mode to trigger. Integer [0..6]. (Read / Write).
        
        Note:
        
        * The shoot modes are as follows:
            * 0: Photo
            * 1: Video (3K)
            * 2: Timer
            * 3: Continuous (Burst)
            * 4: Time-Lapse
            * 5: Video (60 FPS)
            * 6: Loop
            
        * To stop video recording, simply re-trigger the camera.
        """
        return self._camera_data_structure["ShootMode"]
    
    @shoot_mode.setter
    def shoot_mode(self, new_shoot_mode):
        if new_shoot_mode in range(0, 7):
            self._ops_to_apply[21] = {"ModeType":new_shoot_mode}
        else:
            raise ValueError("Can't set that shoot mode")
        
    @property
    def setting_mode(self):
        """Whether the camera is in manual or automatic mode. Bool [0..1]. (Read / Write).
        
        Note:
        
        * The photographic settings (iso, white_balance, exposure_compensation) require the camera to be in manual mode.
        """
        return self._camera_data_structure["SettingMode"]
        
    @setting_mode.setter
    def setting_mode(self, new_setting_mode):
        if new_setting_mode in [0, 1]:
            self._ops_to_apply[29] = {"SettingMode":new_setting_mode}
        else:
            raise ValueError("Can't set that setting mode")
        
    @property
    def charge_flag(self):
        """Whether the camera's battery is charging. Bool [0..1]. (Read only)."""
        return self._camera_data_structure["ChargeFlag"]
        
    @property
    def hdmi_connect_flag(self):
        """Whether the HDMI connector is plugged in. Bool [0..1]. (Read only).
        
        Note:
        
        * There is no HDMI connector exposed on the S1.
        """
        return self._camera_data_structure["HDMIConnectFlag"]
        
    @property
    def sd_card_plug_flag(self):
        """Whether an SD card is plugged in the camera and can be used. Integer [0..2]. (Read only).
        
        Note:
        
        * Values are as follows:
            * 0: No SD card plugged in
            * 1: SD card plugged in (not necessarily readable)
            * 2: SD card plugged in and readable.
        """
        return self._camera_data_structure["SdcardplugFlag"]
        
    @property
    def error_code(self):
        return self._camera_data_structure["ErrorCode"]
        
    @property
    def b_support_30p(self):
        return self._camera_data_structure["bSupport30p"]
        
    @property
    def photo_delay(self):
        return self._camera_data_structure["PhotoDelay"]
        
    @property
    def photo_number(self):
        return self._camera_data_structure["PhotoNumber"]
        
    @property
    def photo_time(self):
        return self._camera_data_structure["PhotoTime"]
        
    @property
    def video_frame_rate(self):
        return self._camera_data_structure["VideoFrameRate"]
        
    @property
    def video_frame_interval(self):
        return self._camera_data_structure["VideoFrameInterval"]
        
    @property
    def loop_video_time(self):
        """Maximum video time in Loop mode in minutes. Integer. (Read only)."""
        return self._camera_data_structure["LoopVideoTime"]

    @property
    def serial_number(self):
        """Product serial number as returned by the camera. String. (Read only)."""
        return self._camera_data_structure["SerialNumber"]
        
    @property
    def product_model(self):
        """Product model as returned by the camera. String. (Read only).
        
        Note:
        
        * This will always be "S1" in this camera.
        """
        return self._camera_data_structure["ProductModel"]
        
    @property
    def firmware_software_version(self):
        """Firmware and software version as returned by the camera. String. (Read only)."""
        return self._camera_data_structure["FirmwareSoftwareVersion"]

    @property
    def iso(self):
        """Equivalent ISO in preset values. Integer [0..4]. (Read / Write).
        
        Note:
        
        * For this setting to be effective the camera must be in Manual Mode (setting_mode=1).
        * The preset values are as follows:
            * 0: AUTO
            * 1: 100
            * 2: 200
            * 3: 400
            * 4: 800
        """
        return self._camera_data_structure["ISO"]
        
    @iso.setter
    def iso(self, new_iso_value):
        if not new_iso_value in range(0,5):
            raise ValueError("Invalid value {new_iso_value} for parameter iso")
        self._ops_to_apply[25] = {"ISO":new_iso_value}
        return self

    @property    
    def white_balance_mode(self):
        """White balance in color temperature presets. Integer [0..4]. (Read / Write).
        
        Note:
        
        * For this setting to be effective the camera must be in Manual Mode (setting_mode=1).
        * The temperature presets are as follows:
            * 0: AUTO
            * 1: 2856K
            * 2: 4000K
            * 3: 5500K
            * 4: 6500K
        """
        return self._camera_data_structure["WhiteBalanceMode"]
        
    @white_balance_mode.setter
    def white_balance_mode(self, new_white_balance_value):
        if not new_white_balance_value in range(0, 5):
            raise ValueError("Invalid value {new_white_balance_value} for parameter white_balance_mode")
        self._ops_to_apply[26] = {"WhiteBalanceMode":new_white_balance_value}
        return self
        
    @property
    def exposure_compensation(self):
        """Exposure compensation in stops. Integer [0..13]. (Read / Write).
        
        Note:
        
        * For this setting to be effective the camera must be in Manual Mode (setting_mode=1).
        * Exposure compensation spans a scale of 13 values (1..13) with 0 being the AUTO setting.
        """
        return self._camera_data_structure["ExposureCompensation"]

    @exposure_compensation.setter
    def exposure_compensation(self, new_exposure_compensation_value):
        if not new_exposure_compensation_value in range(0,14):
            raise ValueError("Invalid value {new_exposure_compensation_value} for parameter exposure_compensation")
        self._ops_to_apply[27] = {"ExposureCompensation":new_exposure_compensation_value}
        return self
        
    @property    
    def scene_mode(self):
        return self._camera_data_structure["SceneMode"]

    @property
    def capacity(self):
        return self._camera_data_structure["capacity"]
                
    @property
    def mute(self):
        """Whether to sound the camera's buzzer. Bool [0..1]. (Read only).
        
        Note:
        
        * This does not seem to be implemented on the S1. Even if you manage to switch this flag to 0
          the buzzer still sounds."""
        return self._camera_data_structure["Mute"]
        
    @property
    def auto_shutdown(self):
        """Minutes to auto-shutdown. Positive Integer. (Read only)."""
        return self._camera_data_structure["AutoShutDown"]
    
    @property
    def wifi_pass(self):
        """The camera's network password. (Read only).
        
        Note:
        
        * The default password is 12345678
        """
        return self._camera_data_structure["WifiPass"]
    
    @property
    def wifi_ssid(self):
        """The SSID of the WiFi interface that the camera advertises. (Read only).
        
        Note:
        
        * By default, the SSID is Pano_[Camera-Serial-Number]."""
        return self._camera_data_structure["WifiSSID"]
        
    @property
    def remain_time(self):
        """Remaining time for video recording, given the capacity of the SD card, in minutes. (Read only)."""
        return self._camera_data_structure["remainTime"]
        
    @property
    def remain_num(self):
        """Remaining number of pictures, given the capacity of the SD card. (Read only)."""
        return self._camera_data_structure["remainNum"]


        
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
        except requests.exceptions.Timeout:
            raise Exception("Request timed out")
        if camera_data.status_code!=200:
            raise Exception("Request failed with code:")
        return camera_data.json()

    def __init__(self, camera_ip="192.168.100.1"):
        """Initialises the main WunderCam client through the camera's Internet Protocol (IP) address.
        
        :param camera_ip: The IP that the camera is on. For WunderCam this is ``192.168.100.1`` by default.
        :type camera_ip: str (IP)
        """
         
        self.camera_ip = None
        self.control_uri = None
        self.file_io_uri = None
        self._current_camera_state = None

        self.control_uri = "http://%s/fcgi_client.cgi" % camera_ip
        try:
            # Check if the service endpoints have come online on the camera.
            is_camera_control_service_live = len(self.__req_data(2))>0
            is_camera_web_server_live = requests.get("http://%s/DCIM/img/" % camera_ip, timeout=5).status_code == 404
            if not (is_camera_control_service_live and is_camera_web_server_live):
                raise Exception("Camera Not Found at {camera_ip}")
            self.camera_ip = camera_ip
            self.control_uri = "http://%s/fcgi_client.cgi" % self.camera_ip
            self.file_io_uri = "http://%s/DCIM/" % self.camera_ip
            self._current_camera_state = self.force_read()
        except Exception:
            raise Exception("Camera Not Found at {camera_ip}")
            
    @property
    def camera_state(self):
        """Prepares and returns the camera state object to the user.
        
        When the object enters the "prepare" state, any variable state changes are logged but **NOT** applied, until 
        the user resets the state of the camera back. At that point, any changes to the state are unrolled, applied 
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
        
    def force_read(self):
        """Performs a full read of all known camera parameters.
        
        Note: The forceread, force_write functions perform more than one requests to the camera's hardware and are slow.
              For simple status changes (e.g. change the ISO and WhiteBalance between two shots), use the sync function.
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
                            Wunder S1 is using.
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
        
        return {"images":ResourceContainer("%sImage/" % self.file_io_uri, file_re = IMG_FILE_RE, group_by = IMG_GROUP_BY, order_by = IMG_ORDER_BY), 
                "videos":ResourceContainer("%sVideo/" % self.file_io_uri, file_re = VID_FILE_RE, group_by = VID_GROUP_BY)}

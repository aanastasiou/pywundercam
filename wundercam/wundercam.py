""" Athanasios Anastasiou, August 2019

The main file that interfaces with a Wunder Cam S1 through Python.
"""

import os           # Handles paths and filenames
import re           # Regular expressions to decode the metadata in image and video filenames
import io           # File handlers for streams in saving SingleStorage
import copy         # Handles copying of the ResourceContainer data structure
import requests     # Handles all file I/O activity with the camera over an HTTP interface
import PIL.Image    # Serves images, directly capable to be modified by python code.

# Convenience presets for the naming rules used by the S1 hardware to name Image and Video files.
# The named attributes of these regular expressions are stored along with a file as the file's metadata.
image_file_re = re.compile("Img_(?P<year>[0-9][0-9][0-9][0-9])(?P<month>[0-9][0-9])(?P<day>[0-9][0-9])_(?P<hour>[0-9][0-9])(?P<minute>[0-9][0-9])(?P<second>[0-9][0-9])_(?P<frame>[0-9][0-9][0-9])\.jpg")
video_file_re = re.compile("Vid_(?P<year>[0-9][0-9][0-9][0-9])(?P<month>[0-9][0-9])(?P<day>[0-9][0-9])_(?P<hour>[0-9][0-9])(?P<minute>[0-9][0-9])(?P<second>[0-9][0-9])_(?P<frame>[0-9][0-9][0-9])\.mp4")
# Named attributes (from the above sequences) to distinguish between single snapshots and "Continuous" snapshots. 
# In the case of "Continuous" takes, WunderCam can pack them together in a sequence automatically.
img_group_by = ["year", "month", "day", "hour", "minute", "second"]
vid_group_by = img_group_by
# Attribute to order image sequences by.
# TODO: LOW, It should be possible for order-by to operate over multiple fields, to produce more complex groupings (e.g.
#       all images taken within an hour.
img_order_by = "frame"
vid_order_by = img_order_by

class SingleResource:    
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
        self.full_remote_filename = full_remote_filename
        if metadata is not None:
            self.metadata = metadata
        # Hash values are used for fast difference operations, when it comes to filtering out which resources where 
        # created by a particular action. See function ResourceList.__sub__() for more details.
        self._hash_value = hash(self.full_remote_filename)
            
    def __hash__(self):
        """A SingleResource's hash value is the string hash of its full filename."""
        return self._hash_value
        
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
            
    def save_to(self, filename):
        """Saves a resource to a local path as a binary file.
        
        :param filename: The local filename to save this file to.
        :type filename: str(path)"""
        
        try:
            data = requests.get(self.full_remote_filename, timeout=5)
        except requests.exceptions.Timeout:
            raise Exception("Request Timedout")
        
        if not data.status_code == 200:
            raise Exception("Transfer went wrong")
            
        with open(filename, "wb") as fd:
            fd.write(data.content)


class SequenceResource:
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

        self._seq = []
        # The hash value of a sequence is the hash value of its concatenated filenames.
        self._hash_value = hash("".join(map(lambda x:x[0], file_list)))
        for a_file in file_list:
            self._seq.append(SingleResource("%s%s" % (file_io_uri,a_file[0]), metadata = a_file[1]))
        # Notice here, resources are essentially immutable.
        self._seq = tuple(self._seq)
        
    def __hash__(self):
        return self._hash_value
        
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
        self._resources = []
        
        try:
            file_data_response = requests.get(file_io_uri, timeout=5)
        except requests.excepetions.Timeout:
            raise Exception("Something went wrong")
            
        self.file_re = file_re
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
        
        asset_idx = {}
        diff_resources = []
        for another_resource in other._resources:
            asset_idx[hash(another_resource)] = another_resource
                
        for a_resource in self._resources:
            try:
                asset_idx[hash(a_resource)]
            except KeyError:
                diff_assets.append(a_resource)
        new_resource_container = copy.copy(self)
        new_resource_container._resources = tuple(diff_resources)
        return new_resource_container
                
                

class CamConf:
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
        self._ops_to_apply = []

        self._camera_data_structure = dict(zip([key for key in self._camera_data_attributes], 
                                                [None]*len(self._camera_data_attributes)))

        if camera_data is not None:
            self._camera_data_structure.update(camera_data)
    
    def _prepare(self):
        """Prepares the state data structure to start queing state request changes."""
        self._ops_to_apply = []
        
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
        return self._camera_data_structure["BatteryGird"]
        
    @property
    def shoot_mode(self):
        return self._camera_data_structure["ShootMode"]
    
    @shoot_mode.setter
    def shoot_mode(self, new_shoot_mode):
        if new_shoot_mode in [0,1,2,3,4,5,6,7]:
            self._camera_data_structure["ShootMode"] = new_shoot_mode
        else:
            raise Exception("Can't set that shoot mode")
        return self
        
    @property
    def setting_mode(self):
        return self._camera_data_structure["SettingMode"]
        
    @property
    def charge_flag(self):
        return self._camera_data_structure["ChargeFlag"]
        
    @property
    def hdmi_connect_flag(self):
        return self._camera_data_structure["HDMIConnectFlag"]
        
    @property
    def sd_card_plug_flag(self):
        return self._camera_data_structure["SDcardplugFlag"]
        
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
        return self._camera_data_structure["LoopVideoTime"]

    @property
    def serial_number(self):
        return self._camera_data_structure["SerialNumber"]
        
    @property
    def product_model(self):
        return self._camera_data_structure["ProductModel"]
        
    @property
    def firmware_software_version(self):
        return self._camera_data_structure["FirmwareSoftwareVersion"]

    @property
    def iso(self):
        return self._camera_data_structure["ISO"]
        
    @iso.setter
    def iso(self, new_iso_value):
        """Sets ISO to one of []"""
        if not new_iso_value in [0,1,2,3,4,5,6,7]:
            raise ValueError("Invalid value {new_iso_value} for parameter iso")
        self._ops_to_apply.append([25,{"ISO":new_iso_value}])
        # self._camera_data_structure["ISO"] = new_iso_value
        return self

    @property    
    def white_balance_mode(self):
        return self._camera_data_structure["WhiteBalanceMode"]
        
    @white_balance_mode.setter
    def white_balance_mode(self, new_white_balance_value):
        """Sets white balance to one of []"""
        if not new_white_balance_value in [0,1,2,3,4,5,6,7]:
            raise ValueError("Invalid value {new_white_balance_value} for parameter white_balance_mode")
        # self._camera_data_structure["WhiteBalanceMode"] = new_white_balance_value
        self._ops_to_apply.append([26, {"WhiteBalanceMode":new_white_balance_value}])
        return self
        
    @property
    def exposure_compensation(self):
        return self._camera_data_structure["ExposureCompensation"]

    @exposure_compensation.setter
    def exposure_compensation(self, new_exposure_compensation_value):
        """Sets ExposureCompensation to one of []"""
        if not new_exposure_compensation_value in [0,1,2,3,4,5,6,7,8]:
            raise ValueError("Invalid value {new_exposure_compensation_value} for parameter exposure_compensation")
        # self._camera_data_structure["ExposureCompensation"] = new_exposure_compensation_value
        self._ops_to_apply.append([27,{"ExposureCompensation":new_exposure_compensation_value}])
        return self
        
    @property    
    def scene_mode(self):
        return self._camera_data_structure["SceneMode"]

    @property
    def capacity(self):
        return self._camera_data_structure["capacity"]
        
    @property    
    def video_remain_time(self):
        return self._camera_data_structure["RemainTime"]
    
    @property
    def photo_remain_frames(self):
        return self._camera_data_structure["RemainNum"]
        
    @property
    def mute(self):
        return self._camera_data_structure["Mute"]
        
    @property
    def auto_shutdown(self):
        return self._camera_data_structure["AutoShutDown"]
    
    @property
    def wifi_pass(self):
        return self._camera_data_structure["WifiPass"]
    
    @property
    def wifi_ssid(self):
        return self._camera_data_structure["WifiSSID"]
        
    @property
    def remain_time(self):
        return self._camera_data_structure["remainTime"]
        
    @property
    def remain_num(self):
        return self._camera_data_structure["remainNum"]


        
class WunderCam:
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

    def __init__(self, camera_ip):
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
            for an_operation in new_camera_state.operations:
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
            cc = CamConf(full_scan_3)
            return cc
        except Exception:
            raise Exception("Something Went wrong")

    def trigger(self):
        """
        Takes a single snapshot using the current configuration.
        """
        self.__req_data(24)
        # TODO: Update frames and video time
        
    def get_resources(self, img_file_re = image_file_re, vid_file_re = video_file_re, img_group_by = img_group_by, vid_group_by = vid_group_by):
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
        """
        
        return {"images":ResourceContainer("%sImage/" % self.file_io_uri, file_re = image_file_re, group_by = img_group_by), 
                "videos":ResourceContainer("%sVideo/" % self.file_io_uri, file_re = video_file_re, group_by = vid_group_by)}

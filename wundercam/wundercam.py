""" Athanasios Anastasiou, August 2019

The main file that interfaces with a Wunder Cam S1 through Python.
"""

import os
import re
import io
import copy
import requests
import PIL.Image

# Convenience presets for the naming rules used by the S1 hardware to name Image and Video files.
# The named attributes of these regular expressions are stored along with a file as the file's metadata.
image_file_re = re.compile("Img_(?P<year>[0-9][0-9][0-9][0-9])(?P<month>[0-9][0-9])(?P<day>[0-9][0-9])_(?P<hour>[0-9][0-9])(?P<minute>[0-9][0-9])(?P<second>[0-9][0-9])_(?P<frame>[0-9][0-9][0-9])\.jpg")
video_file_re = re.compile("Vid_(?P<year>[0-9][0-9][0-9][0-9])(?P<month>[0-9][0-9])(?P<day>[0-9][0-9])_(?P<hour>[0-9][0-9])(?P<minute>[0-9][0-9])(?P<second>[0-9][0-9])_(?P<frame>[0-9][0-9][0-9])\.mp4")
# Named attributes (from the above sequences) to distinguish between single snapshots and "Continuous" snapshots. 
# In the case of "Continuous" takes, WunderCam can pack them together in a sequence automatically.
img_group_by = ["year", "month", "day", "hour", "minute", "second"]
vid_group_by = img_group_by

class SingleAsset:    
    """A single asset held by the camera.
    
    For example, this can be a single image or video stored on the camera's SD card.
    Note: Plain users of this package do not usually need to instantiate this object directly.
    """
    
    def __init__(self, full_remote_filename, metadata = None):
        self.full_remote_filename = full_remote_filename
        if metadata is not None:
            self.metadata = metadata
        self._hash_value = hash(self.full_remote_filename)
            
    def __hash__(self):
        return self._hash_value
        
    def get(self):
        """Retrieves the asset from the camera and serves it to the application in the right format.
        
        Note: As of this writing, anything other than image/jpeg will raise an exception. To save the 
        resource locally, please use save_to."""
        
        try:
            image_data = requests.get(self.full_remote_filename, timeout=5)
        except requests.exceptions.Timeout:
            raise Exception("Request Timedout")
            
        if not image_data.status_code==200:
            raise Exception("Transfer went wrong")
        print(image_data.headers)
        if image_data.headers["content-type"] == "image/jpeg":    
            return PIL.Image.open(io.BytesIO(image_data.content))
        else:
            raise Exception("Cannot handle this content type")
            
    def save_to(self, filename):
        """Saves a resource to a local path.
        
        :param filename:
        :type filename: str(path)"""
        try:
            data = requests.get(self.full_remote_filename, timeout=5)
        except requests.exceptions.Timeout:
            raise Exception("Request Timedout")
        
        if not data.status_code == 200:
            raise Exception("Transfer went wrong")
            
        with open(filename, "wb") as fd:
            fd.write(data.content)

class SequenceAsset:
    
    def __init__(self, file_io_uri, file_list):
        self._seq = []
        self._hash_value = hash("".join(map(lambda x:x[0], file_list)))
        for a_file in file_list:
            self._seq.append(SingleAsset("%s%s" % (file_io_uri,a_file[0]), metadata = a_file[1]))
        self._seq = tuple(self._seq)
        
    def __hash__(self):
        return self._hash_value
        
    def __getitem__(self, item):
        return self._seq[item]
        
    def __len__(self):
        return len(self._seq)
        
    def get(self):
        result = []
        for an_item in self._seq:
            result.append(an_item.get())
        return result
        
    
        
class AssetList:
    """An AssetList represents a list of files that are accessed via an HTTP interface
    
    Usually, in devices like cameras, scanners, etc, the file name of an image, encodes a number of metadata, such 
        as time, date, sequence number and others. The file_rule is used to parse these metadata
    """    
    def __init__(self, file_io_uri, file_re = None, group_by = None):
        """Initialises AssetList and performs an initial scan over remote_path for single or mulitple assets."""
        
        # anchor_re = re.compile("\<a href=\"(?P<href>.+?)\"\>(?P<link_text>.+?)\</a\>") 
        self.anchor_re = re.compile("\<a href=\"(?P<href>.+?)\"\>.+?\</a\>")
        self.file_re = None
        self.group_by = None
        self._assets = []
        
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
            # pdb.set_trace()
            if len(a_file)>1:
                self._assets.append(SequenceAsset(file_io_uri,a_file))
            else:
                self._assets.append(SingleAsset("%s%s" % (file_io_uri,a_file[0][0]),metadata=a_file[0][1]))
        self._assets = tuple(self._assets)
                
    def __getitem__(self,item):
        return self._assets[item]
        
    def __len__(self):
        return len(self._assets)
        
    def __sub__(self, other):
        asset_idx = {}
        diff_assets = []
        for another_asset in other._assets:
            asset_idx[hash(another_asset)] = another_asset
                
        for an_asset in self._assets:
            try:
                asset_idx[hash(an_asset)]
            except KeyError:
                diff_assets.append(an_asset)
        new_asset_list = copy.copy(self)
        new_asset_list._assets = tuple(diff_assets)
        return new_asset_list
                
                

class CamConf:
    """Represents all data that capture the camera's state"""
    _camera_data_attributes = ["CurPvSMStatus", "CurHpSMStatus", "CurWpSMStatus", "BatteryGird", "ShootMode", 
        "SettingMode", "ChargeFlag", "HDMIonnectFlag", "SdcardplugFlag", "ErrorCode", "bSupport30p", "PhotoDelay",
        "PhotoNumber", "PhotoTime", "VideoFrameRate", "VideoFrameInterval", "LoopVideoTime", "SerialNumber", 
        "ProductModel", "FirmwareSoftwareVersion", "ISO", "WhiteBalanceMode", "ExposureCompensation", "SceneMode",
        "capacity", "remainTime", "remainNum", "Mute", "AutoShutDown", "WifiPass", "WifiSSID"]
            
    def __init__(self, camera_data = None):
        self._camera_data_structure={}
        self._ops_to_apply = []

        self._camera_data_structure = dict(zip([key for key in self._camera_data_attributes], 
                                                [None]*len(self._camera_data_attributes)))

        if camera_data is not None:
            self._camera_data_structure.update(camera_data)
    
    def _prepare(self):
        self._ops_to_apply = []
        
    @property
    def operations(self):
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
    def __req_data(self, command, params = None):
        """Makes a request to the camera taking care of timeouts, status codes and return result data type."""        
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
        self._current_camera_state._prepare()
        return self._current_camera_state
        
    @camera_state.setter
    def camera_state(self, new_camera_state):
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
        
    def get_assets(self, img_file_re = image_file_re, vid_file_re = video_file_re, img_group_by = img_group_by, vid_group_by = vid_group_by):
        return {"images":AssetList("%sImage/" % self.file_io_uri, file_re = image_file_re, group_by = img_group_by), 
                "videos":AssetList("%sVideo/" % self.file_io_uri, file_re = video_file_re, group_by = vid_group_by)}

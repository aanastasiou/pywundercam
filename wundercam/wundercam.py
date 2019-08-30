import requests
import time
import pdb


class CamConf:
    """Represents all data that capture the camera's state"""
    _camera_data_structure={}
    _camera_data_attributes = ["CurPvSMStatus", "CurHpSMStatus", "CurWpSMStatus", "BatteryGird", "ShootMode", 
        "SettingMode", "ChargeFlag", "HDMIonnectFlag", "SdcardplugFlag", "ErrorCode", "bSupport30p", "PhotoDelay",
        "PhotoNumber", "PhotoTime", "VideoFrameRate", "VideoFrameInterval", "LoopVideoTime", "SerialNumber", 
        "ProductModel", "FirmwareSoftwareVersion", "ISO", "WhiteBalanceMode", "ExposureCompensation", "SceneMode",
        "capacity", "remainTime", "remainNum", "Mute", "AutoShutDown", "WifiPass", "WifiSSID"]
    
    def __init__(self, camera_data = None):
        current_time = time.time()
        self._camera_data_structure = dict(zip([key for key in self._camera_data_attributes], 
            [value for value in [[None,current_time]]*len(self._camera_data_attributes)]))

        if camera_data is not None:
            self._camera_data_structure.update(dict(zip([key for key in camera_data.keys()],
                [[value, current_time] for value in camera_data.values()])))
            
    @property
    def cur_pv_sm_status(self):
        return self._camera_data_structure["CurPvSMStatus"][0]
        
    @property
    def cur_hp_sm_status(self):
        return self._camera_data_structure["CurHpSMStatus"][0]
        
    @property
    def cur_wp_sm_status(self):
        return self._camera_data_structure["CurWpSMStatus"][0]
        
    @property
    def battery_grid(self):
        return self._camera_data_structure["BatteryGird"][0]
        
    @property
    def shoot_mode(self):
        return self._camera_data_structure["ShootMode"][0]
    
    @shoot_mode.setter
    def shoot_mode(self, new_shoot_mode):
        if new_shoot_mode in []:
            self._camera_data_structure["ShootMode"] = (new_shoot_mode, time.time())
        else:
            raise Exception("Can't set that shoot mode")
        return self
        
    @property
    def setting_mode(self):
        return self._camera_data_structure["SettingMode"][0]
        
    @property
    def charge_flag(self):
        return self._camera_data_structure["ChargeFlag"][0]
        
    @property
    def hdmi_connect_flag(self):
        return self._camera_data_structure["HDMIConnectFlag"][0]
        
    @property
    def sd_card_plug_flag(self):
        return self._camera_data_structure["SDcardplugFlag"][0]
        
    @property
    def error_code(self):
        return self._camera_data_structure["ErrorCode"][0]
        
    @property
    def b_support_30p(self):
        return self._camera_data_structure["bSupport30p"][0]
        
    @property
    def photo_delay(self):
        return self._camera_data_structure["PhotoDelay"][0]
        
    @property
    def photo_number(self):
        return self._camera_data_structure["PhotoNumber"][0]
        
    @property
    def photo_time(self):
        return self._camera_data_structure["PhotoTime"][0]
        
    @property
    def video_frame_rate(self):
        return self._camera_data_structure["VideoFrameRate"][0]
        
    @property
    def video_frame_interval(self):
        return self._camera_data_structure["VideoFrameInterval"][0]
        
    @property
    def loop_video_time(self):
        return self._camera_data_structure["LoopVideoTime"][0]

    @property
    def serial_number(self):
        return self._camera_data_structure["SerialNumber"][0]
        
    @property
    def product_model(self):
        return self._camera_data_structure["ProductModel"][0]
        
    @property
    def firmware_software_version(self):
        return self._camera_data_structure["FirmwareSoftwareVersion"][0]

    @property
    def iso(self):
        return self._camera_data_structure["ISO"][0]
    @iso.setter
    def iso(self, new_iso_value):
        """Sets ISO to one of []"""
        if not new_iso_value in []:
            raise ValueError("Invalid value {new_iso_value} for parameter iso")
        self.shoot_mode = 0
        self._camera_data_structure["ISO"] = (new_iso_value, time.time())
        return self

    @property    
    def white_balance_mode(self):
        return self._camera_data_structure["WhiteBalanceMode"]
        
    @white_balance_mode.setter
    def white_balance_mode(self, new_white_balance_value):
        """Sets white balance to one of []"""
        if not new_is_value in []:
            raise ValueError("Invalid value {new_white_balance_value} for parameter white_balance_mode")
        self.shoot_mode = 0
        self._camera_data_structure["WhiteBalanceMode"] = (new_white_balance_value, time.time())
        return self
        
    @property
    def exposure_compensation(self):
        return self._camera_data_structure["ExposureCompensation"]

    @exposure_compensation.setter
    def exposure_compensation(self, new_exposure_compensation_value):
        """Sets ExposureCompensation to one of []"""
        if not new_exposure_compensation_value in []:
            raise ValueError("Invalid value {new_exposure_compensation_value} for parameter exposure_compensation")
        self.shoot_mode = 0
        self._camera_data_structure["ExposureCompensation"] = (new_exposure_compensation_value, time.time())
        return self
        
    @property    
    def scene_mode(self):
        return self._camera_data_structure["SceneMode"][0]

    @property
    def capacity(self):
        return self._camera_data_structure["capacity"][0]
        
    @property    
    def video_remain_time(self):
        return self._camera_data_structure["RemainTime"][0]
    
    @property
    def photo_remain_frames(self):
        return self._camera_data_structure["RemainNum"][0]
        
    @property
    def mute(self):
        return self._camera_data_structure["Mute"][0]
        
    @property
    def auto_shutdown(self):
        return self._camera_data_structure["AutoShutDown"][0]
    
    @property
    def wifi_pass(self):
        return self._camera_data_structure["WifiPass"][0]
    
    @property
    def wifi_ssid(self):
        return self._camera_data_structure["WifiSSID"][0]
        
    @property
    def remain_time(self):
        return self._camera_data_structure["remainTime"][0]
        
    @property
    def remain_num(self):
        return self._camera_data_structure["remainNum"][0]


        
class WunderCam:
    camera_ip = None
    control_uri = None
    file_io_uri = None
    
    def __req_data(self, command, params = None):
        """Makes a request to the camera taking care of timeouts, status codes and return result data type."""
        try:
            camera_data = requests.get(self.control_uri, {"cmd":command}, timeout=5)
        except requests.exceptions.Timeout:
            raise Exception("Request timed out")
        if camera_data.status_code!=200:
            raise Exception("Request failed with code:")
        return camera_data.json()

    def __init__(self, camera_ip):
        self.control_uri = "http://%s/fcgi_client.cgi" % camera_ip
        try:
            # Check if the service endpoints have come online on the camera.
            is_camera_control_service_live = len(self.__req_data(2))>0
            is_camera_web_server_live = requests.get("http://%s/DCIM/img/" % camera_ip, timeout=5).status_code == 404
            pdb.set_trace() 
            if not (is_camera_control_service_live and is_camera_web_server_live):
                raise Exception("Camera Not Found at {camera_ip}")
            self.camera_ip = camera_ip
            self.control_uri = "http://%s/fcgi_client.cgi" % self.camera_ip
            self.file_io_uri = "http://%s/DCIM" % self.camera_ip
        except Exception:
            raise Exception("Camera Not Found at {camera_ip}")
    
    def sync(self, given_camera_conf):
        """
        Performs a full sync cycle to the camera.
        """
        pass
    
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
        
    def force_write(self):
        pass
                
    def trigger(self):
        """
        Takes a single snapshot using the current configuration.
        """
        pass

"""
This module handles state validation from and to the camera's hardware.

The CamState class handles:
    1. Translation between parameter names as they are known to the camera.
    2. Validation of state values
    3. Queueing of state value requests to the camera.
    
:authors: Athanasios Anastasiou
:date: August 2019
"""

from collections import OrderedDict # Preserves the order by which commands are submitted to the camera.

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
        
        * There is no HDMI connector exposed on the Wunder 360 S1.
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
        
        * This will always be "S1" on this camera.
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
        
        * This does not seem to be implemented on the Wunder 360 S1. Even if you manage to switch this flag to 0
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

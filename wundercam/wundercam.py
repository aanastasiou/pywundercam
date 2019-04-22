import requests

class SnapshotConf:
    """
    Snapshot configration.
    
    Snapshot configuration includes:
    
        * ISO
        * WhiteBalance
        * ExposureCompensation
        * ShootMode
    """
    def __init__(self, iso=None, white_balance=None, exposure_compensation=None, shoot_mode=None):
        self.iso = iso
        self.white_balance = white_balance
        self.exposure_compensation = exposure_compensation
        self.shoot_mode = shoot_mode
        
    @property
    def iso(self):
        pass
    
    @iso.setter
    def iso(self, iso):
        self.iso = iso
    
    @property
    def white_balance(self):
        pass
        
    @pwhite_balance.setter
    def white_balance(self, white_balance):
        pass
        
    @property
    def exposure_compensation(self):
        pass
        
    @exposure_compensation.setter
    def exposure_compensation(self, exposure_compensation):
        pass
        
    @property
    def shoot_mode(self):
        pass
    
    @shoot_mode.setter
    def shoot_mode(self, shoot_mode):
        pass
        
    @property
    def is_charging(self):
        pass
        
    @property
    def is_sdcard_plugged_in(self):
        pass
        
        
class WunderCam:
    def __init__(self,):
        pass
    
    def get_snapshot_conf(self):
        """
        Retrieves the current snapshot configuration from the camera.
        """
        pass
        
    def set_snapshot_conf(self, snapshot_conf=None):
        """
        Configures a shot
        """
        pass
        
    def snapshot(self):
        """
        Takes a single snapshot using the current configuration.
        """
        pass

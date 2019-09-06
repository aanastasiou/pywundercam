"""
This module describes the full exception hierarchy for all possible errors raised by PyWunderCam.

:authors: Athanasios Anastasiou
:date: September 2019
"""

class PyWunderCamError(Exception):
    """Base class for all exceptions originating from the pywundercam module."""
    pass
    
    
class PyWunderCamFileIOError(PyWunderCamError):
    """Base class for errors raised during file transfer"""
    pass
    
    
class PyWunderCamTimeOutError(PyWunderCamFileIOError):
    """Raised when a data transfer time out occurs."""
    pass
    
    
class PyWunderCamConnectionError(PyWunderCamFileIOError):
    """Raised when a connection error is encountered during a data request to the camera."""
    pass
    
    
class PyWunderCamDataTransferError(PyWunderCamFileIOError):
    """Raised when a data transfer error occurs.
    
    For example, in case the request was met with an HTTP404 error."""
    pass
    
    
class PyWunderCamContentTypeError(PyWunderCamFileIOError):
    """Raised when a resource's content type cannot be handled.
    
    In the current version of PyWunderCam, this exception is thrown if the content-type of a file transfer is other than
    image/jpeg."""
    pass
    
    
class PyWunderCamStateError(PyWunderCamError):
    """Base class for camera state related errors."""
    pass
    
    
class PyWunderCamValueError(PyWunderCamStateError):
    """Raised when an attempt is made to set a state variable to an invalid value."""
    pass
    
    
class PyWunderCamCameraNotFoundError(PyWunderCamError):
    """Raised when the camera hardware is unresponsive at the specified IP"""
    pass

class PyWunderCamSDCardUnusable(PyWunderCamError):
    """Raised when the SD card is either not plugged in or is not formatted."""

"""

This module handles all resource I/O (image and video files) from the camera to the local client.


:authors: Athanasios Anastasiou
:date: August 2019
"""

import os                           # Handles paths and filenames
import io                           # File handlers for streams in saving SingleStorage
import copy                         # Handles copying of the ResourceContainer data structure
import requests                     # Handles all file I/O activity with the camera over an HTTP interface
import PIL.Image                    # Serves images, directly capable to be modified by python code.


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
        self._metadata = metadata
        self._full_remote_filename = full_remote_filename
        if metadata is not None:
            self._metadata = metadata
        # Hash values are used for fast difference operations, when it comes to filtering out which resources where 
        # created by a particular action. See function ResourceList.__sub__() for more details.
        self._hash_value = hash(self.full_remote_filename)
        
    @property
    def metadata(self):
        """Returns metadata recovered from a resource's filename.
        
        Note:
        
        * This can be ``None`` if no named regular expression was passed during initialisation of 
          :class:`ResourceContainer`."""
        return self._metadata
          
    @property
    def full_remote_filename(self):
        """Returns the remote filename as this is found on the camera's file space."""
        return self._full_remote_filename
        
    def get(self):
        """Retrieves a resource from the camera and serves it to the application in the right format.
        
        .. warning :: 
            As of writing this line, anything other than image/jpeg will raise an exception. To save the 
            resource locally, please see SingleResource.save_to()."""
        
        try:
            image_data = requests.get(self._full_remote_filename, timeout=5)
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
        
        :param filename: The local filename to save this file to. If ``None``, the original name as found on the camera
                         is used.
        :type filename: str(path)"""
        
        local_filename = filename or os.path.split(self._full_remote_filename)[1]
        
        try:
            data = requests.get(self._full_remote_filename, timeout=5)
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
                          ``ResourceContainer`` for more.
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
        """Returns an array of ``PIL.Image`` images."""
        
        result = []
        for an_item in self._seq:
            result.append(an_item.get())
        return result
        
    def save_to(self, directory=None):
        """Saves an image sequence to a given directory (or the current one if none is provided).
        
        :param directory: The directory to save the files to.
        :type directory: str(path)
        """
        res_dir = directory or "./"
        for an_item in self._seq:
            file_name = "%s%s" % (res_dir, an_item.full_remote_filename)
            an_item.save_to(file_name)
        
    
        
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

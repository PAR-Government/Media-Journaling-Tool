# Add New File Type (e.g. video, audio, image, zip,  ?)

##Overview
In order to bring a new file type into the JT we must answer the following questions:

(1) How should the file be brought into the Journal?

(2) How should a node of this file type Link to other nodes?

(3) What sort of software works with this file type?

(4) What file types is this file type allowed to transition to?

(5) What information should be expected from this file when it donates to a manipulation? 

(6) How can we access the relevant metadata of the file?

The following steps lay out what changes are necessary to answer these questions.

## maskgen.tool_set
 (1) Add new type list to getFileTypes()
 
 (2) Adjust openImage with a new extension to ImageOpener

## maskgen.scenario_model
 (1) Add new extension to LinkTool--Analysis and Mask generation of source and target.  LinkTool is based on link type; one of  'video.video', 'image.video', 'video.image', 'image.image', 'audio.video'  or 'video.audio'.  Zip media are treated similar to videos with an audio stream

 (2) Update linkTools list
 
 (3) Add new extension to AddTool--Additional information recorded on loading and special instructions
 
 (4) Update addTools list

##maskgen.software_loader
 (1) *_loadSoftware* - load a new software type
 
 (2) *get_versions*

##operations.json
 Add transitions to appropriate operations to define which operations can be used with the new type. 
 
 See [New Operation](NewOperation.md) documentation for more details on operations and how they are defined.

## maskgen.masks.donor_rules

 Add a factory and donor processor. The factory is a function that creates a donor processing object.

The donor processor provides the arguments to be collected for the donor edge and the creation of the donor mask.

```
#factory
def donothing_processor(graph,edge_id, startImTuple, destImTuple):
    return DoNothingDonor()
 
#object
class DoNothingDonor:

    def arguments(self):
        return {}

    def create(self,
               arguments={},
               invert=False):
        return None
```

###MetaDataLocator Tool

Add a Locator Tool to the MetaDataLocator.  The locator tool answers meta-data in a consistent way regardless of media type.  

```
    def __init__(self):
        self.tools = {'zip': ZipMetaLocatorTool(self),
                      'image': ImageMetaLocatorTool(self),
                      'audio':AudioMetaLocatorTool(self),
                      'video':VideoMetaLocatorTool(self)}
```

```
class ImageMetaLocatorTool(VideoMetaLocatorTool):

    def __init__(self, locator):
        """
        @type locator: MetaDataLocator
        """
        VideoMetaLocatorTool.__init__(self,locator)

    def get_meta(self,
                 with_frames=False,
                 show_streams=False,
                 count_frames=False,
                 media_types=['video'],
                 frame_meta=['pkt_pts_time', 'pkt_dts_time', 'pkt_duration_time'],
                 frame_limit=None,
                 frame_start=None):
        meta = [] # of dictionary
        # expected attributes are nb_frames, nb_read_frames, duration (in seconds), 
        # width, height, codec_type, codec_name, codec_long_name
        frames = [] # list of dictionary
        if with_frames:
        	# expected attributes include pkt_pts_time,pkt_dts_time, and pkt_duration_time
            frames = [[{}]]
        return meta,frames

    def get_frame_rate(self,default):
        """
        :param locator:
        :param default:
        :param audio:
        :return:
        @type locator: MetaDataLocator
        """
        return 30.0

    def get_duration(self,default=None):
        """
            duration in milliseconds for media
        :param locator:
        :param default:
        :param audio:
        :return:
        @type locator: MetaDataLocator
        """
        return  0.0333
```


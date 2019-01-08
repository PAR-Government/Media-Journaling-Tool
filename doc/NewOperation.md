# Operation

# WHAT IS THIS?

Operations define each manipulation to media.  Operation is designed to be categorical, agnostic to software.  For example, resize is a common operation supported by many operations in similarly consistent approach.  The expected output is a adjustment media with a different size.  Deciding to add a new operation is based on:
​    1. arguments required for capture
​    2. Validation rules
​    3. Mask generation rules
​    4. Probe/Composite Generation rules.

# STEPS

## Comparison and Mask Generation

Determines how two media items--before and after manipulation--compared to generic masks.

For example, Crop Resize is specialty operation found in some tools.  The sofware crops and image and restores the crop to the original size of the image using some interpolation.  It is one operation with 'special sauce'.   It cannot be grouped with the individual Crop and Resize operations since the intermediate crop image is missing and the actual location of the crop is not immmediatly known.  In this case, the comparison function resizes the original image back to the crop size, as gathered from the manipulation sofware tool and recorded by the user.  The next step is to find the location of the crop in the original image.  Finally a mask of the crop region only is created, showing the amount of change that occurred during interpolation.   

Comparison functions live in tool_set or video_tools.

Image comparison signature:

```
def xCompare(img_original, img_manipulated,  arguments=dict()):
   """
    Return mask and initial analysis results such as a location, rotation amount, etc.
   :return mask and initial analysis. Mask is the same dimensions as the source image (img_original)
   @param arguments: collect from user
   @type img_original: numpy.ndarray
   @type img_manipulated: numpy.ndarray
   @rtype:(numpy.ndarray,dict)
   """
```

Image Analysis:

```
def x_analysis(analysis, img_original, img_manipulated, mask=None, linktype=None, arguments=dict(), directory='.'):
    """
    Add analysis items to the analysis dictionary
    @param linkType: image.image, video.image, video.video, etc.
    @type analysis: dict
    @type img_original: maskgen.image_wrap.ImageWrapper
    @type img_manipulated: maskgen.image_wrap.ImageWrapper
    @type mask: maskgen.image_wrap.ImageWrapper
    @type linkType: str
    """
```

Video comparison signature:

```
def x_vid_compare(vid_original, vid_manipulated, name_prefix, time_manager, arguments=None, analysis=dict()):
    """
    Function fills analysis dictionary.
    Function returns a tuple:
    1. list of segments. Each mask is a segment.
    2. list of errors
    @param vid_original: file name of original video/audio
    @param vid_manipulated: file name of original video/audio
    @param time_manager: time constraints from user input
    @param arguments: from user
    @param analysis: place analysis results
    @rtype: (list of segment, list of str)
    @type arguments: dict
    @type vid_original: str
    @type vid_manipulated: str
    """
```

### Analysis Operations

```
def optionalSiftAnalysis(analysis, img1, img2, mask=None, linktype=None,
arguments=dict(),directory='.')
```

Each analysis operation is function, defined by the
*package.module.function name*. The function is defined with the
following parameters:

- analysis -\> a dictionary to place the results
- img1 -\> maskgen.image\_wrap.ImageWrapper for the source image
- img2 -\> maskgen.image\_wrap.ImageWrapper for the destination image
  (result of the operation)
- mask -\> maskgen.image\_wrap.ImageWrapper containing the mask
  generated when comparing the images
- linkType -\> the transition type of the link; one of  'video.video', 'image.video', 'video.image', 'image.image', 'audio.video'  or 'video.audio'.
- arguments -\> a dictionary of arguments provided to the operation
  (collected from the link parameters).
- directory -\> the project directory

## Probe Generation

Probe generation involves overlaying each generated mask over the final media.  This requires applying transformations from manipulations that occur after the mask's associated manipulation.

Transforms are strictly spatial for images when dealing with masks, include resizing, cropping, warping, etc.  For video and audio, transforms are mostly temporal accept for crop and size (wxh) manipulations.   The level of effort to handle warping, spatial object rotation, etc. for video is outside the scope of complexity of the tool.

Probe generation also supports donor media overlay, applying prior transforms in the reverse direction, essentially backing out the manipulations prior to the mask.

During probe and donor image construction, the transformation function takes the current mask and transforms it according to the parameters provided to the associated link operation. For example, a
TransformResize link resizes the composite or donor mask according the resize specification. Donor mask construction is the inverse of composite construction. Thus, if the image size changed from (500,500)
to (450,450), then the donor transformation would resize a (450,450) mask into a (500,500) mask.

Each probe generation for final (also called composite) and donor uses the same function.  The signature is as follows and basic format is as follows.

```
def x_transform(buildState):
    if buildState.isComposite:
            return CompositeImage(buildState.compositeMask.source,
                                  buildState.compositeMask.target,
                                  buildState.compositeMask.media_type,
                                  apply_transform_to_mask(buildState.compositeMask.mask)
    elif buildState.donorMask is not None::
            return CompositeImage(buildState.donorMask.source,
                                  buildState.donorMask.target,
                                  buildState.donorMask.media_type,
                                  apply_reverse_transform_to_mask(buildState.donorMask.mask)
```

Functions *apply_transform_to_mask* and *apply_reverse_transform_to_mask* are user defined for the specific operation.  Masks are maintained in an object *CompositeImage*, either as a *donorMask* or *compositeMask*.  The *CompositeImage* returns the source and target node ids for for the edge associated with the mask, the media type of the mask (video, audio, image, zip) and the masks.

For images, the single *mask* attribute records a *numpy ndarray* of the mask.  Since some masks are processed with multiple edges at the same time, masks are unsigned eight bit single channel arrays with values 1  through 255 in each pixel, identifying the manipulation mask for the specific pixel. Thus, the mask is a composite of masks.  Typically, only mask is represented, but the used of the composite concept is retained for historical purposes.

For audio and video, the masks are in the format of a list of segments in the attribute *videomasks* (e.g. *buildState.compositeMask.videomasks*).   A segment includes start time, end time, start frame, end frame, rate, error, media type, and total frames (end - start + 1).   Spatial data is maintain an HDF5 file.  The file is reference in each segment as *videomask*.  

Each segment has the following components:

- startframe = frame number, from 1, of the first manipulated frame
- endframe = frame number the last manipulated frame
- framecount = endframe -- startframe + 1
- starttime = display time starting at 0 in milliseconds of the first manipulated frame
- endtime = display time of the last manipulated frame in milliseconds
- type = 'audio' or 'video'
- rate = frames per second. Each frame consumes 1000.0/rate milliseconds
- videosegment (file) = the name of the HDF5 spatial mask file.

Accessing these attributes in a segment, using the following functions:

* get_start_time_from_segment(segment, default_value=0) : float milliseconds
* get_start_frame_from_segment(segment, default_value=0) : integer
* get_end_time_from_segment(segment, default_value=0) : float milliseconds
* get_end_frame_from_segment(segment, default_value=0) : integer
* get_frames_from_segment (segment) :integer
* get_rate_from_segment(segment) : float frames per second
* get_type_of_segment(segment) : 'video','image','audio','zip'
* get_error_from_segment(segment) : float milliseconds
* get_file_from_segment(segment) : HDF5 file
* get_mask_from_segment(segment) : numpy ndarray

Creating and updating segments are accomplished through the following methods:

```
def create_segment(starttime=None,
                   startframe=None,
                   endtime=None,
                   endframe=None,
                   type=None,
                   frames=None,
                   videosegment=None,
                   mask=None,
                   rate=None,
                   error=0)
```

```
def update_segment(segment,
                   starttime=None,
                   startframe=None,
                   endtime=None,
                   endframe=None,
                   type=None,
                   frames=None,
                   videosegment=None,
                   mask=None,
                   rate=None,
                   error=None)
```

Historically, the *mask* attribute associated with a composite or donor mask is a single representative sample frame mask.  Unlike the image mask counterpart, this mask is values or 0 or 255, manipulated or non-manipulated respectively

A helpful function is accessing the default set of segments (called a mask set) for the entire source or target media:

```
def getMaskSetForEntireVideo(locator, start_time='00:00:00.000', end_time=None, media_types=['video'],channel=0)
```

### Probe

A probe (maskgen.mask\_rules.Probe) is defined as:

* edgeId = the tuple (source,target) graph link identifier
* targetBaseNodeId = the based node id
* finalNodeId = the final media node id 
* composites = a dictionary describing the location of this image in a one
  or more composite images
* donorBaseNodeId = the donor base media node id
* donorVideoSegments = the list video and audio donor segments
* targetMaskImage = the ImageWrapper target mask image (aligned to target
  final node)
* donorMaskImage= the ImageWrapper donor mask image (aligned to donor)
* targetMaskFileName = the file name of the target mask image (aligned to
  target final node)
* donorMaskFileName = the file name of the donor mask image (aligned to
  donor)
* targetVideoSegments = the list video and audio final node segments
* targetChangeSizeInPixels = tuple of (height,width) change is size (e.g. (0,0))
* level = 0 = the edge level within the graph

## BuildState

Each probe transform function is defined by the *package.module.function
name*. The function is defined to consume a build\_state of type
*maskgen.mask\_rules.BuildState* which contains the following
parameters:

- edge -\> a dictionary containing all the edge arguments and analysis
  results
- edgeMask -\> the numpy ndarray of the edge mask
- compositeMask -\> CompositeImage for video or numpy array for image.
  The contained mask values are set by level starting with 1.
  Alterations should be careful to preserve the numbering. One
  strategy is to process each pixel at a time, convert the level to
  255 and then back again upon completion. 
- donorMask -\> CompositeImage for video or numpy array for image. The
  mask values are 0 and 255. The donorMask attribute is not None, then
  perform the transformation in reverse using the embeddded mask.
- source -\> source node id for edge
- target -\> target node id for edge
- directory -\> location of journal
- pred\_edges -\> list of edge ids for predecessor edges to the source
  node.
- graph -\> the ImageGraph of the journal
- checkEmpies -> indication to check for empty masks, possibly indicating an erroneous obfuscating operation.
- extractor -> MetaDataExtractor using the graph as a 'cache'.

A composite image is defined as a named tuple:

```
CompositeImage = namedtuple('CompositeImage', ['source', 'target', 'media_type', 'videomasks'])
```

Videomasks is a list of segments. 

##Probe Pre-process

The change mask generated during the comparison is often used as the starting state of probe mask, prior to applying transforms.  In somecase, the mask or segments need to be adjusted as the initial state. For example, in select cut frames, the mask reflects the removed frames.  However, these frames do not exist in the final video, thus the video segments record the set neigboring frames of the cut in the final video.

In general, masks and segments are always in the dimensions, spatial and temporal, of the source, identifying on the source what was changed, removed, etc.  In operations that generate masks that cut, resize or otherwise changethese dimensions must be cast into the target media space.

The signature for a preprocess function is as follows:

```
def select_cut_frames_preprocess(mask, edge, target_size):
  """
  mask depends on the media type.
  target size is height and width.
  @type mask: numpy.ndarray for image, list of video segments (dictionary) for video, audio and zip
  @type edge: dict
  @type target_size: (int, int)
  """
```

## Operation

This section describes the operation definition as it exists in the JSON file.

* *category*: Like operations grouped together

* *name*: Operation name that indicates the most common software terminology.  Understandably,  software designers to adopt other common terms.  For example, Liquid Rescale is often a form of seam carving.

* *mandatoryparameters*: Parameters required from the user. Can be conditioned on media type (video and image).

* *optionalparameters*: Parameters not required from the user. Can be conditioned, through the use of a rule , on one or more other parameters, making the parameter mandatory.   A rule is defined by each dependent parameter

  *  *mandatory parameter name*:  defines the list of values that trigger mandatory condition such as  "clone", "stacking"] etc.

* *rules*: Rules are a list of validation rule functions for the operation as defined ealier.  Rule functions are maintained in maskgen.graph_rules.  Rules are executed during validation and on establishing new connections.  Since rules that check donors cannot be run when establishing a new connection, as the donor connection may not exist yet, donor check rules should be prefixed with a 'donor:' designation:

    * donor:checkDonor

* *analysisOperations* : A set of operations that analysis the source, target and difference masks to compile meta-data used for validation and probe generation, such as transform homographies, size changes, etc.

* *maskTransformFunction*:  A dictionary keyed on media type defining probe transform functions as defined earlier

* *compareparameters*: Parameters sent to the comparison function for mask generation.  There are several special parameters:

    *  *function* is a special parameter specifying the alernate mask generating function as discussed in the Comparison and Mask Generation section.
    * *video_function*  is a special parameter specifying the alernate mask generating function for video, audio and zip.
    * *convert_function* is a function that converts the media prior to comparison.  For images, the default activity converts to unsigned 16 bit gray scale.

* *description*: A description of the operation visible to the user

* *includeInMask*: A dictionary of keyed boolean values indicating if the mask associated with an operation is considered a testable mask to be included in a probe (e.g. blue link).  The key is the media type or 'default'--for all unspecified media types.  Example: { 'default': false, 'video':true}

* *transitions*: The set of media type transitions supported by the operation.  Transitions are defined as source media type to target media type, separated by '.' (e.g. "video.video").

* *qaList*: The list of prompts to the user for a probes associated with the operation in QA.

* *donor_processor*: A factory function that creates a donor mask/segment. At this time there are three:  *maskgen.masks.donor_rules.image_interpolate*, *maskgen.masks.donor_rules.audio_donor* and *maskgen.masks.donor_rules.video_donor*.  Use the for their respective operations if the donor has a spatial or temporal constraints (e.g not the entire media as in a global operation such as Antiforensics).

    Thus, not all operations that accept donors require a processor.  For those that use a global mask, it is not needed.

* *generateMask*: describes to the type change information generated during the original and manipulated media during comparison and mask generation.  In some cases, mask generation is not required, only capturing media meta-data changes.  These type of operations are referred to as 'global' operations, affecting diffuse parts of the media type such as transforms. Options for the generate mask attribute include:
    - meta : meta-data only
    - frames: capture meta- data on frames
    - all: include spatial masks
    - audio: include spatial masks



## Parameters

Parameters are defined optional and mandatory sections of the operation.  Each parameter has a the following attributes:

- type - defines the data type
  - *int[min:max]*   - example: int[0:10000]
  - *float[min:max] *  -example: float[0:1.0]
  - *file:<media_type>* - <media_type> is one of [image, video, audio, zip] or a suffix example: file:kml or file:image
  - *list* - If the the type is list, a parameter must also have *value*.
  - *fileset:<search directory>* - example: plugins/JpgFromCamera/QuantizationTables
  - *yesno*
  - *text*
  - *time*
  - *urls*
  - *coordinates* -example: (0,1)
  - *boxpair* - For defining a box and rotation
  - *frame \_or\_time* - picks time if audio, frame if video depending on the source file type
  - *string*
  - *listfromfile:\<filename\>* - a text file containing a list of possible entries
  - *folder:\<location\> * - example folder:plugins/QTTables
- *values* - a list of values for list type.  Values are strings.
  - *_type_:values* - source file type specific values to override the default values; example "video:values".
- *description* - description of the parameter
- *defaultvalue* - default value (optional)
- *source*- Parameter is conditioned to be collected for a specific type of media such image, zip, video or audio (optional).

The source type specific values is inforced in the UI.  It is not enforced in batch projects.  The batch specification to not indicate random selection of values from the parameter if there is a type restriction..
##Comparison and Mask Generation

##Transforms and Preprocessors

Transforms and Preprocessors  as specified as part of *maskTransformFunction*.

There can be one function per each type of media  (image, zip, video, video).  There is also special media preproceessors using keys:
audio_preprocess, video_process, zip_preprocess and image_preprocess.  For example:

```
        "video": "maskgen.mask_rules.select_cut_frames",
        "audio_preprocess": "maskgen.mask_rules.select_cut_frames_preprocess",
        "video_preprocess": "maskgen.mask_rules.select_cut_frames_preprocess",
        "audio": "maskgen.mask_rules.delete_audio"
```

Transforms were describe in the Probe Generation section.  Preprocessor were describe in the Probe Pre-process section.

## Rules

Operation rules are functions that accept three parameters to identify the project graph and the link to be validated.

- masken.software\_loader.Operation instance
- maskgen.image\_graph.ImageGraph
- start node id
- end node id

A rule function returns None if the link is valid, otherwise the function returns a tuple:

- Severity as defined in maskgen.validation.core
- Error String

Example: (Severity.WARNING, 'Starting node appears to be compressed\')

```
def checkCropSize(op, graph, frm, to):
    """
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    """
    edge = graph.get_edge(frm, to)
    if 'shape change' in edge:
        changeTuple = toIntTuple(edge['shape change'])
        if changeTuple[0] > 0 or changeTuple[1] > 0:
            return (Severity.ERROR,'Crop cannot increase a dimension size of the image')
```

## HELP

Help resources are maintained under *resources/help*.  Each operation has several PNG files that describe the operation.

Build the PNG files, placing them in the *resources/help/operationSlides* folder.  Then, link them to the operation within the file *resources/help/image_linker.json*.

```
"TransformCropResize": {
   "images": [
      "operationsSlides/transform_crop_resize.png"
   ]
},
```

# New Rule Functions

Rule functions are used in both operations and project properties. Add
new rule functions follows a similar approach to loading new image
loading plugins. The Setuptools entry point 'maskgen\_rules' permits the
discovery of new rules installed outside the maskgen core module.

```
entry_points= {'maskgen\_rule': [ 'ruleid = apackage.amodule:aRuleFunction']},

```

The package layout is as follows:

* topfolder/
  * setup.py
  * _\_init\_\_.p
  * apackage /
    * amodule.py


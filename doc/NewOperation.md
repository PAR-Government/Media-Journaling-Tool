# Operation

# WHAT IS THIS?

Operations define each manipulation to media.  Operation is designed to be categorical, agnostic to software.  For example, *resize* is a common operation supported by many operations in similarly consistent approach.  The expected output is media with a different size.  

Deciding to add a new operation is based on:

1. Arguments required for capture.
2. Validation rules.
3.  Mask generation rules.
4.  Probe/Composite Generation rules.

# STEPS

## Comparison and Mask Generation

Comparison and Mask Generation collectively determine how two media items--before and after manipulation--are different, generating masks and change meta-data.

For example, Crop Resize is specialty operation found in some tools.  The sofware crops and image and restores the crop to the original size of the image using some interpolation.  It is one operation with 'special sauce'.   It cannot be grouped with the individual Crop and Resize operations since the intermediate crop image is missing and the actual location of the crop is not immmediatly known.  In this case, the comparison function resizes the original image back to the crop size, as gathered from the manipulation sofware tool and recorded by the user.  The next step is to find the location of the crop in the original image.  Finally a mask of the crop region only is created, showing the amount of change that occurred during interpolation.   

Comparison functions live in tool_set or video_tools.

####Image and Frame Comparison Signature

For imaeges, masks use 0 to represent change.  Frames are inverted in comparison and then flipped prior to write to HDF5.  

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

####Image and Frame Analysis Signature

```
def x_analysis(analysis, img_original, img_manipulated, mask=None, linktype=None, arguments=dict(), directory='.'):
    """
    Add analysis items to the provided analysis dictionary
    @param linkType: image.image, video.image, video.video, etc.
    @type analysis: dict
    @type img_original: maskgen.image_wrap.ImageWrapper
    @type img_manipulated: maskgen.image_wrap.ImageWrapper
    @type mask: maskgen.image_wrap.ImageWrapper
    @type linkType: str
    """
```

Each analysis operation is function, defined by the
*package.module.function name*. The function is defined with the
following parameters:

- *analysis* -\> a dictionary to place the results
- *img_original* -\> maskgen.image\_wrap.ImageWrapper for the source image
- *img_manipulated* -\> maskgen.image\_wrap.ImageWrapper for the destination image
  (result of the operation)
- *mask* -\> maskgen.image\_wrap.ImageWrapper containing the mask
  generated when comparing the images
- *linkType* -\> the transition type of the link; one of  'video.video', 'image.video', 'video.image', 'image.image', 'audio.video'  or 'video.audio'.
- *arguments* -\> a dictionary of arguments provided to the operation
  (collected from the link parameters).
- *directory* -\> the project directory

####Video Comparison Signature

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

## Other Mask Types

#### Input Masks

Inputmasks are essential donor masks.  They are special in that they are always referenced in the edge by file name in the attribute *inputmaskname*.

#### Substitute Masks

Substitute masks replace edge masks.  CAUTION: These masks do not reflect actual differences between media.  Instead, they represent intended differences.

##Probe Inclusion

Edge masks included in a probe are selected as part of the probe generation API.  By default, all edge masks that are labeled as to included to in a 'composite' (blue color links in the JT UI) are included in a generated probe set.  

## Composites

The term *Composite* is derived from the notion that a final media is the composite of a series of manipulation.  A *Composite* mask attempts to represent all the changes in one mask media file.    However, each composite mask, depending its make-up, may leave some manipulations not-represented due obfuscation (e.g. Color Masks).

Composites are described in the API documentation.

For the remainder of this document the term 'Composite Image' is misused, as it is only a single representation of one edge/manipulation.

## Probe Generation

Probe generation involves overlaying each generated edge mask over the final media.  This requires applying transformations associated with manipulations that occur after the manipulation that created the mask.  These subsequent transforms are applid in the order represented by the graph.  A single generated edge mask may contribute to more than one final media.  Each subsequent manipulation effectively replaces the mask from the prior manipulation.

> If a manipulation does not effect a mask, the mask is forwarded to the next manipulation's transformation function.  

Transforms are strictly spatial for images when dealing with masks, include resizing, cropping, warping, etc.  For video and audio, transforms are mostly temporal accept for crop and size (wxh) manipulations.   At this time, the level of effort to handle complex spatial adjustments in video such as warping and spatial object rotation is outside the scope of complexity for the tool.

Probe generation also supports donor media overlay, applying prior transforms in the reverse direction, essentially backing out the manipulations prior to the mask.

During probe and donor image construction, the transformation function takes the current mask and transforms it according to the parameters provided to the associated link operation. For example, a
TransformResize link resizes the composite or donor mask according the resize specification. Donor mask construction is the inverse of composite construction. Thus, if the image size changed from (500,500)
to (450,450), then the donor transformation would resize a (450,450) mask into a (500,500) mask.

Each probe generation for final (also called composite) and donor uses the same function.  The signature is as follows and basic format is as follows.

```
def x_transform(buildState):
    if buildState.isComposite:
            return buildState.compositeMask.create(
               apply_transform_to_mask(
               buildState.compositeMask.mask)
    elif buildState.donorMask is not None:
            return buildState.donorMask.create(
                               apply_reverse_transform_to_mask(
                               buildState.donorMask.mask)
```

Functions *apply_transform_to_mask* and *apply_reverse_transform_to_mask* are user defined for the specific operation.  Masks are maintained in an object *CompositeImage*, either as a *donorMask* or *compositeMask*.  The *CompositeImage* contains the source and target node IDs for for the edge associated with the mask, the media type of the mask (video, audio, image, zip) and the masks.

The CompositeImage has the followin attributes:

* source -> node ID of the basis media manipulated to produce the mask for which is being transformed to overlay a final media.
* target -> node ID of the target/result of the manipulation being transformed to overlay a final media.
* media_type -> the media manipulate by the edge from source  to target nodes.
* videomask -> list of non-overlapping segments containing the temporal and spatial records of the manipulation.
* mask -> a single image mask associate with an image manipulation.
* ok -> composites may be invalidated by subsequent manipulations such as obfuscation and removal.
* issubstitute -> records if the originating change mask is a substitute for the JT's calculated different masks.

For images, the single *mask* attribute records a *numpy ndarray* of the mask.  Since some masks are processed with multiple edges at the same time, masks are unsigned eight bit single channel arrays with values 0  through 255 in each pixel, identifying the manipulation mask for the specific pixel. Thus, the mask is a composite of masks.  Only one mask is represented in a CompositeImage, but the use of the composite concept is retained for historical purposes.

For video, the *videomask* attribute contains non-overlapping segments.  The *videosegment* attribute in each segment is set only if the spatial data was generated by the JT's video comparison for the specific manipulation.

For audio and video, the masks are in the format of a list of segments in the attribute *videomasks* (e.g. *buildState.compositeMask.videomasks*).   A segment includes start time, end time, start frame, end frame, rate, error, media type, and total frames (end - start + 1).   Spatial data is maintain as an HDF5 file.  The file is reference in each segment as *videomask*.  

Each segment has the following components:

- startframe = frame number, from 1, of the first manipulated frame
- endframe = frame number the last manipulated frame
- framecount = endframe -- startframe + 1
- starttime = display time starting at 0 in milliseconds of the first manipulated frame
- endtime = display time of the last manipulated frame in milliseconds
- type = 'audio' or 'video'
- rate = frames per second. Each frame consumes 1000.0/rate milliseconds
- videosegment (file) = the name of the HDF5 spatial mask file.
- error = the amount of error in milliseconds; error is introduced as segments are augmented through temporal manipulations such as frame rate changes.

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

Historically, the *mask* attribute associated with a composite or donor mask is a single representative sample frame mask.  Like the image edge mask counterpart, this mask is values or 0 or 255, manipulated or non-manipulated respectively.  Probe image masks are inverted, 0=non-manipulated and 255=manipulated.

A helpful function is accessing the default set of segments (called a mask set) for the entire source or target media (without spatial masks):

```
def getMaskSetForEntireVideo(locator, start_time='00:00:00.000', end_time=None, media_types=['video'],channel=0)
```

### Probe

A probe (maskgen.mask\_rules.Probe) is defined as:

* edgeId = The tuple (source,target) graph link identifier.
* targetBaseNodeId = The based node id.
* finalNodeId = The final media node id.
* composites = A dictionary describing the location of this image in a one
  or more composite images.
* donorBaseNodeId = The donor base media node id.
* donorVideoSegments = The list video and audio donor segments.
* targetMaskImage = The ImageWrapper target mask image (aligned to target
  final node).
* donorMaskImage= The ImageWrapper donor mask image (aligned to donor).
* targetMaskFileName = The file name of the target mask image (aligned to
  target final node).
* donorMaskFileName = The file name of the donor mask image (aligned to
  donor).
* targetVideoSegments = The list video and audio final node segments.
* targetChangeSizeInPixels = A tuple of (height,width)  indicating a change is size (e.g. (0,0)).
* level = The edge level within the graph.
* taskDesignation = Indicates the type of test for which the segment is eligible for: 'spatial', 'temporal','spatial-temporal'
* usesSubsituteMask = Indicates if the JT generated edge mask is replaced with a user generated mask: True/False.  

## BuildState

Each probe transform function is defined by the *package.module.function
name*. The function is defined to consume a build\_state of type
*maskgen.mask\_rules.BuildState* which contains the following
parameters:

- *edge* -\> A dictionary containing all the edge arguments and analysis
  results.
- *edgeMask* -> The numpy ndarray of the edge mask.
- *compositeMask* -\> CompositeImage for video or numpy array for image.
  The contained mask values are set by level starting with 1.
  Alterations should be careful to preserve the numbering. One
  strategy is to process each pixel at a time, convert the level to
  255 and then back again upon completion. 
- *donorMask* -\> CompositeImage for video or numpy array for image. The
  mask values are 0 and 255. The donorMask attribute is not None, then
  perform the transformation in reverse using the embeddded mask.
- *source* -\> Source node id for edge.
- *target* -\> Target node id for edge.
- *directory* -\> Location of journal.
- *pred\_edges* -\> List of edge ids for predecessor edges to the source
  node.
- *graph* -\> The ImageGraph of the journal.
- *checkEmpies* -> An indicator to check for empty masks, possibly indicating an erroneous obfuscating operation.
- *extractor* -> MetaDataExtractor using the graph as a 'cache'.

A composite image is defined as a named tuple:

```
CompositeImage = namedtuple('CompositeImage', ['source', 'target', 'media_type', 'videomasks'])
```

Videomasks is a list of segments. 

##Probe Pre-process

The change mask generated during the comparison is often used as the starting state of probe mask, prior to applying transforms.  In somecase, the mask or segments need to be adjusted as the initial state. For example, in select cut frames, the mask reflects the removed frames.  However, these frames do not exist in the final video, thus the video segments record the set neigboring frames of the cut in the final video.

In general, masks and segments are always in the dimensions, spatial and temporal, of the source, identifying on the source what was changed, removed, etc.  In operations that generate masks that cut, resize or otherwise change these dimensions must be cast into the target media space.

The signature for a preprocess function is as follows:

```
def x_preprocess(mask, edge, target_size):
  """
  mask depends on the media type.
  target size is height and width.
  @type mask: numpy.ndarray for image, list of video segments (dictionary) for video, audio and zip
  @type edge: dict
  @type target_size: (int, int)
  """
```

#### Example: Select Cut Frames

Select Cut Frames recorded video segment does contain a HDF5 spatial mask.  The segment records the dropped/cut frames.  We overlayed on the next manipulations, the dropped frames do not exist.   Instead, the composite mask records the neighbor frames:

 * start frame = one minus the cut start frame.
 * end frame = one plus the cut start frame.

#### Example: Seam Carving

Seam Carving spatial masks represent seams removed from the basis image.  Since these pixels cannot be represented in the next manipulation, the neighbor pixels are represented in the mask.  This appears like two pixel wide lightning stricks across the image, vertically or horizontally.





## Operation

This section describes the operation definition as it exists in the JSON file.

* *category*: Like operations grouped together

* *name*: Operation name that indicates the most common software terminology.  Understandably,  software designers adopt other common terms.  For example, Liquid Rescale is often a form of seam carving.

* *mandatoryparameters*: Parameters required from the user. Can be conditioned on media type (video and image).

* *optionalparameters*: Parameters not required from the user. Can be conditioned, through the use of a rule , on one or more other parameters, making the parameter mandatory.   A rule is defined by each dependent parameter

  *  *mandatory parameter name*:  defines the list of values that trigger mandatory condition such as  "clone", "stacking"] etc.

* *rules*: Rules are a list of validation rule functions for the operation as defined ealier.  Rule functions are maintained in maskgen.graph_rules.  Rules are executed during validation and on establishing new connections.  Since rules that check donors cannot be run when establishing a new connection, as the donor connection may not exist yet, donor check rules should be prefixed with a 'donor:' designation:

    * donor:checkDonor

* *analysisOperations*: A set of operations that analysis the source, target and difference masks to compile meta-data used for validation and probe generation, such as transform homographies, size changes, etc.

* *maskTransformFunction*:  A dictionary keyed on media type defining probe transform functions as defined earlier

* *compareparameters*: Parameters sent to the comparison function for mask generation.  There are several special parameters:

    *  *function* is a special parameter specifying the alernate mask generating function as discussed in the Comparison and Mask Generation section.
    * *video_function*  is a special parameter specifying the alernate mask generating function for video, audio and zip.
    * *convert_function* is a function that converts the media prior to comparison.  For images, the default activity converts to unsigned 16 bit gray scale.

* *description*: A description of the operation visible to the user

* *includeInMask*: A dictionary of keyed boolean values indicating if the mask associated with an operation is considered a testable mask to be included in a probe (e.g. blue link).  The key is the media type or 'default'--for all unspecified media types.  Example: { 'default': false, 'video':true}

* *transitions*: The set of media type transitions supported by the operation.  Transitions are defined as source media type to target media type, separated by '.' (e.g. "video.video").  

    > IMPORTANT: Transitions are associated with file type.  

* *qaList*: The list of prompts to the user for a probes associated with the operation in QA.

* *donor_processor*:  A processor is factory function that creates a donor mask/segment. At this time there are three:  *maskgen.masks.donor_rules.image_interpolate*, *maskgen.masks.donor_rules.audio_donor* and *maskgen.masks.donor_rules.video_donor*.  Use the for their respective operations if the donor has a spatial or temporal constraints (e.g not the entire media as in a global operation such as Antiforensics).

    Thus, not all operations that accept donors require a processor.  For those that use a global mask, it is not needed.

* *generateMask*: Describes to the type change information generated during the original and manipulated media during comparison and mask generation.  In some cases, mask generation is not required, only capturing media meta-data changes.  These type of operations are referred to as 'global' operations, affecting diffuse parts of the media type such as transforms. Options for the generate mask attribute include:

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
  - *folder:\<location\>* - example folder:plugins/QTTables
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
- Optional: A Fix function.

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

### Fix Functions

A fix function promises to fix the issue raised during validation with minimal or no additional input from the user.  A fix function signature is as follows.

~~~
def fixX(graph, start, end):
"""
@param graph: maskgen.image_graph.ImageGraph
@param start: start node id (str) for erroneous edge
@param end: end node id (str) for errorneous edge
~~~

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
entry_points= {'maskgen_rules': [ 'ruleid = apackage.amodule:aRuleFunction']},

```

The package layout is as follows:

* topfolder/
  * setup.py
  * _\_init\_\_.p
  * apackage /
    * amodule.py


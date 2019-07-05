# CGI
## ArtificialLighting
Add sources of illumination that were not originally present.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
    - Source Type: image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate. This operation is often associated with: Antiforensic Illumination, Shadow and Reflection Manipulations 
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## ArtificialReflection
Add sources of reflection that were not originally present.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *minimum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate. This operation is often associated with: Antiforensic Illumination and Reflection Manipulations
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## ArtificialShadow
Add shadows that were not originally present.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate. This operation is often associated with: Antiforensic Illumination, Shadow and Manipulations 
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## CGIFill
Uniformly alter the color of an image within a given selection.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Fill Category* : Fill Operation
   - Type: list
    - Values: uniform color, pattern, paint brush
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## DeepFakeFaceSwap
Face Swap with Deep Fake algorithms.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
+ *urls* : Urls to training videos if available
   - Type: urls
### Optional Paramaters
+ *Trainer* : Trainer used.
   - Type: list
    - Default: Original
    - Values: GAN, GAN128, Original, IAE
+ *Mask Seamless* : Algorithm to erase seams.
   - Type: yesno
    - Default: no
+ *Converter* : Trainer used.
   - Type: list
    - Default: Masked
    - Values: Masked, Adjust
+ *Histogram Color Match* : Match color with histogram (may be the same as adjust color).
   - Type: yesno
    - Default: yes
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *Blur Size* : Blur Kernel Size.
   - Type: int[1:1000]
    - Default: 40
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *Epochs* : Training epochs.
   - Type: int[1:100000000]
    - Default: 10000
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *Mask Blur* : Trainer used.
   - Type: yesno
    - Default: no
+ *Mask Erode* : Erode edges (may reduce the fit).
   - Type: yesno
    - Default: no
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *Adjust Smooth* : Smooth edges.
   - Type: yesno
    - Default: no
+ *Batch Size* : micro batches.
   - Type: int[1:100000000]
    - Default: 32
+ *Detector* : Face Detector used.
   - Type: list
    - Default: all
    - Values: all, hog, cnn
+ *Adjust Color* : Match color intensity.
   - Type: yesno
    - Default: no
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.resize_transform*: APPLIES: IMAGE     Supports local resize through a perspective transform or a global resize.     Global resize with a location change and none interpolation implies a resize of the canvas without     resize of data (inverse of a crop).     'inputmaskname' is a file that identifies the region that was resized for local operations.  In this case,     this helps  identify the target object and create the appropriate perspective transform.

*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Confirm URL(s) {urls} lead to training data
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## DigitalPenDraw
Use the pencil or brush tool to add a pixel overlay to an image or selection.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## Gradient
Apply a donor adjustment within a selection with scaling intensities.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## Handwriting
Use the pencil or brush tool to add a pixel overlay to an image or selection.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Operation includes adding a pattern or 2d structure that is not a 3d model. All 3d models should be documented using the ObjectCGI operation
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## ObjectCGI
Create objects that were not originally present in an image.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *is3D* : Indicates if the CGI is a 3D model with light sources, etc.
   - Type: yesno
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *urls* : An image file containing the image used.  The unused portion of the image should be transparent with an alpha-channel
   - Type: urls
+ *isGAN* : IS CGI Object overlayed using a GAN using using the image/frame itself as input parameters
   - Type: yesno
### Optional Paramaters
+ *kernel* : Algorithm to suppress difference mask noise
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *model image* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Confirm URL(s) {urls} leads to the correct 3D model(s)
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## OverlayObject
Add an object to another image or selection. Do not use a donor image.  Consider using ObjectCGI.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Operation includes adding a pattern or 2d structure that is not a 3d model. All 3d models should be documented using the ObjectCGI operation
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## OverlayText
Add text to an image or selection. Do not use a donor image.  Donor images must be inserted using a PasteSplice operation.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate. This operation is often associated with Date Burn-in
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## SynthesizeGAN
Synthesize an image using a trained GAN model and provided input

Include as Probe Mask for []
### Mandatory Paramaters
+ *Name* : Name of GAN
   - Type: text
+ *urls* : URL of GAN
   - Type: urls
### Optional Paramaters
+ *Random seed value* : The random fed to the GAN to produce the output
   - Type: float
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
## SynthesizeVideo
Synthesize an video scene using a trained GAN model and provided input

Include as Probe Mask for []
### Mandatory Paramaters
+ *KML File* : Name of KML File
   - Type: file:kml
+ *Recording Software* : Name of software to recapture screen
   - Type: text
+ *urls* : URL used to create the flight path simulate
   - Type: urls
+ *Rendering Software* : Name of software used to render the video
   - Type: text
### Optional Paramaters
+ *Video Location* : Where the video is supposed to take place
   - Type: text
+ *Time of Sun* : Time of day video was taken if unknown leave blank
   - Type: text
+ *Time Settings* : The time setting used if changed
   - Type: list
    - Default: Default time
    - Values: Default time, Morning, Evening, Night, Early Morning, Late Morning, Late Evening, Early Evening
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Confirm URL(s) {urls} leads to the correct 3D model(s)
### Analysis Rules
# Layer
## Blend
Edit or paint each pixel to make it the result color. The result color is a random replacement of the pixels with the base color or the blend color, depending on the opacity at any pixel location.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *mode* : Blend Mode
   - Type: list
    - Values: Color Dodge, Color, Darken, Difference, Dissolve, Divide, Exclusion, Hard Light, Hard Mix, Hue, IntensityBurn, Lighten, Lighter Dodge, Linear Burn, Linear Dodge (add), Linear Light, Luminosity, Multiply, Multiply, Pin Light, Saturation, Screen, Smudge, Soft Light, Subtract, Vivid Light
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## LayerFill
Change the fill using a solid color or gradient.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Amount* : Fill level--amount of blended into the layer
   - Type: int[0:100]
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ If this operation follows a paste splice, the operations may be able to be consolidated into a paste splice operation with a blend option
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## LayerOpacity
Change the transparency of a given color overlay.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Amount* : Transparency level
   - Type: int[0:100]
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
# Steganography
## EncodeMessage
Embed text into an Image

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *message* : Filename for the message text
   - Type: file:txt
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
# Laundering
## SocialMedia
Laundering

Include as Probe Mask for []
### Mandatory Paramaters
+ *download* : How was the image downloaded
   - Type: list
    - Values: Mobile Device, Desktop
+ *type* : Service
   - Type: list
    - Values: Facebook, Instagram, Youtube, Twitter
+ *upload* : How was the image uploaded?
   - Type: list
    - Values: Mobile Device, Desktop
### Optional Paramaters
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.resize_transform*: APPLIES: IMAGE     Supports local resize through a perspective transform or a global resize.     Global resize with a location change and none interpolation implies a resize of the canvas without     resize of data (inverse of a crop).     'inputmaskname' is a file that identifies the region that was resized for local operations.  In this case,     this helps  identify the target object and create the appropriate perspective transform.

*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
# Color
## ColorBalance
Alter the Color Temperature of an image on a Yellow Blue Scale.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Is this a global operation that does not need to be added to the composite mask
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## ColorLUT
Changing color space or changing based on a lut.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *lookuptable* : Name of the lookup table (LUT) to color grade layers of footage
   - Type: text
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate. This operation is often associated with TimeOfDay
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Hue
Alter the color of a selection or image without adjusting saturation or luminance.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Source* : source of color.  Other is some color palette or texture. Self is using a color from the same image.
   - Type: list
    - Values: self, other
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Saturation
Alter the color intensity of a given hue.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Direction* : intent of saturation alteration
   - Type: list
    - Values: increase, decrease
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Vibrance
Visually change brightness and saturation

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Direction* : Increase or decrease color vibrance
   - Type: list
    - Values: increase, decrease
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
# Transform
## FrameBlend
An interpolation that changes a selection of frames without changing the total number of frames

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Validation Rules
*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## ImageInterpolation
Replace large selections with an averaging of surrounding pixel groups.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## TransformAffine
Apply a linear mapping method that preserves points, straight lines, and planes

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.affine_transform*: APPLIES: IMAGE     Apply a transform if available, else resize to target shape if shape change as occurred.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
## TransformCrop
Removing edge content from an image. For video, remove data from certain areas of the frame.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
+ *location* : Tuple in form of (x,y) describing the upper left crop corner.
   - Type: coordinates
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkCropSize*: Confirm that a crop occurred.

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

*checkCropMask*: Confirm the cropped image area was not otherwise changed.

### Allowed Transitions
+ image.image
+ video.video
+ zip.zip
### Probe Generation Rules
*image:maskgen.mask_rules.crop_transform*: APPLIES: IMAGE.     Use the location of the crop and size change to crop the incoming composite mask.     For Donors, use the location to place the donor mask into the parent shape.

*video:maskgen.mask_rules.video_crop_transform*: APPLIES: VIDEO     Use the location of the crop and size change to crop the incoming composite mask.     For Donors, use the location to place the donor mask into the parent shape.

### QA Questions
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## TransformCropResize
Crop image and then resize image back to original image size.

Include as Probe Mask for []
### Mandatory Paramaters
+ *crop width* : The width of the crop image prior to resize
   - Type: int[0:100000]
+ *crop height* : The height of the crop image prior to resize
   - Type: int[0:100000]
### Optional Paramaters
+ *Position Mapping* : Maps the bounding regions of each image
   - Type: boxpair
### Validation Rules
### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.crop_resize_transform*: APPLIES: IMAGE     When available, use position mapping.     Position mapping is a box and rotation.  Composite embeds and rotates mask.     Donor generation, crops and rotates (inverse) mask.     Otherwise used calculated crop and height and width then resize.     Composite mask generation crops the mask before resize.     Donor mask generation resizes mask and then embeds mask at the crop position.

### QA Questions
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## TransformDistort
Alter the shape and dimensions of a given selection or image.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.distort_transform*: APPLIES: IMAGE     Apply a transform if available, else resize to target shape if shape change as occurred.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
## TransformDownSample
Down sample a video to a lower frame resolution.

Include as Probe Mask for []
### Mandatory Paramaters
+ *pixel aspect* : .
   - Type: list
    - Source Type: video
    - Values: No Change, Square Pixels (1.0), D1/DV NTSC (0.9091), D1/DV NTSC Widescreen 16:9 (1.2121), D1/DV PAL (1.0940), D1/DV PAL Widescreen 16:9 (1.4587), Anamorphic 2:1 (2.0), HD Anamorphic 1080 (1.333), DVCPRO HD (1.5), Custom
+ *resolution* : Format widthxheight:  1280x960
   - Type: string
### Optional Paramaters
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *interlacing* : Semantic remove attempts to mitigate lines prior to export in non interlaced format.
   - Type: list
    - Source Type: video
    - Values: add, remove, semantic-remove
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## TransformFlip
Reverse pixel coordinates of an image or selection along a vertical or horizontal axis.

Include as Probe Mask for []
### Mandatory Paramaters
+ *flip direction* : Direction of flip.
   - Type: list
    - Values: horizontal, vertical, both
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.flip_transform*: APPLIES: IMAGE     Flips cannot be handled by perspective or affine transforms. Instead, the change mask is used to determine object to flip.     Pixels of the composite (or donor ) mask intersecting the change mask are flipped.     This transform also supports mask shape resize changes. However, this side effect is note recommend, as flip should be     considered a local manipulation.

*video:maskgen.mask_rules.video_flip_transform*: APPLIES: VIDEO     Applies frame rate adjustments first and the flips the masks.     Resize is supported (last), but not recommended as part of the operation.

### QA Questions
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## TransformMove deprecated
Reposition a selection within a larger composition.

Include as Probe Mask for []
### Mandatory Paramaters
+ *inputmaskname* : An image file containing a mask describing the component that was moved. 
   - Type: file:image
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, Map, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
+ *use input mask for composites* : Override JT decision to use the input mask in composite generation
   - Type: list
    - Values: JT decides, yes, no
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkEmpty*: Confirm the change mask is not empty

*checkMoveMask*: Confirm move mask (input mask) is roughly the size and shape of the change mask.     Overlap is considered, as the move might partially overlap the area from which the pixels     came.

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.move_transform*: APPLIES: IMAGE     Use the inputmaskname mask, if provided to select pixels that moved from source to targe image,     calculate homography and move the mask pixels in the mask using the holography.  If an input mask is not provided     or a homography cannot be constructed without or without the input mask, estimate the movement of pixels using     change mask and perform linear transform to all pixels.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftWithInputAnalysis*: Perform SIFT regardless of the global change status, using an input mask from the parameters        to select the source region.
## TransformResize
Alter the dimensions of an image.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
+ *interpolation* : Interpolation is used to resize entire composite images. 'none' indicates a localized change; SIFT is used
   - Type: list
    - Source Type: image
    - Values: none-canvas expanded, bicubic, bilinear, cubic, mesh, lanczos, nearest, other
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask of the component that was moved
   - Type: file:image
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkResizeInterpolation*: Confirm that interpolation

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
+ zip.zip
### Probe Generation Rules
*image:maskgen.mask_rules.resize_transform*: APPLIES: IMAGE     Supports local resize through a perspective transform or a global resize.     Global resize with a location change and none interpolation implies a resize of the canvas without     resize of data (inverse of a crop).     'inputmaskname' is a file that identifies the region that was resized for local operations.  In this case,     this helps  identify the target object and create the appropriate perspective transform.

*video:maskgen.mask_rules.video_resize_transform*: APPLIES: VIDEO     Any shape change.  Supports frame rate changes, although discouraged at the same time.  In frame rate changes,     the resize occurs first before frame adjustment in both donor and composite cases.

### QA Questions
### Analysis Rules
*maskgen.mask_rules.resize_analysis*: APPLIES: IMAGE     Paired with resize_transform, if the shape of the image did not change, then build a homography to describe     the transformation.  Global Transform Analysis is also execute to describe the 'change size ratio' and     'change size category'.
## TransformReverse
Reverse the direction of video play.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Channels* : all includes mono and stereo, depending on available streams
   - Type: list
    - Source Type: audio
    - Values: left, right, all
### Optional Paramaters
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *Homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

*checkAudioLength_Strict*: Confirm audio duration did not change.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.reverse_transform*: 

*video:maskgen.mask_rules.reverse_transform*: 

### QA Questions
### Analysis Rules
## TransformRotate
Alter the angle of display for an image or layer.  The image dimensions may resized to accomodate the rotation.

Include as Probe Mask for []
### Mandatory Paramaters
+ *rotation* : The rotation should be provided in degrees counter-clockwise (ex. -90 for clockwise, 90 for counterclockwise)
   - Type: int[-360:360]
+ *local* : Rotate entire image or a local selection.  Use 'yes' if global but masks in QA created through the rotation are incorrect.
   - Type: yesno
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.rotate_transform*: APPLIES: IMAGE     Rotate mask in accordance to user provided image rotation.  Supports localized and full image rotaton.  In the local case,     a transform is created removing the responsibility of the user from providing an accurate rotation amount.  This assumes such a     transform can be created.  Without a transform, rotation of the mask is performed based on user inputs.

*video:maskgen.mask_rules.video_rotate_transform*: APPLIES: VIDEO     Rotate video masks in the direction of user provided rotation.  This does not support local rotation.

### QA Questions
### Analysis Rules
*maskgen.tool_set.rotateSiftAnalysis*: If the image is rotated by values other than factors of 90 degrees, use SIFT to build a homography.
## TransformScale
Change the size of an image or layer while preserving dimensions.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.scale_transform*: APPLIES: IMAGE     Apply a transform if available, else resize to target shape if shape change as occurred.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
## TransformSeamCarving
Resize an image while preserving the integrity of content.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *inputmasktype* : remove: 255  = removed pixels.  keep: 255 = kept pixels. both: [255,0,0] = remove, [0,255,0] = keep
   - Type: list
    - Values: remove, keep, both
+ *apply mask* : Use mask to apply scaling in probes/QA.
   - Type: yesno
    - Default: no
### Optional Paramaters
+ *homography* : Tune transform during composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, Map, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
+ *neighbor mask* : A 8 unsigned but image file indicating which pixels in the resulting image  had neighbors removed or added
   - Type: file:image
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *column adjuster* : An 16 unsigned bit mapping indices image file directing the change in pixels column from space to another
   - Type: file:image
+ *plugin mask* : A 8 unsigned but image file indicating which pixels in the source image were removed
   - Type: file:image
+ *inputmaskname* : RGB image. Remove = red; Keep = green; The rest is black.
   - Type: file:image
+ *row adjuster* : An 16 unsigned bit mapping indices image file directing the change in pixels row from space to another
   - Type: file:image
+ *composite homography* : Use a single transform or one per probe mask component
   - Type: list
    - Source Type: image
    - Values: Single, Multiple
### Validation Rules
*seamCarvingCheck*: 

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkEmpty*: Confirm the change mask is not empty

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.seam_transform*: 

### QA Questions
+ Seams represent neighbors of pixels removed?
### Analysis Rules
*maskgen.tool_set.seamAnalysis*: Perform SIFT regardless of the global change status.  If neighbor mask is is constructed, indicating the seams     can be calculated, then mark as not Global.
## TransformShear deprecated
Warp the shape of an object or a selection with anchored endpoints.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.shear_transform*: APPLIES: IMAGE     Apply a transform if available, else resize to target shape if shape change as occurred.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
## TransformSkew
Alter the shape or dimensions of a given selection or image along their respective vertices.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.skew_transform*: APPLIES: IMAGE     Apply a transform if available, else resize to target shape if shape change as occurred.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
## TransformWarp
Freely alter the shape or dimensions of a given selection or image.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *Warp Type* : Please include details in the general description.
   - Type: list
    - Values: Liquify, FaceLiquify, Warp, PuppetWarp, Smudge
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, Map, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5, RANSAC-6
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkEmpty*: Confirm the change mask is not empty

*checkHomography*: Confirm homography is available and does not WARP (cross).

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.warp_transform*: APPLIES: IMAGE     Applies a homography to the mask to align to the  manipulated image.  Paired with affine, warping other perspective change operations.     AT this time, input masks (inputmaskname) are not used as supporting information.  This operation does work well with flips.

### QA Questions
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
# Filter
## AddNoise
Add random variations of brightness or color information.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Noise Type* : The type of noise introduced
   - Type: list
    - Values: salt-pepper, shot, uniform, random, gaussian, periodic, other
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Is this a global change that does not need to be included in the composite mask?
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Blur
Make details unclear or less distinct.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Blur Type* : Please include details in the general description.  Smooth textures while preserving edge detail. Use Median Smoothing apply nonlinear digital filtering technique to remove noise while preserving edges
   - Type: list
    - Values: Smooth, Wavelet Denoise, Median Smoothing, Gaussian, Radial, Tilt Shift, Motion, Other, Wiener
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
+ *Laundering* : Is the intent to launder the image or a simply smoothing.
   - Type: yesno
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Is this a global change that does not need to be included in the composite mask?
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## CreativeFilter
Filter to alter visual impact of the image.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Filter Type* : Please include details in the general description.
   - Type: list
    - Values: Oil Paint, Ripple
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *XMP File Name* : XMP file recording meta-data.
   - Type: file:xmp
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Could this operation be done in steps that more accurately describes the manipulation?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## FilterConvolutionKernel
Convolve an image with a custom convolution kernel.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *convolutionkernel* : Text file containing 3x3 or 5x5 convolution kernel, separated by spaces and/or newlines.
   - Type: fileset:
### Optional Paramaters
+ *type* : Description of the desired effect of the kernel (e.g. anti-aliasing, blurring, etc.)
   - Type: list
    - Values: edge detection, anti-alias, sharpen, unsharp masking, blur, gaussian blur, other
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## FilterKeying
Remove a color from a layer of video.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## MotionBlur
Modify an image or image selection to create the illusion of motion.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Mask Correct?
+ Time Stamps Correct?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Sharpening
Enhance edge definition within an image.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Is this a global change that does not need to be included in the composite mask?
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
# Intensity
## Contrast
Shift luminance values on a histogram where higher values become higher and lower values become lower.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Curves
Shift luminance values on a histogram with an editable and flexible curve.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkLevelsVsCurves*: Confirm the Levels is appropriate choice over curves given the detected changes.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Exposure
Shift all luminance values on a histogram to higher or lower values.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Direction* : Shift midtone luminance in the desired direction
   - Type: list
    - Values: increase, decrease, match to video frames
+ *Start Time* : Start frane of the image clip
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End frame of the image clip
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Levels
Adjust brightness, contrast, and tonal range by specifying the location of complete black, complete white, and midtones in a histogram.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip ( frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Luminosity
Alter the values of a luminance histogram.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Normalization
Normalize using histograms.

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *selection type* : Gamma Correction, if applicable
   - Type: list
    - Values: auto, manual, NA
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gamma* : Gamma Correction, if applicable
   - Type: float[0:10]
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
# AdditionalEffect
## AddTransitions
Add a series of frame modifications that create a visual blend between two pieces of media

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## CameraMovement
Make it appear is if the camera is moving or not moving

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Camera Effect* : 
   - Type: list
    - Values: Add, Remove
+ *Approach* : Cropping for Drone Shake or Other
   - Type: list
    - Values: Crop, Other
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Ok?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Fading
Decrease opacity of an image or a layer.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Ok?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## Mosaic
Create a mosaic pattern and then reassemble

Include as Probe Mask for [video]
### Mandatory Paramaters
+ *Vertical Block Number* : Number of rectangular regions created in vertical direction
   - Type: int[1:400000]
+ *Sharp Colors* : Sharp colors
   - Type: yesno
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
+ *Horizontal Block Number* : Number of rectangular regions created in horizontal direction
   - Type: int[1:400000]
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkDuration*: Confirm number of frames has not changed.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Ok?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## ReduceInterlaceFlicker
Smooth the artifacts resultant from interlacing.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Ok?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## WarpStabilize
Distort and/or crop video layers in order to remove camera shake

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *boarders* : Stabilize Only - Displays the entire frame, including the moving edges. Stabilize, Crop = Crops the moving edges without scaling. Stabilize, Crop, Auto-scale = Crops the moving edges and scales up the image to refill the frame. Stabilize, Synthesize Edges =  Fills in the blank space created by the moving edges with content from frames earlier and later in time.
   - Type: list
    - Values: stablize only, stablize crop, crop auto-scale, synthesize edges
+ *result* : Smooth Motion = smoothed at a variable rate, preserving camera motion. No Motion = All motion has been removed in order to make a shot appear as though it was attached to a surface.
   - Type: list
    - Values: smooth motion, no motion
+ *method* : Position = Stabilization is based on position data only and is the most basic way footage can be stabilized. Position, Scale and Rotation = Stabilization is based on manipulations to the frame that change the size, orientation, and location. Perspective  = Uses a type of stabilization in which the entire frame is effectively corner-pinned. If there are not enough areas to track, Warp Stabilizer chooses the previous type (Position, Scale, Rotation). Subspace Warp = Attempts to warp various parts of the frame differently to stabilize the entire frame. If there are not enough areas to track, Warp Stabilizer choose the previous type (Perspective).
   - Type: list
    - Values: position, position,scale and rotation, perspective, subspace warp, checkEmpty
### Optional Paramaters
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkLocalWarn*: Confirm the operation is a 'blue link' given the operation is not global.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Ok?
### Analysis Rules
# PostProcessing
## DuplicateFrameDrop
Remove any frames that are near duplicates of the previous frame.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Threshold* : Threshold to determine how alike the frames have to be lower threshold more alike
   - Type: int[0:100]
### Optional Paramaters
### Validation Rules
*checkLengthSmaller*: Confirm resulting video has less frames that source.

*checkEmpty*: Confirm the change mask is not empty

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Correct?
### Analysis Rules
## PostProcessingSizeUpDownOrgExif
Alter the metadata in order that when the image is displayed it changes the presentation orientation.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkMetaDate*: Confirm the the EXIF date formats did  not change.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## Recapture
Recapture an image through a digital photo of a picture or screen shot.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Output Device* : Type of image display
   - Type: list
    - Values: Matte Paper, Gloss Paper, Flat Paper, LCD, LED, CRT, Screen Shot, Other Device
+ *Capture Printer ID* : ID of printer used to compose the image
   - Type: text
### Optional Paramaters
+ *Position Mapping* : Maps the bounding regions of each image
   - Type: boxpair
+ *Capture Camera ID* : ID of camera used to capture image if not screen shot
   - Type: text
+ *Capture Printer Type* : Base type of printer used to compose the image
   - Type: list
    - Values: Inkjet, Laser, Analog, Other
+ *Capture Distance* : Distance in centimeters from camera to print
   - Type: int[0:100000]
+ *Magnification* : Magnification = (hi/ho) = -(di/do), where hi = image height, ho = object height, and di and do = image and object distance
   - Type: float[0:100000]
+ *Antiforensic Measures* : Anything that was done to obscure the recapture
   - Type: text
+ *Capture Printer Make/Model* : The brand and make of the Printer used to compose the image
   - Type: text
+ *Resolution* : Resolution of output device e.g. 300 DPI of print or PPI of screen. https://www.noteloop.com/kit/display/pixel-density/
   - Type: text
### Validation Rules
*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.recapture_transform*: Use position mapping if available, otherwise try to create and use a homography.     Position mapping is a box and rotation.  Composite embeds mask at the crop position and then rotates mask.     Donor generation, crops and rotates (inverse) mask.

### QA Questions
### Analysis Rules
*maskgen.tool_set.siftAnalysis*: Use SIFT to build a homography for transform type changes that manipulated prior masks for probes.
# TimeAlteration
## TimeAlterationDifferenceEffect
Calculate the color difference between two layers as a useful aid in color correction

Include as Probe Mask for []
### Mandatory Paramaters
+ *Target Layer* : Target layer number to be compared to the effect layer
   - Type: int[0:100]
+ *Alpha Channel* : Specifies how the alpha channel is calculated.
   - Type: list
    - Values: Original, Target, Blend, Max, Full On, Lightness Of Result, Max Of Result, Alpha Difference, Alpha Difference Only
+ *Time Offset* : The relative time in the comparison layer, in seconds, where the layers are compared
   - Type: float[0:1000000]
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## TimeAlterationDisplacementEffect
Distorts the image by shifting pixels across time.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Max Displacement Time* : Sets the maximum time, in seconds, from which pixels are replaced, before or after the current time.
   - Type: int[0:100000000]
+ *Time Resolution* : Sets the number of frames per second in which to replace pixels
   - Type: float[0:10000000]
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## TimeAlterationEcho
Duplicate video frames and replay them at a delay to create a trail.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Starting Intensities* : The opacity of the first image in the echo sequence
   - Type: int[0:100000]
+ *Operator* : The operation used. For example: Add,Maximum,Minimum,Screen,Composite In Back,Composite In Front and Blend
   - Type: string
+ *Number of Echos* : The number of echoes. For example, if the value is 2, the result is a combination of three frames: the current time, the current time + Echo Time, and the current time + (2 * Echo Time).
   - Type: int[0:1000000]
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
+ *Echo Time* : The time, in seconds, between echoes. Negative values create echoes from previous frames; positive values create echoes from upcoming frames.
   - Type: float[-100:100]
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## TimeAlterationFrameRate
Lock a layer to a specific frame rate. May change the number of frames in the video, but not necessarily the length of the video

Include as Probe Mask for []
### Mandatory Paramaters
+ *Frame Rate* : Frames per second
   - Type: float[0:1000000]
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
## TimeAlterationWarp
Alter frame rate and frame blending to change playback rate. Vector Detail is a integer that determines how many motion vectors are used during interpolation. Methods include 'Whole Frames', 'Frame Mix' and 'Pixel Motion'. Adjust Time By controls is a percentage of reduction.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Vector Detail* : Determine how many motion vectors are used during interpolation. The more vectors used, the longer the rendering time. A value of 100 produces one vector per pixel.
   - Type: int[0:100]
+ *Method* : The Method setting determines how interpolated frames are generated.
   - Type: list
    - Values: Whole Frames, Frame Mix, Pixel Motion
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *Weighting* : Weighting red, green, and blue channels in calculations used to analyze the image.  Suggest comma-separated values for RGB.
   - Type: string
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Adjust Time By* : Choose Speed to specify a time adjustment as a percentage
   - Type: float[0:100]
+ *Smoothing* : These controls affect the sharpness of the image.
   - Type: list
    - Values: Build From One Image, Correct Luminance Changes, Filtering
### Validation Rules
*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.time_warp_audio*: 

*video:maskgen.mask_rules.time_warp_frames*: 

### QA Questions
### Analysis Rules
# Output
## MediaStacking
Produce a single image from stacking frames or images in a zip.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
+ *End Time* : End frame
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *XMP File Name* : XMP file provided when exporting from a raw image.
   - Type: file:xmp
+ *Start Time* : Start frame
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Validation Rules
*rotationCheck*: 

### Allowed Transitions
+ video.image
+ zip.image
### Probe Generation Rules
*video:maskgen.mask_rules.median_stacking*: APPLIES: VIDEO     Composite generation extracts a single mask from the given Frame Time.     Donor generation distributes the mask over all contributing frames.

*video_preprocess:maskgen.mask_rules.median_stacking_preprocess*: NA

### QA Questions
### Analysis Rules
## OutputAVI
Export the image in the AVI format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Video Rotated* : Enter yes if the donor is rotated during the paste operation
   - Type: yesno
### Optional Paramaters
+ *pixel aspect* : .
   - Type: list
    - Source Type: video
    - Values: Square Pixels (1.0), D1/DV NTSC (0.9091), D1/DV NTSC Widescreen 16:9 (1.2121), D1/DV PAL (1.0940), D1/DV PAL Widescreen 16:9 (1.4587), Anamorphic 2:1 (2.0), HD Anamorphic 1080 (1.333), DVCPRO HD (1.5), Custom
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkResolution*: Confirm the resolution, width and height of video did not change.

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ video.video
+ image.video
+ zip.video
### Probe Generation Rules
*image:maskgen.mask_rules.image_to_video*: APPLIES: VIDEO     Using the meta data from the video, take composite mask and repeat as if it represented the mask for every single frame     of the video.  In the donor case, pick one a sample mask from the video donor mask to use as the new donor image mask.

*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*zip:maskgen.mask_rules.echo_transform*: Assumes frame rate has not changed.  The composite and donor mask are assumed to not change due to an associated     manipulation operation.

### QA Questions
### Analysis Rules
## OutputAudioCompressed
Export the audio in the compressed format (mp3, m4a, wma, etc).

Include as Probe Mask for []
### Mandatory Paramaters
+ *Audio Sequence File* : CSV file where column one is time fractional milliseconds, column two is zip file entry name (a WAV file).
   - Type: file:csv
    - Source Type: zip
### Optional Paramaters
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkAudioOutputType*: Confirm resulting file is an audio file.

*checkAudioLength_Loose*: Confirm audio duration did not change (allows for some rounding errors).

### Allowed Transitions
+ audio.audio
+ video.audio
+ zip.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.sample_rate_change_transform*: Applies: AUDIO     Sample Rate change results in changing the frame numbers associated manipulation times in temporal segments.

*video:maskgen.mask_rules.sample_rate_change_transform*: Applies: AUDIO     Sample Rate change results in changing the frame numbers associated manipulation times in temporal segments.

### QA Questions
### Analysis Rules
## OutputAudioPCM
Export the stream in the PCM format (wave, aif, etc.).

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
+ *Audio Sequence File* : CSV file where column one is time fractional milliseconds, column two is zip file entry name (a WAV file).
   - Type: file:csv
    - Source Type: zip
+ *sample rate* : Sample rate of file contents
   - Type: int[1:1000000]
    - Source Type: zip
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkAudioOutputType*: Confirm resulting file is an audio file.

*checkAudioLength_Loose*: Confirm audio duration did not change (allows for some rounding errors).

### Allowed Transitions
+ audio.audio
+ video.audio
+ zip.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.sample_rate_change_transform*: Applies: AUDIO     Sample Rate change results in changing the frame numbers associated manipulation times in temporal segments.

*video:maskgen.mask_rules.sample_rate_change_transform*: Applies: AUDIO     Sample Rate change results in changing the frame numbers associated manipulation times in temporal segments.

*zip:maskgen.mask_rules.audio_selection*: For use of zip to audio.     Use Audio Positions to build donor.     Use Audio Positions to substract out masks.     This transform function is incomplete!

### QA Questions
### Analysis Rules
## OutputBmp
Export the image in the bmp format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
+ *XMP File Name* : XMP file provided when exporting from a raw image.
   - Type: file:xmp
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
### Analysis Rules
## OutputCopy
Export the image in the in the same format. Used to branch off a final image  node

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFileTypeUnchanged*: Confirm file type did not change.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.copy_transform*: APPLIES: VIDEO, AUDIO, IMAGE     No change to composite or donor mask.     This transform basiicaly states that the edge's operation does not alter a prior edges mask.

### QA Questions
+ Confirm that no other manipulation was done other than creating a duplicate of the previous file
### Analysis Rules
## OutputDng
Export the image in the DNG format.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## OutputFromZip
Export the image from zip.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
### Allowed Transitions
+ collection.image
### Probe Generation Rules
*image:maskgen.mask_rules.copy_transform*: APPLIES: VIDEO, AUDIO, IMAGE     No change to composite or donor mask.     This transform basiicaly states that the edge's operation does not alter a prior edges mask.

### QA Questions
### Analysis Rules
## OutputHEIC
Export the image in the HEIC format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Quality* : Compression quality- higher numbers are better quality, with 100 being lossless.
   - Type: int[0:100]
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
### Validation Rules
*checkHEICOutputType*: Confirm resulting media is a NEIC or NEIF file.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
+ Confirm that the file was transformed into a HEIC
### Analysis Rules
## OutputJp2
Export the image in the jp2 format.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
### Analysis Rules
## OutputJpg
Export the image in the jpeg format.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
+ *XMP File Name* : XMP file provided when exporting from a raw image.
   - Type: file:xmp
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkJpgOutputType*: Confirm resulting media is a JPG (or JPEG) file.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
### Analysis Rules
## OutputM4
Export the image to lossless format.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkOutputTypeM4*: Confirm resulting media is a M4A or M4V file.

*checkAudioLength_Strict*: Confirm audio duration did not change.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
## OutputMOV
Export the image in the MOV format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *pixel aspect* : .
   - Type: list
    - Source Type: video
    - Values: Square Pixels (1.0), D1/DV NTSC (0.9091), D1/DV NTSC Widescreen 16:9 (1.2121), D1/DV PAL (1.0940), D1/DV PAL Widescreen 16:9 (1.4587), Anamorphic 2:1 (2.0), HD Anamorphic 1080 (1.333), DVCPRO HD (1.5), Custom
### Optional Paramaters
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ video.video
+ zip.video
### Probe Generation Rules
*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
## OutputMP4
Export the image in the MP4 format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *pixel aspect* : .
   - Type: list
    - Source Type: video
    - Values: Square Pixels (1.0), D1/DV NTSC (0.9091), D1/DV NTSC Widescreen 16:9 (1.2121), D1/DV PAL (1.0940), D1/DV PAL Widescreen 16:9 (1.4587), Anamorphic 2:1 (2.0), HD Anamorphic 1080 (1.333), DVCPRO HD (1.5), Custom
### Optional Paramaters
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkMp4OutputType*: Confirm resulting media is a mp4, mpeg or mpg file.

*checkResolution*: Confirm the resolution, width and height of video did not change.

### Allowed Transitions
+ video.video
+ image.video
### Probe Generation Rules
*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
## OutputMosaic
Stitching video frames together to form a comprehensive view of the scene.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Validation Rules
*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ video.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## OutputNEIF
Export the image in the neif format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
+ Confirm that the file was transformed into a NEIF
### Analysis Rules
## OutputNITF
Export the image in the NITF format.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkOutputTypeNITF*: Confirm resulting media is a NITF file.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
### Analysis Rules
## OutputPDF
Export the image in the PDF format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *resolution* : DPI
   - Type: int[0:10000000]
### Optional Paramaters
### Validation Rules
*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
### Analysis Rules
## OutputPng
Export the image in the png format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
+ *XMP File Name* : XMP file provided when exporting from a raw image.
   - Type: file:xmp
### Validation Rules
*checkSizeAndExifPNG*: Confirm conversion to PNG rotated the image according to the EXIF and did not change the size of the image     outside acceptable bounds for lens distortion.

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
+ Confirm that the file was transformed into a png
+ The file was compressed in a lossless fashion
### Analysis Rules
## OutputPng::BitDepth
Export the image in the png format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Depth* : Bit Depth Used
   - Type: list
    - Values: 8, 12, 16, 24, 32
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
+ *XMP File Name* : XMP file provided when exporting from a raw image.
   - Type: file:xmp
### Validation Rules
*checkSizeAndExifPNG*: Confirm conversion to PNG rotated the image according to the EXIF and did not change the size of the image     outside acceptable bounds for lens distortion.

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
+ Confirm that the file was transformed into a png
+ The file was compressed in a lossless fashion
### Analysis Rules
## OutputTif
Export the image in the tif format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Image Rotated* : Did the software rotate the image when removing the EXIF Orientation?
   - Type: yesno
### Optional Paramaters
+ *XMP File Name* : XMP file provided when exporting from a raw image.
   - Type: file:xmp
### Validation Rules
*checkSizeAndExif*: Confirm the dimensions of the image or video did not change except for rotation in accordance to the Orientation meta-data.

*rotationCheck*: 

*checkTifOutputType*: Confirm resulting media is a TIF or TIFF file.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.output_transform*: APPLIES: VIDEO, AUDIO, IMAGE     Applies exif related rotations to align an image to the shape of the resulting image.     Also handes resize, resampling and, for streaming media, sample and frame rate changes.

### QA Questions
### Analysis Rules
## OutputXVID
Export the image in the xvid format.

Include as Probe Mask for []
### Mandatory Paramaters
+ *pixel aspect* : .
   - Type: list
    - Source Type: video
    - Default: Unchanged
    - Values: Square Pixels (1.0), D1/DV NTSC (0.9091), D1/DV NTSC Widescreen 16:9 (1.2121), D1/DV PAL (1.0940), D1/DV PAL Widescreen 16:9 (1.4587), Anamorphic 2:1 (2.0), HD Anamorphic 1080 (1.333), DVCPRO HD (1.5), Custom, Unchanged
### Optional Paramaters
### Validation Rules
*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkOutputType*: Confirm the resulting media type (for an Output operation) matches the expected operaiton type as indicated by the name.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*video:maskgen.mask_rules.output_video_change*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
### Analysis Rules
## OutputZIP
Output a Audio to Zip file of contiguous audio files OR Video a sequence contiguous images(frames)

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *End Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Crop File* : CSV file describing the x,y coordinates of crop for each frame
   - Type: file:txt
### Validation Rules
### Allowed Transitions
+ zip.zip
+ audio.zip
+ video.zip
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
# Audio
## AddAudioSample
Adding a donor audio stream to a video

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
+ *synchronization* : If additional track alignment changes occurred with the addition.
   - Type: list
    - Values: none, spacing, compressing
+ *Direct from PC* : Is audio recorded into the video from PC rather than a separate audio file?
   - Type: yesno
+ *voice* : Is the sample a voice.
   - Type: yesno
+ *add type* : Replacing or overlaying.
   - Type: list
    - Values: replace, overlay, insert
### Optional Paramaters
+ *filter type* : 
   - Type: list
    - Values: EQ Match, Other
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
### Validation Rules
*[DONOR]:checkForDonorAudio*: Confirm audio donor edge exists.

*checkOverlay*: Confirm overlay or replace is selected 'add type'.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkAudioChannels*: Confirm resulting media file has an audio channel.

*checkSampleRate*: Confirm sample rate did not change.

*checkForVideoRetainment*: Confirm video channel is retained in the resulting media file.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkChannelLoss*: Confirm number of streams did not decrease.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkOverlay*: Confirm overlay or replace is selected 'add type'.

*checkAudioOnly*: Confirm number of video frames has not changed.

*checkAudioAdd*: Confirm inserted audio increased the length of the audio channel.

*[DONOR]:checkAudioLengthDonor*: Confirm the Audio Length donor matches the length of frames added or replaced.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.add_audio*: If the 'add type' is insert and the function is processing a composite mask, insert time at the intersecting intervals     with this edge's mask.     If the 'add type' is not insert and the function is processing a composite mask, remove portions of mask segments     that intersect with this edge's masks.     If the 'add type' is insert the function is processing a donor mask, remove portions of the mask segements that intersect     with this edge's masks.     If the 'add type' is not insert and the function is processing a donor mask, insert time at the intersecting intervals     with this edge's mask.

*video:maskgen.mask_rules.add_audio*: If the 'add type' is insert and the function is processing a composite mask, insert time at the intersecting intervals     with this edge's mask.     If the 'add type' is not insert and the function is processing a composite mask, remove portions of mask segments     that intersect with this edge's masks.     If the 'add type' is insert the function is processing a donor mask, remove portions of the mask segements that intersect     with this edge's masks.     If the 'add type' is not insert and the function is processing a donor mask, insert time at the intersecting intervals     with this edge's mask.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioAmplify
Amplify Audio Signal

Include as Probe Mask for []
### Mandatory Paramaters
+ *PreGain* : How much to raise or lower volume
   - Type: int[-100000:100000]
+ *Right Pan* : Percentage Decrease/Increase from -100 to 100
   - Type: int[-100:100]
+ *Fading* : Fading effect
   - Type: list
    - Values: fade in, fade out, both, cross, none
+ *Left Pan* : Percentage Decrease/Increase from -100 to 100
   - Type: int[-100:100]
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
### Optional Paramaters
+ *Final Fade Level* : Final fade level in Db, if applicable
   - Type: int[-100000:100000]
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkDurationAudio*: Confirm Audo duration did not change.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkSampleRate*: Confirm sample rate did not change.

*checkAudioOnly*: Confirm number of video frames has not changed.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

*checkAudioLength_Strict*: Confirm audio duration did not change.

### Allowed Transitions
+ audio.audio
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioCompress
Compress Audio Signal

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Ratio* : How much to curb the output, in decibels (2:1) for example 2.0
   - Type: float[0:100]
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
+ *Threshold* : Decibel Range
   - Type: int[-240:240]
+ *Attack* : Length of time to react to reducing gain 
   - Type: float[0:100]
+ *Gain* : How much to raise volume
   - Type: int[0:100000]
+ *Release* : Length of time to return to normal gain reduction
   - Type: float[0:100]
### Optional Paramaters
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkDurationAudio*: Confirm Audo duration did not change.

*checkSampleRate*: Confirm sample rate did not change.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkAudioLength_Strict*: Confirm audio duration did not change.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ audio.audio
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioCopyAdd
Copy audio stream(s) from one section of video to another (or one stream to the other)

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Copy Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
+ *Insertion Time* : Replace insertion time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *Copy Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *add type* : Replacing or overlaying.
   - Type: list
    - Values: replace, overlay, insert
+ *voice* : Is the sample a voice.
   - Type: yesno
+ *Insertion Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Optional Paramaters
+ *Copy End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
### Validation Rules
*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkOverlay*: Confirm overlay or replace is selected 'add type'.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkFileTypeChange*: Confirm the file type did not change.

*checkAddFrameTime*: Confirm that the start or insertion time is the detect manipulation start time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkSampleRate*: Confirm sample rate did not change.

*checkAudioOnly*: Confirm number of video frames has not changed.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.copy_add_audio*: Use the audio segment identified by copy start and end time as the to overwrite intersecting     parts of the composite mask.

*video:maskgen.mask_rules.copy_add_audio*: Use the audio segment identified by copy start and end time as the to overwrite intersecting     parts of the composite mask.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioEffect
Apply an effect to audio stream

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Effects Type* : Type of filter
   - Type: list
    - Values: Flange, Modulation, Pitch, Distortion, Custom
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
### Optional Paramaters
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
+ *Sample Size* : Bits
   - Type: int[2:64]
+ *Sample Rate* : Hertz
   - Type: int[0:10000000]
+ *Anti Aliasing* : Percent
   - Type: int[1:100]
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *Delay* : MS
   - Type: int[0:10000000]
+ *Rate* : Hertz
   - Type: int[0:10000000]
+ *Frequency* : Frequency
   - Type: int[0:10000000]
+ *Tool Name* : Specific Name of Plugin for Software
   - Type: text
+ *Distortion Type* : Distortion Type
   - Type: list
    - Values: Harmonic, Phase, Frequency Response, Amplitude, Other
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkSampleRate*: Confirm sample rate did not change.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkDurationAudio*: Confirm Audo duration did not change.

*checkAudioLength_Strict*: Confirm audio duration did not change.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioFilter
Apply filter to audio stream

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Filter Type* : Type of filter
   - Type: list
    - Values: high pass, low pass, EQ, FFT, Adaptive, Spectral Subtraction, Frequency Stretch, Ratio, Non Linearity, Time Stretch
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
+ *Smoothing* : If noise smoothing algorithms were applied
   - Type: yesno
### Optional Paramaters
+ *Spectral Decay Rate* : Percentage of frequencies processed for noise below analyzed noise floor
   - Type: int[0:100]
+ *Ratio* : Percentage of frequencies processed for noise below analyzed noise floor
   - Type: float[0:1000000]
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *Frequency* : Frequency
   - Type: int[0:10000000]
+ *Noise Reduction* : Percentage of Noise Reduction
   - Type: int[0:100]
+ *Amplitude Reduction* : In Decibals
   - Type: int[0:40]
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkSampleRate*: Confirm sample rate did not change.

*checkDurationAudio*: Confirm Audo duration did not change.

*checkAudioOnly*: Confirm number of video frames has not changed.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

*checkAudioLength_Strict*: Confirm audio duration did not change.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioReverb
Add Reverb or Dampen an Audio Signal to alter the perception of the room size.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Room Size Change* : How much change is being applied to the original signal
   - Type: list
    - Values: small, medium, large
+ *Damping Filters* : Damping filters applied.
   - Type: list
    - Values: high, low, both, none
+ *Damping* : Damping rather than increasing reverb.
   - Type: yesno
+ *Subtype* : Damping filters applied.
   - Type: list
    - Default: reverb
    - Values: delay, reverb, echo_transform
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
### Optional Paramaters
+ *Pre-Delay* : Milliseconds recording difference between signal and reverb
   - Type: int[0:1000000]
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
+ *Reverb Time* : Milliseconds based on RT60 value.
   - Type: int[-1000000:1000000]
### Validation Rules
*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkSampleRate*: Confirm sample rate did not change.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkDurationAudio*: Confirm Audo duration did not change.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkAudioLength_Strict*: Confirm audio duration did not change.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ audio.audio
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## AudioSample
Extract audio stream(s) from a video

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
+ *Copy Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Optional Paramaters
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
### Validation Rules
*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkSampleRate*: Confirm sample rate did not change.

### Allowed Transitions
+ video.audio
+ audio.audio
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## DeleteAudioSample
Remove a portion or all of an audio stream from a video

Include as Probe Mask for []
### Mandatory Paramaters
+ *Type* : Type of deletion
   - Type: list
    - Values: splice, interpolation, other
+ *Start Time* : Start time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
    - Default: 00:00:00
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Optional Paramaters
+ *End Time* : End time of the audio clip (HH:MI:SS.micro or frame number)
   - Type: time
    - Create new Mask on Update
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkAudioTimeFormat*: Confirm the format of time stamp entries.

*checkSampleRate*: Confirm sample rate did not change.

*checkAudioOnly*: Confirm number of video frames has not changed.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.delete_audio*: APPLIES: AUDIO

*video:maskgen.mask_rules.delete_audio*: APPLIES: AUDIO

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## ReplaceAudioSample
Use the audio stream from a donor to replace the audio stream of the file.

Include as Probe Mask for []
### Mandatory Paramaters
+ *filter type* : Replacing or overlaying.
   - Type: list
    - Values: EQ Match, Other
+ *voice* : Is the sample a voice.
   - Type: yesno
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Optional Paramaters
### Validation Rules
*[DONOR]:checkForDonor*: Confirm donor edge exists.

*checkFileTypeChange*: Confirm the file type did not change.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

*[DONOR]:checkAudioLengthDonor*: Confirm the Audio Length donor matches the length of frames added or replaced.

### Allowed Transitions
+ video.video
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.replace_audio*: APPLIES: AUDIO     Replace the composite mask with this edge's mask.     At this moment, do nothing with the donor mask. Although, dropping the donor mask may be correct.

*video:maskgen.mask_rules.replace_audio*: APPLIES: AUDIO     Replace the composite mask with this edge's mask.     At this moment, do nothing with the donor mask. Although, dropping the donor mask may be correct.

### QA Questions
+ Time Stamps Ok?
### Analysis Rules
## TransformSampleRate
Use the audio stream from a donor to replace the audio stream of the file.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Stream* : all includes mono and stereo, depending on available streams
   - Type: list
    - Values: left, right, all
### Optional Paramaters
### Validation Rules
*checkFrameRateDidChange*: Confirm frame rate changed.

### Allowed Transitions
+ audio.audio
### Probe Generation Rules
*audio:maskgen.mask_rules.sample_rate_change_transform*: Applies: AUDIO     Sample Rate change results in changing the frame numbers associated manipulation times in temporal segments.

### QA Questions
### Analysis Rules
# Paste
## ContentAwareFill
Synthesize nearby content for seamless blending with the surrounding content.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Fill Method* : Does the effect work on a specific frame (intra), or across multiple frames? (inter)
   - Type: list
    - Values: Intraframe, Interframe
+ *purpose* : Purpose: remove an object, enlarge (extend), or healing using sampled pixels.
   - Type: list
    - Values: remove, enlarge, heal, other
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.ca_fill_transform*: APPLIES: IMAGE      Erase mask pixels that intersect the change mask if the purpose is remove, indicating      that the change represented by those mask pixels is no longer visible.      Please note that the fill operation has its own mask and probe, thus algorithm change detection      still has information regarding to change to the 'removed' pixels.  A 'remove' is an erasure      of prior operation manipulations, making them unrecognizable.      In the donor case, pixels are also dropped as they are no longer 'used' from the donor ('removed').

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Verify that content aware fill was used and not paste sampled or content aware scale.
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## ContentAwareMove
Purpose: Move pixels and heal area where they came from and edges of new location.  The input mask describes the initial location.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *inputmaskname* : An image file containing a mask describing the area moved.
   - Type: file:image
### Optional Paramaters
+ *homography max matches* : Maximum number of matched feature points used to compute the homography.
   - Type: int[20:10000]
+ *homography* : Tune transform creation for composite mask generation
   - Type: list
    - Source Type: image
    - Values: None, All, LMEDS, RANSAC-3, RANSAC-4, RANSAC-5
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.move_transform*: APPLIES: IMAGE     Use the inputmaskname mask, if provided to select pixels that moved from source to targe image,     calculate homography and move the mask pixels in the mask using the holography.  If an input mask is not provided     or a homography cannot be constructed without or without the input mask, estimate the movement of pixels using     change mask and perform linear transform to all pixels.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Verify that content aware move was used and not paste sampled or content aware scale.
### Analysis Rules
*maskgen.tool_set.forcedSiftAnalysis*: Perform SIFT regardless of the global change status.
## CopyPaste
Copy & Paste a series of frames within the same video

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Number of Frames* : Numbers of frames copy/pasted
   - Type: int[0:1000000]
+ *add type* : Insert slides frames.  Replacing or overlaying keeps numbers of frames in video the same.
   - Type: list
    - Values: replace, overlay, insert
+ *Dest Paste Time* : Position in the video where the copied frames were pasted(HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Select Start Time* : Start time of the copied video clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *videoinputmaskname* : A video file with a transparency highlighting the sampled areas of the video
   - Type: file:video
    - Source Type: video
### Validation Rules
*checkLengthSameOrBigger*: Confirm media file has the same or increased number of frames.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*video:maskgen.mask_rules.copy_paste_frames*: 

### QA Questions
+ Time Stamps Correct?
### Analysis Rules
## CutPaste
Cut & Paste a series of frames within the same video

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *Number of Frames* : Numbers of frames cut/pasted
   - Type: int[0:1000000]
+ *Dest Paste Time* : Position in the video where the cut frames were pasted(HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *Select Start Time* : Start time of the cut video clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *videoinputmaskname* : A video file with a transparency highlighting the sampled areas of the video
   - Type: file:video
    - Source Type: video
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Time Stamps Correct?
### Analysis Rules
## GANFill
Use a GAN to fill in a selected region of an image.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *samplemaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *purpose* : Purpose: remove an object, enlarge (extend), or healing using sampled pixels.
   - Type: list
    - Values: remove, enlarge, heal, other
### Validation Rules
*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## PasteFrames
Adding a series of frames from a video clip

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *add type* : Replacement does not have to be the same size.
   - Type: list
    - Values: insert, replace
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *videoinputmaskname* : A video file with a transparency highlighting the sampled areas of the video
   - Type: file:video
    - Source Type: video
+ *kernel* : Size of kernel to remove noise
   - Type: int[1:27]
    - Default: 3
### Validation Rules
*[DONOR]:checkForDonor*: Confirm donor edge exists.

*checkPasteFrameLength*: Confirm number of frames increased by donor frames size (as indicated by donor parameters).

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*[DONOR]:checkDonorTimesMatch*: Confirm the number of manipulated frames match the donor.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.paste_add_audio_frames*: 

*video:maskgen.mask_rules.paste_add_frames*: 

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Time Stamps Correct?
### Analysis Rules
## PasteImageSpliceToFrames
Paste into a series of frames an image spliced from another image.  The other image is a Donor image.  The donor image should first be prepared by using an alpha channel to exclude the unselected regions of the image.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *purpose* : Purpose: remove an object, add an object.
   - Type: list
    - Values: remove, add
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *motion mapping* : Is motion mapping used?
   - Type: yesno
+ *subject* : Subject catgeory pasted to image
   - Type: list
    - Values: people, face, gan-face, natural object, gan-natural object, man-made object, gan-made object, large man-made object, large gan-made object, landscape, gan-landscape, other
### Optional Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *videoinputmaskname* : A video file with a transparency highlighting the sampled areas of the video
   - Type: file:video
    - Source Type: video
+ *End Time* : Stop time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkForDonorWithRegion*: Confirm donor mask exists and is selected by a SelectRegion

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Does the mask reflect the image pasted into one frame?
+ Inspected the change masks on the link.
### Analysis Rules
## PasteOverlay
Paste a series of green screen frames from a donor video clip, overlaying frames.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *motion mapping* : Is motion mapping used?
   - Type: yesno
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
+ *purpose* : Purpose: remove an object or add an object.
   - Type: list
    - Values: remove, add
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *videoinputmaskname* : A video file with a transparency highlighting the sampled areas of the video
   - Type: file:video
    - Source Type: video
+ *End Time* : Stop time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Validation Rules
*[DONOR]:checkForDonor*: Confirm donor edge exists.

*checkForSelectFrames*: Confirm operation SelectRegionFromFrames exists on donor path.

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkFrameTimeAlignment*: Confirm that the user provided times match detected modification times.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Time Stamps Correct?
### Analysis Rules
## PasteSampled
Use sampled imagery from a given area to fill an area on the canvas.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *purpose* : Purpose: remove an object, clone (combination of add and remove), healing using sampled pixels, layer stacking to create new paste
   - Type: list
    - Values: remove, clone, heal, stacking
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
### Optional Paramaters
+ *Blend Mode* : 
   - Type: list
    - Values: Minimum, Maximum, Mean, Median, Other
+ *kernel* : Noise regions less than or equal to the size of the width and height of the given kernal are removed
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: 3
    - Values: 3, 5, 7, 9
+ *videoinputmaskname* : A video file with a transparency highlighting the sampled areas of the video
   - Type: file:video
    - Source Type: video
+ *aggregate* : The function to summarize the differences of frame pixels across dimension RGB during mask creation.
   - Type: list
    - Source Type: video
    - Create new Mask on Update
    - Default: max
    - Values: max, sum
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Source Type: video
    - Create new Mask on Update
+ *gain* : Fixed variation of pixel difference used as a tolerance to create masks
   - Type: int[-20:20]:slider
    - Source Type: video
    - Create new Mask on Update
+ *maximum threshold* : Permitted variance in the differences of frame pixels across dimension RGB during mask creation.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 255
+ *inputmaskname* : An image file with a transparency highlighting the sampled areas of the image.
   - Type: file:image
    - Source Type: image
+ *minimum threshold* : Permitted variance in the difference of frame pixels during mask creation before difference is included in the mask,.
   - Type: int[0:255]:slider
    - Source Type: video
    - Create new Mask on Update
    - Default: 0
+ *morphology order* : Order of morphology operations in mask generation- open: removes noise, close: fills gaps.
   - Type: list
    - Create new Mask on Update
    - Default: open:close
    - Values: open:close, close:open
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkLengthSame*: Confirm the length of video did not change, returning a WARNING if not.

*checkFileTypeChange*: Confirm the file type did not change.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*sampledInputMask*: 

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkVideoMasks*: Confirm that video masks exist.

*checkUncompressed*: Confirm the source media file is uncompressed.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.paste_sampled_transform*: APPLIES: IMAGE      Erase mask pixels that intersect the change mask if the purpose is remove, indicating      that the change represented by those mask pixels is no longer visible.      Please note that the paste sample operation has its own mask and probe, thus algorithm change detection      still has information regarding to change to the 'removed' pixels.  A 'remove' is an erasure      of prior operation manipulations, making them unrecognizable.      In the donor case, pixels are also dropped as they are no longer 'used' from the donor ('removed').

*audio:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

*video:maskgen.mask_rules.warp_output_transform*: Applies: VIDEO, AUDIO     Frame rate changes involve minimally changing the frame number associated with frame times in the temporal segments.     At this time, frame masks may be added at regular intervals for increasing frame rate or dropped at regular intervals for     decreasing the frame rate. Interpolation of this frames is not performed. The donor mask adjustments is inverse of composite mask     adjustments.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ If this operation would better be represented by a paste splice, please make the appropriate changes
+ Input masks are only supported for clone type paste sampled. The clone input mask should be a rough but accurate selection of the donor pixels
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## PasteSplice
Paste a region of an image spliced from another image.  The other image is a Donor image.  The donor image should first be prepared by using an alpha channel to exclude the unselected regions of the image.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
+ *donor resized* : Enter yes if the donor is resized during the paste operation
   - Type: yesno
+ *donor cropped* : Enter yes if the donor is cropped the paste operation. Ideally, crop should occur as a SelectRegion operation just prior to donation.
   - Type: yesno
+ *donor rotated* : Enter yes if the donor is rotated during the paste operation
   - Type: yesno
+ *purpose* : Purpose: remove an object, add an object.
   - Type: list
    - Values: remove, add, replace, blend
+ *donor flipped* : Enter yes if the donor is flipped the paste operation.
   - Type: yesno
    - Default: no
+ *subject* : Subject catgeory pasted to image
   - Type: list
    - Values: people, face, gan-face, natural object, gan-natural object, man-made object, gan-made object, large man-made object, large gan-made object, landscape, gan-landscape, other
### Optional Paramaters
+ *mode* : Blend Mode
   - Type: list
    - Values: Color Dodge, Color, Darken, Difference, Dissolve, Divide, Exclusion, Hard Light, Hard Mix, Hue, IntensityBurn, Lighten, Lighter Dodge, Linear Burn, Linear Dodge (add), Linear Light, Luminosity, Multiply, Opacity, Overlay, Pin Light, Saturation, Screen, Soft Light, Subtract, Vivid Light
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkSIFT*: Confirm SIFT homography was created for donor images.

*[DONOR]:checkForDonorWithRegion*: Confirm donor mask exists and is selected by a SelectRegion

*checkFileTypeChange*: Confirm the file type did not change.

*checkLocal*: Confirm the a nont global operation must be a blue link (include as composite mask).

*checkPasteMask*: Confirm that Paste Mask image file is the same dimensions are the source image.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.paste_splice*: APPLIES: IMAGE      Erase mask pixels that intersect the change mask if the purpose is NOT 'blend', indicating      that the change represented by those mask pixels is no longer visible.      Please note that the paste splice operation has its own mask and probe, thus algorithm change detection      still has information regarding to change to the 'pasted over' pixels.  A NON-'blend' is a replacement      of prior operation manipulations, making them unrecognizable.      In the donor case, pixels are also dropped as they are no longer 'used' from the donor (overwritten).

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Does the highlighted area represent the final size, placement and cropping of the pasted object?
+ Are all relevant semantic groups assigned? More than one may be appropriate.
### Analysis Rules
*maskgen.tool_set.localTransformAnalysis*: Non-global operations, capturing 'change size ratio' and 'change size category'.
## Vid2Vid
Use of Vid2Vid GAN to replace a face in a zip of images

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
### Allowed Transitions
+ zip.zip
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
# Select
## SelectCropFrames
Remove all frames before and after the selected video clip.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Validation Rules
*checkLengthSmaller*: Confirm resulting video has less frames that source.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkCropLength*: Confirm that the amount crop frames (video) or samples (audio) matches user input.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*video:maskgen.mask_rules.select_crop_frames*: 

*video_preprocess:maskgen.mask_rules.select_crop_frames_preprocess*: Return temporal segments for the entire video.

*audio_preprocess:maskgen.mask_rules.select_crop_frames_preprocess*: Return temporal segments for the entire video.

### QA Questions
### Analysis Rules
## SelectCutFrames
Remove a series of frames from a video clip.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Validation Rules
*checkLengthSmaller*: Confirm resulting video has less frames that source.

*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkEmpty*: Confirm the change mask is not empty

*checkCutFrames*: Confirm that the amount cut frames (video) or samples (audio) matches user input.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*audio:maskgen.mask_rules.delete_audio*: APPLIES: AUDIO

*video:maskgen.mask_rules.select_cut_frames*: 

*video_preprocess:maskgen.mask_rules.select_cut_frames_preprocess*: Creates the temporal segments of the neighboring frames to the given edge mask. This is the frame before the cut frame to the time of     the cut frame.  The cut frames are no longer in the media segment. The only possibility is to identity the location of the cut with     the frame before after the cut.  The number frames indicated is 2.  This is obviously ignored.

*audio_preprocess:maskgen.mask_rules.select_cut_frames_preprocess*: Creates the temporal segments of the neighboring frames to the given edge mask. This is the frame before the cut frame to the time of     the cut frame.  The cut frames are no longer in the media segment. The only possibility is to identity the location of the cut with     the frame before after the cut.  The number frames indicated is 2.  This is obviously ignored.

### QA Questions
### Analysis Rules
## SelectImageFromFrame
Select a single frame into an image.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Frame Time* : Presentation time of the select frame (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
### Optional Paramaters
### Validation Rules
### Allowed Transitions
+ video.image
### Probe Generation Rules
*video:maskgen.mask_rules.image_selection*: APPLIES : VIDEO     Extract a specific mask from video masks given the user provided Frame time.     This occurs when a single frame is selected, thus only that mask associated with the frame is passed on.

*video_preprocess:maskgen.mask_rules.image_selection_preprocess*: 

### QA Questions
### Analysis Rules
## SelectRegion
Create a limited selection in a donor image.  The result should be preserved in PNG.  Best practice involves using an alpha channel to mask out unselected regions.  The image can then be spliced into a series if frames.

Include as Probe Mask for []
### Mandatory Paramaters
+ *location change* : Did the selected region relocate in the image?
   - Type: list
    - Values: yes, no
+ *subject* : Subject catgeory selected to image
   - Type: list
    - Values: people, face, gan-face, natural object, gan-natural object, man-made object, gan-made object, large man-made object, large gan-made object, landscape, gan-landscape, other
### Optional Paramaters
+ *inputmaskname* : An image file containing a mask describing the areas affected.
   - Type: file:image
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.select_region*: APPLIES: Image     If donor mask is None, use the image's edge mask as the donor (the selected region).     Has not effect on composites.

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Are all relevant semantic groups assigned? More than one may be appropriate.
+ Is the selected region as accurate as possible so that it will represent the area of pixels that will be used in the manipulation.
### Analysis Rules
*maskgen.tool_set.optionalSiftAnalysis*: If 'location change' is not in parameters or 'location change' is no, skip tis step.     Otherwise, use SIFT to find a homography.
## SelectRegionFromFrames
Create a limited selection,removing background,from a donor video,for the intent of pasting.  The result should be a black back ground for non-keyed manipulations.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Start Time* : Start time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
    - Default: 1
### Optional Paramaters
+ *End Time* : End time of the image clip (HH:MI:SS.micro or frame number)
   - Type: frame_or_time
    - Create new Mask on Update
+ *key insertion* : Was a chroma or luminance key inserted into the video?
   - Type: yesno
### Validation Rules
*checkFrameTimes*: Confirm the format and validity of user entered times.  Also assert start time occurs before end time.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.select_region_frames*: Has not effect on composites or donor masks, passing on the donor and composite mask provided.     At this time, selection region frames assumes the provided donor mask is valid.     However, it make sense in the future to accept the select region's spatial temporal mask to overide the incoming     donor mask.

### QA Questions
### Analysis Rules
## SelectRemove
Remove a limited selection within an image.

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
### Optional Paramaters
+ *tolerance* : How much influence a pixel change has on the resulting mask.
   - Type: float[0:1]
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.select_remove*: 

### QA Questions
+ Confirm highlighted area represents the region that was affected by the operation
+ Confirm that this step was necessary and could not be included in the paste splice operation or by recreating previous steps with the final placement of pixels
### Analysis Rules
# AntiForensic
## AberrationCorrection
Chromatic Aberration Correction

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Lenient*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## AddCamFingerprintAveragePRNUFromSet
Add PRNU fingerprint trace, generated from a set of images.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Capture Camera ID* : Local ID of camera used to capture images
   - Type: text
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## AddCamFingerprintPRNU
Add PRNU fingerprint trace from an image.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
+ *Capture Camera ID* : ID of camera used to capture image if not screen shot
   - Type: text
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## AddCameraModel
Copy metadata information from a source.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Camera Model* : Model Name from Browser
   - Type: text
+ *Camera Make* : Make Name from Browser
   - Type: text
### Optional Paramaters
### Validation Rules
*checkSizeAndExif*: Confirm the dimensions of the image or video did not change except for rotation in accordance to the Orientation meta-data.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.exif_transform*: 

*video:maskgen.mask_rules.video_copy_exif*: APPLIES: VIDEO     Rotate video masks in the direction of exif orientation where applicable.     The stream meta-data must indicate the additional or removal of an orientation.     The edge must indicate that a rotation occurred either through 'rotate' meta data.

### QA Questions
+ Exif Changed?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## AntiForensicCopyExif
Copy metadata information from a source.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
+ *rotate* : Was video rotated
   - Type: yesno
### Validation Rules
*checkSizeAndExif*: Confirm the dimensions of the image or video did not change except for rotation in accordance to the Orientation meta-data.

*checkFileTypeChangeForDonor*: Confirm the file type of the donor matches the target of the manipulation.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkTimeStamp*: Confirm the timestamp formats within the metadata did not change.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*image:maskgen.mask_rules.exif_transform*: 

*video:maskgen.mask_rules.video_copy_exif*: APPLIES: VIDEO     Rotate video masks in the direction of exif orientation where applicable.     The stream meta-data must indicate the additional or removal of an orientation.     The edge must indicate that a rotation occurred either through 'rotate' meta data.

### QA Questions
+ Exif Changed?
### Analysis Rules
*maskgen.tool_set.globalTransformAnalysis*: Determine if operation is global. Capture 'change size ratio' and 'change size category'.
## AntiForensicDither
Disguise quantization artifacts by adding noise.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkEightBit*: Confirm image is aligned to 8 bits.

*checkSize*: Confirm the dimensions of the image or video did not change

### Allowed Transitions
+ image.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Exif Changed?
### Analysis Rules
## AntiForensicEditExif
Alter image metadata.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkFileTypeChange*: Confirm the file type did not change.

*checkSameChannels*: Confirm that the number of streams did not change by the manipulation.

*checkMetaDate*: Confirm the the EXIF date formats did  not change.

*checkTimeStamp*: Confirm the timestamp formats within the metadata did not change.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## AntiForensicExifQuantizationTable
Alter Image to be compliant with another images quantization and EXIF

Include as Probe Mask for []
### Mandatory Paramaters
+ *rotate* : Rotate the image counter to the Orientation of copied EXIF.
   - Type: yesno
### Optional Paramaters
### Validation Rules
*checkSizeAndExif*: Confirm the dimensions of the image or video did not change except for rotation in accordance to the Orientation meta-data.

*[DONOR]:checkForDonor*: Confirm donor edge exists.

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkTimeStamp*: Confirm the timestamp formats within the metadata did not change.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*image:maskgen.mask_rules.exif_transform*: 

*video:maskgen.mask_rules.video_copy_exif*: APPLIES: VIDEO     Rotate video masks in the direction of exif orientation where applicable.     The stream meta-data must indicate the additional or removal of an orientation.     The edge must indicate that a rotation occurred either through 'rotate' meta data.

### QA Questions
+ Exif Changed?
### Analysis Rules
## AntiForensicJPGCompression
Use quantization tables and exif data from a particular camera to save an image as JPG.

Include as Probe Mask for []
### Mandatory Paramaters
+ *qtfile* : Quantization table file.
   - Type: fileset:plugins/JpgFromCamera/QuantizationTables
### Optional Paramaters
### Validation Rules
*checkEightBit*: Confirm image is aligned to 8 bits.

### Allowed Transitions
+ image.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
+ Exif Changed?
### Analysis Rules
## BitRescale
Rescale pixel intensity to remove gaps in the histogram

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## ErasureByGAN
Remove effects of manipulations depending on the GAN model and architecture

Include as Probe Mask for [image, audio, video]
### Mandatory Paramaters
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## LensDistortion
Apply artificial lens distortion

Include as Probe Mask for []
### Mandatory Paramaters
+ *Distortion Type* : Type of distortion being applied to image.
   - Type: list
    - Values: Pincushion, Barrel, Mustache
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkEmpty*: Confirm the change mask is not empty

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## RemoveCamFingerprintAveragePRNUFromSet
Remove PRNU fingerprint trace, generated from a set of images from a camera.

Include as Probe Mask for []
### Mandatory Paramaters
+ *Capture Camera ID* : Local ID of camera used to capture images
   - Type: text
### Optional Paramaters
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules
## RemoveCamFingerprintPRNU
Remove PRNU fingerprint from image.

Include as Probe Mask for []
### Mandatory Paramaters
### Optional Paramaters
+ *Capture Camera ID* : ID of camera used to capture image if not screen shot
   - Type: text
### Validation Rules
*checkSize*: Confirm the dimensions of the image or video did not change

*checkEightBit*: Confirm image is aligned to 8 bits.

*checkEmpty*: Confirm the change mask is not empty

*checkFrameRateChange_Strict*: Confirm frame rate has not changed.

### Allowed Transitions
+ image.image
+ video.video
### Probe Generation Rules
*Default*: resize, rotate, crop, and transform where applicable
### QA Questions
### Analysis Rules

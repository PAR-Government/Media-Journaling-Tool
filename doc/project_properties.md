# Project
+ *Last Update User Name*: This property may be changed under File->Settings->Username

   - key: username

   - type: string

   - mandatory: False

   - property value restrictions: None
+ *Creator*: This property cannot be changed

   - key: creator

   - type: string

   - mandatory: False

   - property value restrictions: None
+ *Organization*: Journal Creation Organzation

   - key: organization

   - type: string

   - mandatory: True

   - property value restrictions: None
+ *Description*: Journal Description

   - key: projectdescription

   - type: text

   - mandatory: True

   - property value restrictions: None
+ *Project File*: A project file from the editing software

   - key: projectfile

   - type: file:*

   - mandatory: False

   - property value restrictions: None
+ *Technical Summary*: Journal Technical Summary

   - key: technicalsummary

   - type: text

   - mandatory: False

   - property value restrictions: None
+ *Provenance*: Multlple mixed donor images

   - key: provenance

   - type: yesno

   - mandatory: False

   - property value restrictions: None
+ *QA Comments*: None

   - key: qacomment

   - type: text

   - mandatory: False

   - property value restrictions: None
+ *Validation*: None

   - key: validation

   - type: yesno

   - mandatory: False

   - property value restrictions: None
+ *Validated By*: None

   - key: validatedby

   - type: string

   - mandatory: False

   - property value restrictions: None
+ *Validation Date*: None

   - key: validationdate

   - type: string

   - mandatory: False

   - property value restrictions: None
+ *Semantic Restaging*: Staging a photo that does not truly reflect reality. For example, staging a fake bombing that never occurred

   - key: semanticrestaging

   - type: yesno

   - mandatory: False

   - property value restrictions: None
+ *Semantic Repurposing*: Using an existing piece of media for another purpose (e.g rebroadcasting media in a different context)

   - key: semanticrepurposing

   - type: yesno

   - mandatory: False

   - property value restrictions: None
+ *Semantic Event Fabrication*: A large scale activity that requires an entire volume of manipulated or generated imagery to provide to simulate a full event. This could include imagery that appears to be from many individuals, cameras, and social media accounts

   - key: semanticrefabrication

   - type: yesno

   - mandatory: False

   - property value restrictions: None
+ *Paste Clone Auto Input Mask*: if the input mask was guessed

   - key: autopastecloneinputmask

   - type: yesno

   - mandatory: False

   - property value restrictions: None
+ *Semantic Groups*: Summary of semantic groups used in the journal

   - key: semanticgroups

   - type: list

   - mandatory: False

   - property value restrictions: None
+ *Manipulation Category*: The maximum number of semantic units for all images produced by the project.

   - key: manipulationcategory

   - type: string

   - mandatory: False

   - property value restrictions: None
# Semantic Group
+ *AntiForensic Illumination*: AntiForensic Illumination

   - key: antiforensicillumination

   - type: yesno

   - property value restrictions: None
+ *Aging*: Change of a persons look to indicate older or younger

   - key: aging

   - type: yesno

   - property value restrictions: None
+ *Wound*: Indications of injury on a person

   - key: wound

   - type: yesno

   - property value restrictions: None
+ *Cadaver*: Alter a person image to look like a cadaver

   - key: cadaver

   - type: yesno

   - property value restrictions: None
+ *Crowd Relocation*: Relocate a crowd in a new setting that is not semantically coherent

   - key: crowdrelocation

   - type: yesno

   - property value restrictions: None
+ *Building Relocation*: Relocate a building in a new setting that is not architecturally coherent

   - key: buildingrelocation

   - type: yesno

   - property value restrictions: None
+ *Location Change*: Change visual and meta-data change that forces location incoherence

   - key: locationchange

   - type: yesno

   - property value restrictions: None
+ *Timeofday*: Change lighting to indicate a different time of day

   - key: timeofday

   - type: yesno

   - property value restrictions: None
+ *Date and Time*: Change the date and time for ENF and time specific environment change detection

   - key: dateandtime

   - type: yesno

   - property value restrictions: None
+ *Date Burn-in*: Adding or changing a time stamp on an image

   - key: dateburnin

   - type: yesno

   - property value restrictions: None
+ *Data Embedding Steganography*: Data Embedding Steganography.  All final images must have steganography.

   - key: dataembeddingsteganography

   - type: yesno

   - property value restrictions: None
+ *Data Embedding Watermark*: Data Embedding Watermark.  All final images must have watermarks.

   - key: dataembeddingwatermark

   - type: yesno

   - property value restrictions: None
+ *Face Manipulations*: Manipulations to alter a face or faces (e.g. warp, swap, etc.).

   - key: facemanipulations

   - type: yesno

   - property value restrictions: None
+ *Mood Change*: Face manipulation to change a person's mood

   - key: moodchange

   - type: yesno

   - property value restrictions: None
+ *Shadow Manipulations*: Manipulations to alter a shadows.

   - key: shadowmanipulations

   - type: yesno

   - property value restrictions: None
+ *Weather Changes*: Radically alter the weather, (e.g. add snow or rain to a sunny day)

   - key: weatherchanges

   - type: yesno

   - property value restrictions: None
+ *Ambience Audio Swap*: Swap Ambience (e.g. environment sounds).

   - key: ambienceaudioswap

   - type: yesno

   - property value restrictions: None
+ *Voice Audio Swap*: Voice Swap.

   - key: voiceaudioswap

   - type: yesno

   - property value restrictions: None
+ *Dialog Change*: Dialog of a voice is changed to not match speaker or context.

   - key: dialogchange

   - type: yesno

   - property value restrictions: None
+ *Reflection Manipulations*: Manipulations to reflections.

   - key: reflectionmanipulations

   - type: yesno

   - property value restrictions: None
+ *Tattoos*: Adding, Removing, or Altering  Tattoos

   - key: Tattoos

   - type: yesno

   - property value restrictions: None
+ *Personal Appearance*: Skin Color Change, Dirty Clothing, Coal Dust, Dirt on Skin, Adding or Removing Hair

   - key: Personal Appearance

   - type: yesno

   - property value restrictions: None
+ *Building Destruction*: Destroying a building to look like it was attacked or collapsed

   - key: Building Destruction

   - type: yesno

   - property value restrictions: None
+ *Drone Video Tests*: Processing to make a synthetic video journal

   - key: Drone Video Tests

   - type: yesno

   - property value restrictions: None
+ *Manhattan World*: Putting a object with corners and depth into a Manhattan World image example: table, box, frame

   - key: Manhattan World

   - type: yesno

   - property value restrictions: None
+ *Falsifying Documents*: Change recaptured documents nefariously. Example: Signature Change

   - key: FalsifyingDocuments

   - type: yesno

   - property value restrictions: None
+ *splice/copy*: copying an object into a scene to create a copy of an object in the scene already

   - key: splice/copy

   - type: yesno

   - property value restrictions: None
+ *ENF*: Tests suitable for electric network frequency

   - key: ENF

   - type: yesno

   - property value restrictions: None
+ *Frame From Video*: Taking 1 frame of a video and using that frame as a part of a manipulation

   - key: FrameFromVideo

   - type: yesno

   - property value restrictions: None
+ *Disaster*: Building Fire, Flooding, Earth Quake

   - key: Disaster

   - type: yesno

   - property value restrictions: None
# Final Node
+ *Audio Activity*: Applies to video journals where the final video contains a variety of audio content based on location and audio activity.

   - key: audioactivity

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Remove*: None

   - key: remove

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSampled

   - inclusion rule parameter: purpose

   - inclusion rule value: remove

   - property value restrictions: None
+ *Clone*: None

   - key: clone

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Blur Local*: None

   - key: blurlocal

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Contrast Enhancement*: None

   - key: contrastenhancement

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *ColorEnhancement*: None

   - key: color

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Healing Local*: None

   - key: healinglocal

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSampled

   - inclusion rule parameter: purpose

   - inclusion rule value: heal

   - property value restrictions: None
+ *Histogram Normalization Global*: None

   - key: histogramnormalizationglobal

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Other Enhancements*: None

   - key: otherenhancements

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Man-Made*: None

   - key: manmade

   - type: yesno

   - node type constraint: image

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: man-made object

   - property value restrictions: None
+ *Face*: None

   - key: face

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: face

   - property value restrictions: None
+ *People*: None

   - key: people

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: people

   - property value restrictions: None
+ *Large Man-Made*: None

   - key: largemanmade

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: large man-made object

   - property value restrictions: None
+ *Landscape*: None

   - key: landscape

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: landscape

   - property value restrictions: None
+ *Natural object*: None

   - key: natural

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: natural object

   - property value restrictions: None
+ *Other Subjects*: None

   - key: othersubjects

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteSplice

   - inclusion rule parameter: subject

   - inclusion rule value: other

   - property value restrictions: None
+ *Temporal Clone*: Temporal Clone

   - key: temporalclone

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: CopyPaste

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Temporal Splice*: Temporal Splice

   - key: temporalsplice

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: PasteFrames

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Temporal Remove*: Temporal Remove

   - key: temporalremove

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: SelectCutFrames

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Temporal Reorder*: Temporal Reorder

   - key: temporalreorder

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: CutPaste

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Temporal Other*: Temporal Other

   - key: temporalother

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: TimeAlterationEcho, TimeAlterationPosterizeTime, TimeAlterationDifferenceEffect, TimeAlterationDisplacementEffect, TimeAlterationWarp

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Spatial Clone*: Spatial Clone

   - key: spatialclone

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Spatial Splice*: Spatial Splice

   - key: spatialsplice

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Spatial Remove*: Spatial Remove

   - key: spatialremove

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Spatial Moving Object*: Spatial Moving Object

   - key: spatialmovingobject

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Spatial Moving Camera*: Spatial Moving Camera

   - key: spatialmovingcamera

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: C, a, m, e, r, a, M, o, v, e, m, e, n, t

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Spatial Other*: Spatial Other

   - key: spatialother

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Audio Removal*: Audio Removal

   - key: audioremoval

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: DeleteAudioSample

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Audio Clone*: Audio Clone

   - key: audioclone

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AudioCopyAdd

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Audio Splice*: Audio Splice

   - key: audiosplice

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: ReplaceAudioSample, AddAudioSample, AudioCopyAdd

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Audio Voice Over*: Audio Voice Over

   - key: audiovoiceover

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Audio Voice Swapping*: Audio Voice Swapping

   - key: audiovoiceswapping

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Audio Other*: Audio Other

   - key: audioothers

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AudioFilter, AudioAmplify, AudioCompress

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Post Process Compression*: Post Process Compression

   - key: postprocesscompression

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: OutputMP4, OutputMOV, OutputXVID, OutputJpg

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Post Process Crop Frames*: Post Process Crop Frames

   - key: postprocesscropframes

   - type: yesno

   - node type constraint: video

   - include donors: False

   - operation restrictions: TransformCrop

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Post Process Stabilization*: Post Process Stabilization

   - key: postprocessstabilization

   - type: yesno

   - node type constraint: video

   - include donors: False

   - operation restrictions: WarpStabilize

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Image Reformatting*: None

   - key: imagereformat

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Image Compression*: None

   - key: imagecompression

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Image Compression Table*: None

   - key: imagecompressiontable

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AntiForensicExifQuantizationTable, AntiForensicJPGCompression

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Composite Image Pixel Size*: None

   - key: compositepixelsize

   - type: list

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: small, medium, large
+ *Manipulation Category*: The number of units per node

   - key: manipulationcategory

   - type: text

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Laundering SocialMedia*: Laundering SocialMedia

   - key: launderingsocialmedia

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: SocialMedia

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Laundering Median Filtering*: Laundering Median Filtering

   - key: launderingmedianfiltering

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *AntiForensic CFACorrection*: AntiForensic CFACorrection

   - key: antiforensiccfacorrection

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: CFACorrection, AddCameraModel

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *AntiForensic AberrationCorrection*: AntiForensic AberrationCorrection

   - key: antiforensicaberrationcorrection

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AberrationCorrection

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Recapture*: Recapture

   - key: recapture

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: Recapture

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *AntiForensicAddCamFingerprintPRNU*: AntiForensicAddCamFingerprintPRNU

   - key: antiforensicaddcamfingerprintprnu

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AddCamFingerprintPRNU

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *AntiForensic Noise Restoration*: AntiForensic Noise Restoration

   - key: antiforensicnoiserestoration

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AddNoise

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *AntiForensic Other*: AntiForensic Other

   - key: antiforensicother

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: Undefined, LensDistortion, AntiForensicDither, AntiForensicEditExif, RemoveCamFingerprintPRNU

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Mosaicing*: Mosaicing.

   - key: mosaicing

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: AdditionalEffectMosaic, Mosaic

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Seam Carving*: Seam Carving.

   - key: seamcarving

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: TransformSeamCarving

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Semantic Restaging*: Staging a photo that does not truly reflect reality. For example, staging a fake bombing that never occurred

   - key: semanticrestaging

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Semantic Repurposing*: Using an existing piece of media for another purpose (e.g rebroadcasting media in a different context)

   - key: semanticrepurposing

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *Semantic Event Fabrication*: A large scale activity that requires an entire volume of manipulated or generated imagery to provide to simulate a full event. This could include imagery that appears to be from many individuals, cameras, and social media accounts

   - key: semanticrefabrication

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *GAN Component*: Has a GAN provided the manipulation.

   - key: gan_component

   - type: yesno

   - node type constraint: None

   - include donors: True

   - operation restrictions: SynthesizeGAN, AddCameraModel, DeepFakeFaceSwap, ErasureByGAN, GANFill

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *GAN Generated*: Has a GAN provided the base media.

   - key: gan_generated

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None
+ *CGI Generated*: Has a CGI(model) provided the base media.

   - key: cgi_generated

   - type: yesno

   - node type constraint: None

   - include donors: False

   - operation restrictions: None

   - inclusion rule parameter: None

   - inclusion rule value: None

   - property value restrictions: None

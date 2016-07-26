rules = {}

def run_rules(op, graph, frm,to):
  global rules
  if len(rules) == 0:
    setup()

  results = []
  for rule in (rules[op] if op in rules else []):
     res = rule(graph,frm,to)
     if res is not None:
       results.append(res)
  return results

def setup():
  global rules
  rules['AdditionalEffectAddLightSource'] = [checkSize]
  rules['AdditionalEffectFading'] = [checkSize]
  rules['AdditionalEffectFilterAddNoise'] = [checkSize]
  rules['AdditionalEffectFilterBlur'] = [checkSize]
  rules['AdditionalEffectFilterMedianSmoothing'] = [checkSize]
  rules['AdditionalEffectFilterSharpening'] = [checkSize]
  rules['AdditionalEffectFilterSmoothing'] = [checkSize]
  rules['AdditionalEffectGradientEffect'] = [checkSize]
  rules['AdditionalEffectSoftEdgeBrushing'] = [checkSize]
  rules['AntiForensicCameraFingerprintAberrationCorrection'] = [checkSize]
  rules['AntiForensicCameraFingerprintCFAHiding'] = [checkSize]
  rules['AntiForensicCameraFingerprintCFAInterpolation'] = [checkSize]
  rules['AntiForensicCameraFingerprintCFAResize'] = [checkSize]
  rules['AntiForensicCameraFingerprintCFARotation'] = [checkSize]
  rules['AntiForensicCameraFingerprintENFAlternation'] = [checkSize]
  rules['AntiForensicCameraFingerprintPhotoResponseNonUniformity'] = [checkSize]
  rules['AntiForensicCompressionCompressionNormalization'] = [checkSize]
  rules['AntiForensicExifCameraModelPara'] = [checkSize]
  rules['AntiForensicExifDateTime'] = [checkSize]
  rules['AntiForensicExifManipulationSoftware'] = [checkSize]
  rules['AntiForensicExifQuantizationTable'] = [checkSize]
  rules['AntiforensicFilterNoiseRestoration'] = [checkSize]
  rules['ArtifactsCGIArtificialLighting'] = [checkSize]
  rules['ArtifactsCGIArtificialReflection'] = [checkSize]
  rules['ArtifactsCGIArtificialShadow'] = [checkSize]
  rules['ArtifactsCGIObjectCGI'] = [checkSize]
  rules['ColorBlendColorBurn'] = [checkSize]
  rules['ColorBlendColorInterpolation'] = [checkSize]
  rules['ColorBlendDissolve'] = [checkSize]
  rules['ColorBlendMultiply'] = [checkSize]
  rules['ColorColorBalance'] = [checkSize]
  rules['ColorFill'] = [checkSize]
  rules['ColorHue'] = [checkSize]
  rules['ColorMatchColor'] = [checkSize]
  rules['ColorOpacity'] = [checkSize]
  rules['ColorReplaceColor'] = [checkSize]
  rules['ColorSaturation'] = [checkSize]
  rules['ColorVibranceContentBoosting'] = [checkSize]
  rules['ColorVibranceReduction'] = [checkSize]
  rules['CreationFilterGT'] = [checkSize]
  rules['FillBackground'] = [checkSize]
  rules['FillCloneRubberStamp'] = [checkSize]
  rules['FillContentAwareFill'] = [checkSize]
  rules['FillForeground'] = [checkSize]
  rules['FillGradient'] = [checkSize]
  rules['FillHealingBrush'] = [checkSize]
  rules['FillImageInterpolation'] = [checkSize]
  rules['FillInpainting'] = [checkSize]
  rules['FillLocalRetouching'] = [checkSize]
  rules['FillPaintBrushTool'] = [checkSize]
  rules['FillPaintBucket'] = [checkSize]
  rules['FillPattern'] = [checkSize]
  rules['FillRubberStamp'] = [checkSize]
  rules['FilterBlurMotion'] = [checkSize]
  rules['FilterBlurNoise'] = [checkSize]
  rules['FilterCameraRawFilter'] = [checkSize]
  rules['IntensityBrightness'] = [checkSize]
  rules['IntensityContrast'] = [checkSize]
  rules['IntensityCurves'] = [checkSize]
  rules['IntensityDarken'] = [checkSize]
  rules['IntensityDesaturate'] = [checkSize]
  rules['IntensityExposure'] = [checkSize]
  rules['IntensityHardlight'] = [checkSize]
  rules['IntensityHighlight'] = [checkSize]
  rules['IntensityLevels'] = [checkSize]
  rules['IntensityLighten'] = [checkSize]
  rules['IntensityLuminosity'] = [checkSize]
  rules['IntensitySoftlight'] = [checkSize]
  rules['MarkupDigitalPenDraw'] = [checkSize]
  rules['MarkupHandwriting'] = [checkSize]
  rules['MarkupOverlayObject'] = [checkSize]
  rules['MarkupOverlayText'] = [checkSize]
  rules['OutputBmp'] = [checkSize]
  rules['OutputJpg'] = [checkSize]
  rules['OutputPng'] = [checkSize]
  rules['OutputTif'] = [checkSize]
  rules['PasteClone'] = [checkSize]
  rules['PasteDuplicate'] = [checkSize]
  rules['PasteSplice'] = [checkSize,checkForDonor]
  rules['PostProcessingSizeUpDownOrgExif'] = [checkSize]
  rules['SelectCopy'] = [checkSize]
  rules['SelectRegion'] = [checkSize]
  rules['SelectRemove'] = [checkSize]
  rules['TransformAffine'] = [checkSize]
  rules['TransformContentAwareScale'] = [checkSize]
  rules['TransformCrop'] = []
  rules['TransformDistort'] = [checkSize]
  rules['TransformFlip'] = [checkSize]
  rules['TransformMove'] = [checkSize]
  rules['TransformResample'] = [checkSize]
  rules['TransformResize'] = [sizeChanged]
  rules['TransformRotate'] = []
  rules['TransformScale'] = [sizeChanged]
  rules['TransformSeamCarving'] = [seamCarvingCheck]
  rules['TransformShear'] = [checkSize]
  rules['TransformSkew'] = [checkSize]
  rules['TransformWarp'] = [checkSize]
  rules['Donor'] = [checkDonor]
  rules['AntiForensicCopyExif'] = [checkForDonor]

def checkForDonor(graph,frm,to):
   pred = graph.predecessors(to)
   if len(pred) < 2:
     return 'donor image missing'
   return None

def checkDonor(graph,frm,to):
   pred = graph.predecessors(to)
   if len(pred) < 2:
     return 'donor must be associated with a image node that has a inbound paste operation'
   return None

def seamCarvingCheck(edge):
   change = getSizeChange(graph,frm,to)
   if change is not None and change[0] != 0 and change[1] != 0:
     return 'seam carving should not alter both dimensions of an image'
   return None

def sizeChanged(graph,frm,to):
   change = getSizeChange(graph,frm,to)
   if change is not None and (change[0] == 0 and change[1] == 0):
     return 'operation should change the size of the image'
   return None

def checkSize(graph,frm,to):
   change = getSizeChange(graph,frm,to)
   if change is not None and (change[0] != 0 or change[1] != 0):
     return 'operation is not permitted to change the size of the image'
   return None
      
def getSizeChange(graph,frm,to):
   edge = graph.get_edge(frm,to)
   change= edge['shape change'] if edge is not None and 'shape change' in edge else None
   if change is not None:
       xyparts = change[1:-1].split(',')
       x = int(xyparts[0].strip())
       y = int(xyparts[1].strip())
       return (x,y)
   return None

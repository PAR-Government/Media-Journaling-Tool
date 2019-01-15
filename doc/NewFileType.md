# Add New File Type (e.g. video, audio, image, zip,  ?)
## maskgen.tool_set
 (1) Add new type list to getFileTypes()
 (2) Adjust openImage with a new extension to ImageOpener
## maskgen.scenario_model
 (1) Add new extension to LinkTool--Analysis and Mask generation of source and target.  LinkTool is based on link type; one of  'video.video', 'image.video', 'video.image', 'image.image', 'audio.video'  or 'video.audio'.  Zip media are treated similar to videos with an audio stream

 (2) Update linkTools list
 (3) Add new extension to AddTool--Additional information recorded on loading and special instructions
 (4) Update addTools list

##maskgen.software_loader
 (1) _loadSoftware
 (2) get_versions

##operations.json
 Add transitions to appropriate operations

## maskgen.masks.donor_rules

 Add a factory and donor processor.  The factory is a function theat creates a donor processing object.

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
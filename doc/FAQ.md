# UI

### Video Manipulation Validation Concerns

TBD

### Video Mask Tuning

TBD

# BATCH

### EXTENSIONS

#### Is the state of journal changed if extension fails?

No.  The project JSON file is not updated and the '--completeFile'  is not updated. The log file will have a line: "Project skipped: <projectname>".

#### Why does a core dump occur?

Projects involve many libraries such as libraw, opencv, libjpeg, and ffmpeg. Furthermore, plugins use their own libraries and dependencies.  Some libraries do not play well together (different versions) and some are not thread safe.  

In the case of a core dump, try rerunning the project be extended during the core dump in isolation using a single threaded batch extension (the default).

#### What steps should I take if a batch process is killed or core dumps?

The projects in process during the failure are most likely incomplete and are safe to rerun.  For certainty, look at the consistency between the log file, the update time for the project JSON file and the  '--completeFile' .  

The Log File will have a message referencing the project indication an update: "Project updated [1/1] <projectname>".  This message indicates the JSON is saved.  The JSON still may be saved even if the log file never received the message due to the process failure.

Next the 'complete file' should contain the finished project in the JSON is updated.  

Be sure to check the integrity of the journal JSON file, as it could be in a partial updated state.

It is a good idea to keep a backup of the project to be updated prior to an extension.  Worst case, the back up overlays the failed project and the extension is restarted.

As summary, the updates to the forementioned components occur in this order:

(1) Save Project JSON.

(2) Send Log message to log.

(3) Add project to complete file

### Creation

#### Why does a core dump occur?

Projects involve many libraries such as libraw, opencv, libjpeg, and ffmpeg. Furthermore, plugins use their own libraries and dependencies.  Some libraries do not play well together (different versions) and some are not thread safe.  

In the case of a core dump, try run single threaded. Try isolating the different media resources (images, videos, audio) being supplied to the project in separate groups by type (e.g. CR2 first, then JPG, etc.) .

#### What steps should I take if a batch process is killed or core dumps?

The resource lists is not updated, so the resources used in the projects being constructed at the time of the core dump are still available.   However, the project directories are still in existence.  The batch creation will create new directories with a date/time appended to the name.  Either remove those directories before restart or allow the tool to create the 'dated' directory.

#### What are the indicators of a project failure?

The batch tool log file contains a message "Creation of project <projectname> failed: <reason>".  

If '--keep_failed' is set, then the project directory is retained at the time of failure.  A kept project directory can help identify the root problem. As with core dumps, restarting a failed project creates a new directory if the old project direcory still exists.  The new directory includes a date/time stamp appended to the name .

Finally, a state file is presevered with all the chosen arguments in the project including media resources collected.  The name of the state file is 'failures-<datetime>.txt'.  The project may be rerun using the exact state using the '--from_state' command line argument followed by the name of the failure file.

#### How do I restart a project after a failure?

It is recommended to remove the old project directory and remove the names used media resources manually out of the associated picklist files in the '--workdir' directory.  Alternatively, every failure ends with a state file, named 'failures-<datetime>.txt', recording the state of the arguments for the batch operations at the time of the failure.   The project may be rerun using the exact state using the '--from_state' command line argument followed by the name of the failure file.


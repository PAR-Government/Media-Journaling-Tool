# Project Properties

## Overview

Each Project Property is one of the following.

* Semantic Group
* User Defined property captured as for a joural project.
* A derived property assigned to final media nodes summarizing manipulatons contributed to the final media associated with the node. 

[List of active properties](project_properties.md).

## Details

Project Properties is a JSON file that describes properties captured by the user at the project level. The JSON file also describes properties assigned to each final image done during export.

Semantic groups are also defined as a project properties.

Properties define a value type, using the same type descriptions are operation arguments (see [New Operation](NewOperation.md).

Minimally, the property is defined with the following keys.

* *description* -> User printable name
* *information* -> a more detailed description
* *name* -> key name used when referenced in the JT's project graph.
* *type* -> property value type
* *node* -> is the property automatically derived from node data in the JT graph.
* *_comment* -> internal comment not shown to user of the JT.

### Node

A project property is defined for a final image node if the *node* property attribute is true. Properties may automatically be determined based on rules. The rules are setup in three ways:

1. Existence of an manipulation link with a specified operation
2. Existence of an manipulation link  with a specified operation and argument with a specific valued.
3. A general rule (python function)

Project level properties inspect all edges. Final image node properties inspect those edges from the final node to the base node, ignoring paths of edges starting with a donor.

Since operations may be used for different types of media (image and video), operation based rules can be restricted to a media type given the *nodetype* key with values of 'image' or 'video'.

Multiple operations can be represented by a rule by replace the *operation* key with an *operations* key. The value for the *operations* key is a list of operation names.

Some rules depend on the operation and the assigned value of manipulation links argument/parameter.   The argument/parameter name is referenced by key *parameter*. The argument/parameter value is referenced by key *value*.

Finally,*includedonors* infoms the JT inspect edges leading up to a final node along feeding donor paths.

The result is stored in the final media node as dictionary of key/values.  <u>The dictionary is attached to the final media nodes with key *pathanalysis*.</u>

### Semantic Group

All semantic groups are type *yesno*.  A semantic group is a described label attached to a group of links that cooperation to achive a specific semantic goal.

Properties defining a semantic group contain a key *semanticgroup* with value true.

### Example User-Managed Project Property

~~~
 { 
      "description": "Organization",
      "name": "organization",
      "type": "string",
      "mandatory": true,
      "information":"Journal Creation Organzation"
},
~~~

## Example Edge with Specific Operation for Media Type Video

~~~
{
       "description": "Post Process Crop Frames",
       "name": "postprocesscropframes",
       "node" : true,
       "operations": ["TransformCrop"],
       "nodetype": "video",
       "type": "yesno",
       "information": "Post Process Crop Frames"
 },
~~~



## Example Edge with Specific list of Operations for Media Type Image

~~~
 {  
       "description": "Post Process Compression",
       "name": "postprocesscompression",
       "node" : true,
       "operations": ["OutputMP4","OutputMOV","OutputXVID", "OutputJpg"],
       "type": "yesno",
       "information": "Post Process Compression"
     },
~~~



## Example Edge with Specific Operation and Argument Value

~~~
    {
      "description": "Other Subjects",
      "name": "othersubjects",
      "type":"yesno",
      "operation" :"PasteSplice",
      "parameter":"subject",
      "value":"other",
      "node" : true
    },
~~~



## Example with a Rule

~~~
    {
      "description": "ColorEnhancement",
      "name": "color",
      "type": "yesno",
      "_comment": " any color category operation",
      "rule": "colorGlobalRule",
      "node" : true
    },
~~~

## Example Semantic Group

~~~
{
      "description": "Aging",
      "name": "aging",
      "type": "yesno",
      "semanticgroup" : true,
      "information": "Change of a persons look to indicate older or younger"
},
~~~



## Derived Project Properties

There are steps to finalizing a project:

1. graph_rules.processProjectProperties
2. graph_rules.setFinalNodeProperties (ImageProjectMode,Final Node Identifier) -> set final node summary properties

#### Project Properties

Adds properties, not based on rules.  Instead, they set project level properties based on operation and parameter names.  These are *yesno* properties looking for the presence of edges with an operation.

#### Final Node Properties

The rule function is provided all edges along a path from a base media to final media.  A rule function has the following signature.

~~~
def xRule(scModel, edgeTuples):
"""
@param scModel: ImageProjectModel
@param edgeTuples:  (source node id, target node id, link/edge dictionary)
@return: a single value for the property after inspecting all links

~~~






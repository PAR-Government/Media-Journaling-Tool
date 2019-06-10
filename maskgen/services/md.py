# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from maskgen.software_loader import getOperation,getOperations,getRule,getProjectProperties
from maskgen.support import getValue

def write_header(fp, name, level, status=None):
    fp.write('#'*level)
    fp.write(' ')
    fp.write(name)
    if status is not None:
        fp.write(' %s' % status)
    fp.write('\n')

def write_text(fp, text):
    fp.write(text)
    fp.write('\n')

def write_bullet(fp,text):
    fp.write('+ %s\n' % text)

def write_bullet_emphasize(fp, name, description, items):
    fp.write('+ *%s*: %s\n' % (name, description))
    for item in items:
        fp.write('\n   - %s: %s\n' % (item[0],str(item[1])))

def write_parameter(fp, name, definition):
    fp.write('+ *')
    fp.write(name)
    fp.write('* : ')
    fp.write(getValue(definition, 'description',''))
    fp.write('\n   - Type: %s\n' % definition['type'])
    if getValue(definition,'source'):
      fp.write('    - Source Type: %s\n' % getValue(definition,'source') )
    if getValue(definition,'trigger mask'):
      fp.write('    - Create new Mask on Update\n')
    if getValue(definition,'defaultvalue'):
      fp.write('    - Default: %s\n' % getValue(definition,'defaultvalue') )
    if getValue(definition, 'values'):
          fp.write('    - Values: %s\n' % ', '.join(getValue(definition, 'values')))

def get_function_doc(f):
    doc = f.__doc__
    if doc is None:
        return 'NA'

    def not_neg(value,max_value):
        if value < 0:
            return max_value
        return value

    pos_end = len(doc) - 1
    pos_p = not_neg(doc.find(':param'),pos_end)
    pos_at = not_neg(doc.find('@'),pos_end)
    cut_position = min(pos_p, pos_at, pos_end)
    return doc[0:cut_position].strip().replace('\n',' ')

def write_analysis(fp,rule):
    rule_func = getRule(rule, globals=globals())
    fp.write('*%s*: %s\n' % (rule, get_function_doc(rule_func) if rule_func is not None else 'NA'))

def write_rule(fp,rule):
    if rule.startswith('donor:'):
        prefix = '[DONOR]:'
        rule = rule[6:]
    else:
        prefix =''
    rule_func = getRule(rule, globals=globals(), default_module='maskgen.graph_rules')
    fp.write('*%s%s*: %s\n\n' % (prefix,rule, get_function_doc(rule_func) if rule_func is not None else 'NA'))

def operations_by_category():
    result = {}
    for name, op in getOperations().iteritems():
        data = getValue(result,op.category,[])
        data.append(op.name)
        result[op.category] = data

    for category in result.keys():
        result[category] = sorted(result[category])
    return result

def properties_by_type():
    types = {'Semantic Group': [], 'Final Node':[], 'Project':[]}
    for property in getProjectProperties():
        if property.semanticgroup:
            types['Semantic Group'].append(property)
        elif property.node:
            types['Final Node'].append(property)
        else:
            types['Project'].append(property)
    return types



def to_properties_md():
    with open('project_properties.md', 'w') as fp:
        types = properties_by_type()
        for name, properties in types.iteritems():
            write_header(fp,name,1)
            for property in properties:
                if property.node:
                    items  = [('key', property.name),
                              ('type', property.type),
                              ('node type constraint', property.nodetype),
                              ('include donors', property.includedonors),
                              ('operation restrictions', ', '.join(property.operations) if property.operations else 'None'),
                              ('inclusion rule parameter', property.parameter),
                              ('inclusion rule value', property.value),
                              ('property value restrictions', ', '.join(property.values) if property.values else 'None')
                              ]
                elif property.semanticgroup:
                    items = [('key', property.name),
                             ('type', property.type),
                             ('property value restrictions', ', '.join(property.values) if property.values else 'None')]
                else:
                    items = [('key', property.name),
                             ('type', property.type),
                             ('mandatory', property.mandatory),
                             ('property value restrictions', ', '.join(property.values) if property.values else 'None')]

                write_bullet_emphasize(fp, property.description, property.information, items)


def to_operations_md():
    with open('operations.md','w') as fp:
        for category, operations in operations_by_category().iteritems():
            write_header(fp,category,1)
            for operation_name in operations:
                operation = getOperation(operation_name)
                write_header(fp, operation_name, 2, status='deprecated' if operation.deprecated else None)
                write_text(fp,operation.description)
                default_inc_mask = getValue(operation.includeInMask,'default')
                mask_included = {file_type:getValue(operation.includeInMask,file_type,default_inc_mask)
                                 for file_type in ['video','audio','image']}
                mask_included = [x for x,y in mask_included.iteritems() if y]
                fp.write('\nInclude as Probe Mask for [%s]\n' % ', '.join(mask_included))
                write_header(fp, 'Mandatory Paramaters', 3)
                for key, definition in operation.mandatoryparameters.iteritems():
                    write_parameter(fp, key, definition)
                write_header(fp, 'Optional Paramaters', 3)
                for key, definition in operation.optionalparameters.iteritems():
                    write_parameter(fp, key, definition)
                write_header(fp, 'Validation Rules', 3)
                for rule in operation.rules:
                    write_rule(fp, rule)
                write_header(fp, 'Allowed Transitions', 3)
                for rule in operation.transitions:
                    write_bullet(fp, rule)
                write_header(fp, 'QA Questions', 3)
                if operation.qaList is not None:
                    for rule in operation.qaList:
                        write_bullet(fp, rule)
                write_header(fp, 'Analysis Rules', 3)
                for rule in operation.analysisOperations:
                    write_analysis(fp, rule)


def main(args):
    to_operations_md()
    to_properties_md()

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))




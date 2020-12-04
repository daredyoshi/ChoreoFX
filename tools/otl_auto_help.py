#!/usr/bin/env hython
"""
This should be run from within a houdini python "hython" session.
To set that up source your houdini environment and then execute the script with

hython ./otl_auto_help.py

It will generate helop files for any nodes that do not already have help files. It will pre-fill those files
with the ChoreoFX icon as well as fill in all the parameters it can find on the operators themselves.
"""
import os 
import hou

CWD = os.path.dirname(os.path.realpath(__file__))

HELP_TEMPLATE = r'''= {pretty_name} =
#icon: /Icons/ChoreoFX.svg
#tags: crowds, agents, ChoreoFX

"""Documentation is Coming soon!"""

This is placeholder documentation for {pretty_name}

@parameters
{parms}

@inputs

Placeholder:
    Description of input

@outputs

Placeholder:
    Description of output
'''

PARM_TEMPLATE = """
{pretty_name}:
	#id: {name}
	ToDo
"""

def generate_parm_lines(parm_template_group):
	parm_string = ""
	for parm_template in parm_template_group.parmTemplates():
		# create pretty headers from folder
		if (parm_template.type() == hou.parmTemplateType.Folder):
			parm_string += ('\n== {} =='.format(parm_template.label()))
			parm_string += generate_parm_lines(parm_template)
		else:
			if not parm_template.label() or not parm_template.name():
				continue
			parm_string += PARM_TEMPLATE.format(pretty_name=parm_template.label(), name=parm_template.name())
	return parm_string


def generate_help_for_node_type(node_type):
	node_type_category_lower = node_type.category().name().lower()
	_, namespace, optype, version = node_type.nameComponents()

	help_dir = os.path.abspath(os.path.join(CWD, '..', 'houdini', 'help', 'nodes', node_type_category_lower))
	help_name = '{}--{}-{}.txt'.format(namespace, optype, version)
	help_path = os.path.join(help_dir, help_name)

	if os.path.exists(help_path):
		print "Skipping {} because it already exists"
		return


	if not os.path.exists(help_dir):
		os.makedirs(help_dir)

	parm_template_group = node_type.parmTemplateGroup()

	parm_lines = generate_parm_lines(parm_template_group)

	help_lines = HELP_TEMPLATE.format(
		pretty_name=node_type.description(),
		parms=parm_lines
	)

	with open(help_path, 'w') as f:
		f.write(help_lines)
		print "Generated auto help {}".format(help_path)


def get_all_choreofx_node_types():
	choreofx_node_types = []
	for node_type_category in hou.nodeTypeCategories().values():
		for node_type in node_type_category.nodeTypes().values():
			if node_type.nameComponents()[1] == "choreofx":
				choreofx_node_types.append(node_type)

	return choreofx_node_types

if __name__ == "__main__":
	# to collect all choreofx nodes
	all_choreofx_node_types = get_all_choreofx_node_types()
	for node_type in all_choreofx_node_types:
		generate_help_for_node_type(node_type)
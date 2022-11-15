"""
Flame Project Utilties
    *Flame Project utility*

- Author: Danny Yoon
- Version: 1.0.0

"""

# Changelog:
#     - 1.0.0 (2021.12.04) Added get_project_dict function

__version__ = "1.0.0"

#TODO: make a get project function that uses  /opt/Autodesk/wiretap/tools/current/wiretap_print_tree  -n /projects/TLA_2020x1_hubble
#TODO: Parse this to get Workspace and Shared Library entries.


def _get_projects_from_list(lines):
    """
    _get_projects_from_list()
        Parse /opt/Autodesk/project/project.db file to get project information

    :param lines: Lines of text to parse project info.

    :return: Dictionary of project information.

    - Values are STRINGS! So you need to convert to int or float if needed.
    - Name of the project can be found in the "Name" key.
    """
    import re

    # parse lines
    project_list = []
    for line in lines:
        # use regex to get only the project name
        match = re.match(r'Project:(\w+)={(.+)}', line)
        if match:
            # return project name
            projname = match.group(1)
            paramlist = match.group(2).split(',')
            projdict = {}
            projdict['Name'] = projname
            for param in paramlist:
                paramsplit = param.split('=')
                if len(paramsplit) == 2:
                    projdict[paramsplit[0]] = paramsplit[1].strip('"')
            project_list.append(projdict)
    return project_list

def get_project_from_db(path='/opt/Autodesk/project/project.db'):
    """
    get_project_from_db()
        Get project name from project.db file
    :param path: Path to project.db file
    :return: Project name

    - Values are STRINGS! So you need to convert to int or float if needed.
    - Name of the project can be found in the "Name" key.
    """
    with open(path, 'r') as f:
        lines = f.readlines()
        return _get_projects_from_list(lines)

def get_project_info_from_str(text):
    """
    get_project_info_from_str()
        Get project information from string

    :param text: String to parse
    :return: Dictionary of project information.

    - Values are STRINGS! So you need to convert to int or float if needed.
    - Name of the project can be found in the "Name" key.
    """

    return _get_projects_from_list(text.splitlines())



def get_project_names(project_list):
    """
    get_project_names()
        Get list of project names

    :param project_list: List of project dictionaries

    :return: List of project names.
    """
    project_names = []
    for project in project_list:
        project_names.append(project['Name'])
    return project_names


if __name__ == '__main__':

    from pprint import pprint

    print('get_project_names() OUTPUT:')
    print(get_project_names(get_project_from_db()))

    print('get_project_info_from_str() OUTPUT:')
    teststr = """
Project:Recovered_Media_2021_1={Description="",CreationDate="2021-11-18 14:53:24",SetupDir="Recovered_Media_2021_1",Partition="",HardPtn="stonefs5",Version="8977",FrameWidth="1920",FrameHeight="1080",PixelFormat="124",AspectRatio="1.77778",ProxyEnable="0",ProxyWidth="960",ProxyWidthHint="0.5",ProxyPixelFormat="124",ProxyDepthMode="1",ProxyMinFrameSize="720",ProxyAbove8bits="0",ProxyQuality="lanczos",FieldDominance="2",,ProcessMode="GPU",ProxyRegenState="0",Default="False",ModulePattern="",SoftFxPattern="",TransitionPattern="",ModuleType="",SoftFxType="",TransitionType="",IntermediatesProfile="0",LicenceType=""}  
    """
    pprint(get_project_info_from_str(teststr))

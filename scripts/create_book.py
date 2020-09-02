import nbformat as nbf
import glob
import yaml
from os import path
import json
import copy
from jinja2 import Template

# ******* Paths for notebooks ********
attack_paths = {
    "TA0001" : "01_initial_access",
    "TA0002" : "02_execution",
    "TA0003" : "03_persistence",
    "TA0004" : "04_privilege_escalation",
    "TA0005" : "05_defense_evasion",
    "TA0006" : "06_credential_access",
    "TA0007" : "07_discovery",
    "TA0008" : "08_lateral_movement",
    "TA0009" : "09_collection",
    "TA0011" : "11_command_and_control",
    "TA0010" : "10_exfiltration",
    "TA0040" : "40_impact"
}

# ******* Datasets Summary *********
summary_table = [
    {
        "platform" : "Windows",
        "dataset" : []
    },
    {
        "platform" : "Linux",
        "dataset" : []
    },
    {
        "platform" : "Mac",
        "dataset" : []
    },
    {
        "platform" : "AWS",
        "dataset" : []
    }
]

# ******* Initial TOC Template ********
with open('templates/toc_template.json') as json_file:
    toc_template = json.load(json_file)

# ******** Open every metadata yaml file available ****************
print("[+] Opening metadata yaml files..")
metadata_files = glob.glob(path.join(path.dirname(__file__), "..", "datasets/metadata", "*.yaml"))
metadata_loaded = [yaml.safe_load(open(metadata_file).read()) for metadata_file in metadata_files]

# ******** Translating YAML files to Notebooks ****************
print("\n[+] Translating YAML files to notebooks..")
for metadata in metadata_loaded:
    print("  [>>] Processing {} {} file..".format(metadata['id'], metadata['title']))
    # **** METADATA ****
    notebook_metadata = {
        "kernelspec": {
            "display_name": "PySpark_Python3",
            "language": "python",
            "name": "pyspark3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.7.3"
        }
    }
    # **** INITIALIZE NOTEBOOK ****
    nb = nbf.v4.new_notebook(metadata=notebook_metadata)
    nb['cells'] = []
    # *** TITLE ****
    nb['cells'].append(nbf.v4.new_markdown_cell("# {}".format(metadata['title'])))
    # *** METADATA ****
    nb['cells'].append(nbf.v4.new_markdown_cell("## Metadata"))
    if metadata['simulation_environment']:
        simulation_environment = metadata['simulation_environment']
    else:
        simulation_environment = ''
    if 'script' in metadata['simulation_framework']:
        simulation_script = metadata['simulation_framework']['script']
    else:
        simulation_script = ''
    if metadata['adversary_view']:
        adversary_view = metadata['adversary_view']
    else:
        adversary_view = ''
    table = """
|                   |    |
|:------------------|:---|
| id                | {} |
| author            | {} |
| creation date     | {} |
| platform          | {} |
| Mordor Environment| {} |
| Simulation Type   | {} |
| Simulation Tool   | {} |
| Simulation Script | {} |""".format(metadata['id'], metadata['author'], metadata['creation_date'], metadata['platform'], simulation_environment, metadata['simulation_framework']['type'], metadata['simulation_framework']['name'], simulation_script)
    table_list = [table]
    for dataset in metadata['dataset']:
        table_list.append("| Dataset           | {} |".format(dataset['link']))
    table_list.append("| References        | {} |".format(metadata['references']))
    table_strings = '\n'.join(map(str, table_list))
    nb['cells'].append(nbf.v4.new_markdown_cell(table_strings))
    # *** DATASET DESCRIPTION ****
    nb['cells'].append(nbf.v4.new_markdown_cell("""## Dataset Description
{}""".format(metadata['description'])))
    # *** ADVERSARY VIEW ****
    nb['cells'].append(nbf.v4.new_markdown_cell("""## Adversary View
```
{}
```""".format(metadata['adversary_view'])))
    # *** EXPLORE DATASET ****
    nb['cells'].append(nbf.v4.new_markdown_cell("## Explore Mordor Dataset"))
    nb['cells'].append(nbf.v4.new_markdown_cell("### Initialize Analytics Engine"))
    nb['cells'].append(nbf.v4.new_code_cell(
        """from openhunt.mordorutils import *
spark = get_spark()"""
    ))
    nb['cells'].append(nbf.v4.new_markdown_cell("### Download & Process Mordor File"))
    for dataset in metadata['dataset']:
        if dataset['type'] == 'Windows Event Logs':
            dataset_file = dataset['link']
            break
    nb['cells'].append(nbf.v4.new_code_cell(
        """mordor_file = "{}"
registerMordorSQLTable(spark, mordor_file, "mordorTable")""".format(dataset_file)
    ))
    nb['cells'].append(nbf.v4.new_markdown_cell("### Get to know your data"))
    nb['cells'].append(nbf.v4.new_code_cell(
        """df = spark.sql(
    '''
SELECT *
FROM mordorTable
    '''
)
df.printSchema()
        """))

    platform = metadata['platform'].lower()
    # ***** Update Summary Tables *******
    for table in summary_table:
        if platform in table['platform'].lower():
            for attack in metadata['attack_mappings']:
                for tactic in attack['tactics']:
                    metadata['location'] = attack_paths[tactic]
                    if metadata not in table['dataset']:
                        table['dataset'].append(metadata)

    # ***** Update main TOC template and creating notebook *****
    for attack in metadata['attack_mappings']:
        for to in toc_template:
            if 'chapters' in to.keys():
                for chapter in to['chapters']:
                    if "notebooks/small/{}/{}".format(platform,platform) in chapter.values():
                        for section in chapter['sections']:
                            for tactic in attack['tactics']:
                                if attack_paths[tactic] in section['file']:
                                    metadataDict = {
                                        "file" : "notebooks/small/{}/{}/{}".format(platform,attack_paths[tactic], metadata['id'])
                                    }
                                    if metadataDict not in section['sections']:
                                        print("    [>>] Adding {} to {} path..".format(metadata['id'], attack_paths[tactic]))
                                        section['sections'].append(metadataDict)
                                        print("    [>>] Writing {} as a notebook to {}..".format(metadata['title'], attack_paths[tactic]))
                                        nbf.write(nb, "../docs/notebooks/small/{}/{}/{}.ipynb".format(platform,attack_paths[tactic],metadata['id']))

# ****** Removing empty lists ********
print("\n[+] Removing empty platforms and empty lists..")
for toc in toc_template[:]:
    if 'chapters' in toc.keys():
        for chapter in toc['chapters']:
            if 'sections' in chapter.keys() and len(chapter['sections']) > 0:
                for section in chapter['sections'][:]:
                    if 'sections' in section and not section['sections']:
                        print("  [>>] Removing {} ..".format(section['file']))
                        chapter['sections'].remove(section)

# ****** Creating Datasets Summaries ******
print("\n[+] Creating ATT&CK navigator layers for each platform..")
# Reference: https://github.com/mitre-attack/car/blob/master/scripts/generate_attack_nav_layer.py#L30-L45
for summary in summary_table:
    if len(summary['dataset']) > 0:
        techniques_mappings = dict()
        for dataset in summary['dataset']:
            metadata = dict()
            metadata['name'] = dataset['title']
            metadata['value'] = dataset['id'] 
            for coverage in dataset['attack_mappings']:
                technique = coverage['technique']
                if coverage['sub-technique']:
                    technique = technique + '.' + coverage['sub-technique']
                if technique not in techniques_mappings:
                    techniques_mappings[technique] = []
                    techniques_mappings[technique].append(metadata)
                elif technique in techniques_mappings:
                    if metadata not in techniques_mappings[technique]:
                        techniques_mappings[technique].append(metadata)
        
        VERSION = "3.0" 
        NAME = "THP {} Analytics".format(summary['platform'])
        DESCRIPTION = "Analytics covered by the Threat Hunter Playbook {} detection notebooks".format(summary['platform'])
        DOMAIN = "mitre-enterprise"
        PLATFORM = summary['platform'].lower()

        print("  [>>] Creating navigator layer for {} metadatas..".format(summary['platform']))
        thp_layer = {
            "description": DESCRIPTION,
            "name": NAME,
            "domain": DOMAIN,
            "version": VERSION,
            "techniques": [
                {
                    "score": 1,
                    "techniqueID" : k,
                    "metadata": v
                } for k,v in techniques_mappings.items()
            ],
            "gradient": {
                "colors": [
                    "#ffffff",
                    "#66fff3"
                ],
                "minValue": 0,
                "maxValue": 1
            },
            "legendItems": [
                {
                    "label": "Datasets researched",
                    "color": "#66fff3"
                }
            ]
        }
        open('../docs/notebooks/small/{}/{}.json'.format(PLATFORM,PLATFORM), 'w').write(json.dumps(thp_layer))
    
print("\n[+] Creating dataset summary tables for each platform..")
summary_template = Template(open('templates/summary_template.md').read())
for summary in summary_table:
    if len(summary['dataset']) > 0:
        print("  [>>] Creating summary table for {} datasets..".format(summary['platform']))
        summary_for_render = copy.deepcopy(summary)
        markdown = summary_template.render(summary=summary_for_render)
        open('../docs/notebooks/small/{}/{}.md'.format(summary['platform'].lower(),summary['platform'].lower()), 'w').write(markdown)

# ******* Update Jupyter Book TOC File *************
print("\n[+] Writing final TOC file for Jupyter book..")
with open(r'../docs/_toc.yml', 'w') as file:
    yaml.dump(toc_template, file, sort_keys=False)

# -*- coding: utf-8 -*-

import os
import urlparse
import requests
from lxml import etree
from io import BytesIO
from io import StringIO
from subprocess import call
import string
import random
    
# Attempting to retrieve a Taverna workflow from myexperiment.org. This makes use of the website's RESTful API.

# For now we are merely identifying a workflow by its ID.

response = requests.get('http://www.myexperiment.org/workflow.xml?id=3859')

# Using the lxml XML parser to parse the entry page in order to get the URL of the Taverna file.

parser = etree.XMLParser(ns_clean=True)
tree = etree.parse(BytesIO(response.content), parser)

# Parsing the page for the URL of the Taverna workflow and retrieving it.

workflow_url = tree.xpath('content-uri/text()')
workflow = requests.get(workflow_url[0])

# Extracting the filename from the URL

parse_list = urlparse.urlparse(workflow_url[0]).path.split('/')
filename_workflow = parse_list[len(parse_list) - 1]

if not os.path.isabs(filename_workflow):
    abs_filename_workflow = os.path.abspath(filename_workflow)
else:
    abs_filename_workflow = filename_workflow

taverna_version = 0

if filename_workflow.endswith('.xml'):
    taverna_version = 1
    print('Retrieved a Taverna 1 file with name \'%s\'.' % filename_workflow)

if filename_workflow.endswith('.t2flow'):
    taverna_version = 2
    print('Retrieved a Taverna 2 file with name \'%s\'.' % filename_workflow)

    
# Saving the workflow in the current directory

if taverna_version != 0:
    if not os.path.isfile(abs_filename_workflow):
        workflow_file = open(abs_filename_workflow, 'w')
        workflow_file.write(workflow.text.encode('utf-8'))
        workflow_file.close()
    else:
        print("A file with the name \'%s\' already exists!" % filename_workflow)

# Parsing the workflow file

    workflow_file = open(abs_filename_workflow, 'rb')

    workflow_parser = etree.XMLParser(ns_clean=True)
    workflow_dom = etree.parse(workflow_file, workflow_parser)

    workflow_file.close()

# Retrieving the names of the input ports and the output ports.

    if taverna_version == 2:

        input_ports = workflow_dom.xpath("//*[local-name()='workflow']/*[local-name()='dataflow'][1]/*[local-name()='inputPorts']/*[local-name()='port']/*[local-name()='name'][1]/text()")
        print 'Number of input ports: %u' % len(input_ports)
        print 'List of input ports: %s' % input_ports

        output_ports = workflow_dom.xpath("//*[local-name()='workflow']/*[local-name()='dataflow'][1]/*[local-name()='outputPorts']/*[local-name()='port']/*[local-name()='name'][1]/text()")
        print 'Number of output ports: %u' % len(output_ports)
        print 'List of output ports: %s' % output_ports

    if taverna_version == 1:

        input_ports = workflow_dom.xpath("/*[name()='s:scufl']/*[name()='s:source']/@name")
        print 'Number of input ports: %u' % len(input_ports)
        print 'List of input ports: %s' % input_ports

        output_ports = workflow_dom.xpath("/*[name()='s:scufl']/*[name()='s:sink']/@name")
        print 'Number of output ports: %u' % len(output_ports)
        print 'List of output ports: %s' % output_ports



# Generating the content strings for the Dockerfile

    dockerfile_content = """FROM ubuntu:latest
MAINTAINER Asela Rajapakse <asela.rajapakse@mpimet.mpg.de>
RUN apt-get update && apt-get --yes --allow-unauthenticated install apt-utils
RUN apt-get --yes --allow-unauthenticated install wget && wget https://bitbucket.org/taverna/taverna-commandline-product/downloads/taverna-commandline-core-2.5.0-linux_amd64.deb && dpkg -i taverna-commandline-core-2.5.0-linux_amd64.deb
RUN apt-get --yes --allow-unauthenticated install python && apt-get --yes --allow-unauthenticated install python-pip && pip install --upgrade pip && pip install requests && apt-get --yes --allow-unauthenticated install python-lxml\n"""

    label_content =  """LABEL 'eudat.gef.service.name'='Taverna invocation of %s'
LABEL 'eudat.gef.service.input_directory.path'='/input_directory'
LABEL 'eudat.gef.service.output_directory.path'='/output_directory'\n""" % filename_workflow

    label_content += "LABEL 'eudat.gef.service.input_ports_no'='%s'\n" % len(input_ports)

    for port_no in range(len(input_ports)):
        label_content += "LABEL 'eudat.gef.service.input_port.%u.name'='%s'\n" % (port_no, input_ports[port_no])

    label_content += "LABEL 'eudat.gef.service.output_ports_no'='%s'\n" % len(output_ports)

    for port_no in range(len(output_ports)):
        label_content += "LABEL 'eudat.gef.service.output_port.name'='%s'\n" % output_ports[port_no]

    workflow_copy_content = """COPY %s /Taverna_workflows/
RUN chmod +x /Taverna_workflows/%s\n""" % (filename_workflow,filename_workflow)



# Creating a Dockerfile that builds the image with the Taverna workflow.

    empty_string = ""
    random_string = empty_string.join(random.choice('abcdefghijklmnopqrs0123456789') for _ in range(20))

    filename_dockerfile = random_string

    if not os.path.isabs(filename_dockerfile):
        abs_filename_dockerfile = os.path.abspath(filename_dockerfile)
    else:
        abs_filename_dockerfile = filename_dockerfile

    if not os.path.isfile(abs_filename_dockerfile):
       file = open(abs_filename_dockerfile, 'w')
       file.write(dockerfile_content)
       file.write(label_content)
       file.write(workflow_copy_content)
       file.close()
    else:
       print("A file with the name \'%s\' already exists!" % filename_dockerfile)

    call(['docker', 'build', '-t', 'service_example_xkcd:latest', '-f', '%s' % filename_dockerfile, '.'])

    os.remove(abs_filename_workflow)
    os.remove(abs_filename_dockerfile)

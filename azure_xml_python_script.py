import subprocess
from bs4 import BeautifulSoup as Soup,Comment
import argparse
import os.path
from os import path
import re


# this function is used to get connected to database
def get_cursor():
    import pymysql
    print("Connecting to db...")
    # Define Variables
    # Define Variables
    DBHost = '139.59.50.66'
    DBUser = 'effort'
    DBPass = 'nokpyukwa203'
    DBName = 'Automation_Deployments'

    db = pymysql.connect(host=DBHost, user=DBUser, passwd=DBPass, db=DBName)
    crsr = db.cursor()
    print("DB CURSOR")
    print("Connecting to db... "+DBHost)
    return db, crsr


def standardize_root_context_file(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()
    with open(file_path,"w") as f:
        for line in lines:
            if "RedisHttpSessionConfiguration" in line:
                line = line.replace("<!--", "").replace("-->", "")
            f.write(line)


def handle_web_xml_comments(file_path):
    with open(file_path, "r") as fo:
        content = fo.readlines()
        content = "".join(content)
        # If Spring Session to be commented, keep the platform verifier in the if statement
        if platform == 'api':
            pattern = '''\s*<filter>(\n|\s)*<filter-name>springSessionRepositoryFilter</filter-name>(\n|\s)*<filter-class>org.springframework.web.filter.DelegatingFilterProxy</filter-class>(\n|\s)*</filter>(\n|\s)*<filter-mapping>(\n|\s)*<filter-name>springSessionRepositoryFilter</filter-name>(\n|\s)*<url-pattern>/\*</url-pattern>(\n|\s)*</filter-mapping>\s*'''
            rep = '''<!--  <filter>
                  <filter-name>springSessionRepositoryFilter</filter-name>
                  <filter-class>org.springframework.web.filter.DelegatingFilterProxy</filter-class>
              </filter>
              <filter-mapping>
                  <filter-name>springSessionRepositoryFilter</filter-name>
                  <url-pattern>/*</url-pattern>
              </filter-mapping> -->'''
            content = re.sub(pattern, rep, content)
            subprocess.call(["cp", file_path, file_path + ".bck"])
            f = open(file_path, "w")
            f.write(content)
        else:
            pattern = '''<!--\s*<filter>(\n|\s)*<filter-name>springSessionRepositoryFilter</filter-name>(\n|\s)*<filter-class>org.springframework.web.filter.DelegatingFilterProxy</filter-class>(\n|\s)*</filter>(\n|\s)*<filter-mapping>(\n|\s)*<filter-name>springSessionRepositoryFilter</filter-name>(\n|\s)*<url-pattern>/\*</url-pattern>(\n|\s)*</filter-mapping>\s*-->'''
            rep = '''  <filter>
          <filter-name>springSessionRepositoryFilter</filter-name>
          <filter-class>org.springframework.web.filter.DelegatingFilterProxy</filter-class>
      </filter>
      <filter-mapping>
          <filter-name>springSessionRepositoryFilter</filter-name>
          <url-pattern>/*</url-pattern>
      </filter-mapping>'''
            content = re.sub(pattern,rep,content)
            subprocess.call(["cp", file_path, file_path + ".bck"])
            f = open(file_path, "w")
            f.write(content)


def write_file(write_file_name):
    global bs_content
    f = open(write_file_name, "w")
    if bs_content.body:
        bs_content = bs_content.body.next
    elif bs_content.html:
        bs_content = bs_content.html.next
    else:
        bs_content = bs_content
    #f.write(bs_content.prettify())
    f.write(str(bs_content))


def updateXML(tag,tagName,tagValue,updateParam,updateValue):
    for item in bs_content.find_all(tag,{tagName: tagValue}):
        if not updateParam:
            item.string = updateValue
        else:
            for child in item.children:
                try:
                    if child["name"] == updateParam:
                        child["value"] = updateValue
                except:
                    pass


def comment_elements(commentValue):
    if platform == 'api':
        tags = {"task:scheduler" : "id","task:scheduled-tasks" : "scheduler"}
        for tag in list(tags.keys()):
            toBeCommented = bs_content.find_all(tag,{tags[tag]:commentValue})
            for item in toBeCommented:
                item.replace_with(Comment(str(item)))
    else:
        toBeCommented = bs_content.find_all(commentValue)
        print (toBeCommented)
        for item in toBeCommented:
            item.replace_with(Comment(str(item)))


def uncomment_elements(uncommentValue):
    global bs_content
    for comment in bs_content(text=lambda text: isinstance(text, Comment)):
        if uncommentValue in comment.string:
            tag = Soup(comment, "xml")
            #tag = tag.body
            for item in tag.children:
                if item:
                    item.replace_with(Comment(str(item)))
            comment.replace_with(tag)
    file = 'temp_file.xml'
    write_file(file)
    with open(file, "r") as f:
        lines = f.readlines()
    with open(file, "w") as f:
        for line in lines:
            if line.strip("\n") != "<body>" and line.strip("\n") != "</body>":
                f.write(line)
    with open(file, "r") as f:
        content = f.readlines()
        content = "".join(content)
        bs_content = Soup(content, "xml")
    subprocess.call(["rm", file])
    for comment in bs_content(text=lambda text: isinstance(text, Comment)):
        if uncommentValue in comment.string:
            tag = Soup(comment, "xml")
            #tag = tag.body.next
            comment.replace_with(tag)



def handle_scheduler(uncom):
    import_items = bs_content.find_all("import")
    for item in import_items:
        if re.search("schedulars.xml", item["resource"].lower()):
            toBeCommented = bs_content.find_all("import",{"resource": item["resource"]})[0]
            toBeCommented.replace_with(Comment(str(item)))
    uncomment_elements(uncom)


def handle_scheduler_api_tomcat2():
    global bs_content
    updateValues = {
                    "task:scheduler" : {'id': "bulkUploadScheduler", "pool-size": "1"},
                    "task:scheduled-tasks" : [{"scheduler" : "bulkUploadScheduler"},{"task:scheduled" : {"ref" : "bulkUploadSchedulerTask", "method" : "processBulkUpload", "cron" : "30* * * * * ?"}}]
                    }
    Otag = bs_content.beans
    for value in updateValues.keys():
        if type(updateValues[value]) is list:
            parentTag = bs_content.new_tag(value, **updateValues[value][0])
            childTag = bs_content.new_tag(list(updateValues[value][1].keys())[0], **dict(list(updateValues[value][1].values())[0]))
            parentTag.append(childTag)
            Otag.append(parentTag)
        else:
            newTag = bs_content.new_tag(value, **updateValues[value])
            Otag.append(newTag)


def process_constants_file():
    global bs_content
    valuesToBeUpdated = {}
    if tomcat == "tomcat1":
        valuesToBeUpdated = {"jmsDestination" : "Effortx-api-tomcat1",
                             "jmsDestinationForJobAddOrModifi" : "EffortxJobAddMod-api-tomcat1",
                             "jmsDestinationForJobCompletedRecieve" : "EffortxJobCompleted-api-tomcat1"}
    elif tomcat == "tomcat2":
        valuesToBeUpdated = {"jmsDestination" : "Effortx-api-tomcat2",
                             "jmsDestinationForJobAddOrModifi" : "EffortxJobAddMod-api-tomcat2",
                             "jmsDestinationForJobCompletedRecieve" : "EffortxJobCompleted-api-tomcat2"}
    for value in valuesToBeUpdated.keys():
        toBeUpdated = bs_content.find("entry",{ "key":value})
        toBeUpdated.string.replace_with(valuesToBeUpdated[value])


def handle_exceptions(filename):
    global bs_content
    f = open("temp_"+filename, "w")
    f.write(bs_content.prettify())
    f.close()
    with open("temp_"+filename, "r") as f:
        lines = f.readlines()
    if filename == 'root-context.xml':
        with open("temp_"+filename, "w") as f:
            for line in lines:
                if "property-placeholder" in line and not "context:property-placeholder" in line:
                    line = re.sub("property-placeholder","context:property-placeholder",line)
                f.write(line)
        with open("temp_"+filename, "r") as f:
            content = f.readlines()
            content = "".join(content)
            bs_content = Soup(content, "xml")
        subprocess.call(["rm", "temp_"+filename])
        if platform != 'track' and platform != 'mobile' and platform != 'report' and platform != 'web' and platform != 'api':
            x = '<import resource="schedulars.xml" />'
            xx = Soup(x, 'xml')
            bs_content.beans.append(xx)
    elif filename == 'activemq-context.xml':
        with open("temp_"+filename, "w") as f:
            for line in lines:
                if "listener" in line and not "jms:listener" in line:
                    line = re.sub("listener", "jms:listener", line)
                f.write(line)
        with open("temp_"+filename, "r") as f:
            content = f.readlines()
            content = "".join(content)
            bs_content = Soup(content, "xml")
        subprocess.call(["rm", "temp_"+filename])


def handle_datasources():
    if platform == 'api':
        # toBeCommented = bs_content.find_all('property', {"name": "jdbcUrl"})
        # item = toBeCommented[1]
        # item.replace_with(Comment(str(item)))
        uncommentValue = 'value="120000"'
        uncomment_elements(uncommentValue)
    else:
        toBeCommented = bs_content.find_all('property',{"name":"jdbcUrl"})
        for item in toBeCommented:
            item.replace_with(Comment(str(item)))
        uncommentValue = "connectTimeout=30000&amp;socketTimeout=60000"
        uncomment_elements(uncommentValue)


subprocess.call(["date"])
parser = argparse.ArgumentParser()
parser.add_argument("--files", "-f", help="input XML filename", required=True)
parser.add_argument("--dir", "-d", help="input Folder name", required=True)
# parser.add_argument("--env", "-e",help = "input Environment", required=True)
parser.add_argument("--platform", "-p", help="input Platform", required=True)
# parser.add_argument("--variables", "-v",help = "input Platform", required=True)

args = parser.parse_args()

file_list = args.files.split(",")
base_dir = args.dir
environment = 'test'  # args.env
platform = args.platform
# variables = args.variables

tomcat = base_dir.split("/")[2].split("-")[3]

print(base_dir, file_list, platform)

definedFiles = ['root-context.xml', 'kj-constants.xml', 'web.xml', 'activemq-context.xml', 'log4j.properties',
                'nd-constants.xml', 'schedulars.xml', 'constants.xml']

content = []

# Parameter Mapping
db, crsr = get_cursor()
if platform == "mobile" or platform == "track":
    cmd = '''SELECT `key`,`value` FROM Spoors_Prod_Track'''
elif platform == "web" or platform == "report":
    cmd = '''SELECT `key`,`value` FROM Spoors_Prod_Web'''
elif platform == "api":
    cmd = '''SELECT `key`,`value` FROM Spoors_Prod_Api'''
else:
    cmd = '''SELECT `key`,`value` FROM Spoors_Prod_Track'''
crsr.execute(cmd)
data = crsr.fetchall()

parameterMap = {}
for item in data:
    parameterMap.update({item[0]: item[1]})

# Set platform directory
if platform == "web" or platform == "report":
    platformDir = "effortx"
elif platform == "api":
    platformDir = "effort6"
elif platform == "mobile" or platform == "track":
    platformDir = "mobile"
else:
    platformDir = "effortx"


for file in file_list:
    print ("Processing file - "+file)
    if file == "web.xml":
        file_path = base_dir+"/"+platformDir+"/WEB-INF/"+file
    elif file == "log4j.properties":
        file_path = base_dir + "/" + platformDir + "/WEB-INF/classes/" + file
    else:
        file_path = base_dir + "/" + platformDir + "/WEB-INF/spring/" + file

    if not path.exists(file_path):
        print("No Such Input File Exists. Please check & retry!!!")
        exit(1)
    elif not file in definedFiles:
        print("Not sure what to do with the file, please contact DevOps Admin.")
        exit(1)

    # Read the XML file
    if file == "log4j.properties":
        if platform == 'api':
            continue
        with open(file_path, "r") as f:
            lines = f.readlines()
        subprocess.call(["mv", file_path, file_path + ".bck"])
        with open(file_path, "w") as f:
            for line in lines:
                if "log4j.rootLogger" in line:
                    line = re.sub("INFO", "ERROR", line)
                f.write(line)
        continue

    if file == "web.xml":
        handle_web_xml_comments(file_path)
        continue
    if file == "root-context.xml" and (platform == 'report' or platform == 'web'):
        standardize_root_context_file(file_path)
    with open(file_path, "r") as fo:
        # Read each line in the file, readlines() returns a list of lines
        content = fo.readlines()
        # Combine the lines in the list into a string
        content = "".join(content)
        bs_content = Soup(content, "xml")
    if file == "root-context.xml":
        tag = "bean"
        tagName = "class"
        # if platform == 'report' or platform == 'web':
        #     tagValue = "org.springframework.data.redis.connection.jedis.JedisConnectionFactory"
        # else:
        tagValue = "org.springframework.data.redis.connection.jedis.JedisConnectionFactory"
        updateParam = "hostName"
        updateValue = "192.168.77.46"
        constantsFile = ''
        for constantsFile in file_list:
            if "constants.xml" in constantsFile:
                break
        uncommentValue = "/WEB-INF/spring/"+constantsFile
        commentValue = "context:property-placeholder"
        schedular_file = "chedulars.xml"

        comment_elements(commentValue)
        uncomment_elements(uncommentValue)
        if ((platform != 'track' and platform != 'mobile') and (platform != 'report' and platform != 'web')) and (platform == 'api' and tomcat == "tomcat1"):
            handle_scheduler(schedular_file)
        if platform == 'api' and tomcat == "tomcat2":
            handle_scheduler_api_tomcat2()
        if environment != 'test' and (platform != 'track' and platform != 'mobile'):
            updateXML(tag, tagName, tagValue, updateParam, updateValue)
        if (platform == 'report' or platform == 'web'):
            updateXML(tag, tagName, tagValue, updateParam, updateValue)
        if (platform != 'report' and platform != 'web') or (platform == 'api'):
            handle_datasources()
        handle_exceptions(file)
    elif file == "kj-constants.xml" or file == 'nd-constants.xml':
        params = list(parameterMap.keys())
        for parameter in params:
            tag = "entry"
            tagName = "key"
            tagValue = parameter
            updateParam = ""
            updateValue = parameterMap[tagValue]
            updateXML(tag, tagName, tagValue, updateParam, updateValue)
    elif file == "activemq-context.xml":
        if ((platform == 'track' or platform == 'mobile') and tomcat == 'tomcat4') or \
                ((platform == 'report' or platform == 'web') and tomcat == 'tomcat3') or \
                (platform == 'api') or \
                ((platform != 'track' and platform != 'mobile') and\
                (platform != 'report' and platform != 'web')):
            uncommentValueList = ["jmsDestinationForJobCompletedRecieve", "jmsDestination"]
            for uncommentValue in uncommentValueList:
                print("Uncomment - " + uncommentValue)
                uncomment_elements(uncommentValue)
            handle_exceptions(file)
        elif ((platform == 'track' or platform == 'mobile') and tomcat != 'tomcat4') or\
            ((platform == 'report' or platform == 'web') and tomcat != 'tomcat4'):
            commentValue = "jms:listener-container"
            comment_elements(commentValue)
    elif file == "schedulars.xml":
        print ("I am here")
        if platform == 'api':
            print ("Now I am here")
            toBeCommented = ['revGeoScheduler', 'bulkUploadScheduler', 'processFlatTableDataStatusLocationsSchedularLocation', 'processFlatTableDataStatusSchedularEmployee']
            for item in toBeCommented:
                print (item)
                comment_elements(item)
    elif file == "constants.xml":
        process_constants_file()
    else:
        print ("Did not match with what I know.....")
        pass
    subprocess.call(["cp",file_path,file_path+".bck"])
    write_file(file_path)

import hashlib
import socket
import time
import lib.client as mqtt
import sys
import array
import random
import ConfigParser
import struct
#import ParadoxMap
import importlib
#from ParadoxMap import ParadoxMG5050EventMap, ParadoxMG5050Registers

#Do not edit these variables here, use the config.ini file instead.
Zone_Amount = 32
passw = "abcd"
user = "1234"
IP150_IP = "10.0.0.120"
IP150_Port = 10000
Poll_Speed = 0.5                            #Seconds (float)
MQTT_IP = "10.0.0.130"
MQTT_Port = 1883
MQTT_KeepAlive = 60                         #Seconds

MQTT_Topic_Subscribe_Control = "Paradox/C/"       #e.g. To arm partition 1: Paradox/C/P1/Arm
                                            #Options are Arm, Disarm, Stay, Sleep (case sensitive!)
Topic_Publish_Events = "Paradox/Events"
Events_Payload_Numeric = "False"
Topic_Subscribe_Control = "Paradox/C/"
Startup_Publish_All_Info = "True"
Startup_Update_All_Labels = "True"
Topic_Publish_Labels = "Paradox/Labels"
Alarm_Model = "ParadoxMG5050"
Alarm_Registry_Map = "ParadoxMG5050"
Alarm_Event_Map = "ParadoxMG5050"

#Global variables
Alarm_Control_Action = 0
Alarm_Control_Partition = 0
Alarm_Control_NewState = ""
Output_FControl_Action = 0
Output_FControl_Number = 0
Output_FControl_NewState = ""
Output_PControl_Action = 0
Output_PControl_Number = 0
Output_PControl_NewState = ""
State_Machine = 0
Polling_Enabled = 1
Debug_Mode = 0

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                print ("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global Alarm_Control_Partition
    global Alarm_Control_NewState
    global Alarm_Control_Action
    global Output_FControl_Number
    global Output_FControl_NewState
    global Output_FControl_Action
    global Output_PControl_Number
    global Output_PControl_NewState
    global Output_PControl_Action
    global Polling_Enabled

    valid_states = ['Arm','Disarm','Sleep','Stay']

    print("MQTT Message: " + msg.topic+" "+str(msg.payload))

    topic = msg.topic

    if MQTT_Topic_Subscribe_Control in msg.topic:
        if "Polling" in msg.topic:
            if "Enable" in msg.topic:
                print "Enable polling message received..."
                Polling_Enabled = 1
            if "Disable" in msg.topic:
                print "Disable polling message received..."
                Polling_Enabled = 0

        elif "C/FO/" in msg.topic:
            try:
                Output_FControl_Number = int((topic.split(MQTT_Topic_Subscribe_Control + 'FO/'))[1].split('/')[0])
                print "Output force control number: ", Output_FControl_Number
                Output_FControl_NewState = (topic.split('/FO/'+str(Output_FControl_Number)+'/'))[1]
                print "Output force control state: ", Output_FControl_NewState
                Output_FControl_Action = 1
            except:
                print "MQTT message received with incorrect structure"

        elif "C/PO/" in msg.topic:
            try:
                Output_PControl_Number = int((topic.split(MQTT_Topic_Subscribe_Control + 'PO/'))[1].split('/')[0])
                print "Output pulse control number: ", Output_PControl_Number
                Output_PControl_NewState = (topic.split('/PO/' + str(Output_PControl_Number) + '/'))[1]
                print "Output pulse control state: ", Output_PControl_NewState
                Output_PControl_Action = 1
            except:
                print "MQTT message received with incorrect structure"
        else:
            try:
                Alarm_Control_Partition = int((topic.split(MQTT_Topic_Subscribe_Control + 'P'))[1].split('/')[0])
                print "Alarm control partition: ", Alarm_Control_Partition
                Alarm_Control_NewState = (topic.split('/P'+str(Alarm_Control_Partition)+'/'))[1]
                print "Alarm control state: ", Alarm_Control_NewState
                Alarm_Control_Action = 1
            except:
                print "MQTT message received with incorrect structure"

def connect_ip150socket(address,port):

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((address, port))
    except Exception, e:
        print "Error connecting to IP module (exiting): " + repr(e)
        sys.exit()

    return s


def getAllLabels(Startup_Publish_All_Info = "False"):

    myAlarm.updateZoneLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/Zones", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllZoneNames().items()))

    myAlarm.updateOutputLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/Outputs", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllOutputNames().items()))

    myAlarm.updateUserLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/Users", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllUserLabels().items()))

    myAlarm.updatePartitionLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/Partitions", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllPartitionLabels().items()))

    myAlarm.updateBusModuleLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/BusModules", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllBusModuleLabels().items()))

    myAlarm.updateWirelessRepeaterLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/WirelessRepeaters", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllWirelessRepeaterLabels().items()))

    myAlarm.updateWirelessKeypadLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/WirelessKeypads", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllWirelessKeypadLabels().items()))

    myAlarm.updateWirelessSirenLabels()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/WirelessSirens", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllWirelessSirenLabels().items()))

    myAlarm.updateSiteName()
    if Startup_Publish_All_Info == "True":
        client.publish(Topic_Publish_Labels + "/SiteNames", ';'.join('{}{}'.format(key, ":" + val) for key, val in myAlarm.eventmap.getAllSiteNames().items()))


    return

class paradox:

    loggedin = 0
    aliveSeq = 0
    alarmName = None
    zoneTotal = 0
    zoneStatus = ['']
    zoneNames = ['']
    zonePartition = None
    partitionStatus = None
    partitionName = None
    Skip_Update_Labels = 0

    def __init__(self, _transport, _encrypted=0, _retries=3, _alarmeventmap="ParadoxMG5050", _alarmregmap="ParadoxMG5050"):
        self.comms = _transport    # instance variable unique to each instance
        self.retries = _retries
        self.encrypted = _encrypted
        self.alarmeventmap = _alarmeventmap
        self.alarmregmap = _alarmregmap

        #MyClass = getattr(importlib.import_module("." + self.alarmmodel + "EventMap", __name__))

        try:
            mod = __import__("ParadoxMap", fromlist=[self.alarmeventmap + "EventMap"])
            self.eventmap = getattr(mod, self.alarmeventmap + "EventMap")
        except Exception, e:
            print "Failed to load Event Map (exiting): ", repr(e)
            sys.exit()

        try:
            mod = __import__("ParadoxMap", fromlist=[self.alarmregmap + "Registers"])
            self.registermap = getattr(mod, self.alarmregmap + "Registers")
        except Exception, e:
            print "Failed to load Register Map (defaulting to not update labels from alarm): ", repr(e)
            self.Skip_Update_Labels = 1



        #self.eventmap = ParadoxMG5050EventMap  # Need to check panel type here and assign correct dictionary!
        #self.registermap = ParadoxMG5050Registers  # Need to check panel type here and assign correct dictionary!

    def skipLabelUpdate(self):
        return self.Skip_Update_Labels

    def saveState(self):
        self.eventmap.save()

    def loadState(self):
        print "Loading previous event states and labels from file"
        self.eventmap.load()

    def login(self, password):              # Construct the login message, 16 byte header +
                                            # 16byte [or multiple] payloading being the password
        print "Logging into alarm system..."

        header = "\xaa"                    # First construct the 16 byte header, starting with 0xaa

        header += bytes(bytearray([len(password)]))    # Add the length of the password which is appended after the header
        header += "\x00\x03"               # No idea what this is

        if self.encrypted == 0:             # Encryption flag
            header += "\x08"               # Encryption off [default for now]
        else:
            header += "\x09"               # Encryption on

        header += "\xf0\x00\x0a"           # No idea what this is, although the fist byte seems like a sequence number
        #header += "\xf0\x00\x0e\x00\x01"    # iParadox initial request

        header = header.ljust(16, '\xee')           # The remained of the 16B header is filled with 0xee

        message = password                 # Add the password as the start of the payload

        # FIXME: Add support for passwords longer than 16 characters
        message = message.ljust(16, '\xee')           # The remainder of the 16B payload is filled with 0xee

        reply = self.readDataRaw(header + message)   # Send message to the alarm panel and read the reply

        if reply[4] == '\x38':
            print "Login to alarm panel successful"
            loggedin = 1
        else:
            loggedin = 0

        header = list(header)

        header[1] = '\x00'
        header[5] = '\xf2'
        header2 = "".join(header)
        self.readDataRaw(header2)

        header[5] = '\xf3'
        header2 = "".join(header)
        reply = self.readDataRaw(header2)

        reply = list(reply)                           # Send "waiting" header until reply is at least 48 bytes in length indicating ready state

        header[1] = '\x25'
        header[3] = '\x04'
        header[5] = '\x00'
        header2 = "".join(header)
        message = '\x72\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        message = self.format37ByteMessage(message)
        reply = self.readDataRaw(header2 + message)

        header[1] = '\x26'
        header[3] = '\x03'
        header[5] = '\xf8'
        header2 = "".join(header)
        message = '\x50\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        message = self.format37ByteMessage(message)
        reply = self.readDataRaw(header2 + message)

        header[1] = '\x25'
        header[3] = '\x04'
        header[5] = '\x00'
        header2 = "".join(header)
        message = '\x5f\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        message = self.format37ByteMessage(message)
        reply = self.readDataRaw(header2 + message)

        header[1] = '\x25'
        header[3] = '\x04'
        header[5] = '\x00'
        header2 = "".join(header)
        message = '\x00\x00\x00\x00\x41\x04\x91\x11\x00\x00\x00\x00\x19\x00\x00\x01\x12\xa5\x02\x02\x3f\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00'
        message = self.format37ByteMessage(message)
        reply = self.readDataRaw(header2 + message)

        header[1] = '\x25'
        header[3] = '\x04'
        header[5] = '\x00'
        header2 = "".join(header)
        message = '\x50\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        message = self.format37ByteMessage(message)
        reply = self.readDataRaw(header2 + message)

        header[1] = '\x25'
        header[3] = '\x04'
        header[5] = '\x00'
        header2 = "".join(header)
        message = '\x50\x00\x0e\x52\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        message = self.format37ByteMessage(message)
        reply = self.readDataRaw(header2 + message)


        return loggedin

    def format37ByteMessage(self, message):
        checksum = 0

        if len(message) % 37 != 0:

            for val in message:                   # Calculate checksum
                checksum += ord(val)

            #print "CS: " + str(checksum)
            while checksum > 255:
                checksum = checksum - (checksum/256)*256

            #print "CS: " + str(checksum)

            message += bytes(bytearray([checksum])) # Add check to end of message

            msgLen = len(message)                 # Pad with 0xee till end of last 16 byte message

            if (msgLen % 16) != 0:
                message = message.ljust((msgLen/16+1)*16, '\xee')

        #print " ".join(hex(ord(i)) for i in message)

        return message

    def updateGenericLabels(self, mapping_dict, destination_dict):

        registers = mapping_dict

        total = sum(1 for x in registers if isinstance(x, int))
        # print "Amount of numeric items in dictionary to read: " + str(total)

        header = registers["Header"]
        skip_next = 0

        for x in range(1, total+1):

            if skip_next == 1:
                skip_next = 0
                continue

            # print "Update generic registers step: " + str(x)

            message = registers[x]["Send"]
            try:
                next_message = registers[x + 1]["Send"]
            except KeyError:
                skip_next = 1
                # print "no next key"

            # print "Current msg " + " ".join(hex(ord(i)) for i in message)
            # print "Next msg    " + " ".join(hex(ord(i)) for i in next_message)

            assert isinstance(message, basestring), "Message to be sent is not a string: %r" % message
            message = message.ljust(36, '\x00')

            #print " ".join(hex(ord(i)) for i in message)

            reply = self.readDataRaw(header + self.format37ByteMessage(message))

            start = registers[x]["Receive"]["Start"]
            finish = registers[x]["Receive"]["Finish"]
            # self.zoneNames.append(reply[start:finish].rstrip()) FIXME: remove all internal zoneNames references and only use the dict
            destination_dict(x, reply[start:finish].rstrip().translate(None, '\x00'))

            if (skip_next == 0) and (message[0:len(next_message)] == next_message):
                # print "Same"
                start = registers[x + 1]["Receive"]["Start"]
                finish = registers[x + 1]["Receive"]["Finish"]
                destination_dict(x + 1, reply[start:finish].rstrip().translate(None, '\x00'))
                skip_next = 1

        return destination_dict

    def updateOutputLabels(self):

        x = self.updateGenericLabels(self.registermap.getOutputLabelRegisters(),
                                     self.eventmap.setOutputName)

        print "Outputs (PGM) detected: "
        print self.eventmap.getAllOutputNames()

        return x

    def updateZoneLabels(self):

        x = self.updateGenericLabels(self.registermap.getZoneLabelRegisters(),
                                     self.eventmap.setZoneName)

        self.zoneTotal = sum(1 for x in self.registermap.getZoneLabelRegisters() if isinstance(x, int))

        print "Zones detected: "
        print self.eventmap.getAllZoneNames()

        return x

    def updatePartitionLabels(self):

        x = self.updateGenericLabels(self.registermap.getPartitionLabelRegisters(),
                                     self.eventmap.setPartitionLabel)

        print "Partitions detected: "
        print self.eventmap.getAllPartitionLabels()

        return x

    def updateUserLabels(self):

        x = self.updateGenericLabels(self.registermap.getUserLabelRegisters(),
                                     self.eventmap.setUserLabel)

        print "Users detected: "
        print self.eventmap.getAllUserLabels()

        return x

    def updateBusModuleLabels(self):

        x = self.updateGenericLabels(self.registermap.getBusModuleLabelRegisters(),
                                     self.eventmap.setBusModuleLabel)

        print "Bus Modules detected: "
        print self.eventmap.getAllBusModuleLabels()

        return x

    def updateWirelessRepeaterLabels(self):

        x = self.updateGenericLabels(self.registermap.getWirelessRepeaterLabelRegisters(),
                                     self.eventmap.setWirelessRepeaterLabel)

        print "Wireless Repeaters detected: "
        print self.eventmap.getAllWirelessRepeaterLabels()

        return x

    def updateWirelessKeypadLabels(self):

        x = self.updateGenericLabels(self.registermap.getWirelessKeypadLabelRegisters(),
                                 self.eventmap.setWirelessKeypadLabel)

        print "Wireless Keypads detected: "
        print self.eventmap.getAllWirelessKeypadLabels()

        return x

    def updateSiteName(self):

        x = self.updateGenericLabels(self.registermap.getSiteNameRegisters(),
                                     self.eventmap.setSiteName)

        print "Site Name(s) detected: "
        print self.eventmap.getAllSiteNames()

        return x

    def updateWirelessSirenLabels(self):

        x = self.updateGenericLabels(self.registermap.getWirelessSirenLabelRegisters(),
                                     self.eventmap.setWirelessSirenLabel)

        print "Wireless Sirens detected: "
        print self.eventmap.getAllWirelessSirenLabels()

        return x

    def testForEvents(self, Events_Payload_Numeric = 0, Debug_Mode = 0):

        reply_amount, headers, messages = self.splitMessage(self.readDataRaw('', Debug_Mode))

        if Debug_Mode >= 1:
            print '.'
            reply = '.'

        if Debug_Mode >= 1 and reply_amount > 1:
            print "Multiple data: " + repr(messages)

        if reply_amount > 0:
            for message in messages:

                if Debug_Mode >= 2:
                    print "Event data: " + " ".join(hex(ord(i)) for i in message)

                if Events_Payload_Numeric == 0:

                    if len(message) > 0:
                        if message[0] == '\xe2' or message[0] == '\xe0':

                            try:

                                event,subevent = self.eventmap.getEventDescription(ord(message[7]), ord(message[8]))

                                reply = "Event:" + event + ";SubEvent:" + subevent

                                if Debug_Mode >= 1:
                                    print reply

                                client.publish(Topic_Publish_Events, reply, qos=0, retain=False)

                            except ValueError:
                                reply = "No register entry for Event: " + str(ord(message[7])) + ", Sub-Event: " + str(ord(message[8]))

                        else:
                            reply = "Unknown event: " + " ".join(hex(ord(i)) for i in message)

                else:

                    reply = "E:" + str(ord(message[7])) + ";SE:" + str(ord(message[8]))

        return reply

    def splitMessage(self, request=''): # FIXME: Make msg a list to handle multiple 37byte replies

        if len(request) > 0:

            requests = request.split('\xaa')

            del requests[0]

            for i, val in enumerate(requests):
                requests[i] = '\xaa' + val
                #print "Request seq " + str(i) + ": " + " ".join(hex(ord(i)) for i in requests[i])

            #print "Request(s): ", requests

            replyAmount = len(requests)
            x = replyAmount

            headers = []*replyAmount
            messages = []*replyAmount

            #print "Reply amount: ", x

            x -= 1

            #print "Going into while with first element: " + requests[0]

            while x >= 0:
                #print "Working on number " + str(x) + ": " + " ".join(hex(ord(i)) for i in requests[i])
                if len(requests[x]) > 16:
                    headers.append(requests[x][:16])
                    messages.append(requests[x][16:])

                elif len(requests[x]) == 16:
                    headers.append(requests[x][:16])
                    messages.append([])
                    #return headers, ''
                x -= 1

            return replyAmount, headers, messages

        else:
            return 0, [], []

    def sendData(self, request=''):

        if len(request) > 0:
            self.comms.send(request)
            time.sleep(0.25)

    def readDataRaw(self, request='', Debug_Mode = 0):

        #self.testForEvents()                # First check for any pending events received

        tries = self.retries

        while tries > 0:
            try:
                if Debug_Mode >= 2:
                    print str(len(request)) + "->   " + " ".join(hex(ord(i)) for i in request)
                self.sendData(request)
                inc_data = self.comms.recv(1024)
                if Debug_Mode >= 2:
                    print str(len(inc_data)) + "<-   " + " ".join(hex(ord(i)) for i in inc_data)
                tries = 0

            except socket.timeout, e:
                err = e.args[0]
                if err == 'timed out':
                    tries = 0
                    return ''
                    # sleep(1)
                    #print 'Receive timed out, ret'
                    #continue
                else:
                    print "Error reading data from IP module, retrying again... (" + str(tries) + "): " + repr(e)
                    tries -= 1
                    time.sleep(2)
            except socket.error, e:
                print "Unknown error on socket connection, retrying... ", repr(e)
                tries -= 1
                if tries == 0:
                    print "Failure, disconnected."
                    sys.exit(1)
            else:
                if len(inc_data) == 0:
                    print 'Socket connection closed by remote host'
                    sys.exit(0)
                else:
                    return inc_data

    def readDataStruct37(self, inputData=''):  # Sends data, read input data and return the Header and Message

        rawdata = self.readDataRaw(inputData)

        #Extract the header and message
        if len(rawdata) > 16:
            header = rawdata[:16]
            message = rawdata[17:]

        return header, message

    def controlGenericOutput(self, mapping_dict, output, state):

        registers = mapping_dict

        header = registers["Header"]

        if Debug_Mode >= 1:
            print "Sending generic Output Control: Output: " + str(output) + ", State: " + state

        message = registers[output][state]

        assert isinstance(message, basestring), "Message to be sent is not a string: %r" % message
        message = message.ljust(36, '\x00')

        #print " ".join(hex(ord(i)) for i in message)

        reply = self.readDataRaw(header + self.format37ByteMessage(message))

        return

    def controlPGM(self, pgm, state="OFF"):

        #print state.upper()

        assert (isinstance(pgm, int) and pgm >=0 and pgm <= 16), "Problem with PGM number: %r" % str(pgm)
        assert (isinstance(pgm, int) and pgm >=0 and pgm <= 16), "Problem with PGM number: %r" % str(pgm)
        assert isinstance(state, basestring), "State given is not a string: %r" % str(state)
        assert (state.upper() == "ON" or state.upper() == "OFF"), "State is not given correctly: %r" % str(state)

        self.controlGenericOutput(self.registermap.getControlOutputRegisters(), pgm, state.upper())

        return

    def controlGenericAlarm(self, mapping_dict, partition, state):
        registers = mapping_dict

        header = registers["Header"]

        print "Sending generic Alarm Control: Partition: " + str(partition) + ", State: " + state

        message = registers[partition][state]

        assert isinstance(message, basestring), "Message to be sent is not a string: %r" % message
        message = message.ljust(36, '\x00')

        # print " ".join(hex(ord(i)) for i in message)

        reply = self.readDataRaw(header + self.format37ByteMessage(message))

        return

    def controlAlarm(self, partition=1, state="Disarm"):

        assert (isinstance(partition, int) and partition >= 0 and partition <= 16), "Problem with partition number: %r" % str(partition)
        assert isinstance(state, basestring), "State given is not a string: %r" % str(state)
        assert (state.upper() in self.registermap.getAlarmRegisters()[partition]), "State is not given correctly: %r" % str(state)

        self.controlGenericAlarm(self.registermap.getAlarmRegisters(), partition, state.upper())

        return

    def disconnect(self):

        header = "\xaa\x00\x00\x03\x51\xff\x00\x0e\x00\x01\xee\xee\xee\xee\xee\xee"

        self.readDataRaw(header)

    def keepAlive(self):

        header = "\xaa\x25\x00\x04\x08\x00\x00\x14\xee\xee\xee\xee\xee\xee\xee\xee"

        message = "\x50\x00\x80"

        message += bytes(bytearray([self.aliveSeq]))

        message += "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

        self.sendData(header + message)

        self.aliveSeq += 1
        if self.aliveSeq > 6:
            self.aliveSeq = 0

    def walker(self, ):
        self.zoneTotal = Zone_Amount

        print "Reading (" + str(Zone_Amount) + ") zone names..."

        header = "\xaa\x25\x00\x04\x08\x00\x00\x14\xee\xee\xee\xee\xee\xee\xee\xee"

        for x in range(16, 65535, 32):
            message = "\xe2\x00"
            zone = x
            zone = list(struct.pack("H", zone))
            swop = zone[0]
            zone[0] = zone[1]
            zone[1] = swop

            temp = "".join(zone)
            #print " ".join(hex(ord(i)) for i in temp)
            message += temp

            message += "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            # print " ".join(hex(ord(i)) for i in message)
            reply = self.readDataRaw(header + self.format37ByteMessage(message))

            print reply
            #print " ".join(hex(ord(i)) for i in reply)

            time.sleep(0.3)

        return


if __name__ == '__main__':

    State_Machine = 0

    while True:


        # -------------- Read Config file ----------------
        if State_Machine <= 0:

            print "Reading config.ini file..."

            try:

                Config = ConfigParser.ConfigParser()
                Config.read("config.ini")
                Alarm_Model = Config.get("Alarm", "Alarm_Model")
                Alarm_Registry_Map = Config.get("Alarm", "Alarm_Registry_Map")
                Alarm_Event_Map = Config.get("Alarm", "Alarm_Event_Map")
                Zone_Amount = int(Config.get("Alarm", "Zone_Amount"))
                if Zone_Amount % 2 != 0:
                    Zone_Amount += 1
                passw = Config.get("IP150", "Password")
                user = Config.get("IP150", "Pincode")
                IP150_IP = Config.get("IP150", "IP")
                IP150_Port = int(Config.get("IP150", "IP_Software_Port"))
                MQTT_IP = Config.get("MQTT Broker", "IP")
                MQTT_Port = int(Config.get("MQTT Broker", "Port"))

                Topic_Publish_Events = Config.get("MQTT Topics", "Topic_Publish_Events")
                Events_Payload_Numeric = int(Config.get("MQTT Topics", "Events_Payload_Numeric"))
                Topic_Subscribe_Control = Config.get("MQTT Topics", "Topic_Subscribe_Control")
                Startup_Publish_All_Info = Config.get("MQTT Topics", "Startup_Publish_All_Info")
                Topic_Publish_Labels = Config.get("MQTT Topics", "Topic_Publish_Labels")

                Startup_Update_All_Labels = Config.get("Application", "Startup_Update_All_Labels")
                Debug_Mode = int(Config.get("Application", "Debug_Mode"))

                print "config.ini file read successfully"
                State_Machine += 1

            except Exception, e:
                print "******************* Error reading config.ini file (will use defaults): " + repr(e)
                State_Machine = 1

                attempts = 3
        # -------------- MQTT ----------------
        elif State_Machine == 1:

            try:

                print "Attempting connection to MQTT Broker: " + MQTT_IP + ":" + str(MQTT_Port)
                client = mqtt.Client()
                client.on_connect = on_connect
                client.on_message = on_message

                client.connect(MQTT_IP, MQTT_Port, MQTT_KeepAlive)

                client.loop_start()

                client.subscribe(MQTT_Topic_Subscribe_Control + "#")

                print "MQTT client subscribed to control messages on topic: " + MQTT_Topic_Subscribe_Control + "#"

                State_Machine += 1

            except Exception, e:

                print "MQTT connection error (" + str(attempts) + ": " + repr(e)
                time.sleep(Poll_Speed * 5)
                attempts -= 1

                if attempts < 1:
                    print "Error within State_Machine: " + str(State_Machine) + ": " + repr(e)
                    State_Machine -= 1
                    print "Going to State_Machine: " + str(State_Machine)

            attempts = 5

        # -------------- Login to IP Module ----------------
        elif State_Machine == 2 and Polling_Enabled == 1:

            try:

                comms = connect_ip150socket(IP150_IP, IP150_Port)

                myAlarm = paradox(comms, 0, 3, Alarm_Event_Map, Alarm_Registry_Map)

                myAlarm.login(passw)

                State_Machine += 1

            except Exception, e:

                print "Error attempting login to IP module (" + str(attempts) + ": " + repr(e)
                time.sleep(Poll_Speed * 5)
                attempts -= 1

                if attempts < 1:
                    print "Error within State_Machine: " + str(State_Machine) + ": " + repr(e)
                    State_Machine -= 1
                    print "Going to State_Machine: " + str(State_Machine)

            attempts = 3
        # -------------- Reading Labels ----------------
        elif State_Machine == 3 and Polling_Enabled == 1:

            try:

                if Startup_Update_All_Labels == "True" and myAlarm.skipLabelUpdate() == 0:

                    print "Updating all labels from alarm"
                    getAllLabels(Startup_Publish_All_Info)

                    State_Machine += 1
                    print "Listening for events..."

                else:

                    State_Machine += 1
                    print "Listening for events..."

            except Exception, e:

                print "Error reading labels: " + repr(e)
                time.sleep(Poll_Speed * 5)
                attempts -= 1

                if attempts < 1:
                    print "Error within State_Machine: " + str(State_Machine) + ": " + repr(e)
                    State_Machine -= 1
                    print "Going to State_Machine: " + str(State_Machine)

            Alarm_Control_Action = 0
            attempts = 3
            # -------------- Checking Events & Actioning Controls ----------------
        elif State_Machine == 4 and Polling_Enabled == 1:

            try:

                # Test for new events & publish to broker
                myAlarm.testForEvents(Events_Payload_Numeric, Debug_Mode)

                # Test for pending Alarm Control
                if Alarm_Control_Action == 1:
                    myAlarm.login(passw)
                    myAlarm.controlAlarm(Alarm_Control_Partition, Alarm_Control_NewState)
                    Alarm_Control_Action = 0

                # Test for pending Force Output Control
                if Output_FControl_Action == 1:
                    myAlarm.login(passw)
                    myAlarm.controlPGM(Output_FControl_Number, Output_FControl_NewState)
                    Output_FControl_Action = 0

                # Test for pending Pulse Output Control
                if Output_PControl_Action == 1:
                    myAlarm.login(passw)
                    myAlarm.controlPGM(Output_PControl_Number, Output_PControl_NewState)
                    time.sleep(0.5)
                    if Output_PControl_NewState.upper() == "ON":
                        myAlarm.controlPGM(Output_PControl_Number, "OFF")
                    else:
                        myAlarm.controlPGM(Output_PControl_Number, "ON")
                    Output_PControl_Action = 0

                time.sleep(Polling_Enabled)

                myAlarm.keepAlive()

            except Exception, e:

                print "Error during normal poll: " + repr(e) + ", Attempt: " + str(attempts)
                time.sleep(Poll_Speed * 5)
                attempts -= 1

                if attempts < 1:
                    print "Error within State_Machine: " + str(State_Machine) + ": " + repr(e)
                    State_Machine -= 1
                    print "Going to State_Machine: " + str(State_Machine)


        elif Polling_Enabled == 0 and State_Machine <= 4:

            print "Disabling polling & disconnecting from Alarm"
            comms.close()
            State_Machine = 10

            print "Polling Disabled"

        elif Polling_Enabled == 1:
            State_Machine = 2

        elif State_Machine == 10:

            time.sleep(3)
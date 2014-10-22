# Ben Goldberg and Louie Brann
# File Transfer Utility

import sys, os
import socket, select
import subprocess
import pickle
import copy
import math
import re


def getMissingPackets(fileBuffer):
    """
    Input: Array of packets
    Output: Bitstring, if ith char is 0, that packet is missing.
                       if ith char is 1, that packet is present.
    """
    missingPackets = ""
    
    for packet in fileBuffer:
        if packet == None:
            missingPackets += "0"
        else:
            missingPackets += "1"

    return missingPackets

def getRTT(destName):
    """ 
    Input: String name of host to ping
    Output: Average of 3 roundtrip times to communicate with that host, in seconds
    """
    pingMsg = "ping -c 3 " + destName

    process = subprocess.Popen(pingMsg, shell=True, stdout=subprocess.PIPE)
    pingResult = process.communicate()[0]
    rttAvgMs = float(pingResult.split(" ")[-2].split("/")[1])

    return float(rttAvgMs)/float(1000)

def main(argv):
    udpPort  = 44000
    tcpPort  = 44001
    packetSize = 1024
    packetsPerWindow = 512
    windowSize = packetsPerWindow * packetSize
    
    #Receiver
    if len(argv) == 0:

        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpSocket.bind(("", udpPort))
        udpSocket.setblocking(0)

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.bind(("", tcpPort))
        tcpSocket.listen(1)

        #TCP: Accept incoming handshake 
        establishedTcp, addr = tcpSocket.accept()

        rtt = getRTT(addr[0])

        currentWindow = 0
        numWindows = 2
        while currentWindow < numWindows:

            establishedTcp.setblocking(1)

            fileMetadataPickled = establishedTcp.recv(packetSize)
            if not fileMetadataPickled:
                print "no data"
                sys.exit(2)
            fileMetadata = pickle.loads(fileMetadataPickled)

            # We want future recv calls to be non-blocking
            establishedTcp.setblocking(0)

        
            #Make data-structures to put data from udpSocket
            fileName, numPackets, numWindows = fileMetadata
            fileBuffer = [None] * numPackets
            udpTimeoutCounter = 0
            while True:
                # If there is a packet, receive it

                udpReady = select.select([udpSocket], [], [], rtt)

                if udpReady[0]:
                    currentPacket, addr = udpSocket.recvfrom(packetSize)

                    # Put packet data into file buffer
                    packetIndex = int(currentPacket[:13])
                    
                    packetData = currentPacket[14:]

                    fileBuffer[packetIndex] = copy.deepcopy(packetData)

                    udpTimeoutCounter = 0
                    continue

                # If we've only timed out once or twice, start loop over
                udpTimeoutCounter += 1
                if udpTimeoutCounter < 3:
                    continue

                # If we've timed out more than twice, send missing packets
                #check which packets are missing
                missingPackets = getMissingPackets(fileBuffer)
                establishedTcp.send(missingPackets)

                #     #if we have received all data, break and close connections
                if "0" not in missingPackets:
                    currentWindow += 1
                    break

            # Close all connections
            # socket.shutdown(tcpSocket)
            # socket.close(tcpSocket)
            #socket.shutdown(establishedTcp)
            #socket.close(establishedTcp)
            #socket.close(udpSocket)

            outString = "".join(fileBuffer)

            if currentWindow - 1 == 0:
                outFile = open(fileName, 'w')
            else:
                outFile = open(fileName, 'a')

            outFile.write(outString)

    #Sender
    else:
        #parse command line inputs
        if len(argv) == 2:
            source = argv[0]
            fileName = source[source.find(":") + 1:]

            dest = argv[1]
            colonPos = dest.find(":")
            destFileName = fileName
            destHostname = dest[0:colonPos]
            if colonPos != len(dest) - 1:
                destFileName = dest[colonPos+1:]
            elif colonPos == -1:
                print "No destHostname specified."
            destIP = socket.gethostbyname(destHostname)
        else:
            print 'ftu.py <source> <dest>'
            sys.exit(2)
        
        
        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.connect((destIP, tcpPort))

        #Open file and put data into dataToSend
        inFile = open(fileName, 'r')
        fileSize = os.path.getsize(fileName)
        numWindows = int(math.ceil(float(fileSize) / float(windowSize)))

        dataToSend = [None] * numWindows
        for i in range(numWindows):
            dataToSend = inFile.read(windowSize)

            # Split window into packetsToSend
            stepSize = packetSize - 14;
            numPackets = int(math.ceil(float(len(dataToSend))/ float(stepSize)))
            packetsToSend = [None] * numPackets
            for j in range(numPackets):
                indexStr = str(j)
                indexStr = "0" * (13 - len(indexStr)) + indexStr
                dataOffset = j * stepSize
                packetsToSend[j] = indexStr + " " + dataToSend[dataOffset:dataOffset + stepSize]

            #TCP: Send fileName and numPackets to send
            fileMetadata = (destFileName, numPackets, numWindows)
            fileMetadataPickled = pickle.dumps(fileMetadata)
            tcpSocket.send(fileMetadataPickled)

            # Go through entire file, sending all packets until known to be transferred
            packetCounter = 0
            missingPackets = "0" * numPackets
            bufSize = packetsPerWindow + packetsPerWindow/64
            while missingPackets != "1" * numPackets:

                #UDP: send pickled data
                if missingPackets[packetCounter] == "0":
                    udpSocket.sendto(packetsToSend[packetCounter], (destIP,udpPort))

                # Increment packet counter
                packetCounter += 1

                # If all packets are sent, send all done message
                if packetCounter == numPackets:

                    # Receive list of missed packets
                    missingPackets = tcpSocket.recv(packetsPerWindow + packetsPerWindow/64)

                    numMissing = missingPackets.count("0")
                    print "%" + " done: " + str(float(i)/float(numWindows))

                    # Reset for next set of packets to send
                    packetCounter = 0



if __name__ == "__main__":
    main(sys.argv[1:]) 

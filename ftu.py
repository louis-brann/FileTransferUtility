# Ben Goldberg and Louie Brann
# File Transfer Utility

import sys, os
import socket, select
import pickle
import copy
import math


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

def main(argv):
    udpPort  = 44000
    tcpPort  = 44001
    louieIP  = "134.173.42.215"
    benIP    = "134.173.42.9"
    filePath = "/Users/Guest/Desktop/FileTransferUtility/random.txt"
    fileName = "random.txt"
    allDone  = False
    packetSize = 1024
    
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

        fileMetadataPickled = establishedTcp.recv(packetSize)
        if not fileMetadataPickled:
            print "no data"
            sys.exit(2)
        fileMetadata = pickle.loads(fileMetadataPickled)
        print fileMetadata

        # We want future recv calls to be non-blocking
        establishedTcp.setblocking(0)

        #Make datastructures to put data from udpSocket
        fileName, numPackets = fileMetadata
        fileBuffer = [None] * numPackets
        while True:
            # If there is a packet, receive it
            udpReady = select.select([udpSocket], [], [], .01)
            if udpReady[0]:
                currentPacket, addr = udpSocket.recvfrom(packetSize)

                # Put packet data into file buffer
                packetIndex = int(currentPacket[:13])
                packetData = currentPacket[14:]
                fileBuffer[packetIndex] = copy.deepcopy(packetData)

            # Check for done signal
            tcpReady = select.select([establishedTcp], [], [], .01)
            if tcpReady[0]:
                data = establishedTcp.recv(packetSize)

                #check which packets are missing
                missingPackets = getMissingPackets(fileBuffer)

                #send this information to sender as bitset
                missingPacketsPickled = pickle.dumps(missingPackets)
                establishedTcp.send(missingPacketsPickled)

                #if we have received all data, break and close connections
                if "0" not in missingPackets:
                    break

        # Close all connections
        # socket.shutdown(tcpSocket)
        # socket.close(tcpSocket)
        #socket.shutdown(establishedTcp)
        #socket.close(establishedTcp)
        #socket.close(udpSocket)

        outString = pickle.loads("".join(fileBuffer))

        outFile = open(fileName, 'wb')
        outFile.write(outString)

    #Sender
    else:
        #parse command line inputs
        if len(argv) == 2:
            source = argv[0]
            dest = argv[1]
        else:
            print 'ftu.py <source> <dest>'
            sys.exit(2)
        
        
        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.connect((benIP, tcpPort))

        #Open file and put data into dataToSend
        inFile = open(fileName, 'r')
        dataToSend = inFile.read()
        dataToSendPickled = pickle.dumps(dataToSend)

        # Get packets to send
        stepSize = packetSize - 14;
        numPackets = int(math.ceil(float(len(dataToSendPickled))/ float(stepSize)))
        packetsToSend = [None] * numPackets
        for i in range(numPackets):
            indexStr = str(i)
            indexStr = "0" * (13 - len(indexStr)) + indexStr
            dataOffset = i * stepSize
            packetsToSend[i] = indexStr + " " + dataToSendPickled[dataOffset:dataOffset + stepSize]

        #TCP: Send fileName and numPackets to send
        fileMetadata = (fileName, numPackets)
        fileMetadataPickled = pickle.dumps(fileMetadata)
        tcpSocket.send(fileMetadataPickled)

        # Go through entire file, sending all packets until known to be transferred
        packetCounter = 0
        missingPackets = "0" * numPackets
        while missingPackets != "1" * numPackets:
            #UDP: send pickled data
            if missingPackets[packetCounter] == "0":
                udpSocket.sendto(packetsToSend[packetCounter], (benIP,udpPort))

            # Increment packet counter
            packetCounter += 1

            # If all packets are sent, send all done message
            if packetCounter == numPackets:
                tcpSocket.send("All done")

                # Receive list of missed packets
                missingPacketsPickled = tcpSocket.recv(packetSize)
                missingPackets = pickle.loads(missingPacketsPickled)

                numMissing = missingPackets.count("0")
                print "%" + "done: " + str(numMissing/numPackets)

                # Reset for next set of packets to send
                packetCounter = 0



if __name__ == "__main__":
    main(sys.argv[1:]) 
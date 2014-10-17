# Ben Goldberg and Louie Brann
# File Transfer Utility

import socket
import pickle
import copy
import sys, os
import math
import select

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

def parseMissingPackets(packetsToSend, missingPackets):
    """
    Inputs: Array of packets we already sent
            Bit string denoting which packets we missed
    Outputs: An array of packets that need to be resent
    """
    return [ packetsToSend[i] for i in range(len(missingPackets)) if missingPackets[i]=="0" ]

def main(argv):
    udpPort  = 44000
    tcpPort  = 44001
    louieIP  = "134.173.42.215"
    benIP    = "134.173.42.9"
    filePath = "/Users/Guest/Desktop/FileTransferUtility/example.txt"
    fileName = "example.txt"
    allDone  = False
    packetSize = 1024
    
    #Receiver
    if len(argv) == 0:

        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpSocket.bind(("", udpPort))

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.bind(("", tcpPort))
        tcpSocket.setblocking(0)
        tcpSocket.listen(1)

        #TCP: Accept incoming handshake 
        establishedTcp, addr = tcpSocket.accept()

        fileMetadataPickled = establishedTcp.recv(packetSize)
        if not fileMetadataPickled:
            print "no data"
        fileMetadata = pickle.loads(fileMetadataPickled)
        print fileMetadata

        #Make datastructures to put data from udpSocket
        fileName, fileSize = fileMetadata
        numPackets = int(math.ceil(float(fileSize) / float(packetSize)))
        fileBuffer = [None] * numPackets
        while True:
            # Receive packet
            currentPacketPickled, addr = udpSocket.recvfrom(packetSize)
            currentPacket = pickle.loads(currentPacketPickled)

            # Put packet data into file buffer
            packetIndex, packetDataPickled = currentPacket
            packetData = pickle.dumps(packetDataPickled)
            fileBuffer[packetIndex] = copy.deepcopy(packetData)

            # Check for done signal
            ready = select.select([tcpSocket], [], [], .01)
            if ready[0]:
                data = tcpSocket.recv(packetSize)
                allDone = 1

            # If we receive "done" signal
            if allDone:
                #check which packets are missing
                missingPackets = checkMissingPackets(fileBuffer)

                #send this information to sender as bitset
                missingPacketsPickled = pickle.dumps(missingPackets)
                tcpSocket.send(missingPacketsPickled)

                #if we have received all data, break and close connections
                if int(missingPackets) == 0:
                    break

        # Close all connections
        socket.shutdown(tcpSocket)
        socket.close(tcpSocket)
        socket.close(udpSocket)

        print fileBuffer

        outFile = open(fileName, 'wb')
        outFile.write("".join(fileBuffer))

    #Sender
    else:
        # #parse command line inputs
        # if len(argv) == 2:
        #     source = argv[0]
        #     dest = argv[1]
        # else:
        #     print 'ftu.py <source> <dest>'
        #     sys.exit(2)
        
        
        #make UDP socket
        udpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #make TCP socket
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSocket.connect((benIP, tcpPort))

        #get filesize
        fileSize = os.path.getsize(filePath)
        fileMetadata = (fileName, fileSize)

        #TCP: Send fileName and fileSize
        fileMetadataPickled = pickle.dumps(fileMetadata)
        tcpSocket.send(fileMetadataPickled)

        #Open file and put data into dataToSend
        inFile = open(fileName, 'r')
        dataToSend = inFile.read()

        # Prepickle all data
        dataToSendPickled = pickle.dumps(dataToSend)
        packetsToSend = [(i, dataToSendPickled[i:i + packetSize]) for i in range(0, len(dataToSendPickled), packetSize)]

        # Go through entire file, sending all packets until known to be transferred
        numPackets = int(math.ceil(float(fileSize) / float(packetSize)))
        packetCounter = 0
        while True:

            #UDP: send pickled data
            packetPickled = pickle.dumps(packetsToSend[packetCounter])
            udpSocket.sendto(packetPickled, (benIP,udpPort))

            # Increment packet index
            packetCounter += 1 

            # If all packets are sent, send all done message
            if packetCounter + 1 == len(packetsToSend):
                tcpSocket.send("All done")

                # Receive list of missed packets
                missingPacketsPickled = tcpSocket.recv(packetSize)
                missingPackets = pickle.loads(missingPacketsPickled)

                # Parse missing packets 
                packetsToSend = parseMissingPackets(packetsToSend, missingPackets)

                # If we missed no packets, break
                if len(packetsToSend) == 0:
                    break

        # Close all connections
        socket.shutdown(tcpSocket)
        socket.close(tcpSocket)
        socket.close(udpSocket)



if __name__ == "__main__":
    main(sys.argv[1:]) 
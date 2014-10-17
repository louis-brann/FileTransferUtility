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
        fileName, fileSize = fileMetadata
        numPackets = int(math.ceil(float(fileSize) / float(packetSize)))
        fileBuffer = [None] * numPackets
        while True:
            print "=== TOP ==="
            # If there is a packet, receive it
            ready = select.select([udpSocket], [], [], .01)
            if ready[0]:
                print "received UDP packet"
                currentPacketPickled, addr = udpSocket.recvfrom(2*packetSize)
                currentPacket = pickle.loads(currentPacketPickled)

                # Put packet data into file buffer
                packetIndex, packetData = currentPacket
                print "packetData " + str(packetData)
                fileBuffer[packetIndex] = copy.deepcopy(packetData)

            # Check for done signal
            ready = select.select([establishedTcp], [], [], .01)
            if ready[0]:
                print "received all done"
                data = establishedTcp.recv(packetSize)
                print "data: " + str(data)

                # We know the sender is done sending
            #     allDone = 1

            # # If the sender is done sending
            # if allDone:
            #     # Reset allDone for next round
            #     allDone = 0

                #check which packets are missing
                missingPackets = getMissingPackets(fileBuffer)
                print "Missing packets: " + str(missingPackets)

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

        # Get packets to send
        packetsToSend = [(i, dataToSend[i:i + packetSize - ]) for i in range(0, len(dataToSend), packetSize)]

        # Go through entire file, sending all packets until known to be transferred
        packetCounter = 0
        while True:
            print "packetCounter " + str(packetCounter)
            print "len(packetsToSend) " + str(len(packetsToSend))
            #UDP: send pickled data
            packetPickled = pickle.dumps(packetsToSend[packetCounter])
            udpSocket.sendto(packetPickled, (benIP,udpPort))

            # Increment packet counter
            packetCounter += 1

            # If all packets are sent, send all done message
            if packetCounter == len(packetsToSend):
                tcpSocket.send("All done")

                # Receive list of missed packets
                missingPacketsPickled = tcpSocket.recv(packetSize)
                missingPackets = pickle.loads(missingPacketsPickled)

                # Parse missing packets 
                packetsToSend = parseMissingPackets(packetsToSend, missingPackets)

                # Reset for next set of packets to send
                packetCounter = 0

                # If we missed no packets, break
                if len(packetsToSend) == 0:
                    break



if __name__ == "__main__":
    main(sys.argv[1:]) 